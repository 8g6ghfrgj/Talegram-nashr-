import logging
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

# استيراد حالات المحادثة من config.py مع معالجة الأخطاء
try:
    from config import (
        ADD_ACCOUNT,
        ADD_AD_TYPE,
        ADD_AD_TEXT,
        ADD_AD_MEDIA,
        ADD_GROUP,
        ADD_PRIVATE_REPLY,
        ADD_ADMIN,
        ADD_RANDOM_REPLY,
        ADD_PRIVATE_TEXT,
        ADD_GROUP_TEXT,
        ADD_GROUP_PHOTO,
        ADD_GROUP_TEXT_REPLY,
        ADD_GROUP_PHOTO_REPLY,
        ADD_GROUP_PHOTO_MEDIA,
        ADD_RANDOM_MEDIA,
        AD_TYPES,
        MESSAGES,
        BUTTONS,
        DELAY_SETTINGS,
        OWNER_ID
    )
except ImportError as e:
    logger.error(f"خطأ في استيراد المتغيرات من config.py: {e}")
    
    # تعريف قيم افتراضية في حالة فشل الاستيراد
    (
        ADD_ACCOUNT,
        ADD_AD_TYPE,
        ADD_AD_TEXT,
        ADD_AD_MEDIA,
        ADD_GROUP,
        ADD_PRIVATE_REPLY,
        ADD_ADMIN,
        ADD_RANDOM_REPLY,
        ADD_PRIVATE_TEXT,
        ADD_GROUP_TEXT,
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
        'owner_only': "❌ فقط المالك الرئيسي يستطيع تنفيذ هذا الأمر!",
        'no_accounts': "❌ لا توجد حسابات نشطة!",
        'no_ads': "❌ لا توجد إعلانات!",
        'ad_added': "✅ تم حفظ الإعلان بنجاح!",
        'account_added': "✅ تم إضافة الحساب بنجاح!",
        'group_added': "✅ تم إضافة المجموعة بنجاح!",
        'admin_added': "✅ تم إضافة المشرف بنجاح!"
    }
    
    BUTTONS = {
        'main_menu': {
            'accounts': "👥 إدارة الحسابات",
            'ads': "📢 إدارة الإعلانات",
            'groups': "👥 إدارة المجموعات",
            'replies': "💬 إدارة الردود",
            'admins': "👨‍💼 إدارة المشرفين",
            'start_publishing': "🚀 بدء النشر",
            'stop_publishing': "⏹️ إيقاف النشر"
        },
        'back': "🔙 رجوع",
        'cancel': "❌ إلغاء"
    }
    
    DELAY_SETTINGS = {
        'publishing': {
            'between_ads': 0.1,
            'between_groups': 0.2,
            'between_cycles': 30,
            'group_publishing_delay': 60
        }
    }
    
    OWNER_ID = 8148890042


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
            await query.edit_message_text(MESSAGES['unauthorized'])
            return
        
        logger.info(f"معالجة الزر: {data} للمستخدم: {user_id}")
        
        try:
            # معالجة أزرار الرجوع أولاً
            if data.startswith("back_to_"):
                await self.handle_back_buttons(query, context, data)
                return
            
            # أزرار إدارة الحسابات
            elif data == "manage_accounts":
                await self.account_handlers.manage_accounts(query, context)
            elif data == "add_account":
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
            
            # أزرار إدارة الإعلانات
            elif data == "manage_ads":
                await self.ad_handlers.manage_ads(query, context)
            elif data == "add_ad":
                # عرض خيارات أنواع الإعلانات
                keyboard = [
                    [
                        InlineKeyboardButton(BUTTONS['ad_types']['text'], callback_data="ad_type_text"),
                        InlineKeyboardButton(BUTTONS['ad_types']['photo'], callback_data="ad_type_photo")
                    ],
                    [
                        InlineKeyboardButton(BUTTONS['ad_types']['contact'], callback_data="ad_type_contact"),
                        InlineKeyboardButton(BUTTONS['back'], callback_data="back_to_ads")
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
            
            # أزرار إدارة المجموعات
            elif data == "manage_groups":
                await self.group_handlers.manage_groups(query, context)
            elif data == "add_group":
                await self.group_handlers.add_group_start(query, context)
            elif data == "show_groups":
                await self.group_handlers.show_groups(query, context)
            elif data == "start_join_groups":
                await self.group_handlers.start_join_groups(query, context)
            elif data == "stop_join_groups":
                await self.group_handlers.stop_join_groups(query, context)
            
            # أزرار إدارة المشرفين
            elif data == "manage_admins":
                await self.admin_handlers.manage_admins(query, context)
            elif data == "add_admin":
                # التحقق إذا كان المستخدم هو المالك
                if user_id != OWNER_ID:
                    await query.edit_message_text(MESSAGES['owner_only'].format(OWNER_ID))
                    return
                await self.admin_handlers.add_admin_start(query, context)
            elif data == "show_admins":
                await self.admin_handlers.show_admins(query, context)
            elif data == "system_stats":
                await self.admin_handlers.show_system_stats(query, context)
            elif data == "export_data":
                await self.admin_handlers.export_data(query, context)
            elif data.startswith("delete_admin_"):
                # التحقق إذا كان المستخدم هو المالك
                if user_id != OWNER_ID:
                    await query.edit_message_text(MESSAGES['owner_only'].format(OWNER_ID))
                    return
                try:
                    admin_id = int(data.replace("delete_admin_", ""))
                    await self.admin_handlers.delete_admin(query, context, admin_id)
                except (ValueError, IndexError) as e:
                    logger.error(f"خطأ في استخراج admin_id من {data}: {e}")
                    await query.edit_message_text("❌ خطأ في معالجة الأمر!")
            elif data.startswith("toggle_admin_"):
                # التحقق إذا كان المستخدم هو المالك
                if user_id != OWNER_ID:
                    await query.edit_message_text(MESSAGES['owner_only'].format(OWNER_ID))
                    return
                try:
                    admin_id = int(data.replace("toggle_admin_", ""))
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
                await self.reply_handlers.add_private_reply_start(query, context)
            elif data == "add_group_text_reply":
                await self.reply_handlers.add_group_text_reply_start(query, context)
            elif data == "add_group_photo_reply":
                await self.reply_handlers.add_group_photo_reply_start(query, context)
            elif data == "add_random_reply":
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
                # حفظ نوع الإعلان في context
                ad_type = data.replace("ad_type_", "")
                context.user_data['ad_type'] = ad_type
                
                # عرض رسالة بناءً على النوع
                if ad_type == "text":
                    message = "📝 **الإعلان النصي**\n\nأرسل نص الإعلان:"
                elif ad_type == "photo":
                    message = "🖼️ **الإعلان مع صورة**\n\nأرسل نص الإعلان:"
                elif ad_type == "contact":
                    message = "📞 **الإعلان مع جهة اتصال**\n\nأرسل نص الإعلان:"
                else:
                    message = "📢 **إضافة إعلان**\n\nأرسل نص الإعلان:"
                
                keyboard = [[InlineKeyboardButton(BUTTONS['cancel'], callback_data="back_to_ads")]]
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
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الزر {data}: {e}", exc_info=True)
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
            return ConversationHandler.END

    async def handle_back_buttons(self, query, context, data):
        """معالجة أزرار الرجوع"""
        try:
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
            elif data == "back_to_show_admins":
                await self.admin_handlers.show_admins(query, context)
            elif data == "back_to_show_ads":
                await self.ad_handlers.show_ads(query, context)
            elif data == "back_to_show_accounts":
                await self.account_handlers.show_accounts(query, context)
            elif data == "back_to_show_groups":
                await self.group_handlers.show_groups(query, context)
            elif data == "back_to_show_replies":
                await self.reply_handlers.show_replies_menu(query, context)
            else:
                await self.show_main_menu(query, context)
        except Exception as e:
            logger.error(f"خطأ في معالجة زر الرجوع {data}: {e}")
            await query.edit_message_text("❌ خطأ في معالجة أمر الرجوع!")

    async def show_main_menu(self, query, context):
        """عرض القائمة الرئيسية"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES['unauthorized'])
            return
        
        keyboard = [
            [InlineKeyboardButton(BUTTONS['main_menu']['accounts'], callback_data="manage_accounts")],
            [InlineKeyboardButton(BUTTONS['main_menu']['ads'], callback_data="manage_ads")],
            [InlineKeyboardButton(BUTTONS['main_menu']['groups'], callback_data="manage_groups")],
            [InlineKeyboardButton(BUTTONS['main_menu']['replies'], callback_data="manage_replies")],
            [InlineKeyboardButton(BUTTONS['main_menu']['admins'], callback_data="manage_admins")],
            [InlineKeyboardButton(BUTTONS['main_menu']['start_publishing'], callback_data="start_publishing")],
            [InlineKeyboardButton(BUTTONS['main_menu']['stop_publishing'], callback_data="stop_publishing")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            MESSAGES['start'],
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
                keyboard = [[InlineKeyboardButton(BUTTONS['back'], callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    MESSAGES['no_accounts'] + "\n\nيجب إضافة حسابات أولاً قبل بدء النشر.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            # التحقق من وجود إعلانات
            ads = self.db.get_ads(admin_id)
            if not ads:
                keyboard = [[InlineKeyboardButton(BUTTONS['back'], callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    MESSAGES['no_ads'] + "\n\nيجب إضافة إعلانات أولاً قبل بدء النشر.",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                return
            
            if self.manager.start_publishing(admin_id):
                keyboard = [
                    [InlineKeyboardButton(BUTTONS['main_menu']['stop_publishing'], callback_data="stop_publishing")],
                    [InlineKeyboardButton("💬 بدء الرد في الخاص", callback_data="start_private_reply")],
                    [InlineKeyboardButton("👥 بدء الرد في القروبات", callback_data="start_group_reply")],
                    [InlineKeyboardButton("🎲 بدء الرد العشوائي", callback_data="start_random_reply")],
                    [InlineKeyboardButton(BUTTONS['back'], callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "🚀 **تم بدء النشر بأقصى سرعة!**\n\n"
                    f"✅ **عدد الحسابات:** {len(accounts)}\n"
                    f"✅ **عدد الإعلانات:** {len(ads)}\n"
                    f"⏱️ **تأخير نشر القروبات:** {DELAY_SETTINGS['publishing']['group_publishing_delay']} ثانية\n"
                    f"⚡ **بين الإعلانات:** {DELAY_SETTINGS['publishing']['between_ads']} ثانية\n"
                    f"⚡ **بين المجموعات:** {DELAY_SETTINGS['publishing']['between_groups']} ثانية\n"
                    f"⚡ **بين الدورات:** {DELAY_SETTINGS['publishing']['between_cycles']} ثانية\n\n"
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
                keyboard = [[InlineKeyboardButton(BUTTONS['back'], callback_data="back_to_main")]]
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
                        self.account_handlers.add_account_session
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                    MessageHandler(filters.CONTACT, self.process_ad_media)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.group_handlers.add_group_link
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.admin_handlers.add_admin_id
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.reply_handlers.add_private_reply_text
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.reply_handlers.add_group_text_reply_trigger
                    )
                ],
                ADD_GROUP_TEXT_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.reply_handlers.add_group_text_reply_text
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.reply_handlers.add_group_photo_reply_trigger
                    )
                ],
                ADD_GROUP_PHOTO_REPLY: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.reply_handlers.add_group_photo_reply_text
                    )
                ],
                ADD_GROUP_PHOTO_MEDIA: [
                    MessageHandler(
                        filters.PHOTO,
                        self.reply_handlers.add_group_photo_reply_photo
                    )
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
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
                        self.reply_handlers.add_random_reply_text
                    )
                ],
                ADD_RANDOM_MEDIA: [
                    MessageHandler(
                        filters.PHOTO,
                        self.reply_handlers.add_random_reply_media
                    ),
                    CommandHandler("skip", self.reply_handlers.skip_random_reply_media)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.cancel, pattern="^back_to_")
            ]
        )
        application.add_handler(random_reply_conv)

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
                return await self.ad_handlers.add_ad_text(update, context)
            elif ad_type == "photo":
                # إعلان مع صورة - طلب الصورة
                keyboard = [[InlineKeyboardButton(BUTTONS['cancel'], callback_data="back_to_ads")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "✅ تم حفظ النص.\n\n"
                    "🖼️ الآن أرسل الصورة:",
                    reply_markup=reply_markup
                )
                
                return ADD_AD_MEDIA
            elif ad_type == "contact":
                # إعلان مع جهة اتصال - طلب جهة الاتصال
                keyboard = [[InlineKeyboardButton(BUTTONS['cancel'], callback_data="back_to_ads")]]
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
        """معالجة وسائط الإعلان (صورة أو جهة اتصال)"""
        try:
            # الحصول على نوع الإعلان
            ad_type = context.user_data.get('ad_type', 'text')
            
            if ad_type == "photo" and update.message.photo:
                # حفظ الصورة
                photo = update.message.photo[-1]
                context.user_data['ad_photo_id'] = photo.file_id
                
                # حفظ الإعلان في قاعدة البيانات
                return await self.ad_handlers.save_ad(update, context)
                
            elif ad_type == "contact" and update.message.contact:
                # حفظ جهة الاتصال
                contact = update.message.contact
                context.user_data['ad_contact'] = {
                    'phone_number': contact.phone_number,
                    'first_name': contact.first_name,
                    'last_name': contact.last_name or ''
                }
                
                # حفظ الإعلان في قاعدة البيانات
                return await self.ad_handlers.save_ad(update, context)
            else:
                await update.message.reply_text("❌ نوع وسائط غير مدعوم!")
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"خطأ في معالجة وسائط الإعلان: {e}")
            await update.message.reply_text("❌ حدث خطأ في معالجة الوسائط!")
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء الأمر الحالي"""
        try:
            # تنظيف بيانات المستخدم
            context.user_data.clear()
            
            if update.message:
                user_id = update.message.from_user.id
                if not self.db.is_admin(user_id):
                    await update.message.reply_text(MESSAGES['unauthorized'])
                    return ConversationHandler.END
                
                await update.message.reply_text("❌ تم إلغاء الأمر.")
            elif update.callback_query:
                await update.callback_query.answer()
                user_id = update.callback_query.from_user.id
                if not self.db.is_admin(user_id):
                    await update.callback_query.edit_message_text(MESSAGES['unauthorized'])
                    return ConversationHandler.END
                
                # الرجوع إلى القائمة المناسبة
                await self.handle_back_buttons(update.callback_query, context, "back_to_main")
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"خطأ في إلغاء الأمر: {e}")
            return ConversationHandler.END

    # ============ دوال مساعدة ============
    
    async def handle_ad_type_selection(self, query, context, ad_type):
        """معالجة اختيار نوع الإعلان"""
        context.user_data['ad_type'] = ad_type
        
        # عرض رسالة بناءً على النوع
        if ad_type == "text":
            message = "📝 **الإعلان النصي**\n\nأرسل نص الإعلان:"
        elif ad_type == "photo":
            message = "🖼️ **الإعلان مع صورة**\n\nأرسل نص الإعلان:"
        elif ad_type == "contact":
            message = "📞 **الإعلان مع جهة اتصال**\n\nأرسل نص الإعلان:"
        else:
            message = "📢 **إضافة إعلان**\n\nأرسل نص الإعلان:"
        
        keyboard = [[InlineKeyboardButton(BUTTONS['cancel'], callback_data="back_to_ads")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ADD_AD_TEXT

    def get_ad_type_description(self, ad_type):
        """الحصول على وصف نوع الإعلان"""
        return AD_TYPES.get(ad_type, "غير معروف")

    async def show_error_message(self, update, context, error_message):
        """عرض رسالة خطأ"""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(error_message)
            elif update.message:
                await update.message.reply_text(error_message)
        except Exception as e:
            logger.error(f"خطأ في عرض رسالة الخطأ: {e}")

    async def show_success_message(self, update, context, success_message):
        """عرض رسالة نجاح"""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(success_message)
            elif update.message:
                await update.message.reply_text(success_message)
        except Exception as e:
            logger.error(f"خطأ في عرض رسالة النجاح: {e}")

    # ============ دوال للتحقق ============
    
    async def check_admin_permission(self, user_id):
        """التحقق من صلاحية المشرف"""
        return self.db.is_admin(user_id)

    async def check_owner_permission(self, user_id):
        """التحقق من صلاحية المالك"""
        return user_id == OWNER_ID

    async def validate_user_input(self, text, min_length=1, max_length=4000):
        """التحقق من صحة إدخال المستخدم"""
        if not text:
            return False, "النص لا يمكن أن يكون فارغاً"
        
        if len(text) < min_length:
            return False, f"النص قصير جداً (الحد الأدنى {min_length} حرف)"
        
        if len(text) > max_length:
            return False, f"النص طويل جداً (الحد الأقصى {max_length} حرف)"
        
        return True, "النص صالح"

    # ============ دوال للعرض ============
    
    async def show_loading_message(self, query, message="جاري المعالجة..."):
        """عرض رسالة تحميل"""
        await query.edit_message_text(message)

    async def update_message_with_buttons(self, query, message, buttons):
        """تحديث الرسالة مع أزرار"""
        keyboard = []
        for row in buttons:
            keyboard_row = []
            for button in row:
                if isinstance(button, tuple):
                    keyboard_row.append(InlineKeyboardButton(button[0], callback_data=button[1]))
                else:
                    keyboard_row.append(InlineKeyboardButton(button, callback_data=button))
            keyboard.append(keyboard_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

    # ============ دوال المساعدة للمحادثات ============
    
    async def start_conversation(self, update, context, conversation_state):
        """بدء محادثة"""
        context.user_data['conversation_active'] = True
        return conversation_state

    async def end_conversation(self, update, context):
        """إنهاء محادثة"""
        context.user_data['conversation_active'] = False
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_conversation_timeout(self, update, context):
        """معالجة انتهاء وقت المحادثة"""
        await self.show_error_message(update, context, "⏰ انتهى وقت المحادثة. يرجى البدء من جديد.")
        return await self.end_conversation(update, context)

    # ============ دوال خاصة بمعالجة الأخطاء ============
    
    async def handle_database_error(self, update, context, error):
        """معالجة خطأ قاعدة البيانات"""
        logger.error(f"خطأ في قاعدة البيانات: {error}")
        await self.show_error_message(
            update, 
            context, 
            "❌ حدث خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى لاحقاً."
        )
        return await self.end_conversation(update, context)

    async def handle_network_error(self, update, context, error):
        """معالجة خطأ الشبكة"""
        logger.error(f"خطأ في الشبكة: {error}")
        await self.show_error_message(
            update, 
            context, 
            "❌ حدث خطأ في الاتصال بالشبكة. يرجى التحقق من اتصالك بالإنترنت."
        )
        return await self.end_conversation(update, context)

    async def handle_validation_error(self, update, context, error_message):
        """معالجة خطأ التحقق"""
        await self.show_error_message(update, context, f"❌ {error_message}")
        # لا ننهي المحادثة، نعطي المستخدم فرصة أخرى
        return ADD_AD_TEXT if context.user_data.get('ad_type') else ADD_ACCOUNT

    # ============ دوال للاستخدام العام ============
    
    def create_button_grid(self, buttons_data, columns=2):
        """إنشاء شبكة أزرار"""
        grid = []
        row = []
        
        for i, (text, callback_data) in enumerate(buttons_data.items(), 1):
            row.append(InlineKeyboardButton(text, callback_data=callback_data))
            
            if i % columns == 0:
                grid.append(row)
                row = []
        
        if row:  # إذا بقي أزرار في الصف الأخير
            grid.append(row)
        
        return grid

    async def send_temporary_message(self, update, context, message, duration=5):
        """إرسال رسالة مؤقتة"""
        if update.message:
            msg = await update.message.reply_text(message)
            # حذف الرسالة بعد المدة المحددة
            context.job_queue.run_once(
                lambda ctx: ctx.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id),
                duration
            )
        return True

    # ============ دوال للتدقيق ============
    
    async def audit_action(self, user_id, action, details=""):
        """تدقيق الإجراءات"""
        logger.info(f"تدقيق: المستخدم {user_id} - الإجراء: {action} - التفاصيل: {details}")
        # يمكن إضافة حفظ في قاعدة البيانات هنا

    async def log_conversation_start(self, user_id, conversation_type):
        """تسجيل بدء المحادثة"""
        logger.info(f"بدء محادثة: المستخدم {user_id} - النوع: {conversation_type}")

    async def log_conversation_end(self, user_id, conversation_type, success=True):
        """تسجيل نهاية المحادثة"""
        status = "ناجحة" if success else "فاشلة"
        logger.info(f"نهاية محادثة: المستخدم {user_id} - النوع: {conversation_type} - الحالة: {status}")
