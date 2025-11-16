# ========================================
# File: main_checkin.py
# UPDATED VERSION - Check-in scraper
# ========================================
from config.settings import Config
from src.scraper_playwright import BoxMagicScraper
import logging
import json
from datetime import datetime

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/checkin_scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("="*80)
    logger.info("BoxMagic Check-in Scraper - Starting")
    logger.info("="*80)
    
    try:
        Config.validate()
        
        scraper = BoxMagicScraper(Config)
        scraper.start_browser(use_saved_session=True)
        
        # Verify browser is ready
        if not scraper.page:
            logger.error("Browser page not initialized!")
            scraper.close()
            return
        
        logger.info(f"✓ Browser ready. Current URL: {scraper.page.url}")
        
        # Scrape check-in data for dates 17-22 November 2025
        logger.info("\nStarting check-in data scraping for dates 17-22 Nov 2025...\n")
        
        try:
            checkin_data = scraper.scrape_checkin_all_dates(
                start_day=17,
                end_day=22,
                month=11,
                year=2025
            )
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}", exc_info=True)
            scraper.page.screenshot(path=str(Config.SCREENSHOTS_DIR / 'scraping_error.png'))
            raise
        
        # Save check-in data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkin_output_file = Config.DATA_DIR / f'checkin_data_{timestamp}.json'
        
        if not checkin_data or not checkin_data.get('dates'):
            logger.warning("⚠ No check-in data returned!")
            checkin_data = {
                'error': 'No data scraped', 
                'scrapedAt': datetime.now().isoformat(),
                'dates': {}
            }
        
        with open(checkin_output_file, 'w', encoding='utf-8') as f:
            json.dump(checkin_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✓ Check-in data saved to: {checkin_output_file}")
        
        # Print detailed summary
        if checkin_data and 'summary' in checkin_data:
            logger.info("\n" + "="*80)
            logger.info("CHECK-IN SCRAPING SUMMARY")
            logger.info("="*80)
            summary = checkin_data['summary']
            logger.info(f"  Total dates processed:    {summary.get('totalDates', 0)}")
            logger.info(f"  Total classes found:      {summary.get('totalClasses', 0)}")
            logger.info(f"  Total reservations:       {summary.get('totalReservations', 0)}")
            logger.info("="*80 + "\n")
            
            # Print breakdown by date
            if checkin_data.get('dates'):
                logger.info("Breakdown by date:")
                for date_str, date_data in checkin_data['dates'].items():
                    total_res = sum(
                        c.get('totalReservations', 0) 
                        for c in date_data.get('classes', {}).values()
                    )
                    logger.info(f"  {date_str}: {date_data.get('totalClasses', 0)} classes, {total_res} reservations")
                logger.info("")
        
        scraper.close()
        
        logger.info("="*80)
        logger.info("✓ Scraping completed successfully!")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"\n✗ Fatal error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()