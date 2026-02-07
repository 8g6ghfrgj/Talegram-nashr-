import sys
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from config import BOT_TOKEN, OWNER_ID, MESSAGES
from database.database import BotDatabase
from managers.telegram_manager import TelegramBotManager

# menus سيتم إنشاؤه بعد هذه الخطوة
from menus import show_main_menu


# ==================================================
# LOGGING
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ==================================================
# MAIN BOT CLASS
# ==================================================

class MainBot:

    def __init__(self):

        if not BOT_TOKEN:
            print("❌ BOT_TOKEN غير موجود")
            sys.exit(1)

        # ===== DATABASE =====
        self.db = BotDatabase()

        # ===== MANAGER =====
        self.manager = TelegramBotManager(self.db)

        # ===== APPLICATION =====
        self.app = Application.builder().token(BOT_TOKEN).build()

        # ===== HANDLERS =====
        self.register_handlers()

        # ===== ADD OWNER =====
        self.db.add_admin(
            OWNER_ID,
            "owner",
            "المالك الرئيسي",
            True
        )


    # ==================================================
    # /start
    # ==================================================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        user_id = update.effective_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return

        await show_main_menu(update, context)


    # ==================================================
    # REGISTER HANDLERS
    # ==================================================

    def register_handlers(self):

        self.app.add_handler(CommandHandler("start", self.start))

        # لاحقًا سنضيف:
        # - menus callbacks
        # - conversations هنا (واحد واحد)

        self.app.add_error_handler(self.error_handler)


    # ==================================================
    # ERROR HANDLER
    # ==================================================

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):

        logger.exception(context.error)

        if update and getattr(update, "effective_message", None):
            try:
                await update.effective_message.reply_text(
                    "❌ حدث خطأ في النظام"
                )
            except:
                pass


    # ==================================================
    # RUN
    # ==================================================

    def run(self):

        print("🚀 Bot is running...")
        self.app.run_polling()


# ==================================================
# MAIN
# ==================================================

def main():

    bot = MainBot()
    bot.run()


if __name__ == "__main__":
    main()
