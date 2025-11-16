import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # URLs
    LOGIN_URL = os.getenv('LOGIN_URL', 'https://boxmagic.cl/login')
    CALENDAR_URL = os.getenv('CALENDAR_URL', 'https://boxmagic.cl/horarios/agenda_general')
    
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
    
    @classmethod
    def validate(cls):
        if not all([cls.USERNAME, cls.PASSWORD]):
            raise ValueError("Missing USERNAME or PASSWORD in .env file")
        
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
