from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import threading
import os
from zoneinfo import ZoneInfo

from config.settings import Config
from src.scraper_playwright import BoxMagicScraper

os.makedirs("logs", exist_ok=True)
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"DEBUG: PLAYWRIGHT_BROWSERS_PATH = {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all origins (no restrictions)
CORS(app)

logger.info("CORS configured for all origins")

# Global variables
LATEST_CHECKIN_DATA = {}
LATEST_CALENDAR_DATA = {}
SCRAPING_STATUS = {
    'is_scraping': False,
    'last_scrape': None,
    'last_success': None,
    'next_scheduled': None,
    'error': None
}

# File paths
DATA_DIR = Path(__file__).parent / 'data' / 'output'
LATEST_CHECKIN_FILE = DATA_DIR / 'latest_checkin.json'
LATEST_CALENDAR_FILE = DATA_DIR / 'latest_calendar.json'


def load_latest_data():
    """Load latest data from files on startup"""
    global LATEST_CHECKIN_DATA, LATEST_CALENDAR_DATA
    
    try:
        if LATEST_CHECKIN_FILE.exists():
            with open(LATEST_CHECKIN_FILE, 'r', encoding='utf-8') as f:
                LATEST_CHECKIN_DATA = json.load(f)
            logger.info(f"Loaded latest check-in data from {LATEST_CHECKIN_FILE}")
        
        if LATEST_CALENDAR_FILE.exists():
            with open(LATEST_CALENDAR_FILE, 'r', encoding='utf-8') as f:
                LATEST_CALENDAR_DATA = json.load(f)
            logger.info(f"Loaded latest calendar data from {LATEST_CALENDAR_FILE}")
    except Exception as e:
        logger.error(f"Error loading data: {e}")


