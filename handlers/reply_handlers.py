import os
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    ADD_PRIVATE_TEXT,
    ADD_RANDOM_REPLY,
    MESSAGES
)

logger = logging.getLogger(__name__)


class ReplyHandlers:

    def __init__(self, db, manager):
        self.db = db
        self.manager = manager


    # ==================================================
    # REPLIES MENU
    # ==================================================

    async def manage_replies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return

        keyboard = [
            [InlineKeyboardButton("➕ إضافة رد خاص", callback_data="add_private_reply")],
            [InlineKeyboardButton("➕ إضافة رد عشوائي", callback_data="add_random_reply")],
            [InlineKeyboardButton("📋 عرض الردود الخاصة", callback_data="show_private_replies")],
            [InlineKeyboardButton("📋 عرض الردود العشوائية", callback_data="show_random_replies")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]

        await query.edit_message_text(
            "💬 إدارة الردود",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # PRIVATE REPLY
    # ==================================================

    async def add_private_reply_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return ConversationHandler.END

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]
        ]

        await query.edit_message_text(
            "📝 أرسل نص الرد الخاص:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADD_PRIVATE_TEXT


    async def add_private_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        message = update.message
        user_id = message.from_user.id

        text = message.text.strip()

        if len(text) < 1:
            await message.reply_text("❌ النص فارغ")
            return ADD_PRIVATE_TEXT

        success, msg = self.db.add_private_reply(user_id, text)

        if success:
            await message.reply_text("✅ تم إضافة الرد الخاص")
        else:
            await message.reply_text(f"❌ {msg}")

        context.user_data.clear()
        return ConversationHandler.END


    # ==================================================
    # RANDOM REPLY (TEXT + OPTIONAL PHOTO)
    # ==================================================

    async def add_random_reply_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        if not self.db.is_admin(user_id):
            await query.edit_message_text(MESSAGES["unauthorized"])
            return ConversationHandler.END

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("⏭ تخطي الصورة", callback_data="skip_media")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]
        ]

        await query.edit_message_text(
            "📝 أرسل نص الرد العشوائي (أو اضغط تخطي لإضافة صورة فقط):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADD_RANDOM_REPLY


    async def add_random_reply_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        message = update.message

        text = message.text.strip()

        if len(text) < 1:
            await message.reply_text("❌ النص فارغ")
            return ADD_RANDOM_REPLY

        context.user_data["random_text"] = text

        keyboard = [
            [InlineKeyboardButton("⏭ تخطي الصورة", callback_data="skip_media")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_process")]
        ]

        await message.reply_text(
            "🖼️ أرسل صورة الرد (أو تخطي):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return ADD_RANDOM_REPLY


    async def add_random_reply_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        message = update.message
        user_id = message.from_user.id

        os.makedirs("temp_files/random_replies", exist_ok=True)

        photo = message.photo[-1]
        file = await photo.get_file()

        name = f"reply_{int(datetime.now().timestamp())}.jpg"
        path = f"temp_files/random_replies/{name}"

        await file.download_to_drive(path)

        text = context.user_data.get("random_text")

        success, msg = self.db.add_random_reply(
            user_id,
            "photo",
            text,
            path
        )

        if success:
            await message.reply_text("✅ تم إضافة الرد العشوائي بالصورة")
        else:
            await message.reply_text(f"❌ {msg}")

        context.user_data.clear()
        return ConversationHandler.END


    # ==================================================
    # SKIP MEDIA HANDLER
    # ==================================================

    async def skip_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        text = context.user_data.get("random_text")

        if not text:
            # يعني المستخدم اختار صورة فقط بدون نص
            await query.edit_message_text("🖼️ أرسل الصورة فقط:")
            return ADD_RANDOM_REPLY

        success, msg = self.db.add_random_reply(
            user_id,
            "text",
            text,
            None
        )

        if success:
            await query.edit_message_text("✅ تم إضافة الرد العشوائي النصي")
        else:
            await query.edit_message_text(f"❌ {msg}")

        context.user_data.clear()
        return ConversationHandler.END


    # ==================================================
    # SHOW PRIVATE REPLIES
    # ==================================================

    async def show_private_replies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        replies = self.db.get_private_replies(user_id)

        if not replies:
            await query.edit_message_text("❌ لا توجد ردود خاصة")
            return

        text = "💬 الردود الخاصة:\n\n"
        keyboard = []

        for r in replies[:15]:
            rid, admin_id, rtext, added = r

            text += f"#{rid}\n{rtext}\n{added}\n──────────\n"

            keyboard.append([
                InlineKeyboardButton(
                    "🗑 حذف",
                    callback_data=f"delete_private_reply_{rid}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔄 تحديث", callback_data="show_private_replies"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_replies")
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # SHOW RANDOM REPLIES
    # ==================================================

    async def show_random_replies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):

        query = update.callback_query
        user_id = query.from_user.id

        replies = self.db.get_random_replies(user_id)

        if not replies:
            await query.edit_message_text("❌ لا توجد ردود عشوائية")
            return

        text = "🎲 الردود العشوائية:\n\n"
        keyboard = []

        for r in replies[:15]:
            rid, admin_id, rtype, rtext, media, added = r

            icon = "📝" if rtype == "text" else "🖼️"

            text += f"#{rid} {icon}\n"

            if rtext:
                text += f"{rtext[:40]}...\n"

            text += f"{added}\n──────────\n"

            keyboard.append([
                InlineKeyboardButton(
                    "🗑 حذف",
                    callback_data=f"delete_random_reply_{rid}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔄 تحديث", callback_data="show_random_replies"),
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_replies")
        ])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # ==================================================
    # DELETE REPLIES
    # ==================================================

    async def delete_private_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, reply_id: int):

        query = update.callback_query
        user_id = query.from_user.id

        if self.db.delete_private_reply(reply_id, user_id):
            await query.answer("✅ تم الحذف")
        else:
            await query.answer("❌ فشل الحذف")

        await self.show_private_replies(update, context)


    async def delete_random_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE, reply_id: int):

        query = update.callback_query
        user_id = query.from_user.id

        if self.db.delete_random_reply(reply_id, user_id):
            await query.answer("✅ تم الحذف")
        else:
            await query.answer("❌ فشل الحذف")

        await self.show_random_replies(update, context)
