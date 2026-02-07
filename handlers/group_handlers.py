from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from menus import show_groups_menu


class GroupHandlers:

    def __init__(self, db):
        self.db = db


    # ==================================================
    # SHOW GROUPS
    # ==================================================

    async def show_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        groups = self.db.get_groups(admin_id)

        if not groups:
            await query.edit_message_text(
                "❌ لا توجد مجموعات مضافة",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_groups")]
                ])
            )
            return

        text = "👥 المجموعات:\n\n"
        keyboard = []

        for grp in groups:
            group_id, _, link, status, added = grp

            status_text = {
                "pending": "⏳ معلقة",
                "joined": "✅ منضمة",
                "failed": "❌ فشل"
            }.get(status, status)

            text += f"#{group_id} — {status_text}\n"
            text += f"{link}\n"
            text += f"{added}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    "🗑 حذف",
                    callback_data=f"delete_group_{group_id}"
                )
            ])

        keyboard.append(
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_groups")]
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # DELETE GROUP
    # ==================================================

    async def delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: int):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        self.db.delete_group(group_id, admin_id)

        await self.show_groups(update, context)


    # ==================================================
    # GROUP STATS
    # ==================================================

    async def group_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        groups = self.db.get_groups(admin_id)

        total = len(groups)
        pending = sum(1 for g in groups if g[3] == "pending")
        joined = sum(1 for g in groups if g[3] == "joined")
        failed = sum(1 for g in groups if g[3] == "failed")

        text = (
            "📊 إحصائيات المجموعات\n\n"
            f"👥 الإجمالي: {total}\n"
            f"⏳ معلقة: {pending}\n"
            f"✅ منضمة: {joined}\n"
            f"❌ فشل: {failed}"
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_groups")]
            ])
        )
