from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from menus import show_main_menu

SET_DELAY = 100  # حالة محادثة مستقلة (لا تتعارض)


# ==================================================
# START
# ==================================================

async def set_delay_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "⏱ أرسل عدد الثواني بين كل مجموعة (مثال: 5):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_set_delay")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
    )

    return SET_DELAY


# ==================================================
# RECEIVE DELAY
# ==================================================

async def set_delay_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    manager = context.application.bot_data["manager"]

    try:
        delay = float(update.message.text)

        if delay < 1:
            await update.message.reply_text("❌ أقل مدة هي 1 ثانية")
            return SET_DELAY

        manager.publish_delay = delay
        await update.message.reply_text(f"✅ تم ضبط وقت النشر إلى {delay} ثانية")

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ أرسل رقم صحيح")
        return SET_DELAY


# ==================================================
# CANCEL
# ==================================================

async def cancel_set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_main_menu(update, context)

    return ConversationHandler.END


# ==================================================
# BACK
# ==================================================

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_main_menu(update, context)

    return ConversationHandler.END


# ==================================================
# CONVERSATION
# ==================================================

def get_set_publish_delay_conversation():

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(set_delay_start, pattern="^menu_set_delay$")
        ],
        states={
            SET_DELAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_delay_receive)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_set_delay, pattern="^cancel_set_delay$"),
            CallbackQueryHandler(back_main, pattern="^back_main$")
        ],
        name="set_publish_delay_conversation",
        persistent=False
    )
