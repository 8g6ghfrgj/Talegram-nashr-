import os
import sys
import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import (
    BOT_TOKEN,
    OWNER_ID,
    ADD_ACCOUNT,
    MESSAGES
)

from database.database import BotDatabase

from handlers.account_handlers import AccountHandlers
from handlers.ad_handlers import AdHandlers
from handlers.group_handlers import GroupHandlers
from handlers.reply_handlers import ReplyHandlers
from handlers.admin_handlers import AdminHandlers
from handlers.conversation_handlers import ConversationHandlers

from managers.telegram_manager import TelegramBotManager


# ==================================================
# LOGGING
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
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

        # Database
        self.db = BotDatabase()

        # Manager
        self.manager = TelegramBotManager(self.db)

        # Handlers
        self.account_handlers = AccountHandlers(self.db, self.manager)
        self.ad_handlers = AdHandlers(self.db, self.manager)
        self.group_handlers = GroupHandlers(self.db, self.manager)
        self.reply_handlers = ReplyHandlers(self.db, self.manager)
        self.admin_handlers = AdminHandlers(self.db, self.manager)

        self.conversation_handlers = ConversationHandlers(
            self.db,
            self.manager,
            self.admin_handlers,
            self.account_handlers,
            self.ad_handlers,
            self.group_handlers,
            self.reply_handlers
        )

        # Telegram app
        self.app = Application.builder().token(BOT_TOKEN).build()

        self.setup_handlers()

        self.add_owner_if_not_exists()

        print("✅ البوت جاهز")


    # ==================================================
    # OWNER
    # ==================================================

    def add_owner_if_not_exists(self):
        try:
            self.db.add_admin(
                OWNER_ID,
                "@owner",
                "المالك الرئيسي",
                True
            )
        except:
            pass


    # ==================================================
    # START
    # ==================================================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        user_id = update.effective_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return

        keyboard = [
            [InlineKeyboardButton("👥 إدارة الحسابات", callback_data="manage_accounts")],
            [InlineKeyboardButton("📢 إدارة الإعلانات", callback_data="manage_ads")],
            [InlineKeyboardButton("👥 إدارة المجموعات", callback_data="manage_groups")],
            [InlineKeyboardButton("💬 إدارة الردود", callback_data="manage_replies")],
            [InlineKeyboardButton("👨‍💼 إدارة المشرفين", callback_data="manage_admins")],
            [InlineKeyboardButton("🚀 بدء النشر", callback_data="start_publishing")],
            [InlineKeyboardButton("⏹️ إيقاف النشر", callback_data="stop_publishing")]
        ]

        await update.message.reply_text(
            MESSAGES["start"],
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


    # ==================================================
    # CALLBACK ROUTER
    # ==================================================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return

        data = query.data

        try:

            # ---------- MAIN MENUS ----------

            if data == "manage_accounts":
                await self.account_handlers.manage_accounts(query, context)

            elif data == "manage_ads":
                await self.ad_handlers.manage_ads(query, context)

            elif data == "manage_groups":
                await self.group_handlers.manage_groups(query, context)

            elif data == "manage_replies":
                await self.reply_handlers.manage_replies(query, context)

            elif data == "manage_admins":
                await self.admin_handlers.manage_admins(query, context)

            elif data == "start_publishing":
                await self.conversation_handlers.start_publishing(query, context)

            elif data == "stop_publishing":
                await self.conversation_handlers.stop_publishing(query, context)


            # ---------- ACCOUNT SECTION ----------

            elif data == "add_account":
                return await self.account_handlers.add_account_start(update, context)

            elif data == "show_accounts":
                await self.account_handlers.show_accounts(query, context)

            elif data == "account_stats":
                await self.account_handlers.show_account_stats(query, context)


            elif data.startswith("delete_account_"):
                acc_id = int(data.split("_")[-1])
                await self.account_handlers.delete_account(query, context, acc_id)

            elif data.startswith("toggle_account_"):
                acc_id = int(data.split("_")[-1])
                await self.account_handlers.toggle_account_status(query, context, acc_id)


            # ---------- BACK BUTTONS ----------

            elif data in (
                "back_to_main",
                "back_to_accounts",
                "back_to_ads",
                "back_to_groups",
                "back_to_replies",
                "back_to_admins",
                "back_to_private_replies",
                "back_to_group_replies"
            ):
                await self.conversation_handlers.handle_back_buttons(
                    query, context, data
                )


            # ---------- OTHER CALLBACKS ----------

            else:
                await self.conversation_handlers.handle_callback(query, context)


        except Exception as e:

            logger.error(f"Callback error: {e}")

            try:
                await query.edit_message_text(
                    "❌ حدث خطأ غير متوقع في النظام."
                )
            except:
                pass


    # ==================================================
    # CANCEL
    # ==================================================

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        user_id = update.message.from_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return ConversationHandler.END

        await update.message.reply_text("❌ تم الإلغاء")

        await self.start(update, context)

        return ConversationHandler.END


    # ==================================================
    # TEXT FALLBACK
    # ==================================================

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        user_id = update.message.from_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text(MESSAGES["unauthorized"])
            return

        await update.message.reply_text(
            "⚠️ استخدم الأزرار للتنقل داخل البوت"
        )


    # ==================================================
    # HANDLERS SETUP
    # ==================================================

    def setup_handlers(self):

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("cancel", self.cancel))

        # Conversation handlers (ads, replies, etc)
        self.conversation_handlers.setup_conversation_handlers(self.app)

        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text)
        )


    # ==================================================
    # RUN
    # ==================================================

    def run(self):

        print("🚀 البوت يعمل الآن...")

        self.app.run_polling(
            drop_pending_updates=True
        )


# ==================================================
# MAIN
# ==================================================

def main():
    bot = MainBot()
    bot.run()


if __name__ == "__main__":
    main()
