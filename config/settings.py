import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # URLs
    LOGIN_URL = os.getenv('LOGIN_URL', 'https://boxmagic.cl/login')
    CALENDAR_URL = os.getenv('CALENDAR_URL', 'https://boxmagic.cl/horarios/agenda_general')
    CHECKIN_URL = os.getenv('CHECKIN_URL', 'https://boxmagic.cl/checkin/clases')
    
    # Credentials
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / 'data' / 'output'
    LOG_DIR = BASE_DIR / 'logs'
    SCREENSHOTS_DIR = BASE_DIR / 'screenshots'
    
    # Browser settings
    HEADLESS = False  # Set to True to hide browser
    TIMEOUT = 30000  # 30 seconds in milliseconds
    TIMEZONE = os.getenv('TIMEZONE', 'America/Mexico_City')
    
    # API/Server settings
    PORT = int(os.getenv('PORT', 5000))
    FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 3000))
    # Frontend URL - use explicit URL if provided, otherwise build from port
    _frontend_url = os.getenv('FRONTEND_URL')
    FRONTEND_URL = _frontend_url if _frontend_url else f'http://localhost:{FRONTEND_PORT}'
    
    @classmethod
    def validate(cls):
        if not all([cls.USERNAME, cls.PASSWORD]):
            raise ValueError("Missing USERNAME or PASSWORD in .env file")
        
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
