hereimport os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from downloader.yt_dlp_handler import download_media
from database.db_manager import db
from config import Config
from utils.rate_limiter import rate_limit
from utils.helpers import format_file_size, human_readable_time
import logging

logger = logging.getLogger(__name__)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle URLs sent by user"""
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    # Rate limiting
    if not await rate_limit(user_id, "download"):
        await update.message.reply_text(
            "⏳ لديك عدد تحميل كبير جداً. الرجاء الانتظار قليلاً."
        )
        return
    
    # Check VIP status
    is_vip = await db.is_vip(user_id)
    user = await db.get_user(user_id)
    
    # Deduct points if not VIP
    if not is_vip:
        points_needed = Config.POINTS_PER_DOWNLOAD
        if user.get("points", 0) < points_needed:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 شراء نقاط", callback_data="buy_points")
            ]])
            await update.message.reply_text(
                f"⚠️ رصيدك لا يكفي للتحميل!\n"
                f"تحتاج {points_needed} نقطة\n"
                f"رصيدك الحالي: {user.get('points', 0)} نقطة",
                reply_markup=keyboard
            )
            return
        await db.deduct_points(user_id, points_needed)
    
    # Send processing message
    msg = await update.message.reply_text("🔄 جاري تحليل الرابط...")
    
    try:
        # Get video info
        info = await download_media(url, get_info_only=True)
        
        if not info:
            await msg.edit_text("❌ رابط غير صالح أو غير مدعوم")
            return
        
        # Create quality selection keyboard
        keyboard = []
        formats = info.get('formats', [])
        qualities = ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '2160p', '4K']
        
        for q in qualities:
            if any(f.get('height') == int(q.replace('p', '')) for f in formats):
                keyboard.append([InlineKeyboardButton(
                    f"📹 {q}", 
                    callback_data=f"quality_{q}_{url}"
                )])
        
        keyboard.append([InlineKeyboardButton("🎵 MP3 فقط", callback_data=f"audio_{url}")])
        
        info_text = f"""
📹 *{info.get('title', 'فيديو')}*

⏱️ المدة: {human_readable_time(info.get('duration', 0))}
📊 الحجم: {format_file_size(info.get('filesize', 0))}
👁️ المشاهدات: {info.get('view_count', 0)}
❤️ الإعجابات: {info.get('like_count', 0)}

اختر الجودة:
        """
        
        await msg.edit_text(
            info_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await msg.edit_text("❌ حدث خطأ أثناء معالجة الرابط")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("quality_"):
        _, quality, url = data.split("_", 2)
        await download_and_send(query, url, quality, is_audio=False)
        
    elif data.startswith("audio_"):
        _, url = data.split("_", 1)
        await download_and_send(query, url, None, is_audio=True)
        
    elif data == "buy_points":
        await show_points_packages(query)

async def download_and_send(query, url, quality=None, is_audio=False):
    """Download and send the media"""
    user_id = query.from_user.id
    await query.edit_message_text("📥 جاري التحميل...")
    
    try:
        # Check if VIP for faster download
        is_vip = await db.is_vip(user_id)
        
        # Download media
        file_path = await download_media(
            url, 
            quality=quality, 
            is_audio=is_audio,
            is_vip=is_vip
        )
        
        if not file_path or not os.path.exists(file_path):
            await query.edit_message_text("❌ فشل التحميل")
            return
        
        # Increment download count
        await db.increment_downloads(user_id)
        
        # Send file
        file_size = os.path.getsize(file_path)
        
        if file_size > Config.MAX_FILE_SIZE:
            # Send as document if too large
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=os.path.basename(file_path),
                    caption="✅ تم التحميل بنجاح"
                )
        else:
            if is_audio:
                with open(file_path, 'rb') as f:
                    await query.message.reply_audio(
                        audio=f,
                        title=os.path.basename(file_path)
                    )
            else:
                with open(file_path, 'rb') as f:
                    await query.message.reply_video(
                        video=f,
                        caption="✅ تم التحميل بنجاح"
                    )
        
        await query.delete_message()
        
        # Cleanup
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"Download and send error: {e}")
        await query.edit_message_text("❌ حدث خطأ أثناء التحميل")
