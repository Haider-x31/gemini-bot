herefrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_manager import db
from config import Config

async def create_main_keyboard(user_id: int):
    """Create main menu keyboard"""
    is_vip = await db.is_vip(user_id)
    user = await db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📥 تحميل فيديو", callback_data="download_video")],
        [InlineKeyboardButton("🎵 تحميل صوت", callback_data="download_audio")],
        [
            InlineKeyboardButton("👤 حسابي", callback_data="profile"),
            InlineKeyboardButton("💎 نقاطي", callback_data="points")
        ],
        [
            InlineKeyboardButton("👑 VIP", callback_data="vip_info"),
            InlineKeyboardButton("🎁 إحالة", callback_data="referral")
        ],
        [InlineKeyboardButton("📞 دعم", callback_data="support")],
        [InlineKeyboardButton("📢 قنوات السيرفر", callback_data="channels")]
    ]
    
    if is_vip:
        keyboard.insert(2, [InlineKeyboardButton("✨ مميزات VIP", callback_data="vip_features")])
    
    return InlineKeyboardMarkup(keyboard)

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is subscribed to all required channels"""
    user_id = update.effective_user.id
    channels = await db.get_force_channels()
    
    if not channels:
        return True
    
    not_subscribed = []
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    
    if not_subscribed:
        keyboard = []
        for channel in not_subscribed:
            keyboard.append([InlineKeyboardButton(
                "📢 اشترك في القناة",
                url=f"https://t.me/{channel.replace('@', '')}"
            )])
        keyboard.append([InlineKeyboardButton("✅ تحقق", callback_data="check_sub")])
        
        await update.message.reply_text(
            "⚠️ للاستمرار في استخدام البوت، يجب الاشتراك في القنوات التالية:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    
    return True

def format_file_size(bytes):
    """Format file size to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"

def human_readable_time(seconds):
    """Convert seconds to human readable time"""
    if not seconds:
        return "غير معروف"
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days > 0:
        parts.append(f"{days} يوم")
    if hours > 0:
        parts.append(f"{hours} ساعة")
    if minutes > 0:
        parts.append(f"{minutes} دقيقة")
    if seconds > 0:
        parts.append(f"{seconds} ثانية")
    
    return " ".join(parts[:2])
