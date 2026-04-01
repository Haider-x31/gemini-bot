import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from database.db_manager import db
from handlers import start, download, points, vip, profile, referral, admin
from utils.rate_limiter import RateLimiter
from web.keep_alive import keep_alive
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DownloaderBot:
    def __init__(self):
        self.application = None
        self.rate_limiter = RateLimiter()
        
    async def init(self):
        """Initialize bot components"""
        await db.connect()
        logger.info("Database connected")
        
        # Create download directory
        os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
        
    async def setup_handlers(self):
        """Setup all handlers"""
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", start.start_command))
        self.application.add_handler(CommandHandler("admin", admin.admin_panel))
        self.application.add_handler(CommandHandler("my", profile.my_profile))
        self.application.add_handler(CommandHandler("points", points.show_points))
        self.application.add_handler(CommandHandler("vip", vip.show_vip_info))
        self.application.add_handler(CommandHandler("referral", referral.referral_info))
        self.application.add_handler(CommandHandler("stats", admin.stats_command, filters=filters.Chat(Config.ADMIN_IDS)))
        
        # Message handler for URLs
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            download.handle_url
        ))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(download.handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
    async def error_handler(self, update, context):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ حدث خطأ. الرجاء المحاولة مرة أخرى."
            )
    
    async def start(self):
        """Start the bot"""
        await self.init()
        await self.setup_handlers()
        
        # Start webhook or polling
        if Config.WEBHOOK_URL:
            await self.application.bot.set_webhook(Config.WEBHOOK_URL)
            self.application.run_webhook(
                listen="0.0.0.0",
                port=Config.PORT,
                url_path=Config.BOT_TOKEN,
                webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
            )
        else:
            # Start keep-alive server if on Render
            if os.environ.get("RENDER"):
                keep_alive()
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Bot started polling")
            await asyncio.Event().wait()  # Keep running

if __name__ == "__main__":
    bot = DownloaderBot()
    asyncio.run(bot.start())
