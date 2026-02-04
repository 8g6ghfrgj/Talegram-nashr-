import os
import logging
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

# استيراد مكونات المشروع
from config import BOT_TOKEN, OWNER_ID
from database.database import BotDatabase
from managers.telegram_manager import TelegramBotManager

from handlers.admin_handlers import AdminHandlers
from handlers.account_handlers import AccountHandlers
from handlers.ad_handlers import AdHandlers
from handlers.group_handlers import GroupHandlers
from handlers.reply_handlers import ReplyHandlers
from handlers.conversation_handlers import ConversationHandlers


# ===================== إعداد السجل =====================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ===================== Health Server =====================

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"✅ Health server running on port {port}")
    server.serve_forever()


# ===================== Main Bot =====================

class MainBot:

    def __init__(self):

        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN غير موجود في المتغيرات البيئية")
            exit(1)

        # قاعدة البيانات
        self.db = BotDatabase()

        # مدير التليجرام
        self.manager = TelegramBotManager(self.db)

        # المعالجات
        self.admin_handlers = AdminHandlers(self.db, self.manager)
        self.account_handlers = AccountHandlers(self.db, self.manager)
        self.ad_handlers = AdHandlers(self.db, self.manager)
        self.group_handlers = GroupHandlers(self.db, self.manager)
        self.reply_handlers = ReplyHandlers(self.db, self.manager)

        self.conversation_handlers = ConversationHandlers(
            self.db,
            self.manager,
            self.admin_handlers,
            self.account_handlers,
            self.ad_handlers,
            self.group_handlers,
            self.reply_handlers
        )

        # التطبيق
        self.application = Application.builder().token(BOT_TOKEN).build()

        self.user_conversations = {}

        self.setup_handlers()
        self.add_owner()
        self.create_directories()


    # ===================== أدوات =====================

    def add_owner(self):
        try:
            success, message = self.db.add_admin(
                OWNER_ID,
                "@owner",
                "المالك الرئيسي",
                True
            )
            logger.info(message)
        except Exception as e:
            logger.error(f"خطأ إضافة المالك: {e}")


    def create_directories(self):
        paths = [
            "temp_files/ads",
            "temp_files/group_replies",
            "temp_files/random_replies"
        ]

        for path in paths:
            os.makedirs(path, exist_ok=True)


    def get_user_context(self, user_id):
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = {}
        return self.user_conversations[user_id]


    # ===================== الأوامر =====================

    async def start(self, update: Update, context):

        user_id = update.effective_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ ليس لديك صلاحية.")
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

        markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🚀 لوحة تحكم البوت\n\nاختر العملية:",
            reply_markup=markup
        )


    async def cancel(self, update: Update, context):

        user_id = update.effective_user.id

        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ ليس لديك صلاحية.")
            return

        await update.message.reply_text("❌ تم إلغاء العملية.")
        await self.start(update, context)

        return ConversationHandler.END


    # ===================== الأزرار =====================

    async def handle_callback(self, update: Update, context):

        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text("❌ ليس لديك صلاحية.")
            return

        data = query.data

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
            await self.manager.start_publishing(query, context)

        elif data == "stop_publishing":
            await self.manager.stop_publishing(query, context)

        else:
            await self.conversation_handlers.handle_callback(query, context)


    # ===================== الرسائل =====================

    async def handle_message(self, update: Update, context):
        # في حال احتجت منطق إضافي مستقبلاً
        pass


    # ===================== إعداد Handlers =====================

    def setup_handlers(self):

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("cancel", self.cancel))

        self.conversation_handlers.setup_conversation_handlers(self.application)

        self.application.add_handler(
            CallbackQueryHandler(self.handle_callback)
        )

        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )


    # ===================== التشغيل =====================

    def run(self):

        logger.info("🚀 البوت يعمل الآن")

        # Health server
        threading.Thread(
            target=run_health_server,
            daemon=True
        ).start()

        try:
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES
            )

        except KeyboardInterrupt:
            logger.info("🛑 تم الإيقاف")

            asyncio.run(self.manager.cleanup_all())

        except Exception as e:
            logger.error(f"❌ خطأ تشغيل: {e}")
            raise


# ===================== Start =====================

if __name__ == "__main__":

    try:
        bot = MainBot()
        bot.run()

    except Exception as e:
        logger.error(f"❌ خطأ فادح: {e}")
        print("🔄 إعادة التشغيل...")
