import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackQueryHandler
)

logger = logging.getLogger(__name__)

# استيراد حالات المحادثة من config.py
try:
    from config import (
        ADD_ACCOUNT, ADD_AD_TYPE, ADD_AD_TEXT, ADD_AD_MEDIA,
        ADD_GROUP, ADD_PRIVATE_REPLY, ADD_ADMIN,
        ADD_RANDOM_REPLY, ADD_PRIVATE_TEXT, ADD_GROUP_TEXT,
        ADD_GROUP_PHOTO, ADD_GROUP_TEXT_REPLY, 
        ADD_GROUP_PHOTO_REPLY, ADD_GROUP_PHOTO_MEDIA,
        ADD_RANDOM_MEDIA, AD_TYPES, MESSAGES
    )
except ImportError:
    # تعريف قيم افتراضية في حالة فشل الاستيراد
    (
        ADD_ACCOUNT, ADD_AD_TYPE, ADD_AD_TEXT, ADD_AD_MEDIA,
        ADD_GROUP, ADD_PRIVATE_REPLY, ADD_ADMIN,
        ADD_RANDOM_REPLY, ADD_PRIVATE_TEXT, ADD_GROUP_TEXT,
        ADD_GROUP_PHOTO
    ) = range(11)
    
    ADD_GROUP_TEXT_REPLY = 11
    ADD_GROUP_PHOTO_REPLY = 12
    ADD_GROUP_PHOTO_MEDIA = 13
    ADD_RANDOM_MEDIA = 14
    
    AD_TYPES = {
        'text': '📝 نص فقط',
        'photo': '🖼️ صورة مع نص',
        'contact': '📞 جهة اتصال (VCF)'
    }
    
    MESSAGES = {
        'start': "🚀 لوحة تحكم البوت الفعلي",
        'unauthorized': "❌ ليس لديك صلاحية للوصول إلى هذا البوت.",
        'no_accounts': "❌ لا توجد حسابات نشطة!",
        'no_ads': "❌ لا توجد إعلانات!",
        'ad_added': "✅ **تم حفظ الإعلان بنجاح!**",
        'account_added': "✅ **تم إضافة الحساب بنجاح!**"
    }

