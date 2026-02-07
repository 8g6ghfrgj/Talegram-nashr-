from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import ADD_GROUP
from menus import show_groups_menu


# ==================================================
# START ADD GROUP
# ==================================================

async def add_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_add_group")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_groups")]
    ]

    await query.edit_message_text(
        "👥 أرسل رابط المجموعة أو الـ @username:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ADD_GROUP


# ==================================================
# RECEIVE GROUP LINK
# ==================================================

async def add_group_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()
    user_id = update.effective_user.id
    db = context.application.bot_data["db"]

    # تحقق بسيط
    if not (
        text.startswith("https://t.me/")
        or text.startswith("t.me/")
        or text.startswith("@")
    ):
        await update.message.reply_text(
            "❌ الرابط غير صحيح\n"
            "أرسل رابط مثل:\n"
            "https://t.me/example\n"
            "أو @example"
        )
        return ADD_GROUP

    success, msg = db.add_group(user_id, text)

    if success:
        await update.message.reply_text("✅ تم إضافة المجموعة بنجاح")
    else:
        await update.message.reply_text(f"❌ فشل الإضافة: {msg}")

    context.user_data.clear()
    return ConversationHandler.END


# ==================================================
# CANCEL
# ==================================================

async def cancel_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_groups_menu(update, context)

    return ConversationHandler.END


# ==================================================
# BACK
# ==================================================

async def back_to_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_groups_menu(update, context)

    return ConversationHandler.END


# ==================================================
# CONVERSATION HANDLER
# ==================================================

def get_add_group_conversation():

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_group_start, pattern="^add_group$")
        ],
        states={
            ADD_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_group_receive)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_group, pattern="^cancel_add_group$"),
            CallbackQueryHandler(back_to_groups, pattern="^back_groups$")
        ],
        name="add_group_conversation",
        persistent=False
    )
