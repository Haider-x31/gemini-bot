hereimport yt_dlp
import os
import asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)

class YTDLPHandler:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
        }
    
    async def get_info(self, url):
        """Extract video info"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                return info
        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            return None
    
    async def download(self, url, quality=None, is_audio=False, is_vip=False):
        """Download media"""
        opts = self.ydl_opts.copy()
        
        # Set output template
        opts['outtmpl'] = os.path.join(Config.DOWNLOAD_PATH, '%(title)s.%(ext)s')
        
        if is_audio:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            if quality:
                height = int(quality.replace('p', ''))
                opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            else:
                opts['format'] = 'bestvideo+bestaudio/best'
            
            # For VIP users, allow higher bitrate
            if is_vip:
                opts['postprocessor_args'] = ['-preset', 'veryfast']
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                filename = ydl.prepare_filename(info)
                
                if is_audio:
                    filename = filename.rsplit('.', 1)[0] + '.mp3'
                
                return filename
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None

ytdlp = YTDLPHandler()
download_media = ytdlp.download
