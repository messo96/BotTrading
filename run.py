import sys
import logging
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MORNING_BRIEFING_TIME, AFTERNOON_BRIEFING_TIME, TIMEZONE
from src.bot import create_bot_application

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("BotTrading")

def main():
    print("=" * 60)
    print("   🚀 AVVIO TRADING BROKER ASSISTANT BOT TELEGRAM")
    print("=" * 60)

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("\n❌ ERRORE: TELEGRAM_BOT_TOKEN non configurato!")
        print("\nPer far funzionare il bot:")
        print("1. Apri Telegram e cerca @BotFather")
        print("2. Invia /newbot e segui le istruzioni per dare un nome al bot")
        print("3. Copia il token HTTP API che ti viene fornito")
        print("4. Crea un file '.env' copiando '.env.example' e incolla il token:")
        print("   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
        print("5. Riavvia questo script: python run.py\n")
        sys.exit(1)

    print(f"• Fuso Orario: {TIMEZONE}")
    print(f"• Morning Briefing (Europa & Crypto): {MORNING_BRIEFING_TIME} (Lun-Ven)")
    print(f"• Afternoon Briefing (Pre-Market USA): {AFTERNOON_BRIEFING_TIME} (Lun-Ven)")
    print(f"• Chat ID predefinito per notifiche: {TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else 'Non impostato (puoi ricavarlo con /chatid)'}")
    print("\nIn attesa di messaggi su Telegram... (Premi CTRL+C per arrestare)")
    print("-" * 60)

    try:
        app = create_bot_application()
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Errore fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

