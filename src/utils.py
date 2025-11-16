import logging
import time
from functools import wraps
from pathlib import Path
import os
def setup_logging(log_file='logs/scraper.log'):
    os.makedirs("logs", exist_ok=True)
    """Configure logging for the application"""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def retry(max_attempts=3, delay=1):
    """Decorator to retry a function if it fails"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def save_to_file(data, filename, format='json'):
    """Save scraped data to file"""
    import json
    import csv
    from pathlib import Path
    
    filepath = Path(filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif format == 'csv':
        if isinstance(data, list) and len(data) > 0:
            keys = data[0].keys()
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
    
    logging.info(f"Data saved to {filepath}")
