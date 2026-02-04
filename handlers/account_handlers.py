import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import ADD_ACCOUNT, MESSAGES
from database.text_encoder import TextEncoder

logger = logging.getLogger(__name__)

class AccountHandlers:
    def __init__(self, db, manager):
        self.db = db
        self.manager = manager
        self.text_encoder = TextEncoder()
    
    async def manage_accounts(self, query, context):
        """عرض قائمة إدارة الحسابات"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                MESSAGES['unauthorized'],
                reply_markup=reply_markup
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة حساب", callback_data="add_account")],
            [InlineKeyboardButton("👥 عرض الحسابات", callback_data="show_accounts")],
            [InlineKeyboardButton("📊 إحصائيات الحسابات", callback_data="account_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👥 إدارة الحسابات\n\n"
            "اختر الإجراء الذي تريد تنفيذه:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def add_account_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إضافة حساب"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES['unauthorized'])
            return ConversationHandler.END
        
        await query.edit_message_text(
            "📱 **إضافة حساب جديد**\n\n"
            "أرسل كود الجلسة (Session String):\n\n"
            "يمكنك الحصول عليه من:\n"
            "1. بوت @SessionStringBot\n"
            "2. أو موقع session.telegra.ph\n\n"
            "⚠️ **تحذير:** تأكد من صلاحية الكود قبل الإرسال\n\n"
            "أرسل /cancel للإلغاء",
            parse_mode='Markdown'
        )
        
        context.user_data['adding_account'] = True
        return ADD_ACCOUNT
    
    async def add_account_session(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة كود الجلسة"""
        user_id = update.message.from_user.id
        
        if not self.db.is_admin(user_id):
            await update.message.reply_text(MESSAGES['unauthorized'])
            return ConversationHandler.END
        
        session_string = update.message.text.strip()
        
        # التحقق من صحة الكود الأساسي
        if len(session_string) < 100:
            await update.message.reply_text(
                "❌ كود الجلسة غير صحيح!\n"
                "يجب أن يكون أطول من 100 حرف.\n"
                "حاول مرة أخرى أو أرسل /cancel للإلغاء"
            )
            return ADD_ACCOUNT
        
        await update.message.reply_text("⏳ جاري اختبار وتفعيل الجلسة...")
        
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            
            # اختبار الجلسة
            client = TelegramClient(StringSession(session_string), 1, "b")
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                await client.disconnect()
                
                # استخراج معلومات الحساب
                phone = me.phone if me.phone else "غير معروف"
                name = f"{me.first_name} {me.last_name}" if me.last_name else me.first_name
                username = f"@{me.username}" if me.username else "لا يوجد"
                
                # إضافة الحساب إلى قاعدة البيانات
                success, message = self.db.add_account(session_string, phone, name, username, user_id)
                
                if success:
                    keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back_to_accounts")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        f"✅ {message}\n\n"
                        f"📱 **معلومات الحساب:**\n"
                        f"👤 **الاسم:** {name}\n"
                        f"📞 **الهاتف:** {phone}\n"
                        f"🔗 **المستخدم:** {username}\n"
                        f"🆔 **المعرف:** {me.id}\n\n"
                        f"💾 تم حفظ الجلسة في قاعدة البيانات",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(f"❌ {message}")
            else:
                await client.disconnect()
                await update.message.reply_text(
                    "❌ كود الجلسة غير صالح!\n"
                    "تأكد من:\n"
                    "1. صحة الكود\n"
                    "2. أن الحساب مفعل\n"
                    "3. عدم وجود حظر على الحساب"
                )
                return ADD_ACCOUNT
                
        except Exception as e:
            logger.error(f"خطأ في اختبار الجلسة: {e}")
            await update.message.reply_text(
                f"❌ خطأ في الجلسة: {str(e)}\n\n"
                "تأكد من:\n"
                "1. صحة كود الجلسة\n"
                "2. اتصال الإنترنت\n"
                "3. عدم وجود حظر مؤقت"
            )
            return ADD_ACCOUNT
        
        context.user_data.pop('adding_account', None)
        return ConversationHandler.END
    
    async def show_accounts(self, query, context):
        """عرض جميع الحسابات"""
        user_id = query.from_user.id
        accounts = self.db.get_accounts(user_id)
        
        if not accounts:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_accounts")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ لا توجد حسابات مضافة!\n"
                "استخدم زر 'إضافة حساب' لإضافة حسابات جديدة.",
                reply_markup=reply_markup
            )
            return
        
        # إحصائيات سريعة
        stats = self.db.get_statistics(user_id)
        
        text = f"👥 **الحسابات المضافة** ({stats['accounts']['active']}/{stats['accounts']['total']} نشطة)\n\n"
        
        keyboard = []
        
        for account in accounts[:20]:  # عرض أول 20 حساب فقط
            acc_id, session_string, phone, name, username, is_active, added_date, status, last_publish = account
            
            status_emoji = "🟢" if is_active else "🔴"
            publish_status = "✅" if status == 'active' else "⏸️"
            
            text += f"**#{acc_id}** - {name}\n"
            text += f"{status_emoji} {publish_status} | 📱 {phone}\n"
            text += f"🔗 {username}\n"
            
            if last_publish:
                text += f"📅 آخر نشر: {last_publish[:16]}\n"
            
            text += "─" * 20 + "\n"
            
            # أزرار لكل حساب
            keyboard.append([
                InlineKeyboardButton(f"🗑️ حذف #{acc_id}", callback_data=f"delete_account_{acc_id}"),
                InlineKeyboardButton(f"{'⏸️ إيقاف' if is_active else '▶️ تشغيل'} #{acc_id}", 
                                   callback_data=f"toggle_account_{acc_id}")
            ])
        
        if len(accounts) > 20:
            text += f"\n... وعرض {len(accounts) - 20} حساب إضافي"
        
        keyboard.append([
            InlineKeyboardButton("🔄 تحديث القائمة", callback_data="show_accounts"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_accounts")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def delete_account(self, query, context, account_id):
        """حذف حساب"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES['unauthorized'])
            return
        
        # الحصول على معلومات الحساب قبل الحذف
        accounts = self.db.get_accounts(user_id)
        account_name = ""
        for acc in accounts:
            if acc[0] == account_id:
                account_name = acc[3]
                break
        
        # حذف الحساب
        if self.db.delete_account(account_id, user_id):
            await query.edit_message_text(
                f"✅ تم حذف الحساب #{account_id} ({account_name}) بنجاح"
            )
        else:
            await query.edit_message_text(
                f"❌ فشل حذف الحساب #{account_id}\n"
                "قد يكون الحساب غير موجود أو ليس لديك صلاحية لحذفه."
            )
        
        # العودة إلى قائمة الحسابات
        await self.show_accounts(query, context)
    
    async def toggle_account_status(self, query, context, account_id):
        """تبديل حالة الحساب (تفعيل/تعطيل)"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES['unauthorized'])
            return
        
        # البحث عن الحساب
        accounts = self.db.get_accounts(user_id)
        account_found = False
        current_status = None
        
        for acc in accounts:
            if acc[0] == account_id:
                account_found = True
                current_status = acc[5]  # is_active
                break
        
        if not account_found:
            await query.edit_message_text(f"❌ الحساب #{account_id} غير موجود!")
            return
        
        # تبديل الحالة
        conn = self.db.conn if hasattr(self.db, 'conn') else None
        if not conn:
            # إعادة الاتصال
            import sqlite3
            conn = sqlite3.connect(self.db.db_name)
        
        cursor = conn.cursor()
        new_status = 0 if current_status else 1
        
        try:
            cursor.execute('UPDATE accounts SET is_active = ? WHERE id = ?', (new_status, account_id))
            conn.commit()
            
            status_text = "✅ مفعل" if new_status else "⏸️ متوقف"
            await query.edit_message_text(f"✅ تم {status_text} الحساب #{account_id}")
            
        except Exception as e:
            logger.error(f"خطأ في تبديل حالة الحساب: {e}")
            await query.edit_message_text(f"❌ فشل تبديل حالة الحساب: {str(e)}")
        finally:
            if conn:
                conn.close()
        
        await self.show_accounts(query, context)
    
    async def show_account_stats(self, query, context):
        """عرض إحصائيات الحسابات"""
        user_id = query.from_user.id
        
        if not self.db.is_admin(user_id):
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(MESSAGES['unauthorized'], reply_markup=reply_markup)
            return
        
        stats = self.db.get_statistics(user_id)
        
        text = "📊 **إحصائيات الحسابات**\n\n"
        
        text += f"👥 **الحسابات:**\n"
        text += f"   • الإجمالي: {stats['accounts']['total']}\n"
        text += f"   • النشطة: {stats['accounts']['active']}\n"
        text += f"   • غير النشطة: {stats['accounts']['total'] - stats['accounts']['active']}\n\n"
        
        text += f"📢 **الإعلانات:** {stats['ads']}\n\n"
        
        text += f"👥 **المجموعات:**\n"
        text += f"   • الإجمالي: {stats['groups']['total']}\n"
        text += f"   • المنضمة: {stats['groups']['joined']}\n"
        text += f"   • المعلقة: {stats['groups']['total'] - stats['groups']['joined']}\n\n"
        
        # الحصول على آخر النشاطات
        logs = self.db.get_logs(limit=5)
        if logs:
            text += "📋 **آخر النشاطات:**\n"
            for log in logs:
                log_id, log_admin, action, details, timestamp = log
                text += f"   • {action}: {details}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="account_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_accounts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
