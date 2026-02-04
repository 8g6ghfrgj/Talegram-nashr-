import os
import logging
import threading
import asyncio
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update

# استيراد المكونات من الهيكل الجديد
from config import BOT_TOKEN, OWNER_ID
from database.database import BotDatabase
from managers.telegram_manager import TelegramBotManager
from handlers.admin_handlers import AdminHandlers
from handlers.account_handlers import AccountHandlers
from handlers.ad_handlers import AdHandlers
from handlers.group_handlers import GroupHandlers
from handlers.reply_handlers import ReplyHandlers
from handlers.conversation_handlers import ConversationHandlers
from config import (
    ADD_ACCOUNT, ADD_AD_TYPE, ADD_AD_TEXT, ADD_AD_MEDIA,
    ADD_GROUP, ADD_PRIVATE_REPLY, ADD_ADMIN,
    ADD_RANDOM_REPLY, ADD_PRIVATE_TEXT, ADD_GROUP_TEXT,
    ADD_GROUP_PHOTO
)

# إعداد السجل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# خادم HTTP للتحقق من الصحة
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def log_message(self, *args):
        pass

def run_health_server():
    """تشغيل خادم HTTP للتحقق من الصحة"""
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Health server running on port {port}")
    server.serve_forever()

class MainBot:
    def __init__(self):
        # التحقق من التوكن
        if not BOT_TOKEN:
            print("❌ خطأ: لم يتم تعيين BOT_TOKEN في متغيرات البيئة")
            print("⚠️ يرجى إضافة BOT_TOKEN في Render.com → Environment")
            exit(1)
        
        # تهيئة قاعدة البيانات
        self.db = BotDatabase()
        
        # تهيئة المدير
        self.manager = TelegramBotManager(self.db)
        
        # تهيئة المعالجات
        self.admin_handlers = AdminHandlers(self.db, self.manager)
        self.account_handlers = AccountHandlers(self.db, self.manager)
        self.ad_handlers = AdHandlers(self.db, self.manager)
        self.group_handlers = GroupHandlers(self.db, self.manager)
        self.reply_handlers = ReplyHandlers(self.db, self.manager)
        self.conversation_handlers = ConversationHandlers(
            self.db, self.manager, self.admin_handlers,
            self.account_handlers, self.ad_handlers,
            self.group_handlers, self.reply_handlers
        )
        
        # تهيئة التطبيق
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # إعداد المعالجات
        self.setup_handlers()
        
        # إضافة المالك الرئيسي إذا لم يكن موجوداً
        self._add_owner()
        
        # إنشاء المجلدات المطلوبة
        self._create_directories()
        
        # متغير لحفظ سياق المستخدمين
        self.user_conversations = {}
    
    def _add_owner(self):
        """إضافة المالك الرئيسي إلى قاعدة البيانات"""
        try:
            success, message = self.db.add_admin(OWNER_ID, "@owner", "المالك الرئيسي", True)
            if success:
                logger.info(f"✅ {message}")
            else:
                logger.info(f"⚠️ {message}")
        except Exception as e:
            logger.error(f"خطأ في إضافة المالك: {e}")
    
    def _create_directories(self):
        """إنشاء المجلدات المطلوبة"""
        directories = ["temp_files/ads", "temp_files/group_replies", "temp_files/random_replies"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ تم إنشاء المجلد: {directory}")
    
    def get_user_context(self, user_id):
        """الحصول على سياق المستخدم"""
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = {}
        return self.user_conversations[user_id]
    
    async def start(self, update: Update, context):
        """بدء البوت"""
        user = update.effective_user
        user_id = user.id
        
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ ليس لديك صلاحية للوصول إلى هذا البوت.")
            return
        
        user_context = self.get_user_context(user_id)
        user_context['conversation_active'] = False
        
        keyboard = [
            [InlineKeyboardButton("👥 إدارة الحسابات", callback_data="manage_accounts")],
            [InlineKeyboardButton("📢 إدارة الإعلانات", callback_data="manage_ads")],
            [InlineKeyboardButton("👥 إدارة المجموعات", callback_data="manage_groups")],
            [InlineKeyboardButton("💬 إدارة الردود", callback_data="manage_replies")],
            [InlineKeyboardButton("👨‍💼 إدارة المشرفين", callback_data="manage_admins")],
            [InlineKeyboardButton("🚀 بدء النشر", callback_data="start_publishing")],
            [InlineKeyboardButton("⏹️ إيقاف النشر", callback_data="stop_publishing")]
        ]
        
        from telegram import InlineKeyboardMarkup
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚀 لوحة تحكم البوت الفعلي - الإصدار المعدل\n\n"
            "⚡ النشر بأقصى سرعة مع تأمين الحسابات\n"
            "⚡ الردود التلقائية بأقصى سرعة\n"
            "⚡ الانضمام للمجموعات بأقصى سرعة\n\n"
            "اختر الإجراء الذي تريد تنفيذه:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def cancel(self, update: Update, context):
        """إلغاء الأمر الحالي"""
        user_id = update.message.from_user.id
        if not self.db.is_admin(user_id):
            await update.message.reply_text("❌ ليس لديك صلاحية للوصول إلى هذا البوت.")
            return
        
        user_context = self.get_user_context(user_id)
        user_context['conversation_active'] = False
        
        await update.message.reply_text("❌ تم إلغاء الأمر.")
        await self.start(update, context)
        return ConversationHandler.END
    
    async def handle_callback(self, update: Update, context):
        """معالجة الأزرار"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not self.db.is_admin(user_id):
            await query.edit_message_text("❌ ليس لديك صلاحية للوصول إلى هذا البوت.")
            return
        
        data = query.data
        
        # توجيه الأزرار إلى المعالجات المناسبة
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
        elif data in ["back_to_main", "back_to_accounts", "back_to_ads", 
                     "back_to_groups", "back_to_replies", "back_to_admins",
                     "back_to_private_replies", "back_to_group_replies"]:
            await self.conversation_handlers.handle_back_buttons(query, context, data)
        else:
            # معالجة الأزرار الأخرى عبر conversation_handlers
            await self.conversation_handlers.handle_callback(query, context)
    
    def setup_handlers(self):
        """إعداد معالجات البوت"""
        # معالجات الأوامر الأساسية
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("cancel", self.cancel))
        
        # إضافة معالجات المحادثة
        self.conversation_handlers.setup_conversation_handlers(self.application)
        
        # معالج الأزرار
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # معالج الرسائل العامة (للرد على الأوامر في المحادثات)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def handle_message(self, update: Update, context):
        """معالجة الرسائل النصية العامة"""
        # هذه الوظيفة تتعامل مع الرسائل التي لا تكون جزءاً من محادثة
        pass
    
    def run(self):
        """تشغيل البوت"""
        print("=" * 60)
        print("🚀 بوت النشر الفعلي - الإصدار المعدل")
        print("=" * 60)
        print("✅ تم تعديل التأخيرات حسب خوارزميات تليجرام:")
        print("   ⏱️  تأخير نشر القروبات: 60 ثانية")
        print("   ⚡ السرعات الأخرى: كما هي")
        print(f"   👑 المالك الوحيد: الآيدي {OWNER_ID}")
        print("   📁 اسم ملف جهات الاتصال: تسوي سكليف صحتي واتساب.vcf")
        print("=" * 60)
        print("📊 البوت يعمل الآن! اضغط Ctrl+C للإيقاف")
        print("=" * 60)
        
        # بدء خادم HTTP في خيط منفصل
        http_thread = threading.Thread(target=run_health_server, daemon=True)
        http_thread.start()
        
        # تشغيل البوت
        try:
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            print("\n\n🛑 إيقاف البوت...")
            # تنظيف الموارد
            asyncio.run(self.manager.cleanup_all())
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            raise

if __name__ == "__main__":
    try:
        bot = MainBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ خطأ فادح في تشغيل البوت: {e}")
        print(f"❌ خطأ: {e}")
        print("🔄 جاري إعادة التشغيل...")
        # يمكن إضافة إعادة تشغيل تلقائية هنا إذا لزم الأمر
