import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
    
    # Database
    USE_MONGODB = os.getenv("USE_MONGODB", "False").lower() == "true"
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "downloader_bot")
    
    # SQLite fallback
    SQLITE_PATH = os.getenv("SQLITE_PATH", "data.db")
    
    # Download settings
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "downloads/")
    ALLOWED_FORMATS = ["mp4", "mp3", "webm"]
    
    # Points & VIP
    DEFAULT_POINTS = int(os.getenv("DEFAULT_POINTS", 100))
    POINTS_PER_DOWNLOAD = int(os.getenv("POINTS_PER_DOWNLOAD", 10))
    VIP_PRICE = int(os.getenv("VIP_PRICE", 1000))
    VIP_DURATION_DAYS = int(os.getenv("VIP_DURATION_DAYS", 30))
    
    # Rate limiting
    RATE_LIMIT_DOWNLOADS = int(os.getenv("RATE_LIMIT_DOWNLOADS", 10))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", 60))  # seconds
    
    # Webhook/Keep alive
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.getenv("PORT", 8080))
    
    # Channel subscription
    FORCE_SUB_CHANNELS = os.getenv("FORCE_SUB_CHANNELS", "").split(",")
    
    @classmethod
    def validate(cls):
        assert cls.BOT_TOKEN, "BOT_TOKEN is required"
        if not cls.ADMIN_IDS or cls.ADMIN_IDS == [0]:
            raise ValueError("ADMIN_IDS must be set in .env")
