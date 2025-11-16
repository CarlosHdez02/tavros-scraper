from config.settings import Config
from src.scraper_playwright import BoxMagicScraper
import logging
import json
from datetime import datetime
import os

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("Starting BoxMagic check-in scraper...")
    
    try:
        Config.validate()
        
        scraper = BoxMagicScraper(Config)
        scraper.start_browser(use_saved_session=True)
        
        # Verify browser is ready
        if not scraper.page:
            logger.error("Browser page not initialized!")
            scraper.close()
            return
        
        logger.info(f"Browser ready. Current URL: {scraper.page.url}")
        
        # Scrape check-in data for dates 17-22
        logger.info("\n" + "="*80)
        logger.info("Starting check-in data scraping...")
        logger.info("="*80 + "\n")
        
        try:
            checkin_data = scraper.scrape_checkin_all_dates(
                start_day=17,
                end_day=22,
                month=11,
                year=2025
            )
        except Exception as e:
            logger.error(f"Error in scrape_checkin_all_dates: {str(e)}", exc_info=True)
            scraper.page.screenshot(path=str(Config.SCREENSHOTS_DIR / 'main_error.png'))
            raise
        
        # Save check-in data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkin_output_file = Config.DATA_DIR / f'checkin_data_{timestamp}.json'
        
        if not checkin_data:
            logger.warning("No check-in data returned! Data might be empty.")
            checkin_data = {'error': 'No data scraped', 'scrapedAt': datetime.now().isoformat()}
        
        with open(checkin_output_file, 'w', encoding='utf-8') as f:
            json.dump(checkin_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Check-in data saved to {checkin_output_file}")
        
        # Print check-in summary
        if checkin_data and 'summary' in checkin_data:
            logger.info("\n" + "="*80)
            logger.info("CHECK-IN SCRAPING SUMMARY")
            logger.info("="*80)
            summary = checkin_data['summary']
            logger.info(f"Total dates: {summary.get('totalDates', 0)}")
            logger.info(f"Total classes: {summary.get('totalClasses', 0)}")
            logger.info(f"Total reservations: {summary.get('totalReservations', 0)}")
            logger.info("="*80 + "\n")
        elif checkin_data and 'dates' in checkin_data:
            logger.info("\n" + "="*80)
            logger.info("CHECK-IN SCRAPING SUMMARY")
            logger.info("="*80)
            logger.info(f"Total dates processed: {len(checkin_data.get('dates', {}))}")
            logger.info("="*80 + "\n")
        else:
            logger.warning("No summary data available. Check the output file for details.")
        
        scraper.close()
        
        logger.info("Scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()