def save_data_to_file(data, file_path):
    """Save data to file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {file_path}: {e}")
        return False


def run_checkin_scraper():
    """Run check-in scraper"""
    global LATEST_CHECKIN_DATA, SCRAPING_STATUS
    
    if SCRAPING_STATUS['is_scraping']:
        logger.warning("Scraping already in progress, skipping...")
        return
    
    try:
        SCRAPING_STATUS['is_scraping'] = True
        SCRAPING_STATUS['last_scrape'] = datetime.now().isoformat()
        SCRAPING_STATUS['error'] = None
        
        logger.info("="*80)
        logger.info("Starting scheduled check-in scraping...")
        logger.info("="*80)
        
        Config.validate()
        
        # Force headless mode for API server to avoid terminal issues
        original_headless = Config.HEADLESS
        Config.HEADLESS = True
        
        scraper = BoxMagicScraper(Config)
        # Auto-login if session is invalid or doesn't exist
        scraper.start_browser(use_saved_session=True, auto_login=True)
        
        # Restore original headless setting
        Config.HEADLESS = original_headless
        
        # Calculate date range (today + next 7 days)
        tz = ZoneInfo(Config.TIMEZONE)
        today = datetime.now(tz)
        days_count = 7
        
        logger.info(f"Scraping {days_count} days starting from {today.strftime('%d-%m-%Y')}")
        
        # Define callback for incremental saving
        def on_progress(data):
            global LATEST_CHECKIN_DATA
            try:
                # Update global data
                LATEST_CHECKIN_DATA = data
                # Save to file
                save_data_to_file(data, LATEST_CHECKIN_FILE)
                logger.info(f"✓ Progress saved: {len(data.get('dates', {}))} dates scraped")
            except Exception as e:
                logger.error(f"Error saving progress: {e}")

        # Scrape check-in data
        checkin_data = scraper.scrape_checkin_all_dates(
            start_date=today,
            days_count=days_count,
            on_progress=on_progress,
            existing_data=LATEST_CHECKIN_DATA
        )
        
        scraper.close()
        
        if checkin_data and checkin_data.get('dates'):
            # Save to latest file
            save_data_to_file(checkin_data, LATEST_CHECKIN_FILE)
            
            # Also save timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = DATA_DIR / f'checkin_data_{timestamp}.json'
            save_data_to_file(checkin_data, backup_file)
            
            # Update global data
            LATEST_CHECKIN_DATA = checkin_data
            
            SCRAPING_STATUS['last_success'] = datetime.now().isoformat()
            logger.info("✓ Check-in scraping completed successfully!")
        else:
            raise Exception("No data scraped")
        
    except Exception as e:
        logger.error(f"Error during scheduled scraping: {e}", exc_info=True)
        SCRAPING_STATUS['error'] = str(e)
    finally:
        SCRAPING_STATUS['is_scraping'] = False


def run_calendar_scraper():
    """Run calendar scraper"""
    global LATEST_CALENDAR_DATA, SCRAPING_STATUS
    
    try:
        logger.info("Starting scheduled calendar scraping...")
        
        Config.validate()
        
        # Force headless mode for API server to avoid terminal issues
        original_headless = Config.HEADLESS
        Config.HEADLESS = True
        
        scraper = BoxMagicScraper(Config)
        # Auto-login if session is invalid or doesn't exist
        scraper.start_browser(use_saved_session=True, auto_login=True)
        
        # Restore original headless setting
        Config.HEADLESS = original_headless
        
        # Navigate and scrape calendar
        calendar_data = scraper.scrape_calendar_with_details()
        
        scraper.close()
        
        if calendar_data and calendar_data.get('events'):
            save_data_to_file(calendar_data, LATEST_CALENDAR_FILE)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = DATA_DIR / f'calendar_data_{timestamp}.json'
            save_data_to_file(calendar_data, backup_file)
            
            LATEST_CALENDAR_DATA = calendar_data
            logger.info("✓ Calendar scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during calendar scraping: {e}", exc_info=True)


# ========================================
# API ENDPOINTS
# ========================================

@app.route('/')
def home():
    """API home"""
    return jsonify({
        'status': 'online',
        'message': 'BoxMagic API Server',
        'version': '1.0',
        'endpoints': {
            'GET /api/checkin': 'Get latest check-in data',
            'GET /api/checkin/<date>': 'Get check-in data for specific date (DD-MM-YYYY)',
            'GET /api/calendar': 'Get latest calendar/schedule data',
            'GET /api/all-data': 'Get all scraped data (check-in + calendar)',
            'GET /api/status': 'Get scraping status',
            'POST /api/scrape/now': 'Trigger immediate scraping',
            'GET /health': 'Health check'
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/status')
def status():
    """Get scraping status"""
    return jsonify({
        'status': SCRAPING_STATUS,
        'data_available': {
            'checkin': bool(LATEST_CHECKIN_DATA),
            'calendar': bool(LATEST_CALENDAR_DATA)
        }
    })


@app.route('/api/checkin')
def get_checkin_data():
    """Get all check-in data"""
    if not LATEST_CHECKIN_DATA:
        return jsonify({
            'error': 'No data available',
            'message': 'Check-in data has not been scraped yet'
        }), 404
    
    return jsonify(LATEST_CHECKIN_DATA)


@app.route('/api/checkin/<date>')
def get_checkin_by_date(date):
    """Get check-in data for specific date"""
    if not LATEST_CHECKIN_DATA:
        return jsonify({'error': 'No data available'}), 404
    
    dates = LATEST_CHECKIN_DATA.get('dates', {})
    
    if date not in dates:
        return jsonify({
            'error': 'Date not found',
            'available_dates': list(dates.keys())
        }), 404
    
    return jsonify({
        'date': date,
        'data': dates[date]
    })


@app.route('/api/checkin/class/<date>/<class_name>')
def get_checkin_by_class(date, class_name):
    """Get reservations for specific class on specific date"""
    if not LATEST_CHECKIN_DATA:
        return jsonify({'error': 'No data available'}), 404
    
    dates = LATEST_CHECKIN_DATA.get('dates', {})
    
    if date not in dates:
        return jsonify({'error': 'Date not found'}), 404
    
    classes = dates[date].get('classes', {})
    
    if class_name not in classes:
        return jsonify({
            'error': 'Class not found',
            'available_classes': list(classes.keys())
        }), 404
    
    return jsonify({
        'date': date,
        'class': class_name,
        'data': classes[class_name]
    })


@app.route('/api/calendar')
def get_calendar_data():
    """Get calendar/schedule data"""
    if not LATEST_CALENDAR_DATA:
        return jsonify({
            'error': 'No data available',
            'message': 'Calendar data has not been scraped yet'
        }), 404
    
    return jsonify(LATEST_CALENDAR_DATA)


@app.route('/api/scrape/now', methods=['POST'])
def trigger_scrape():
    """Trigger immediate scraping"""
    if SCRAPING_STATUS['is_scraping']:
        return jsonify({
            'error': 'Scraping already in progress',
            'status': SCRAPING_STATUS
        }), 409
    
    # Get scrape type from request
    data = request.get_json() or {}
    scrape_type = data.get('type', 'checkin')  # 'checkin' or 'calendar'
    
    # Run scraper in background thread
    if scrape_type == 'checkin':
        thread = threading.Thread(target=run_checkin_scraper)
    elif scrape_type == 'calendar':
        thread = threading.Thread(target=run_calendar_scraper)
    else:
        return jsonify({'error': 'Invalid scrape type'}), 400
    
    thread.start()
    
    return jsonify({
        'message': f'{scrape_type.capitalize()} scraping started',
        'status': SCRAPING_STATUS
    })


@app.route('/api/all-data')
def get_all_data():
    """Get all scraped data (both check-in and calendar)"""
    if not LATEST_CHECKIN_DATA and not LATEST_CALENDAR_DATA:
        return jsonify({
            'error': 'No data available',
            'message': 'No data has been scraped yet'
        }), 404
    
    response = {
        'scrapedAt': datetime.now().isoformat(),
        'status': SCRAPING_STATUS,
        'data': {
            'checkin': LATEST_CHECKIN_DATA if LATEST_CHECKIN_DATA else None,
            'calendar': LATEST_CALENDAR_DATA if LATEST_CALENDAR_DATA else None
        },
        'summary': {
            'checkin_available': bool(LATEST_CHECKIN_DATA),
            'calendar_available': bool(LATEST_CALENDAR_DATA),
            'total_dates': len(LATEST_CHECKIN_DATA.get('dates', {})) if LATEST_CHECKIN_DATA else 0,
            'total_classes': LATEST_CHECKIN_DATA.get('summary', {}).get('totalClasses', 0) if LATEST_CHECKIN_DATA else 0,
            'total_reservations': LATEST_CHECKIN_DATA.get('summary', {}).get('totalReservations', 0) if LATEST_CHECKIN_DATA else 0,
            'total_calendar_events': len(LATEST_CALENDAR_DATA.get('events', [])) if LATEST_CALENDAR_DATA else 0
        }
    }
    
    return jsonify(response)


# ========================================
# SCHEDULER SETUP
# ========================================

def setup_scheduler():
    """Setup scheduled scraping"""
    scheduler = BackgroundScheduler()
    
    # Schedule check-in scraping every 15 minutes
    scheduler.add_job(
        func=run_checkin_scraper,
        trigger=CronTrigger(minute='*/15'),
        id='checkin_scraper',
        name='Check-in scraper every 15 minutes',
        replace_existing=True
    )
    
    # Schedule calendar scraping daily at 3 AM
    scheduler.add_job(
        func=run_calendar_scraper,
        trigger=CronTrigger(hour=3, minute=0),
        id='calendar_scraper',
        name='Daily calendar scraper',
        replace_existing=True
    )
    
    scheduler.start()
    
    # Update next scheduled time
    jobs = scheduler.get_jobs()
    if jobs:
        SCRAPING_STATUS['next_scheduled'] = str(jobs[0].next_run_time)
    
    logger.info("✓ Scheduler started")
    logger.info(f"  - Check-in scraping: Every 15 minutes")
    logger.info(f"  - Calendar scraping: Daily at 3:00 AM")
    
    return scheduler


def start_keep_alive():
    """Ping the server itself to prevent sleeping on Free Tier"""
    import requests
    import time
    
    # Get external URL from Render environment
    url = os.environ.get('RENDER_EXTERNAL_URL')
    if not url:
        logger.warning("RENDER_EXTERNAL_URL not found. Keep-alive disabled.")
        return

    # Ensure URL ends with /health
    if not url.endswith('/'):
        url += '/'
    target_url = url + 'health'
    
    logger.info(f"Starting keep-alive pinger for {target_url}")
    
    def pinger():
        while True:
            try:
                # Sleep for 14 minutes (Render sleeps after 15 mins inactivity)
                time.sleep(14 * 60)
                logger.info(f"Pinging {target_url} to keep alive...")
                response = requests.get(target_url, timeout=10)
                logger.info(f"Keep-alive ping status: {response.status_code}")
            except Exception as e:
                logger.error(f"Keep-alive ping failed: {e}")
                # Wait a bit before retrying to avoid spamming logs if network is down
                time.sleep(60)

    # Start pinger in background thread
    thread = threading.Thread(target=pinger, daemon=True)
    thread.start()


if __name__ == '__main__':
    logger.info("="*80)
    logger.info("BoxMagic API Server Starting...")
    logger.info("="*80)
    
    # Load existing data
    load_latest_data()
    
    # Setup scheduler
    scheduler = setup_scheduler()
    
    # Always run initial scrape on startup (in background thread)
    logger.info("Running initial scrape on startup...")
    initial_scrape_thread = threading.Thread(target=run_checkin_scraper, daemon=True)
    initial_scrape_thread.start()
    
    # Start keep-alive pinger
    start_keep_alive()
    
    # Start Flask server
    port = Config.PORT
    logger.info(f"\n✓ API Server running on http://localhost:{port}")
    logger.info(f"✓ CORS enabled for all origins")
    logger.info("="*80 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()