from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from menus import show_accounts_menu
from config import ADD_ACCOUNT


# ==================================================
# START ADD ACCOUNT
# ==================================================

async def add_account_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_add_account")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_accounts")]
    ]

    await query.edit_message_text(
        "📥 أرسل جلسة Telethon (StringSession):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ADD_ACCOUNT


# ==================================================
# RECEIVE SESSION
# ==================================================

async def add_account_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    session = update.message.text.strip()
    user_id = update.effective_user.id
    db = context.application.bot_data["db"]

    if len(session) < 50:
        await update.message.reply_text("❌ الجلسة غير صالحة")
        return ADD_ACCOUNT

    success, msg = db.add_account(user_id, session)

    if success:
        await update.message.reply_text("✅ تم إضافة الحساب بنجاح")
    else:
        await update.message.reply_text(f"❌ فشل الإضافة: {msg}")

    context.user_data.clear()
    return ConversationHandler.END


# ==================================================
# CANCEL
# ==================================================

async def cancel_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_accounts_menu(update, context)

    return ConversationHandler.END


# ==================================================
# BACK
# ==================================================

async def back_to_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_accounts_menu(update, context)

    return ConversationHandler.END


# ==================================================
# CONVERSATION HANDLER
# ==================================================

def get_add_account_conversation():

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_account_start, pattern="^add_account$")
        ],
        states={
            ADD_ACCOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_receive)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_account, pattern="^cancel_add_account$"),
            CallbackQueryHandler(back_to_accounts, pattern="^back_accounts$")
        ],
        name="add_account_conversation",
        persistent=False
    )
