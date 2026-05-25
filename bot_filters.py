from telegram import Update
from telegram.ext import ContextTypes


def admin_reply_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.admin import is_admin
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and is_admin(user_id):
            chat = update.effective_chat
            # في المحادثة الخاصة (DM) لا يُطبَّق الفلتر أبداً
            if chat and chat.type == "private":
                return await func(update, context)
            msg = update.message
            if msg:
                reply = msg.reply_to_message
                if not reply or not reply.from_user or reply.from_user.id != context.bot.id:
                    return
        return await func(update, context)
    return wrapper
