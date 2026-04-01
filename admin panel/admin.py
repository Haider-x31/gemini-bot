herefrom telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_manager import db
from config import Config
from utils.helpers import admin_only
import asyncio

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel main menu"""
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("💎 إدارة VIP", callback_data="admin_vip")],
        [InlineKeyboardButton("📝 تعديل الرسائل", callback_data="admin_messages")],
        [InlineKeyboardButton("📢 إدارة القنوات", callback_data="admin_channels")],
        [InlineKeyboardButton("🏆 أفضل المستخدمين", callback_data="admin_top")],
        [InlineKeyboardButton("📜 سجل النشاط", callback_data="admin_logs")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="admin_close")]
    ]
    
    await update.message.reply_text(
        "🎛️ *لوحة تحكم الأدمن*\n\nاختر الإجراء:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    total_users = await db.get_total_users()
    total_downloads = await db.get_total_downloads()
    total_vip = await db.get_total_vip()
    
    stats_text = f"""
📊 *إحصائيات البوت*

👥 إجمالي المستخدمين: {total_users}
📥 إجمالي التحميلات: {total_downloads}
💎 عدد VIP: {total_vip}

🟢 البوت يعمل بكفاءة
    """
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

@admin_only
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if not context.args:
        await update.message.reply_text(
            "📢 *إرسال رسالة جماعية*\n\n"
            "استخدم:\n`/broadcast نص الرسالة`\n\n"
            "لإرسال رسالة للجميع",
            parse_mode="Markdown"
        )
        return
    
    message = " ".join(context.args)
    users = await db.get_all_users()
    
    sent = 0
    failed = 0
    
    progress_msg = await update.message.reply_text("🔄 جاري الإرسال...")
    
    for user in users:
        try:
            await context.bot.send_message(
                user["user_id"],
                message,
                parse_mode="Markdown"
            )
            sent += 1
            await asyncio.sleep(0.05)  # Avoid hitting rate limits
        except:
            failed += 1
    
    await progress_msg.edit_text(
        f"✅ تم الإرسال بنجاح\n\n"
        f"تم الإرسال: {sent}\n"
        f"فشل: {failed}"
    )
