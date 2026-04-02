herefrom functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import Config

def admin_only(func):
    """Decorator to restrict command to admins only"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ هذا الأمر مخصص للأدمن فقط")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def check_subscription(func):
    """Decorator to check channel subscription"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from utils.helpers import check_subscription as check_sub
        if not await check_sub(update, context):
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
