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
            logging.FileHandler('logs/scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    logger = setup_logging()
    logger.info("Starting BoxMagic scraper with coach filtering...")
    
    try:
        Config.validate()
        
        scraper = BoxMagicScraper(Config)
        scraper.start_browser(use_saved_session=True)
        
        # Option 1: Get available coaches first
        logger.info("Fetching available coaches...")
        coaches = scraper.get_available_coaches()
        logger.info(f"Available coaches: {coaches}")
        
        # Option 2: Scrape for a specific coach
        # Uncomment to scrape for one coach:
        # target_coach = "César Toro"
        # logger.info(f"Scraping calendar for coach: {target_coach}")
        # calendar_data = scraper.scrape_calendar_with_details(coach_name=target_coach)
        
        # Option 3: Scrape for ALL coaches (recommended)
        logger.info("Scraping calendar for ALL coaches...")
        calendar_data = scraper.scrape_all_coaches()
        
        # Save data
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Config.DATA_DIR / f'calendar_by_coaches_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(calendar_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {output_file}")
        
        # Print summary
        if 'coaches' in calendar_data:
            logger.info("\n" + "="*60)
            logger.info("SCRAPING SUMMARY")
            logger.info("="*60)
            for coach, data in calendar_data['coaches'].items():
                logger.info(f"{coach}: {data.get('totalEvents', 0)} events")
            logger.info("="*60 + "\n")
        
        scraper.close()
        
        logger.info("Scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()