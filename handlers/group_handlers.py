import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import ADD_GROUP, GROUP_STATUS, MESSAGES

logger = logging.getLogger(__name__)


class GroupHandlers:

    def __init__(self, db, manager):
        self.db = db
        self.manager = manager


    # ==================================================
    # GROUPS MENU
    # ==================================================

    async def manage_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return

        keyboard = [
            [InlineKeyboardButton("➕ إضافة مجموعة", callback_data="add_group")],
            [InlineKeyboardButton("📋 عرض المجموعات", callback_data="show_groups")],
            [InlineKeyboardButton("🚀 بدء الانضمام", callback_data="start_join_groups")],
            [InlineKeyboardButton("⏹️ إيقاف الانضمام", callback_data="stop_join_groups")],
            [InlineKeyboardButton("📊 إحصائيات", callback_data="group_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]

        await query.edit_message_text(
            "👥 إدارة المجموعات",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # START ADD GROUP
    # ==================================================

    async def add_group_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return ConversationHandler.END

        context.user_data.clear()

        await query.edit_message_text(
            "🔗 أرسل رابط المجموعة أو القناة:"
        )

        return ADD_GROUP


    # ==================================================
    # ADD GROUP LINK
    # ==================================================

    async def add_group_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        message = update.message
        user_id = message.from_user.id

        link = message.text.strip()

        if not link.startswith("http"):
            await message.reply_text("❌ الرابط غير صالح")
            return ADD_GROUP

        success, msg = self.db.add_group(user_id, link)

        if success:
            await message.reply_text("✅ تم إضافة المجموعة بنجاح")
        else:
            await message.reply_text(f"❌ {msg}")

        context.user_data.clear()
        return ConversationHandler.END


    # ==================================================
    # SHOW GROUPS
    # ==================================================

    async def show_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        groups = self.db.get_groups(user_id)

        if not groups:
            await query.edit_message_text("❌ لا توجد مجموعات")
            return

        text = "👥 المجموعات:\n\n"
        keyboard = []

        for group in groups[:15]:

            group_id, link, status, added, _ = group

            status_label = GROUP_STATUS.get(status, status)

            text += f"#{group_id}\n"
            text += f"{link}\n"
            text += f"{status_label}\n"
            text += f"{added[:16]}\n──────────\n"

            keyboard.append([
                InlineKeyboardButton(
                    f"🗑 حذف #{group_id}",
                    callback_data=f"delete_group_{group_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔄 تحديث", callback_data="show_groups"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_groups")
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # DELETE GROUP
    # ==================================================

    async def delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: int):

        query = update.callback_query
        user_id = query.from_user.id

        if self.db.delete_group(group_id, user_id):
            await query.answer("✅ تم الحذف")
        else:
            await query.answer("❌ فشل الحذف")

        await self.show_groups(update, context)


    # ==================================================
    # START JOIN GROUPS
    # ==================================================

    async def start_join_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if self.manager.start_join_groups(user_id):
            await query.edit_message_text("🚀 بدأ الانضمام إلى المجموعات")
        else:
            await query.edit_message_text("⚠️ عملية الانضمام تعمل بالفعل")


    # ==================================================
    # STOP JOIN GROUPS
    # ==================================================

    async def stop_join_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if self.manager.stop_join_groups(user_id):
            await query.edit_message_text("⏹️ تم إيقاف الانضمام")
        else:
            await query.edit_message_text("⚠️ الانضمام غير نشط")


    # ==================================================
    # GROUP STATS
    # ==================================================

    async def show_group_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        groups = self.db.get_groups(user_id)

        total = len(groups)

        pending = len([g for g in groups if g[2] == "pending"])
        joined = len([g for g in groups if g[2] == "joined"])
        failed = len([g for g in groups if g[2] == "failed"])

        text = (
            "📊 إحصائيات المجموعات\n\n"
            f"👥 الإجمالي: {total}\n"
            f"⏳ معلقة: {pending}\n"
            f"✅ منضمة: {joined}\n"
            f"❌ فشل: {failed}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="group_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_groups")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
