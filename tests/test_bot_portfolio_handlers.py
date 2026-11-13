import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src import bot


class TestPortfolioHandlers(unittest.IsolatedAsyncioTestCase):
    chat_id = 123

    def setUp(self):
        self.context = SimpleNamespace(user_data={}, args=[])
        self.load_portfolio = patch("src.bot.load_portfolio", return_value=[])
        self.add_position = patch("src.bot.add_position")
        self.update_entry_price = patch("src.bot.update_entry_price", return_value=True)
        self.update_stop_loss = patch("src.bot.update_stop_loss", return_value=True)
        self.update_take_profit = patch("src.bot.update_take_profit", return_value=True)
        self.load_archived_portfolio = patch("src.bot.load_archived_portfolio", return_value=[])
        self.mock_load_portfolio = self.load_portfolio.start()
        self.mock_add_position = self.add_position.start()
        self.mock_update_entry_price = self.update_entry_price.start()
        self.mock_update_stop_loss = self.update_stop_loss.start()
        self.mock_update_take_profit = self.update_take_profit.start()
        self.mock_load_archived_portfolio = self.load_archived_portfolio.start()
        self.addCleanup(self.load_portfolio.stop)
        self.addCleanup(self.add_position.stop)
        self.addCleanup(self.update_entry_price.stop)
        self.addCleanup(self.update_stop_loss.stop)
        self.addCleanup(self.update_take_profit.stop)
        self.addCleanup(self.load_archived_portfolio.stop)

    def callback_update(self, data, chat_id=None):
        message = SimpleNamespace(
            chat_id=chat_id or self.chat_id,
            reply_text=AsyncMock(return_value=SimpleNamespace(message_id=500))
        )
        query = SimpleNamespace(
            data=data,
            message=message,
            answer=AsyncMock()
        )
        return SimpleNamespace(
            callback_query=query,
            effective_chat=SimpleNamespace(id=chat_id or self.chat_id),
            message=None
        ), message

    def price_update(self, text, reply_to_id=None, chat_id=None):
        message = SimpleNamespace(
            text=text,
            chat_id=chat_id or self.chat_id,
            reply_to_message=SimpleNamespace(message_id=reply_to_id) if reply_to_id else None,
            reply_text=AsyncMock(return_value=SimpleNamespace(message_id=501))
        )
        return SimpleNamespace(
            message=message,
            effective_chat=SimpleNamespace(id=chat_id or self.chat_id),
            callback_query=None
        ), message

    async def begin_price_flow(self, callback_data):
        update, message = self.callback_update(callback_data)
        await bot.callback_button_handler(update, self.context)
        self.assertEqual(len(message.reply_text.await_args_list), 2)
        cancel_keyboard = message.reply_text.await_args_list[1].kwargs["reply_markup"]
        self.assertEqual(cancel_keyboard.inline_keyboard[0][0].callback_data, "port_cancel_pending")
        return message.reply_text.await_args_list[0]

    async def test_buy_and_sell_price_flows_add_the_selected_direction(self):
        for direction in ("BUY", "SELL"):
            with self.subTest(direction=direction):
                prompt = await self.begin_price_flow(f"port_{direction.lower()}_AAPL")
                pending = self.context.user_data["pending_portfolio"]
                self.assertEqual(pending["direction"], direction)
                self.assertEqual(pending["chat_id"], self.chat_id)
                self.assertEqual(pending["prompt_message_id"], 500)
                self.assertTrue(prompt.kwargs["reply_markup"].force_reply)

                self.mock_add_position.return_value = {
                    "ticker": "AAPL",
                    "direction": direction
                }
                update, _ = self.price_update("182.50", reply_to_id=500)
                await bot.portfolio_input_handler(update, self.context)

                self.mock_add_position.assert_called_with("AAPL", direction, 182.5)
                self.assertNotIn("pending_portfolio", self.context.user_data)
                self.mock_add_position.reset_mock()

    async def test_edit_flow_updates_entry_price_only_on_prompt_reply(self):
        self.mock_load_portfolio.return_value = [{"ticker": "AAPL"}]
        await self.begin_price_flow("port_edit_AAPL")

        unrelated, _ = self.price_update("185.25")
        await bot.portfolio_input_handler(unrelated, self.context)
        self.mock_update_entry_price.assert_not_called()
        self.assertIn("pending_portfolio", self.context.user_data)

        reply, _ = self.price_update("185,25", reply_to_id=500)
        await bot.portfolio_input_handler(reply, self.context)
        self.mock_update_entry_price.assert_called_once_with("AAPL", 185.25)
        self.assertNotIn("pending_portfolio", self.context.user_data)

    async def test_invalid_price_keeps_flow_active_with_a_new_reply_target(self):
        await self.begin_price_flow("port_buy_AAPL")
        invalid, message = self.price_update("not a price", reply_to_id=500)

        await bot.portfolio_input_handler(invalid, self.context)

        self.mock_add_position.assert_not_called()
        self.assertIn("pending_portfolio", self.context.user_data)
        self.assertEqual(self.context.user_data["pending_portfolio"]["prompt_message_id"], 501)
        message.reply_text.assert_awaited_once()

        valid, _ = self.price_update("180", reply_to_id=501)
        self.mock_add_position.return_value = {"ticker": "AAPL", "direction": "BUY"}
        await bot.portfolio_input_handler(valid, self.context)
        self.mock_add_position.assert_called_once_with("AAPL", "BUY", 180.0)

    async def test_message_in_another_chat_cannot_complete_pending_flow(self):
        await self.begin_price_flow("port_buy_AAPL")
        other_chat, message = self.price_update("180", reply_to_id=500, chat_id=456)

        await bot.portfolio_input_handler(other_chat, self.context)

        self.mock_add_position.assert_not_called()
        message.reply_text.assert_not_awaited()
        self.assertIn("pending_portfolio", self.context.user_data)

        self.mock_add_position.return_value = {"ticker": "AAPL", "direction": "BUY"}
        original_chat, _ = self.price_update("180", reply_to_id=500)
        await bot.portfolio_input_handler(original_chat, self.context)

        self.mock_add_position.assert_called_once_with("AAPL", "BUY", 180.0)
        self.assertNotIn("pending_portfolio", self.context.user_data)

    async def test_portfolio_callback_in_another_chat_does_not_clear_pending_flow(self):
        await self.begin_price_flow("port_buy_AAPL")
        other_chat, message = self.callback_update("port_cancel_pending", chat_id=456)

        await bot.callback_button_handler(other_chat, self.context)

        self.assertIn("pending_portfolio", self.context.user_data)
        self.assertEqual(self.context.user_data["pending_portfolio"]["chat_id"], self.chat_id)
        self.assertIn("un'altra chat", message.reply_text.await_args.args[0])

    async def test_cancel_callback_clears_pending_flow(self):
        await self.begin_price_flow("port_buy_AAPL")
        update, message = self.callback_update("port_cancel_pending")

        await bot.callback_button_handler(update, self.context)

        self.assertNotIn("pending_portfolio", self.context.user_data)
        self.assertEqual(message.reply_text.await_args.args[0], "Operazione annullata.")

    async def test_scan_result_registration_prompts_for_direction(self):
        update, message = self.callback_update("port_add_prompt_NVDA")

        await bot.callback_button_handler(update, self.context)

        prompt = message.reply_text.await_args
        self.assertIn("Registra NVDA", prompt.args[0])
        keyboard = prompt.kwargs["reply_markup"].inline_keyboard
        self.assertEqual([button.callback_data for button in keyboard[0]], [
            "port_buy_NVDA",
            "port_sell_NVDA"
        ])
        self.assertEqual(keyboard[1][0].callback_data, "port_cancel_pending")
        self.assertNotIn("pending_portfolio", self.context.user_data)

    async def test_archive_and_delete_callbacks_update_position(self):
        with patch("src.bot.archive_position", return_value=True) as archive, \
                patch("src.bot.remove_position", return_value=True) as remove, \
                patch("src.bot.portfolio_command", new_callable=AsyncMock) as show_portfolio:
            archive_update, archive_message = self.callback_update("port_archive_AAPL")
            await bot.callback_button_handler(archive_update, self.context)

            archive.assert_called_once_with("AAPL")
            self.assertIn("archiviato", archive_message.reply_text.await_args.args[0])
            show_portfolio.assert_awaited_once_with(archive_update, self.context)

            show_portfolio.reset_mock()
            delete_update, delete_message = self.callback_update("port_delete_NVDA")
            await bot.callback_button_handler(delete_update, self.context)

            remove.assert_called_once_with("NVDA")
            self.assertIn("eliminato", delete_message.reply_text.await_args.args[0])
            show_portfolio.assert_awaited_once_with(delete_update, self.context)

    def test_legacy_portfolio_command_alias_is_registered(self):
        handlers = []
        app = SimpleNamespace(
            add_error_handler=lambda *_: None,
            add_handler=lambda handler, **kwargs: handlers.append(handler),
            job_queue=None
        )
        builder = SimpleNamespace(
            token=lambda _: builder,
            request=lambda _: builder,
            build=lambda: app
        )
        with patch("src.bot.TELEGRAM_BOT_TOKEN", "test-token"), \
                patch("src.bot.HTTPXRequest"), \
                patch("src.bot.ApplicationBuilder", return_value=builder):
            bot.create_bot_application()

        portfolio_commands = {
            command
            for handler in handlers
            if getattr(handler, "callback", None) is bot.portfolio_command
            for command in handler.commands
        }
        self.assertIn("portafoglio", portfolio_commands)

    async def test_expired_price_prompt_is_cleared(self):
        await self.begin_price_flow("port_buy_AAPL")
        self.context.user_data["pending_portfolio"]["created_at"] = 0
        expired_reply, message = self.price_update("180", reply_to_id=500)

        await bot.portfolio_input_handler(expired_reply, self.context)

        self.mock_add_position.assert_not_called()
        self.assertNotIn("pending_portfolio", self.context.user_data)
        message.reply_text.assert_awaited_once()

    async def test_archive_history_pages_show_older_positions(self):
        self.mock_load_archived_portfolio.return_value = [
            {
                "ticker": f"OLD{index:02}",
                "direction": "BUY",
                "entry_price": 100 + index,
                "archived_at": "01/01/2026"
            }
            for index in range(12)
        ]

        first_update, first_message = self.callback_update("portfolio_history")
        await bot.callback_button_handler(first_update, self.context)
        first_text = first_message.reply_text.await_args.args[0]
        self.assertIn("OLD11", first_text)
        self.assertNotIn("OLD00", first_text)
        next_button = first_message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(next_button.callback_data, "portfolio_history_page_1")

        older_update, older_message = self.callback_update(next_button.callback_data)
        await bot.callback_button_handler(older_update, self.context)
        older_text = older_message.reply_text.await_args.args[0]
        self.assertIn("OLD01", older_text)
        self.assertIn("OLD00", older_text)
        previous_button = older_message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(previous_button.callback_data, "portfolio_history_page_0")

    async def test_private_chat_accepts_direct_price_input_without_reply(self):
        await self.begin_price_flow("port_buy_NVDA")
        direct_update, _ = self.price_update("145.50", reply_to_id=None)
        direct_update.effective_chat.type = "private"
        self.mock_add_position.return_value = {"ticker": "NVDA", "direction": "BUY", "entry_price": 145.50}

        await bot.portfolio_input_handler(direct_update, self.context)

        self.mock_add_position.assert_called_once_with("NVDA", "BUY", 145.50)
        self.assertNotIn("pending_portfolio", self.context.user_data)

    def test_portfolio_management_keyboard_includes_asset_names(self):
        positions = [{"ticker": "NVDA", "raw_ticker": "NVDA"}, {"ticker": "GC=F", "raw_ticker": "XAUUSD"}]
        keyboard = bot.get_portfolio_management_keyboard(positions)
        button_texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
        self.assertTrue(any("NVDA" in text for text in button_texts))
        self.assertTrue(any("XAU" in text or "Oro" in text for text in button_texts))
        self.assertTrue(any("SL" in text for text in button_texts))
        self.assertTrue(any("TP" in text for text in button_texts))

    async def test_sl_and_tp_interactive_flows_update_levels(self):
        self.mock_load_portfolio.return_value = [{"ticker": "NVDA", "entry_price": 140.0, "direction": "BUY"}]

        # Test Stop Loss flow
        await self.begin_price_flow("port_sl_NVDA")
        self.assertEqual(self.context.user_data["pending_portfolio"]["action"], "sl")
        reply_sl, _ = self.price_update("135.00", reply_to_id=500)
        await bot.portfolio_input_handler(reply_sl, self.context)
        self.mock_update_stop_loss.assert_called_once_with("NVDA", 135.00)
        self.assertNotIn("pending_portfolio", self.context.user_data)

        # Test Take Profit flow
        await self.begin_price_flow("port_tp_NVDA")
        self.assertEqual(self.context.user_data["pending_portfolio"]["action"], "tp")
        reply_tp, _ = self.price_update("160.00", reply_to_id=500)
        await bot.portfolio_input_handler(reply_tp, self.context)
        self.mock_update_take_profit.assert_called_once_with("NVDA", 160.00)
        self.assertNotIn("pending_portfolio", self.context.user_data)

    async def test_portfolio_sl_and_tp_text_commands(self):
        msg = SimpleNamespace(reply_text=AsyncMock())
        cmd_update = SimpleNamespace(message=msg, effective_chat=SimpleNamespace(id=self.chat_id))

        self.context.args = ["sl", "NVDA", "135.50"]
        await bot.portfolio_command(cmd_update, self.context)
        self.mock_update_stop_loss.assert_called_with("NVDA", 135.50)

        self.context.args = ["tp", "NVDA", "165.00"]
        await bot.portfolio_command(cmd_update, self.context)
        self.mock_update_take_profit.assert_called_with("NVDA", 165.00)


if __name__ == "__main__":
    unittest.main()
