import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import ADD_ADMIN, MESSAGES, OWNER_ID

logger = logging.getLogger(__name__)


class AdminHandlers:

    def __init__(self, db, manager):
        self.db = db
        self.manager = manager


    # ==================================================
    # ADMINS MENU
    # ==================================================

    async def manage_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return

        keyboard = [
            [InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin")],
            [InlineKeyboardButton("📋 عرض المشرفين", callback_data="show_admins")],
            [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="system_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]

        await query.edit_message_text(
            "👨‍💼 إدارة المشرفين",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # START ADD ADMIN (OWNER ONLY)
    # ==================================================

    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if user_id != OWNER_ID:
            await query.edit_message_text("❌ هذا الخيار للمالك فقط")
            return ConversationHandler.END

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]
        ]

        await query.edit_message_text(
            "👤 أرسل آيدي المشرف الجديد:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADD_ADMIN


    # ==================================================
    # ADD ADMIN ID
    # ==================================================

    async def add_admin_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        message = update.message
        owner_id = message.from_user.id

        if owner_id != OWNER_ID:
            await message.reply_text("❌ هذا الخيار للمالك فقط")
            return ConversationHandler.END

        try:
            admin_id = int(message.text.strip())
        except ValueError:
            await message.reply_text("❌ الآيدي غير صحيح")
            return ADD_ADMIN

        success, msg = self.db.add_admin(
            admin_id,
            f"admin_{admin_id}",
            "مشرف",
            True
        )

        if success:
            await message.reply_text("✅ تم إضافة المشرف بنجاح")
        else:
            await message.reply_text(f"❌ {msg}")

        context.user_data.clear()
        return ConversationHandler.END


    # ==================================================
    # SHOW ADMINS
    # ==================================================

    async def show_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query

        admins = self.db.get_admins()

        if not admins:
            await query.edit_message_text("❌ لا يوجد مشرفين")
            return

        text = "👨‍💼 قائمة المشرفين:\n\n"
        keyboard = []

        for admin in admins:

            # DB schema:
            # id, username, role, active, added
            admin_id, username, role, status, added = admin

            status_icon = "✅" if status == 1 else "⛔"

            text += f"{status_icon} {admin_id}\n"
            text += f"{role}\n{added}\n──────────\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"{'⛔ تعطيل' if status == 1 else '✅ تفعيل'}",
                    callback_data=f"toggle_admin_{admin_id}"
                ),
                InlineKeyboardButton(
                    "🗑 حذف",
                    callback_data=f"delete_admin_{admin_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔄 تحديث", callback_data="show_admins"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admins")
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # DELETE ADMIN
    # ==================================================

    async def delete_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, admin_id: int):

        query = update.callback_query

        if admin_id == OWNER_ID:
            await query.answer("❌ لا يمكن حذف المالك")
            return

        if self.db.delete_admin(admin_id):
            await query.answer("✅ تم حذف المشرف")
        else:
            await query.answer("❌ فشل الحذف")

        await self.show_admins(update, context)


    # ==================================================
    # TOGGLE ADMIN STATUS
    # ==================================================

    async def toggle_admin_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, admin_id: int):

        query = update.callback_query

        if admin_id == OWNER_ID:
            await query.answer("❌ لا يمكن تعطيل المالك")
            return

        if self.db.toggle_admin_status(admin_id):
            await query.answer("🔁 تم تغيير الحالة")
        else:
            await query.answer("❌ فشل التغيير")

        await self.show_admins(update, context)


    # ==================================================
    # SYSTEM STATS
    # ==================================================

    async def show_system_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query

        stats = self.db.get_system_statistics()

        text = (
            "📊 إحصائيات النظام\n\n"
            f"👨‍💼 المشرفين: {stats['admins']}\n"
            f"👥 الحسابات: {stats['accounts']}\n"
            f"📢 الإعلانات: {stats['ads']}\n"
            f"👥 المجموعات: {stats['groups']}\n"
            f"💬 الردود: {stats['replies']}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="system_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admins")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
