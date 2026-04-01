Enterfrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_manager import db
from utils.helpers import create_main_keyboard, check_subscription
import re

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user exists
    existing = await db.get_user(user.id)
    if not existing:
        # Handle referral
        referred_by = None
        if context.args and context.args[0].startswith("ref_"):
            code = context.args[0][4:]
            ref_user = await db.get_user_by_referral_code(code)
            if ref_user:
                referred_by = ref_user["user_id"]
        
        await db.create_user(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            referred_by=referred_by
        )
        
        # Welcome message
        welcome_msg = await db.get_message("welcome", f"""
🎉 *مرحباً بك في بوت التحميل الشامل* {user.full_name}!

✨ يمكنك تحميل الفيديوهات من:
• YouTube (فيديو، صوت، Shorts، قوائم)
• TikTok (بدون علامة مائية)
• Instagram (Reels, Posts, Stories)
• Facebook, Twitter/X

🎁 تم إضافة {await db.get_message("default_points", "100")} نقطة مجاناً!

استخدم الأزرار أدناه للبدء 🚀
        """)
        
        keyboard = await create_main_keyboard(user.id)
        await update.message.reply_text(
            welcome_msg,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        # Return user
        keyboard = await create_main_keyboard(user.id)
        await update.message.reply_text(
            f"✨ أهلاً بعودتك {user.full_name}!",
            reply_markup=keyboard
        )
    
    # Check channel subscription
    await check_subscription(update, context)
