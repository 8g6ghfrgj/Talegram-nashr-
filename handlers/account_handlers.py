from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from menus import show_accounts_menu


class AccountHandlers:

    def __init__(self, db):
        self.db = db


    # ==================================================
    # SHOW ACCOUNTS
    # ==================================================

    async def show_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        accounts = self.db.get_accounts(admin_id)

        if not accounts:
            await query.edit_message_text(
                "❌ لا توجد حسابات مضافة",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_accounts")]
                ])
            )
            return

        text = "👥 الحسابات:\n\n"
        keyboard = []

        for acc in accounts:
            acc_id, _, session, active, added = acc
            status = "✅ نشط" if active == 1 else "⛔ معطل"

            text += f"#{acc_id} — {status}\n"
            text += f"{added}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    "🔁 تفعيل / تعطيل",
                    callback_data=f"toggle_account_{acc_id}"
                ),
                InlineKeyboardButton(
                    "🗑 حذف",
                    callback_data=f"delete_account_{acc_id}"
                )
            ])

        keyboard.append(
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_accounts")]
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # TOGGLE ACCOUNT
    # ==================================================

    async def toggle_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE, account_id: int):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        self.db.toggle_account_status(account_id, admin_id)

        await self.show_accounts(update, context)


    # ==================================================
    # DELETE ACCOUNT
    # ==================================================

    async def delete_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE, account_id: int):

        query = update.callback_query
        await query.answer()

        admin_id = query.from_user.id
        self.db.delete_account(account_id, admin_id)

        await self.show_accounts(update, context)
