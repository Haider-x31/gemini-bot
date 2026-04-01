import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import aiosqlite
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from utils.logger import logger

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.use_mongo = Config.USE_MONGODB
        
    async def connect(self):
        if self.use_mongo:
            self.client = AsyncIOMotorClient(Config.MONGODB_URI)
            self.db = self.client[Config.DATABASE_NAME]
            await self._create_mongo_indexes()
        else:
            self.conn = await aiosqlite.connect(Config.SQLITE_PATH)
            await self._create_sqlite_tables()
        logger.info(f"Database connected (Mongo: {self.use_mongo})")
    
    async def _create_mongo_indexes(self):
        await self.db.users.create_index("user_id", unique=True)
        await self.db.users.create_index("referral_code", unique=True)
        await self.db.vips.create_index("user_id", unique=True)
    
    async def _create_sqlite_tables(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                points INTEGER DEFAULT 100,
                total_downloads INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vips (
                user_id INTEGER PRIMARY KEY,
                expires_at TIMESTAMP
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                key TEXT PRIMARY KEY,
                text TEXT
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                chat_id TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.conn.commit()
    
    # User methods
    async def get_user(self, user_id: int) -> Optional[Dict]:
        if self.use_mongo:
            return await self.db.users.find_one({"user_id": user_id})
        else:
            async with self.conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def create_user(self, user_id: int, username: str = None, full_name: str = None, referred_by: int = None):
        referral_code = f"REF{user_id}"
        now = datetime.now()
        
        if self.use_mongo:
            user = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "points": Config.DEFAULT_POINTS,
                "total_downloads": 0,
                "referral_code": referral_code,
                "referred_by": referred_by,
                "created_at": now
            }
            await self.db.users.insert_one(user)
            
            # Give referral bonus
            if referred_by:
                await self.add_points(referred_by, 50)
                await self.log_action(referred_by, "referral", f"Referred {user_id}")
        else:
            await self.conn.execute("""
                INSERT INTO users (user_id, username, full_name, points, referral_code, referred_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, full_name, Config.DEFAULT_POINTS, referral_code, referred_by))
            await self.conn.commit()
            
            if referred_by:
                await self.add_points(referred_by, 50)
        
        return await self.get_user(user_id)
    
    async def update_user(self, user_id: int, **kwargs):
        if self.use_mongo:
            await self.db.users.update_one({"user_id": user_id}, {"$set": kwargs})
        else:
            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            await self.conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
            await self.conn.commit()
    
    async def add_points(self, user_id: int, points: int):
        if self.use_mongo:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"points": points}}
            )
        else:
            await self.conn.execute(
                "UPDATE users SET points = points + ? WHERE user_id = ?",
                (points, user_id)
            )
            await self.conn.commit()
    
    async def deduct_points(self, user_id: int, points: int) -> bool:
        user = await self.get_user(user_id)
        if user and user.get("points", 0) >= points:
            if self.use_mongo:
                await self.db.users.update_one(
                    {"user_id": user_id},
                    {"$inc": {"points": -points}}
                )
            else:
                await self.conn.execute(
                    "UPDATE users SET points = points - ? WHERE user_id = ?",
                    (points, user_id)
                )
                await self.conn.commit()
            return True
        return False
    
    async def increment_downloads(self, user_id: int):
        if self.use_mongo:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"total_downloads": 1}}
            )
        else:
            await self.conn.execute(
                "UPDATE users SET total_downloads = total_downloads + 1 WHERE user_id = ?",
                (user_id,)
            )
            await self.conn.commit()
    
    # VIP methods
    async def is_vip(self, user_id: int) -> bool:
        if self.use_mongo:
            vip = await self.db.vips.find_one({"user_id": user_id})
            if vip and vip.get("expires_at") > datetime.now():
                return True
        else:
            async with self.conn.execute(
                "SELECT expires_at FROM vips WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and datetime.fromisoformat(row[0]) > datetime.now():
                    return True
        return False
    
    async def set_vip(self, user_id: int, days: int = Config.VIP_DURATION_DAYS):
        expires_at = datetime.now() + timedelta(days=days)
        if self.use_mongo:
            await self.db.vips.update_one(
                {"user_id": user_id},
                {"$set": {"expires_at": expires_at}},
                upsert=True
            )
        else:
            await self.conn.execute(
                "INSERT OR REPLACE INTO vips (user_id, expires_at) VALUES (?, ?)",
                (user_id, expires_at.isoformat())
            )
            await self.conn.commit()
    
    # Messages
    async def get_message(self, key: str, default: str) -> str:
        if self.use_mongo:
            msg = await self.db.messages.find_one({"key": key})
            return msg.get("text", default) if msg else default
        else:
            async with self.conn.execute(
                "SELECT text FROM messages WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
    
    async def set_message(self, key: str, text: str):
        if self.use_mongo:
            await self.db.messages.update_one(
                {"key": key},
                {"$set": {"text": text}},
                upsert=True
            )
        else:
            await self.conn.execute(
                "INSERT OR REPLACE INTO messages (key, text) VALUES (?, ?)",
                (key, text)
            )
            await self.conn.commit()
    
    # Channels
    async def get_force_channels(self) -> List[str]:
        if self.use_mongo:
            channels = await self.db.channels.find().to_list(length=None)
            return [ch["chat_id"] for ch in channels]
        else:
            async with self.conn.execute("SELECT chat_id FROM channels") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    
    async def add_channel(self, chat_id: str, name: str = None):
        if self.use_mongo:
            await self.db.channels.update_one(
                {"chat_id": chat_id},
                {"$set": {"name": name}},
                upsert=True
            )
        else:
            await self.conn.execute(
                "INSERT OR REPLACE INTO channels (chat_id, name) VALUES (?, ?)",
                (chat_id, name)
            )
            await self.conn.commit()
    
    async def remove_channel(self, chat_id: str):
        if self.use_mongo:
            await self.db.channels.delete_one({"chat_id": chat_id})
        else:
            await self.conn.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
            await self.conn.commit()
    
    # Logging
    async def log_action(self, user_id: int, action: str, details: str = None):
        if self.use_mongo:
            await self.db.logs.insert_one({
                "user_id": user_id,
                "action": action,
                "details": details,
                "timestamp": datetime.now()
            })
        else:
            await self.conn.execute(
                "INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details)
            )
            await self.conn.commit()
    
    # Statistics
    async def get_total_users(self) -> int:
        if self.use_mongo:
            return await self.db.users.count_documents({})
        else:
            async with self.conn.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        if self.use_mongo:
            cursor = self.db.users.find().sort("total_downloads", -1).limit(limit)
            return await cursor.to_list(length=limit)
        else:
            async with self.conn.execute(
                "SELECT user_id, username, total_downloads FROM users ORDER BY total_downloads DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"user_id": r[0], "username": r[1], "total_downloads": r[2]} for r in rows]

db = Database()
