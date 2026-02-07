from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import ADD_ADMIN, OWNER_ID
from menus import show_admins_menu


# ==================================================
# START ADD ADMIN (OWNER ONLY)
# ==================================================

async def add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # 🔒 المالك فقط
    if user_id != OWNER_ID:
        await query.edit_message_text(
            "❌ هذه العملية متاحة للمالك الرئيسي فقط.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_admins")]
            ])
        )
        return ConversationHandler.END

    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_add_admin")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_admins")]
    ]

    await query.edit_message_text(
        "👤 أرسل آيدي المستخدم (ID) لإضافته كمشرف:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ADD_ADMIN


# ==================================================
# RECEIVE ADMIN ID
# ==================================================

async def add_admin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):

    db = context.application.bot_data["db"]
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text("❌ أرسل آيدي رقمي صحيح")
        return ADD_ADMIN

    admin_id = int(text)

    success, _ = db.add_admin(
        admin_id=admin_id,
        username="admin",
        role="مشرف",
        active=True
    )

    if success:
        await update.message.reply_text("✅ تم إضافة المشرف بنجاح")
    else:
        await update.message.reply_text("❌ فشل إضافة المشرف")

    context.user_data.clear()
    return ConversationHandler.END


# ==================================================
# CANCEL
# ==================================================

async def cancel_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_admins_menu(update, context)

    return ConversationHandler.END


# ==================================================
# BACK
# ==================================================

async def back_to_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    if update.callback_query:
        await update.callback_query.answer()
        await show_admins_menu(update, context)

    return ConversationHandler.END


# ==================================================
# CONVERSATION HANDLER
# ==================================================

def get_add_admin_conversation():

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_admin_start, pattern="^add_admin$")
        ],
        states={
            ADD_ADMIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_receive)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_admin, pattern="^cancel_add_admin$"),
            CallbackQueryHandler(back_to_admins, pattern="^back_admins$")
        ],
        name="add_admin_conversation",
        persistent=False
    )
