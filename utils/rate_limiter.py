Enterimport time
from collections import defaultdict
from config import Config

class RateLimiter:
    def __init__(self):
        self.downloads = defaultdict(list)
    
    async def is_allowed(self, user_id: int, action: str = "download") -> bool:
        """Check if user is within rate limits"""
        if action == "download":
            now = time.time()
            user_downloads = self.downloads[user_id]
            
            # Remove old entries
            user_downloads = [t for t in user_downloads if now - t < Config.RATE_LIMIT_PERIOD]
            self.downloads[user_id] = user_downloads
            
            if len(user_downloads) >= Config.RATE_LIMIT_DOWNLOADS:
                return False
            
            self.downloads[user_id].append(now)
            return True
        
        return True

rate_limiter = RateLimiter()
rate_limit = rate_limiter.is_allowed