class ConversationHandlers:
    def __init__(self, db, manager, admin_handlers, account_handlers,
                 ad_handlers, group_handlers, reply_handlers):
        self.db = db
        self.manager = manager
        self.admin_handlers = admin_handlers
        self.account_handlers = account_handlers
        self.ad_handlers = ad_handlers
        self.group_handlers = group_handlers
        self.reply_handlers = reply_handlers
        self.active_conversations = {}  # لتتبع المحادثات النشطة

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة جميع الأزرار العامة"""
        query = update.callback_query
        
        if query is None:
            logger.error("Received callback without query")
            return
        
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        # التحقق من صلاحية المستخدم
        if not self.db.is_admin(user_id):
            await query.edit_message_text("❌ ليس لديك صلاحية للوصول إلى هذا البوت.")
            return
        
        logger.info(f"معالجة الزر: {data} للمستخدم: {user_id}")
        
        # التحقق من وجود محادثة نشطة
        if user_id in self.active_conversations:
            if data not in ["back_to_", "cancel"]:
                await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                return
        
        try:
            # معالجة أزرار الرجوع أولاً
            if data.startswith("back_to_"):
                await self.handle_back_buttons(query, context, data)
                return
            
            # أزرار إدارة الحسابات
            elif data == "manage_accounts":
                await self.account_handlers.manage_accounts(query, context)
            elif data == "add_account":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة حساب
                self.active_conversations[user_id] = "add_account"
                await self.account_handlers.add_account_start(query, context)
            elif data == "show_accounts":
                await self.account_handlers.show_accounts(query, context)
            elif data.startswith("delete_account_"):
                try:
                    account_id = int(data.replace("delete_account_", ""))
                    await self.account_handlers.delete_account(query, context, account_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج account_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            elif data.startswith("toggle_account_"):
                try:
                    account_id = int(data.replace("toggle_account_", ""))
                    await self.account_handlers.toggle_account_status(query, context, account_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج account_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            # أزرار إدارة الإعلانات
            elif data == "manage_ads":
                await self.ad_handlers.manage_ads(query, context)
            elif data == "add_ad":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # عرض خيارات أنواع الإعلانات
                keyboard = [
                    [
                        InlineKeyboardButton("📝 إعلان نصي", callback_data="ad_type_text"),
                        InlineKeyboardButton("🖼️ إعلان بصورة", callback_data="ad_type_photo")
                    ],
                    [
                        InlineKeyboardButton("📞 إعلان جهة اتصال", callback_data="ad_type_contact"),
                        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_ads")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📢 **اختر نوع الإعلان:**\n\n"
                    "📝 **نصي:** إعلان مكتوب فقط\n"
                    "🖼️ **بصورة:** إعلان مع صورة\n"
                    "📞 **جهة اتصال:** إعلان مع جهة اتصال",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            elif data == "show_ads":
                await self.ad_handlers.show_ads(query, context)
            elif data == "ad_stats":
                await self.ad_handlers.show_ad_stats(query, context)
            elif data.startswith("delete_ad_"):
                try:
                    ad_id = int(data.replace("delete_ad_", ""))
                    await self.ad_handlers.delete_ad(query, context, ad_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج ad_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            elif data.startswith("toggle_ad_"):
                try:
                    ad_id = int(data.replace("toggle_ad_", ""))
                    await self.ad_handlers.toggle_ad_status(query, context, ad_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج ad_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            # أزرار إدارة المجموعات
            elif data == "manage_groups":
                await self.group_handlers.manage_groups(query, context)
            elif data == "add_group":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة مجموعة
                self.active_conversations[user_id] = "add_group"
                await self.group_handlers.add_group_start(query, context)
            elif data == "show_groups":
                await self.group_handlers.show_groups(query, context)
            elif data == "start_join_groups":
                await self.group_handlers.start_join_groups(query, context)
            elif data == "stop_join_groups":
                await self.group_handlers.stop_join_groups(query, context)
            elif data.startswith("delete_group_"):
                try:
                    group_id = int(data.replace("delete_group_", ""))
                    await self.group_handlers.delete_group(query, context, group_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج group_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            elif data.startswith("toggle_group_"):
                try:
                    group_id = int(data.replace("toggle_group_", ""))
                    await self.group_handlers.toggle_group_status(query, context, group_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج group_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            # أزرار إدارة المشرفين
            elif data == "manage_admins":
                await self.admin_handlers.manage_admins(query, context)
            elif data == "add_admin":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # التحقق من صلاحية المستخدم (فقط المالك يمكنه إضافة مشرفين)
                if user_id != 8148890042:  # المالك الرئيسي
                    await query.edit_message_text("❌ فقط المالك الرئيسي يمكنه إضافة مشرفين!")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة مشرف
                self.active_conversations[user_id] = "add_admin"
                await self.admin_handlers.add_admin_start(query, context)
            elif data == "show_admins":
                await self.admin_handlers.show_admins(query, context)
            elif data == "system_stats":
                await self.admin_handlers.show_system_stats(query, context)
            elif data == "export_data":
                await self.admin_handlers.export_data(query, context)
            elif data.startswith("delete_admin_"):
                try:
                    admin_id = int(data.replace("delete_admin_", ""))
                    # التحقق من صلاحية المستخدم (فقط المالك يمكنه حذف مشرفين)
                    if user_id != 8148890042:  # المالك الرئيسي
                        await query.edit_message_text("❌ فقط المالك الرئيسي يمكنه حذف مشرفين!")
                        return
                    await self.admin_handlers.delete_admin(query, context, admin_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج admin_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            elif data.startswith("toggle_admin_"):
                try:
                    admin_id = int(data.replace("toggle_admin_", ""))
                    # التحقق من صلاحية المستخدم (فقط المالك يمكنه تعديل صلاحيات مشرفين)
                    if user_id != 8148890042:  # المالك الرئيسي
                        await query.edit_message_text("❌ فقط المالك الرئيسي يمكنه تعديل صلاحيات المشرفين!")
                        return
                    await self.admin_handlers.toggle_admin_status(query, context, admin_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج admin_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            # أزرار إدارة الردود
            elif data == "manage_replies":
                await self.reply_handlers.manage_replies(query, context)
            elif data == "private_replies":
                await self.reply_handlers.manage_private_replies(query, context)
            elif data == "group_replies":
                await self.reply_handlers.manage_group_replies(query, context)
            elif data == "show_replies":
                await self.reply_handlers.show_replies_menu(query, context)
            elif data == "add_private_reply":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة رد خاص
                self.active_conversations[user_id] = "add_private_reply"
                await self.reply_handlers.add_private_reply_start(query, context)
            elif data == "add_group_text_reply":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة رد نصي
                self.active_conversations[user_id] = "add_group_text_reply"
                await self.reply_handlers.add_group_text_reply_start(query, context)
            elif data == "add_group_photo_reply":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة رد بصورة
                self.active_conversations[user_id] = "add_group_photo_reply"
                await self.reply_handlers.add_group_photo_reply_start(query, context)
            elif data == "add_random_reply":
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                # وضع علامة أن المستخدم في محادثة إضافة رد عشوائي
                self.active_conversations[user_id] = "add_random_reply"
                await self.reply_handlers.add_random_reply_start(query, context)
            
            # أزرار حذف الردود
            elif data.startswith("delete_private_reply_"):
                try:
                    reply_id = int(data.replace("delete_private_reply_", ""))
                    await self.reply_handlers.delete_private_reply(query, context, reply_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج reply_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            elif data.startswith("delete_text_reply_"):
                try:
                    reply_id = int(data.replace("delete_text_reply_", ""))
                    await self.reply_handlers.delete_text_reply(query, context, reply_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج reply_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            elif data.startswith("delete_photo_reply_"):
                try:
                    reply_id = int(data.replace("delete_photo_reply_", ""))
                    await self.reply_handlers.delete_photo_reply(query, context, reply_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج reply_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            elif data.startswith("delete_random_reply_"):
                try:
                    reply_id = int(data.replace("delete_random_reply_", ""))
                    await self.reply_handlers.delete_random_reply(query, context, reply_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج reply_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            
            # أزرار عرض الردود للحذف
            elif data == "show_private_replies_delete":
                await self.reply_handlers.show_private_replies_delete(query, context)
            elif data == "show_text_replies_delete":
                await self.reply_handlers.show_text_replies_delete(query, context)
            elif data == "show_photo_replies_delete":
                await self.reply_handlers.show_photo_replies_delete(query, context)
            elif data == "show_random_replies_delete":
                await self.reply_handlers.show_random_replies_delete(query, context)
            
            # أزرار النشر
            elif data == "start_publishing":
                await self.start_publishing(query, context)
            elif data == "stop_publishing":
                await self.stop_publishing(query, context)
            
            # أزرار الرد الخاص
            elif data == "start_private_reply":
                await self.reply_handlers.start_private_reply(query, context)
            elif data == "stop_private_reply":
                await self.reply_handlers.stop_private_reply(query, context)
            
            # أزرار الرد الجماعي
            elif data == "start_group_reply":
                await self.reply_handlers.start_group_reply(query, context)
            elif data == "stop_group_reply":
                await self.reply_handlers.stop_group_reply(query, context)
            
            # أزرار الرد العشوائي
            elif data == "start_random_reply":
                await self.reply_handlers.start_random_reply(query, context)
            elif data == "stop_random_reply":
                await self.reply_handlers.stop_random_reply(query, context)
            
            # أزرار أنواع الإعلانات
            elif data in ["ad_type_text", "ad_type_photo", "ad_type_contact"]:
                # التحقق من وجود محادثة نشطة
                if user_id in self.active_conversations:
                    await query.edit_message_text("⚠️ لديك محادثة نشطة بالفعل. أكملها أو ألغها أولاً.")
                    return
                
                # حفظ نوع الإعلان في context
                ad_type = data.replace("ad_type_", "")
                context.user_data['ad_type'] = ad_type
                self.active_conversations[user_id] = f"add_ad_{ad_type}"
                
                # عرض رسالة بناءً على النوع
                if ad_type == "text":
                    message = "📝 **الإعلان النصي**\n\nأرسل نص الإعلان:"
                elif ad_type == "photo":
                    message = "🖼️ **الإعلان مع صورة**\n\nأرسل نص الإعلان:"
                elif ad_type == "contact":
                    message = "📞 **الإعلان مع جهة اتصال**\n\nأرسل نص الإعلان:"
                else:
                    message = "📢 **إضافة إعلان**\n\nأرسل نص الإعلان:"
                
                keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # إرجاع الحالة المناسبة لبدء المحادثة
                return ADD_AD_TEXT
            
            # الأزرار غير المعروفة
            else:
                await query.edit_message_text(
                    "❌ أمر غير معروف!\n"
                    "استخدم الأزرار المتاحة فقط."
                )
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الزر {data}: {e}", exc_info=True)
            # إزالة المستخدم من المحادثات النشطة في حالة حدوث خطأ
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            try:
                await query.edit_message_text(
                    "❌ حدث خطأ غير متوقع في النظام.\n"
                    "الرجاء المحاولة مرة أخرى أو الاتصال بالمطور."
                )
            except:
                # إذا فشل تحرير الرسالة، حاول إرسال رسالة جديدة
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ حدث خطأ غير متوقع في النظام.\n"
                         "الرجاء المحاولة مرة أخرى أو الاتصال بالمطور."
                )

    async def handle_back_buttons(self, query, context, data):
        """معالجة أزرار الرجوع"""
        try:
            user_id = query.from_user.id
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            if data == "back_to_main":
                await self.show_main_menu(query, context)
            elif data == "back_to_accounts":
                await self.account_handlers.manage_accounts(query, context)
            elif data == "back_to_ads":
                await self.ad_handlers.manage_ads(query, context)
            elif data == "back_to_groups":
                await self.group_handlers.manage_groups(query, context)
            elif data == "back_to_replies":
                await self.reply_handlers.manage_replies(query, context)
            elif data == "back_to_admins":
                await self.admin_handlers.manage_admins(query, context)
            elif data == "back_to_private_replies":
                await self.reply_handlers.manage_private_replies(query, context)
            elif data == "back_to_group_replies":
                await self.reply_handlers.manage_group_replies(query, context)
            elif data == "back_to_stats":
                await self.admin_handlers.show_system_stats(query, context)
            else:
                await self.show_main_menu(query, context)
        except Exception as e:
            logger.error(f"خطأ في معالجة زر الرجوع {data}: {e}")
            await query.edit_message_text("❌ خطأ في معالجة أمر الرجوع!")

    async def show_main_menu(self, query, context):
        """عرض القائمة الرئيسية"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            await query.edit_message_text("❌ ليس لديك صلاحية للوصول إلى هذا البوت.")
            return
        
        # إزالة المستخدم من المحادثات النشطة
        if user_id in self.active_conversations:
            del self.active_conversations[user_id]
        
        # الحصول على إحصائيات سريعة
        accounts_count = len(self.db.get_all_accounts(user_id))
        ads_count = len(self.db.get_ads(user_id))
        groups_count = len(self.db.get_groups(user_id))
        
        keyboard = [
            [InlineKeyboardButton("👥 إدارة الحسابات", callback_data="manage_accounts")],
            [InlineKeyboardButton("📢 إدارة الإعلانات", callback_data="manage_ads")],
            [InlineKeyboardButton("👥 إدارة المجموعات", callback_data="manage_groups")],
            [InlineKeyboardButton("💬 إدارة الردود", callback_data="manage_replies")],
            [InlineKeyboardButton("👨‍💼 إدارة المشرفين", callback_data="manage_admins")],
            [InlineKeyboardButton("🚀 بدء النشر", callback_data="start_publishing")],
            [InlineKeyboardButton("⏹️ إيقاف النشر", callback_data="stop_publishing")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🚀 **لوحة تحكم البوت الفعلي**\n\n"
            f"📊 **الإحصائيات:**\n"
            f"👥 الحسابات: {accounts_count}\n"
            f"📢 الإعلانات: {ads_count}\n"
            f"👥 المجموعات: {groups_count}\n\n"
            f"⚡ النشر بأقصى سرعة ممكنة\n"
            f"⚡ الردود التلقائية بأقصى سرعة\n"
            f"⚡ الانضمام للمجموعات بأقصى سرعة\n\n"
            "اختر الإجراء الذي تريد تنفيذه:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def start_publishing(self, query, context):
        """بدء النشر التلقائي"""
        try:
            admin_id = query.from_user.id
            
            # التحقق من وجود حسابات
            accounts = self.db.get_active_publishing_accounts(admin_id)
            if not accounts:
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ لا توجد حسابات نشطة!\n\n"
                    "يجب إضافة حسابات أولاً قبل بدء النشر.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود إعلانات
            ads = self.db.get_ads(admin_id)
            if not ads:
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ لا توجد إعلانات!\n\n"
                    "يجب إضافة إعلانات أولاً قبل بدء النشر.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود مجموعات
            groups = self.db.get_groups(admin_id)
            if not groups:
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "❌ لا توجد مجموعات!\n\n"
                    "يجب إضافة مجموعات أولاً قبل بدء النشر.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            if self.manager.start_publishing(admin_id):
                keyboard = [
                    [InlineKeyboardButton("⏹️ إيقاف النشر", callback_data="stop_publishing")],
                    [InlineKeyboardButton("💬 بدء الرد في الخاص", callback_data="start_private_reply")],
                    [InlineKeyboardButton("👥 بدء الرد في القروبات", callback_data="start_group_reply")],
                    [InlineKeyboardButton("🎲 بدء الرد العشوائي", callback_data="start_random_reply")],
                    [InlineKeyboardButton("📊 الإحصائيات", callback_data="ad_stats")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "🚀 **تم بدء النشر بأقصى سرعة!**\n\n"
                    f"✅ **عدد الحسابات:** {len(accounts)}\n"
                    f"✅ **عدد الإعلانات:** {len(ads)}\n"
                    f"✅ **عدد المجموعات:** {len(groups)}\n"
                    f"⏱️ **تأخير نشر القروبات:** 60 ثانية\n"
                    f"⚡ **بين الإعلانات:** 0.1 ثانية\n"
                    f"⚡ **بين المجموعات:** 0.2 ثانية\n"
                    f"⚡ **بين الدورات:** 30 ثانية\n\n"
                    "سيبدأ البوت بالنشر في جميع المجموعات الآن مع تأمين الحسابات.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"✅ بدأ النشر للمشرف {admin_id}")
            else:
                await query.edit_message_text("⚠️ النشر يعمل بالفعل!")
                
        except Exception as e:
            logger.error(f"خطأ في بدء النشر: {e}")
            await query.edit_message_text(
                "❌ حدث خطأ في بدء النشر.\n"
                "الرجاء المحاولة مرة أخرى."
            )

    async def stop_publishing(self, query, context):
        """إيقاف النشر التلقائي"""
        try:
            admin_id = query.from_user.id
            
            if self.manager.stop_publishing(admin_id):
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("⏹️ تم إيقاف النشر!", reply_markup=reply_markup)
                logger.info(f"⏹️ توقف النشر للمشرف {admin_id}")
            else:
                await query.edit_message_text("⚠️ النشر غير نشط!")
                
        except Exception as e:
            logger.error(f"خطأ في إيقاف النشر: {e}")
            await query.edit_message_text("❌ حدث خطأ في إيقاف النشر.")

    def setup_conversation_handlers(self, application):
        """إعداد معالجات المحادثة"""
        # معالج الأزرار الرئيسي
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # محادثة إضافة الحساب
        add_account_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.account_handlers.add_account_start,
                pattern="^add_account$"
            )],
            states={
                ADD_ACCOUNT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_account_session
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(add_account_conv)
        
        # محادثة إضافة الإعلان
        add_ad_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.handle_callback,
                pattern="^ad_type_"
            )],
            states={
                ADD_AD_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.process_ad_text
                    )
                ],
                ADD_AD_MEDIA: [
                    MessageHandler(filters.PHOTO, self.process_ad_media),
                    MessageHandler(filters.CONTACT, self.process_ad_media),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_ad_media_text)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(add_ad_conv)
        
        # محادثة إضافة المجموعة
        add_group_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.group_handlers.add_group_start,
                pattern="^add_group$"
            )],
            states={
                ADD_GROUP: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_group_link
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(add_group_conv)
        
        # محادثة إضافة المشرف
        add_admin_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.admin_handlers.add_admin_start,
                pattern="^add_admin$"
            )],
            states={
                ADD_ADMIN: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_admin_id
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(add_admin_conv)
        
        # محادثة إضافة رد خاص
        private_reply_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.reply_handlers.add_private_reply_start,
                pattern="^add_private_reply$"
            )],
            states={
                ADD_PRIVATE_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_private_reply_text
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(private_reply_conv)
        
        # محادثة إضافة رد نصي في القروبات
        group_text_reply_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.reply_handlers.add_group_text_reply_start,
                pattern="^add_group_text_reply$"
            )],
            states={
                ADD_GROUP_TEXT: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_group_text_reply_trigger
                    )
                ],
                ADD_GROUP_TEXT_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_group_text_reply_text
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(group_text_reply_conv)
        
        # محادثة إضافة رد مع صورة في القروبات
        group_photo_reply_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.reply_handlers.add_group_photo_reply_start,
                pattern="^add_group_photo_reply$"
            )],
            states={
                ADD_GROUP_PHOTO: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_group_photo_reply_trigger
                    )
                ],
                ADD_GROUP_PHOTO_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_group_photo_reply_text
                    )
                ],
                ADD_GROUP_PHOTO_MEDIA: [
                    MessageHandler(
                        filters.PHOTO,
                        self.add_group_photo_reply_photo
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(group_photo_reply_conv)
        
        # محادثة إضافة رد عشوائي
        random_reply_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.reply_handlers.add_random_reply_start,
                pattern="^add_random_reply$"
            )],
            states={
                ADD_RANDOM_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_random_reply_text
                    )
                ],
                ADD_RANDOM_MEDIA: [
                    MessageHandler(
                        filters.PHOTO,
                        self.add_random_reply_media
                    ),
                    CommandHandler("skip", self.skip_random_reply_media)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_conversation),
                CallbackQueryHandler(self.cancel_conversation, pattern="^cancel$")
            ]
        )
        application.add_handler(random_reply_conv)

    # ============ دوال معالجة المحادثات ============

    async def add_account_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة جلسة حساب"""
        try:
            session_string = update.message.text
            user_id = update.message.from_user.id
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ الحساب في قاعدة البيانات
            account_id = self.db.add_account(user_id, session_string)
            
            if account_id:
                keyboard = [
                    [InlineKeyboardButton("👥 عرض الحسابات", callback_data="show_accounts")],
                    [InlineKeyboardButton("➕ إضافة حساب آخر", callback_data="add_account")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة الحساب بنجاح!**\n\n"
                    f"🆔 **رقم الحساب:** `{account_id}`\n"
                    f"📱 **رقم الهاتف:** {session_string[:20]}...\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة حساب جديد رقم {account_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة الحساب! تأكد من صحة الجلسة.")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الحساب: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الحساب!")
            return ConversationHandler.END

    async def process_ad_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة نص الإعلان"""
        try:
            text = update.message.text
            user_id = update.message.from_user.id
            
            # حفظ النص في context
            context.user_data['ad_text'] = text
            context.user_data['user_id'] = user_id
            
            # الحصول على نوع الإعلان
            ad_type = context.user_data.get('ad_type', 'text')
            
            if ad_type == "text":
                # إعلان نصي - حفظ مباشرة
                return await self.save_ad(update, context)
            elif ad_type == "photo":
                # إعلان مع صورة - طلب الصورة
                keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "✅ تم حفظ النص.\n\n"
                    "🖼️ الآن أرسل الصورة:",
                    reply_markup=reply_markup
                )
                
                return ADD_AD_MEDIA
            elif ad_type == "contact":
                # إعلان مع جهة اتصال - طلب جهة الاتصال
                keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "✅ تم حفظ النص.\n\n"
                    "📞 الآن أرسل جهة الاتصال (Contact):",
                    reply_markup=reply_markup
                )
                
                return ADD_AD_MEDIA
            else:
                await update.message.reply_text("❌ نوع إعلان غير معروف!")
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"خطأ في معالجة نص الإعلان: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الإعلان!")
            return ConversationHandler.END

    async def process_ad_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة وسائط الإعلان (صورة)"""
        try:
            # الحصول على نوع الإعلان
            ad_type = context.user_data.get('ad_type', 'photo')
            
            if ad_type == "photo" and update.message.photo:
                # حفظ الصورة
                photo = update.message.photo[-1]
                context.user_data['ad_photo_id'] = photo.file_id
                
                # حفظ الإعلان في قاعدة البيانات
                return await self.save_ad(update, context)
            else:
                await update.message.reply_text("❌ يرجى إرسال صورة صحيحة!")
                return ADD_AD_MEDIA
                
        except Exception as e:
            logger.error(f"خطأ في معالجة وسائط الإعلان: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الصورة!")
            return ConversationHandler.END

    async def process_ad_media_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة وسائط الإعلان (جهة اتصال كنص)"""
        try:
            # الحصول على نوع الإعلان
            ad_type = context.user_data.get('ad_type', 'contact')
            
            if ad_type == "contact":
                # يمكن معالجة نص جهة الاتصال هنا
                contact_text = update.message.text
                context.user_data['ad_contact_text'] = contact_text
                
                # حفظ الإعلان في قاعدة البيانات
                return await self.save_ad(update, context)
            else:
                await update.message.reply_text("❌ هذا النوع لا يدعم النص!")
                return ADD_AD_MEDIA
                
        except Exception as e:
            logger.error(f"خطأ في معالجة نص جهة الاتصال: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة جهة الاتصال!")
            return ConversationHandler.END

    async def save_ad(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حفظ الإعلان النهائي في قاعدة البيانات"""
        try:
            user_id = update.message.from_user.id if update.message else context.user_data.get('user_id')
            text = context.user_data.get('ad_text', '')
            ad_type = context.user_data.get('ad_type', 'text')
            
            media_id = None
            contact_info = None
            
            if ad_type == 'photo':
                media_id = context.user_data.get('ad_photo_id')
            elif ad_type == 'contact':
                # يمكن استخدام نص جهة الاتصال أو بيانات Contact
                contact_info = context.user_data.get('ad_contact_text', 'جهة اتصال')
            
            # حفظ الإعلان في قاعدة البيانات
            ad_id = self.db.add_ad(
                user_id=user_id,
                text=text,
                ad_type=ad_type,
                media_id=media_id,
                contact_info=contact_info
            )
            
            # تنظيف context
            context.user_data.clear()
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            keyboard = [
                [InlineKeyboardButton("📢 عرض الإعلانات", callback_data="show_ads")],
                [InlineKeyboardButton("➕ إضافة إعلان آخر", callback_data="add_ad")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **تم حفظ الإعلان بنجاح!**\n\n"
                f"🆔 **رقم الإعلان:** `{ad_id}`\n"
                f"📝 **النوع:** {AD_TYPES.get(ad_type, ad_type)}\n"
                f"📝 **النص:** {text[:100]}...\n"
                f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"تم إضافة إعلان جديد رقم {ad_id} للمستخدم {user_id}")
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعلان: {e}")
            await update.message.reply_text("❌ حدث خطأ في حفظ الإعلان!")
            return ConversationHandler.END

    async def add_group_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة رابط مجموعة"""
        try:
            group_link = update.message.text
            user_id = update.message.from_user.id
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ المجموعة في قاعدة البيانات
            group_id = self.db.add_group(user_id, group_link)
            
            if group_id:
                keyboard = [
                    [InlineKeyboardButton("👥 عرض المجموعات", callback_data="show_groups")],
                    [InlineKeyboardButton("➕ إضافة مجموعة أخرى", callback_data="add_group")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة المجموعة بنجاح!**\n\n"
                    f"🆔 **رقم المجموعة:** `{group_id}`\n"
                    f"🔗 **الرابط:** {group_link}\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة مجموعة جديدة رقم {group_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة المجموعة! تأكد من صحة الرابط.")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المجموعة: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة المجموعة!")
            return ConversationHandler.END

    async def add_admin_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة آيدي مشرف"""
        try:
            admin_id_text = update.message.text
            user_id = update.message.from_user.id
            
            # التحقق من أن المستخدم هو المالك
            if user_id != 8148890042:
                await update.message.reply_text("❌ فقط المالك الرئيسي يمكنه إضافة مشرفين!")
                return ConversationHandler.END
            
            try:
                new_admin_id = int(admin_id_text)
            except ValueError:
                await update.message.reply_text("❌ يرجى إدخال آيدي صحيح (أرقام فقط)!")
                return ADD_ADMIN
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ المشرف في قاعدة البيانات
            admin_db_id = self.db.add_admin(new_admin_id)
            
            if admin_db_id:
                keyboard = [
                    [InlineKeyboardButton("👨‍💼 عرض المشرفين", callback_data="show_admins")],
                    [InlineKeyboardButton("➕ إضافة مشرف آخر", callback_data="add_admin")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة المشرف بنجاح!**\n\n"
                    f"🆔 **رقم المشرف:** `{admin_db_id}`\n"
                    f"👤 **آيدي المستخدم:** {new_admin_id}\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة مشرف جديد رقم {admin_db_id} للمستخدم {new_admin_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة المشرف!")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة المشرف: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة المشرف!")
            return ConversationHandler.END

    async def add_private_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة رد خاص"""
        try:
            reply_text = update.message.text
            user_id = update.message.from_user.id
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ الرد في قاعدة البيانات
            reply_id = self.db.add_private_reply(user_id, reply_text)
            
            if reply_id:
                keyboard = [
                    [InlineKeyboardButton("💬 عرض الردود", callback_data="show_replies")],
                    [InlineKeyboardButton("➕ إضافة رد آخر", callback_data="add_private_reply")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة الرد الخاص بنجاح!**\n\n"
                    f"🆔 **رقم الرد:** `{reply_id}`\n"
                    f"📝 **النص:** {reply_text[:100]}...\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة رد خاص جديد رقم {reply_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة الرد!")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد الخاص: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الرد!")
            return ConversationHandler.END

    # ============ دوال الردود الجماعية ============

    async def add_group_text_reply_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة محفز رد نصي جماعي"""
        try:
            trigger = update.message.text
            user_id = update.message.from_user.id
            
            context.user_data['reply_trigger'] = trigger
            
            keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم حفظ المحفز: {trigger}\n\n"
                "📝 الآن أرسل نص الرد:",
                reply_markup=reply_markup
            )
            
            return ADD_GROUP_TEXT_REPLY
            
        except Exception as e:
            logger.error(f"خطأ في معالجة محفز الرد: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة المحفز!")
            return ConversationHandler.END

    async def add_group_text_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة نص رد نصي جماعي"""
        try:
            reply_text = update.message.text
            user_id = update.message.from_user.id
            trigger = context.user_data.get('reply_trigger', '')
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ الرد في قاعدة البيانات
            reply_id = self.db.add_group_text_reply(user_id, trigger, reply_text)
            
            if reply_id:
                keyboard = [
                    [InlineKeyboardButton("💬 عرض الردود", callback_data="show_replies")],
                    [InlineKeyboardButton("➕ إضافة رد آخر", callback_data="add_group_text_reply")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة الرد النصي الجماعي بنجاح!**\n\n"
                    f"🆔 **رقم الرد:** `{reply_id}`\n"
                    f"🔤 **المحفز:** {trigger}\n"
                    f"📝 **النص:** {reply_text[:100]}...\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة رد نصي جماعي جديد رقم {reply_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة الرد!")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد النصي الجماعي: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الرد!")
            return ConversationHandler.END

    async def add_group_photo_reply_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة محفز رد بصورة جماعي"""
        try:
            trigger = update.message.text
            user_id = update.message.from_user.id
            
            context.user_data['reply_trigger'] = trigger
            
            keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم حفظ المحفز: {trigger}\n\n"
                "📝 الآن أرسل نص الرد:",
                reply_markup=reply_markup
            )
            
            return ADD_GROUP_PHOTO_REPLY
            
        except Exception as e:
            logger.error(f"خطأ في معالجة محفز الرد: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة المحفز!")
            return ConversationHandler.END

    async def add_group_photo_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة نص رد بصورة جماعي"""
        try:
            reply_text = update.message.text
            user_id = update.message.from_user.id
            trigger = context.user_data.get('reply_trigger', '')
            
            context.user_data['reply_text'] = reply_text
            
            keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم حفظ النص: {reply_text[:50]}...\n\n"
                "🖼️ الآن أرسل الصورة:",
                reply_markup=reply_markup
            )
            
            return ADD_GROUP_PHOTO_MEDIA
            
        except Exception as e:
            logger.error(f"خطأ في معالجة نص الرد: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة النص!")
            return ConversationHandler.END

    async def add_group_photo_reply_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة صورة رد بصورة جماعي"""
        try:
            photo = update.message.photo[-1]
            user_id = update.message.from_user.id
            trigger = context.user_data.get('reply_trigger', '')
            reply_text = context.user_data.get('reply_text', '')
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # حفظ الرد في قاعدة البيانات
            reply_id = self.db.add_group_photo_reply(user_id, trigger, reply_text, photo.file_id)
            
            if reply_id:
                keyboard = [
                    [InlineKeyboardButton("💬 عرض الردود", callback_data="show_replies")],
                    [InlineKeyboardButton("➕ إضافة رد آخر", callback_data="add_group_photo_reply")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إضافة الرد بالصورة الجماعي بنجاح!**\n\n"
                    f"🆔 **رقم الرد:** `{reply_id}`\n"
                    f"🔤 **المحفز:** {trigger}\n"
                    f"📝 **النص:** {reply_text[:100]}...\n"
                    f"🖼️ **الصورة:** تمت الإضافة\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة رد بصورة جماعي جديد رقم {reply_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة الرد!")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد بالصورة الجماعي: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الرد!")
            return ConversationHandler.END

    # ============ دوال الردود العشوائية ============

    async def add_random_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة نص رد عشوائي"""
        try:
            reply_text = update.message.text
            user_id = update.message.from_user.id
            
            context.user_data['reply_text'] = reply_text
            
            keyboard = [
                [InlineKeyboardButton("🖼️ إضافة صورة", callback_data="add_photo")],
                [InlineKeyboardButton("⏭️ تخطي الصورة", callback_data="skip_photo")],
                [InlineKeyboardButton("🔙 إلغاء", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم حفظ النص: {reply_text[:50]}...\n\n"
                "🖼️ هل تريد إضافة صورة مع الرد؟",
                reply_markup=reply_markup
            )
            
            return ADD_RANDOM_MEDIA
            
        except Exception as e:
            logger.error(f"خطأ في معالجة نص الرد العشوائي: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة النص!")
            return ConversationHandler.END

    async def add_random_reply_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة إضافة صورة رد عشوائي"""
        try:
            photo = update.message.photo[-1] if update.message.photo else None
            user_id = update.message.from_user.id
            reply_text = context.user_data.get('reply_text', '')
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            media_id = photo.file_id if photo else None
            
            # حفظ الرد في قاعدة البيانات
            reply_id = self.db.add_random_reply(user_id, reply_text, media_id)
            
            if reply_id:
                keyboard = [
                    [InlineKeyboardButton("🎲 عرض الردود العشوائية", callback_data="show_random_replies_delete")],
                    [InlineKeyboardButton("➕ إضافة رد آخر", callback_data="add_random_reply")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                media_info = "مع صورة 🖼️" if media_id else "نص فقط 📝"
                
                await update.message.reply_text(
                    f"✅ **تم إضافة الرد العشوائي بنجاح!**\n\n"
                    f"🆔 **رقم الرد:** `{reply_id}`\n"
                    f"📝 **النص:** {reply_text[:100]}...\n"
                    f"📊 **النوع:** {media_info}\n"
                    f"📅 **تاريخ الإضافة:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"تم إضافة رد عشوائي جديد رقم {reply_id} للمستخدم {user_id}")
            else:
                await update.message.reply_text("❌ فشل في إضافة الرد!")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إضافة الرد العشوائي: {e}")
            await update.message.reply_text("❌ حدث خطأ في إضافة الرد!")
            return ConversationHandler.END

    async def skip_random_reply_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تخطي إضافة صورة للرد العشوائي"""
        return await self.add_random_reply_media(update, context)

    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء المحادثة الحالية"""
        try:
            user_id = None
            
            if update.message:
                user_id = update.message.from_user.id
            elif update.callback_query:
                user_id = update.callback_query.from_user.id
            
            # إزالة المستخدم من المحادثات النشطة
            if user_id in self.active_conversations:
                del self.active_conversations[user_id]
            
            # تنظيف context
            if context.user_data:
                context.user_data.clear()
            
            if update.message:
                keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("❌ تم إلغاء الأمر.", reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.answer()
                await self.show_main_menu(update.callback_query, context)
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إلغاء المحادثة: {e}")
            return ConversationHandler.END
