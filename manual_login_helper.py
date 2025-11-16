from playwright.sync_api import sync_playwright
from config.settings import Config
import json

def manual_login():
    Config.validate()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        print("Opening login page...")
        page.goto(Config.LOGIN_URL)
        
        print("\n" + "="*60)
        print("PLEASE LOGIN MANUALLY IN THE BROWSER WINDOW")
        print("After logging in successfully, press Enter here...")
        print("="*60 + "\n")
        
        input()
        
        # Save session
        storage_state = context.storage_state()
        storage_file = Config.BASE_DIR / 'session.json'
        
        with open(storage_file, 'w') as f:
            json.dump(storage_state, f, indent=2)
        
        print(f"✓ Session saved to {storage_file}")
        page.screenshot(path=str(Config.SCREENSHOTS_DIR / 'logged_in.png'))
        browser.close()

if __name__ == "__main__":
    manual_login()