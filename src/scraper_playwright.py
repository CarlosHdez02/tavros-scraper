
# ========================================
# File: src/scraper_playwright.py
# ENHANCED VERSION - Coach filtering + data extraction
# ========================================
from playwright.sync_api import sync_playwright, Page, TimeoutError
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
import time
import os
import re
import subprocess
logger = logging.getLogger(__name__)

class BoxMagicScraper:
    """
    Scraper for BoxMagic calendar using Playwright
    """
    
    def __init__(self, config):
        self.config = config
        self.playwright = None
        self.browser = None
        self.page = None
        self.is_logged_in = False
    
    def login(self) -> bool:
        """
        Automatically login using credentials from config
        Returns True if login successful, False otherwise
        """
        try:
            logger.info("Attempting automatic login...")
            
            # Navigate to login page
            logger.info(f"Navigating to login page: {self.config.LOGIN_URL}")
            self.page.goto(self.config.LOGIN_URL, wait_until='networkidle')
            self.page.wait_for_timeout(2000)
            
            # Try multiple selectors for username/email field
            username_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[name="username"]',
                'input[name="user"]',
                'input[id*="email"]',
                'input[id*="username"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="usuario" i]',
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, self.config.USERNAME)
                        logger.info(f"✓ Username filled using selector: {selector}")
                        username_filled = True
                        break
                except:
                    continue
            
            if not username_filled:
                logger.error("Could not find username/email field")
                return False
            
            # Try multiple selectors for password field
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[name="pass"]',
                'input[id*="password"]',
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.fill(selector, self.config.PASSWORD)
                        logger.info(f"✓ Password filled using selector: {selector}")
                        password_filled = True
                        break
                except:
                    continue
            
            if not password_filled:
                logger.error("Could not find password field")
                return False
            
            # Try multiple selectors for login button
            login_button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Login")',
                'button:has-text("Iniciar")',
                'button:has-text("Entrar")',
                'button:has-text("Sign in")',
                'button.login',
                'button[class*="login"]',
            ]
            
            button_clicked = False
            for selector in login_button_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        logger.info(f"✓ Login button clicked using selector: {selector}")
                        button_clicked = True
                        break
                except:
                    continue
            
            if not button_clicked:
                # Try pressing Enter on password field
                try:
                    self.page.keyboard.press('Enter')
                    logger.info("✓ Login attempted via Enter key")
                    button_clicked = True
                except:
                    pass
            
            if not button_clicked:
                logger.error("Could not find or click login button")
                return False
            
            # Wait for navigation after login
            self.page.wait_for_timeout(3000)
            
            # Check if login was successful
            current_url = self.page.url
            logger.info(f"Current URL after login attempt: {current_url}")
            
            # Check if we're on the intermediate user selection page
            # This page shows user profile with "Admin panel" button
            # The button structure: <div class="Ui2Boton"> containing <button type="button" aria-label="Boton"></button>
            # and the text "Admin panel" is in a sibling div
            
            # First, check if we're on the intermediate page by looking for the Ui2Boton structure
            is_intermediate_page = False
            try:
                # Check for Ui2Boton divs (these are the button containers)
                if self.page.locator('.Ui2Boton').count() > 0:
                    is_intermediate_page = True
                    logger.info("Detected intermediate user selection page (Ui2Boton found)")
            except:
                pass
            
            # Also check by looking for "Admin panel" text
            admin_panel_selectors = [
                '.Ui2Boton:has-text("Admin panel") button[aria-label="Boton"]',
                '.Ui2Boton:has-text("Admin panel") button',
                'div.Ui2Boton:has-text("Admin panel")',
                'button[aria-label="Boton"]',  # Generic fallback - will need to find the right one
                'a:has-text("Admin panel")',
                'a:has-text("Admin Panel")',
                'button:has-text("Admin panel")',
            ]
            
            # Also check by URL pattern and page content
            if 'auth.boxmagic.cl/login' in current_url:
                try:
                    # Wait a bit for page to load
                    self.page.wait_for_timeout(1000)
                    page_text = self.page.locator('body').inner_text().lower()
                    if 'admin panel' in page_text or 'access to sessions' in page_text or 'not your account' in page_text:
                        is_intermediate_page = True
                        logger.info("Detected intermediate page by URL and content")
                except:
                    pass
            
            # If on intermediate page, click "Admin panel"
            if is_intermediate_page:
                logger.info("Clicking 'Admin panel' to proceed...")
                admin_clicked = False
                
                # Try specific selectors first
                for selector in admin_panel_selectors:
                    try:
                        if self.page.locator(selector).count() > 0:
                            self.page.click(selector)
                            logger.info(f"✓ Clicked 'Admin panel' using selector: {selector}")
                            admin_clicked = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                # If specific selectors didn't work, use JavaScript to find the correct button
                if not admin_clicked:
                    try:
                        clicked = self.page.evaluate('''
                            () => {
                                // Find all Ui2Boton divs
                                const botones = document.querySelectorAll('.Ui2Boton');
                                for (let botonDiv of botones) {
                                    // Check if this div contains "Admin panel" text
                                    const text = botonDiv.textContent || botonDiv.innerText || '';
                                    if (text.toLowerCase().includes('admin panel')) {
                                        // Find the button inside this div
                                        const button = botonDiv.querySelector('button[aria-label="Boton"]') || 
                                                      botonDiv.querySelector('button');
                                        if (button) {
                                            button.click();
                                            return true;
                                        }
                                        // If no button found, click the div itself
                                        botonDiv.click();
                                        return true;
                                    }
                                }
                                
                                // Fallback: find any button with aria-label="Boton" near "Admin panel" text
                                const allButtons = document.querySelectorAll('button[aria-label="Boton"]');
                                for (let btn of allButtons) {
                                    const parent = btn.closest('.Ui2Boton');
                                    if (parent) {
                                        const text = parent.textContent || parent.innerText || '';
                                        if (text.toLowerCase().includes('admin panel')) {
                                            btn.click();
                                            return true;
                                        }
                                    }
                                }
                                
                                return false;
                            }
                        ''')
                        if clicked:
                            logger.info("✓ Clicked 'Admin panel' via JavaScript (targeting Ui2Boton structure)")
                            admin_clicked = True
                        else:
                            logger.warning("Could not find Admin panel button via JavaScript")
                    except Exception as e:
                        logger.warning(f"Could not click Admin panel via JavaScript: {e}")
                
                if admin_clicked:
                    # Wait for navigation after clicking Admin panel
                    self.page.wait_for_timeout(3000)
                    self.page.wait_for_load_state('networkidle', timeout=10000)
                    current_url = self.page.url
                    logger.info(f"Current URL after clicking Admin panel: {current_url}")
            
            # Check if login was successful (we're no longer on login page)
            if 'login' not in current_url.lower() or current_url != self.config.LOGIN_URL:
                logger.info("✓ Login successful and navigated to application!")
                
                # Save session for future use
                session_file = self.config.DATA_DIR / 'session.json'
                storage_state = self.context.storage_state()
                with open(session_file, 'w') as f:
                    json.dump(storage_state, f, indent=2)
                logger.info(f"✓ Session saved to {session_file}")
                
                self.is_logged_in = True
                return True
            else:
                logger.error("Login failed - still on login page")
                self.page.screenshot(
                    path=str(self.config.SCREENSHOTS_DIR / 'login_failed.png')
                )
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}", exc_info=True)
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'login_error.png')
            )
            return False
    
    def start_browser(self, use_saved_session=True, auto_login=True):
        """Initialize browser and optionally login"""
        is_render = os.getenv("RENDER", None) is not None
        logger.info("Starting browser...")
        # Force set the browsers path if on Render
        if is_render:
            # Use persistent disk: /opt/render/project/src/data/playwright-browsers
            # self.config.DATA_DIR is .../data/output, so we want .../data/playwright-browsers
            persistent_browsers_path = self.config.DATA_DIR.parent / 'playwright-browsers'
            
            logger.info(f"Render environment detected. Setting PLAYWRIGHT_BROWSERS_PATH to persistent disk: {persistent_browsers_path}")
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(persistent_browsers_path)
            
            # Check if browsers are installed
            if not persistent_browsers_path.exists() or not any(persistent_browsers_path.iterdir()):
                logger.info("Browsers not found on persistent disk. Installing...")
                try:
                    subprocess.run(['playwright', 'install', 'chromium'], check=True)
                    logger.info("✓ Browsers installed successfully to persistent disk")
                except Exception as e:
                    logger.error(f"Failed to install browsers: {e}")
            else:
                logger.info("✓ Browsers found on persistent disk")

        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
        
        session_file = self.config.DATA_DIR / 'session.json'
        storage_state = None
        session_valid = False
        
        if use_saved_session and session_file.exists():
            try:
                logger.info("Loading saved session...")
                with open(session_file, 'r') as f:
                    storage_state = json.load(f)
                session_valid = True
            except Exception as e:
                logger.warning(f"Could not load session file: {e}")
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            storage_state=storage_state
        )
        
        self.page = self.context.new_page()
        
        # Verify session is still valid by checking if we're logged in
        if session_valid and storage_state:
            try:
                # Navigate to a protected page to verify session
                self.page.goto(self.config.CHECKIN_URL, wait_until='networkidle', timeout=10000)
                self.page.wait_for_timeout(2000)
                
                # Check if we're redirected to login (session invalid)
                if 'login' in self.page.url.lower():
                    logger.warning("Saved session appears to be invalid, will attempt login")
                    session_valid = False
                else:
                    self.is_logged_in = True
                    logger.info("✓ Logged in using saved session")
            except Exception as e:
                logger.warning(f"Could not verify session: {e}, will attempt login")
                session_valid = False
        
        # If no valid session, attempt automatic login
        if not self.is_logged_in and auto_login:
            if self.login():
                logger.info("✓ Automatic login successful")
            else:
                logger.error("✗ Automatic login failed")
        
        logger.info("Browser started successfully")
    
    def get_available_coaches(self) -> List[str]:
        """
        Get list of available coaches from the dropdown
        """
        try:
            logger.info(f"Navigating to calendar: {self.config.CALENDAR_URL}")
            self.page.goto(self.config.CALENDAR_URL, wait_until='networkidle')
            
            # Wait for page to load
            self.page.wait_for_selector('.pace-done', timeout=self.config.TIMEOUT)
            self.page.wait_for_timeout(2000)
            
            # Take screenshot to see the initial state
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'coach_dropdown_initial.png'),
                full_page=True
            )
            
            # Find the Profesor dropdown and extract all options
            coaches = self.page.evaluate('''
                () => {
                    // Look for all select elements
                    const selects = document.querySelectorAll('select');
                    
                    for (let select of selects) {
                        // Get all option texts
                        const options = Array.from(select.options);
                        const optionTexts = options.map(opt => opt.text.trim());
                        
                        // Check if this looks like the coach/professor dropdown
                        // It should have names or "Profesor" label
                        if (optionTexts.some(text => 
                            text.includes('Profesor') || 
                           re.match(r"[A-Z][a-z]+\s+[A-Z][a-z]+", text)  // Matches "FirstName LastName"
                        )) {
                            // Return all non-empty options, excluding generic labels
                            return options
                                .map(opt => ({
                                    value: opt.value,
                                    text: opt.text.trim()
                                }))
                                .filter(opt => 
                                    opt.text.length > 0 && 
                                    opt.text !== 'Profesor' && 
                                    opt.text !== 'Seleccionar' &&
                                    opt.text !== 'Todos' &&
                                    opt.value !== ''
                                )
                                .map(opt => opt.text);
                        }
                    }
                    
                    return [];
                }
            ''')
            
            if coaches and len(coaches) > 0:
                logger.info(f"Found {len(coaches)} coaches: {coaches}")
                return coaches
            
            logger.warning("Could not find coach dropdown or no coaches available")
            return []
            
        except Exception as e:
            logger.error(f"Error getting coaches: {str(e)}")
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'coach_dropdown_error.png')
            )
            return []
    
    def select_coach(self, coach_name: str) -> bool:
        """
        Select a specific coach from the dropdown and click Filter button
        """
        try:
            logger.info(f"Selecting coach: {coach_name}")
            
            # Step 1: Find and click the Profesor dropdown to open it
            logger.info("Step 1: Opening Profesor dropdown...")
            dropdown_opened = False
            
            # Try multiple ways to find and open the dropdown
            dropdown_selectors = [
                'select:has-text("Profesor")',
                'select[name*="profesor"]',
                'select[name*="coach"]',
            ]
            
            for selector in dropdown_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        # Click to open dropdown
                        self.page.click(selector)
                        self.page.wait_for_timeout(500)
                        dropdown_opened = True
                        logger.info(f"✓ Dropdown opened with selector: {selector}")
                        break
                except:
                    continue
            
            if not dropdown_opened:
                # Try JavaScript approach - find any select with Profesor options
                dropdown_opened = self.page.evaluate('''
                    () => {
                        const selects = document.querySelectorAll('select');
                        for (let select of selects) {
                            const options = Array.from(select.options);
                            if (options.some(opt => opt.text.includes('Profesor'))) {
                                select.focus();
                                select.click();
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                if dropdown_opened:
                    self.page.wait_for_timeout(500)
                    logger.info("✓ Dropdown opened via JavaScript")
            
            if not dropdown_opened:
                logger.error("Failed to open dropdown")
                self.page.screenshot(
                    path=str(self.config.SCREENSHOTS_DIR / 'dropdown_not_opened.png')
                )
                return False
            
            # Step 2: Select the coach from dropdown
            logger.info(f"Step 2: Selecting coach '{coach_name}' from dropdown...")
            selected = self.page.evaluate('''
                (coachName) => {
                    const selects = document.querySelectorAll('select');
                    
                    for (let select of selects) {
                        const options = Array.from(select.options);
                        
                        // Look for coach dropdown (has "Profesor" or coach names)
                        const hasCoachOptions = options.some(opt => 
                            opt.text.includes('Profesor') || 
                            /[A-Z][a-z]+\\s+[A-Z][a-z]+/.test(opt.text)
                        );
                        
                        if (hasCoachOptions) {
                            // Find matching option
                            const matchingOption = options.find(opt => 
                                opt.text.trim() === coachName ||
                                opt.text.trim().includes(coachName) ||
                                coachName.includes(opt.text.trim())
                            );
                            
                            if (matchingOption) {
                                select.value = matchingOption.value;
                                
                                // Trigger change events
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                select.dispatchEvent(new Event('input', { bubbles: true }));
                                
                                if (window.jQuery) {
                                    window.jQuery(select).trigger('change');
                                }
                                
                                return true;
                            }
                        }
                    }
                    return false;
                }
            ''', coach_name)
            
            if not selected:
                logger.error(f"Could not find coach in dropdown: {coach_name}")
                self.page.screenshot(
                    path=str(self.config.SCREENSHOTS_DIR / f'coach_not_found_{coach_name.replace(" ", "_")}.png')
                )
                return False
            
            logger.info(f"✓ Coach '{coach_name}' selected in dropdown")
            self.page.wait_for_timeout(500)
            
            # Take screenshot after selection
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / f'after_coach_selection_{coach_name.replace(" ", "_")}.png')
            )
            
            # Step 3: Click the "Filtrar" button
            logger.info("Step 3: Clicking 'Filtrar' button...")
            filter_clicked = False
            
            # Try multiple selectors for the filter button
            filter_selectors = [
                'button:has-text("Filtrar")',
                'button:has-text("Filter")',
                'input[type="submit"]:has-text("Filtrar")',
                'a:has-text("Filtrar")',
                '.btn:has-text("Filtrar")',
                '[value="Filtrar"]'
            ]
            
            for selector in filter_selectors:
                try:
                    if self.page.locator(selector).count() > 0:
                        self.page.click(selector)
                        filter_clicked = True
                        logger.info(f"✓ Filter button clicked with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not filter_clicked:
                # Try to find any button near the dropdown that might be the filter
                filter_clicked = self.page.evaluate('''
                    () => {
                        const buttons = document.querySelectorAll('button, input[type="submit"], a.btn');
                        for (let btn of buttons) {
                            const text = btn.textContent.trim().toLowerCase();
                            if (text.includes('filtrar') || text.includes('filter') || text.includes('aplicar')) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                if filter_clicked:
                    logger.info("✓ Filter button clicked via JavaScript")
            
            if not filter_clicked:
                logger.warning("Could not find 'Filtrar' button - calendar might auto-filter")
                # Some calendars auto-filter without a button
            
            # Step 4: Wait for calendar to reload with filtered data
            logger.info("Step 4: Waiting for calendar to reload...")
            try:
                # Wait for loading indicator
                self.page.wait_for_selector('.pace-running, .pace-active', timeout=2000)
            except:
                pass  # Loading might be instant
            
            # Wait for loading to complete
            self.page.wait_for_selector('.pace-done', timeout=self.config.TIMEOUT)
            self.page.wait_for_timeout(2000)
            
            # Wait for calendar events to appear
            try:
                self.page.wait_for_selector('.fc-time-grid-event', timeout=self.config.TIMEOUT)
            except:
                logger.warning("No events found after filtering - coach might have no classes")
            
            self.page.wait_for_timeout(1000)
            
            # Take screenshot after filtering
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / f'after_filter_{coach_name.replace(" ", "_")}.png')
            )
            
            logger.info(f"✓ Successfully filtered calendar for coach: {coach_name}")
            return True
                
        except Exception as e:
            logger.error(f"Error selecting coach: {str(e)}")
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / f'select_coach_error_{coach_name.replace(" ", "_")}.png'),
                full_page=True
            )
            return False
    
    def scrape_calendar_with_details(self, coach_name: Optional[str] = None) -> Dict:
        """
        Scrape calendar data including modal details for each event
        Optionally filter by coach name
        """
        if not self.is_logged_in:
            logger.error("Not logged in. Please login first.")
            return {}
        
        try:
            logger.info(f"Navigating to calendar: {self.config.CALENDAR_URL}")
            
            # Navigate to calendar page
            self.page.goto(self.config.CALENDAR_URL, wait_until='networkidle')
            
            # Wait for calendar to load
            logger.info("Waiting for calendar to load...")
            self.page.wait_for_selector('.pace-done', timeout=self.config.TIMEOUT)
            self.page.wait_for_timeout(3000)
            
            # If coach specified, select them
            if coach_name:
                if not self.select_coach(coach_name):
                    logger.error(f"Failed to select coach: {coach_name}")
                    return {}
            
            # Take screenshot
            screenshot_name = f'calendar_loaded_{coach_name.replace(" ", "_") if coach_name else "all"}.png'
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / screenshot_name),
                full_page=True
            )
            
            # Get all event elements
            event_selectors = '.fc-time-grid-event.fc-v-event.fc-event'
            self.page.wait_for_selector(event_selectors, timeout=self.config.TIMEOUT)
            
            # Get basic event data
            events_data = self.page.evaluate('''
                () => {
                    const events = [];
                    const eventElements = document.querySelectorAll('.fc-time-grid-event.fc-v-event.fc-event');
                    
                    eventElements.forEach((element, index) => {
                        const text = element.textContent.trim();
                        const style = element.getAttribute('style') || '';
                        
                        const timeMatch = text.match(/(\\d{1,2}:\\d{2})\\s*-\\s*(\\d{1,2}:\\d{2})/);
                        
                        events.push({
                            index: index,
                            text: text,
                            startTime: timeMatch ? timeMatch[1] : null,
                            endTime: timeMatch ? timeMatch[2] : null,
                            style: style,
                            hasTime: timeMatch !== null
                        });
                    });
                    
                    return events;
                }
            ''')
            
            # Filter events with valid time
            valid_events = [e for e in events_data if e['hasTime']]
            logger.info(f"Found {len(valid_events)} events to process")
            
            # Now click each event to get details
            detailed_events = []
            event_elements = self.page.query_selector_all(event_selectors)
            
            for idx, event_data in enumerate(valid_events):
                try:
                    logger.info(f"Processing event {idx + 1}/{len(valid_events)}: {event_data['startTime']} - {event_data['endTime']}")
                    
                    # Find the corresponding element
                    if idx < len(event_elements):
                        element = event_elements[idx]
                        
                        # Scroll element into view
                        element.scroll_into_view_if_needed()
                        self.page.wait_for_timeout(500)
                        
                        # Click the event to open modal
                        element.click()
                        
                        # Wait for modal to appear
                        self.page.wait_for_selector('.modal-content, [role="dialog"], .modal', timeout=5000)
                        self.page.wait_for_timeout(1000)
                        
                        # Extract modal details
                        modal_details = self.page.evaluate('''
                            () => {
                                const modal = document.querySelector('.modal-content, [role="dialog"], .modal');
                                if (!modal) return null;
                                
                                const getCleanValue = (labelText) => {
                                    const allElements = Array.from(modal.querySelectorAll('*'));
                                    
                                    for (let el of allElements) {
                                        const text = el.textContent.trim();
                                        
                                        if (text.startsWith(labelText)) {
                                            const value = text.replace(labelText, '').trim();
                                            const cleanValue = value.split(/\\n|\\s{2,}/)[0].trim();
                                            return cleanValue || null;
                                        }
                                    }
                                    return null;
                                };
                                
                                const getTeachers = () => {
                                    const text = modal.textContent;
                                    const match = text.match(/Profesores asignados:\\s*([^Select]+?)(?=Select|Sala|$)/);
                                    if (match) {
                                        const names = match[1].match(/[A-Z][a-z]+\\s+[A-Z][a-z]+/g) || [];
                                        return [...new Set(names)].join(', ');
                                    }
                                    return null;
                                };
                                
                                return {
                                    day: getCleanValue('Día:'),
                                    className: getCleanValue('Clase:'),
                                    program: getCleanValue('Programa'),
                                    startTime: getCleanValue('Hora Inicio:'),
                                    endTime: getCleanValue('Hora Fin:'),
                                    capacity: getCleanValue('Cupos de clientes por clase:'),
                                    trialClass: getCleanValue('Clase de prueba:'),
                                    onlineClass: getCleanValue('Clase Online'),
                                    freeClass: getCleanValue('Clase libre'),
                                    teachers: getTeachers()
                                };
                            }
                        ''')
                        
                        # Take screenshot of modal
                        modal_screenshot = f'modal_{coach_name.replace(" ", "_") if coach_name else "all"}_event_{idx}.png'
                        self.page.screenshot(
                            path=str(self.config.SCREENSHOTS_DIR / modal_screenshot)
                        )
                        
                        # Close modal
                        close_selectors = [
                            'button:has-text("Cerrar")',
                            'button:has-text("Close")',
                            '.modal-close',
                            '[aria-label="Close"]',
                            'button.close'
                        ]
                        
                        modal_closed = False
                        for selector in close_selectors:
                            try:
                                if self.page.locator(selector).count() > 0:
                                    self.page.click(selector)
                                    modal_closed = True
                                    break
                            except:
                                continue
                        
                        if not modal_closed:
                            self.page.keyboard.press('Escape')
                        
                        self.page.wait_for_timeout(1000)
                        
                        # Combine data and add coach info
                        combined_event = {
                            **event_data,
                            'modalDetails': modal_details,
                            'filteredCoach': coach_name
                        }
                        detailed_events.append(combined_event)
                        
                        logger.info(f"✓ Extracted details for event at {event_data['startTime']}")
                        
                except Exception as e:
                    logger.error(f"Error processing event {idx}: {str(e)}")
                    try:
                        self.page.keyboard.press('Escape')
                        self.page.wait_for_timeout(500)
                    except:
                        pass
                    continue
            
            logger.info(f"Successfully extracted details for {len(detailed_events)} events")
            
            return {
                'coach': coach_name,
                'events': detailed_events,
                'totalEvents': len(detailed_events),
                'pageTitle': 'BoxMagic',
                'url': self.config.CALENDAR_URL,
                'scrapedAt': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to scrape calendar: {str(e)}")
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'scraping_error.png')
            )
            return {}
    
    def scrape_all_coaches(self) -> Dict:
        """
        Scrape calendar data for all available coaches
        """
        coaches = self.get_available_coaches()
        
        if not coaches:
            logger.error("No coaches found")
            return {}
        
        all_data = {
            'scrapedAt': datetime.now().isoformat(),
            'totalCoaches': len(coaches),
            'coaches': {}
        }
        
        for coach in coaches:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing coach: {coach}")
            logger.info(f"{'='*60}\n")
            
            coach_data = self.scrape_calendar_with_details(coach_name=coach)
            
            if coach_data:
                all_data['coaches'][coach] = coach_data
                logger.info(f"✓ Completed scraping for {coach}: {coach_data.get('totalEvents', 0)} events")
            else:
                logger.error(f"✗ Failed to scrape data for {coach}")
        
        return all_data
    
    # Find and replace this method in src/scraper_playwright.py

    def select_date_on_checkin(self, date_str: str) -> bool:
        logger.info(f"Selecting date: {date_str}")
        
        date_selector = '#class_date'
        
        try:
            # Wait for the date input to be available
            self.page.wait_for_selector(date_selector, timeout=10000)
            
            logger.info(f"Found date input with selector: {date_selector}")
            
            # Set the date value using JavaScript
            success = self.page.evaluate('''
                (args) => {
                    const dateValue = args.dateValue;
                    const selector = args.selector;
                    const input = document.querySelector(selector);
                    if (!input) return false;
                    
                    // Set the value
                    input.value = dateValue;
                    
                    // Trigger multiple events to ensure it's picked up
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.dispatchEvent(new Event('blur', { bubbles: true }));
                    
                    // If jQuery is available, trigger change event
                    if (window.jQuery) {
                        window.jQuery(input).val(dateValue).trigger('change');
                    }
                    
                    // If there's a datepicker, try to update it
                    if (window.jQuery && window.jQuery(input).data('datepicker')) {
                        window.jQuery(input).datepicker('update', dateValue);
                        window.jQuery(input).datepicker('setDate', dateValue);
                    }
                    
                    return true;
                }
            ''', {'dateValue': date_str, 'selector': date_selector})
            
            if not success:
                logger.error("Failed to set date value via JavaScript")
                return False
            
            # Wait longer for the date change to process and classes to load
            logger.info("Waiting for classes dropdown to populate...")
            self.page.wait_for_timeout(3000)
            
            # Take screenshot after date selection
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / f'after_date_select_{date_str.replace("-", "_")}.png')
            )
            
            logger.info(f"✓ Date selected: {date_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error with date selector {date_selector}: {str(e)}")
            return False
        
    def get_available_classes_for_date(self) -> List[Dict]:
        logger.info("Getting available classes for selected date...")
        
        # Use the specific selector for the class dropdown
        class_selector = '#clases'
        
        try:
            # Wait for the class dropdown to be available
            self.page.wait_for_selector(class_selector, timeout=10000)
            logger.info("✓ Class dropdown found")
            
            # Wait for the loading indicator to disappear
            try:
                # Look for loading indicator
                loading_selector = '#select_clases_loading, .bm-loader'
                if self.page.locator(loading_selector).count() > 0:
                    logger.info("Waiting for classes to load...")
                    self.page.wait_for_selector(loading_selector, state='hidden', timeout=10000)
                    logger.info("✓ Loading complete")
            except:
                pass  # No loading indicator or already hidden
            
            # Wait a bit more for JavaScript to populate options
            self.page.wait_for_timeout(3000)
            
            # Check if options are loaded by looking for options with value
            max_retries = 5
            for attempt in range(max_retries):
                classes = self.page.evaluate('''
                    (selector) => {
                        const select = document.querySelector(selector);
                        if (!select) return [];
                        
                        const options = Array.from(select.options);
                        return options
                            .map(opt => ({
                                value: opt.value,
                                text: opt.text.trim(),
                                index: opt.index
                            }))
                            .filter(opt => 
                                opt.text.length > 0 && 
                                opt.value !== '' &&
                                !opt.text.includes('Selecciona una clase') &&
                                !opt.text.includes('Seleccionar') &&
                                !opt.text.includes('Select')
                            );
                    }
                ''', class_selector)
                
                if classes and len(classes) > 0:
                    logger.info(f"✓ Found {len(classes)} classes for this date")
                    # Log first few classes for debugging
                    for i, c in enumerate(classes[:3]):
                        logger.info(f"  - Class {i+1}: {c['text']}")
                    if len(classes) > 3:
                        logger.info(f"  ... and {len(classes) - 3} more")
                    return classes
                
                logger.info(f"Attempt {attempt + 1}/{max_retries}: No classes found yet, waiting...")
                self.page.wait_for_timeout(2000)
            
            logger.warning("No classes found after multiple retries")
            
            # Take screenshot for debugging
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'no_classes_found.png')
            )
            
            # Get the HTML of the select to see what's there
            select_html = self.page.evaluate('''
                (selector) => {
                    const select = document.querySelector(selector);
                    return select ? select.innerHTML : 'SELECT NOT FOUND';
                }
            ''', class_selector)
            logger.debug(f"Select HTML: {select_html[:500]}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error with class selector {class_selector}: {str(e)}")
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'class_selector_error.png')
            )
            return []
        
    def select_class_and_extract_reservations(self, class_info: Dict, date_str: str) -> Dict:
        """
        Select a class and extract all reservation data using the API endpoint
        class_info: dict with 'value', 'text', 'index' keys
        date_str: date in format "DD-MM-YYYY"
        """
        try:
            logger.info(f"Selecting class: {class_info['text']}")
            
            # Extract class ID from the value (format: "104996-237092" or similar)
            class_id = class_info.get('value', '')
            
            # Use the specific selector for the class dropdown
            class_selector = '#clases'
            
            # Select the class from the dropdown
            try:
                self.page.wait_for_selector(class_selector, timeout=10000)
                
                # Try standard Playwright select_option first (most reliable)
                try:
                    logger.info(f"Attempting to select class value: {class_info['value']}")
                    self.page.select_option(class_selector, value=class_info['value'])
                    self.page.wait_for_timeout(1000)
                    
                    # Verify selection
                    selected_value = self.page.evaluate(f'document.querySelector("{class_selector}").value')
                    if selected_value == class_info['value']:
                        logger.info(f"✓ Successfully selected class via select_option: {class_id}")
                    else:
                        logger.warning(f"select_option seemed to fail. Expected {class_info['value']}, got {selected_value}")
                        raise Exception("Selection verification failed")
                        
                except Exception as e:
                    logger.warning(f"Standard select_option failed: {e}, trying JavaScript fallback...")
                    
                    # Fallback to JavaScript selection
                    class_selected = self.page.evaluate('''
                        (classValue, selector) => {
                            const select = document.querySelector(selector);
                            if (!select) return null;
                            
                            // Try setting value directly
                            select.value = classValue;
                            
                            // Dispatch events
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            select.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            if (window.jQuery) {
                                window.jQuery(select).val(classValue).trigger('change');
                            }
                            return select.value;
                        }
                    ''', class_info['value'], class_selector)
                    
                    if class_selected == class_info['value']:
                        logger.info(f"✓ Selected class via JavaScript fallback")
                    else:
                        logger.error("✗ All selection methods failed")
                        
            except Exception as e:
                logger.error(f"Error selecting class: {str(e)}")
            
            if not class_id:
                logger.error(f"Could not determine class ID for: {class_info['text']}")
                return {}
            
            # Wait a bit for the page to process the selection
            self.page.wait_for_timeout(2000)
            
                # Helper function to call API and check results
                def call_api(url):
                    logger.info(f"Fetching data from API: {url}")
                    try:
                        # Use page context to make the API call (to include cookies/auth)
                        # Adding headers just in case, though page.request should handle cookies
                        response = self.page.request.get(url, headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json, text/javascript, */*; q=0.01'
                        })
                        
                        logger.info(f"API Response Status: {response.status}")
                        if response.status != 200:
                            return None
                        
                        response_text = response.text()
                        logger.debug(f"API Response Body: {response_text[:500]}...")
                        return response.json()
                    except Exception as e:
                        logger.error(f"API request failed: {e}")
                        return None

                # 1. Try with original date format (DD-MM-YYYY)
                api_url = f"https://boxmagic.cl/checkin/get_alumnos_clase/{class_id}?fecha_where={date_str}&method=alumnos"
                data = call_api(api_url)
                
                # 2. If empty or failed, try YYYY-MM-DD format
                if not data or not data.get('success', False) or not data.get('alumnos', []):
                    try:
                        # Convert DD-MM-YYYY to YYYY-MM-DD
                        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                        date_iso = date_obj.strftime("%Y-%m-%d")
                        
                        logger.info(f"Retrying with ISO date format: {date_iso}")
                        api_url_iso = f"https://boxmagic.cl/checkin/get_alumnos_clase/{class_id}?fecha_where={date_iso}&method=alumnos"
                        data_iso = call_api(api_url_iso)
                        
                        if data_iso and data_iso.get('success', False) and data_iso.get('alumnos', []):
                            logger.info("✓ ISO date format returned data!")
                            data = data_iso
                        else:
                            logger.info("ISO date format also returned no data")
                    except Exception as e:
                        logger.warning(f"Date conversion failed: {e}")

                if not data:
                    logger.error("API call failed (None response)")
                    return {}
                
                if not data.get('success', False):
                    logger.warning(f"API returned success=false for class {class_id}. Full response: {data}")
                    return {
                        'class': class_info['text'],
                        'classId': class_id,
                        'reservations': [],
                        'totalReservations': 0,
                        'extractedAt': datetime.now().isoformat(),
                        'apiResponse': data
                    }
                
                alumnos = data.get('alumnos', [])
                logger.info(f"✓ Retrieved {len(alumnos)} reservations from API for class: {class_info['text']}")
                
                # Format the reservations data
                formatted_reservations = []
                for alumno in alumnos:
                    formatted_reservations.append({
                        'id': alumno.get('id'),
                        'reserva_id': alumno.get('reserva_id'),
                        'hash_reserva_id': alumno.get('hash_reserva_id'),
                        'name': alumno.get('name', '').strip(),
                        'last_name': alumno.get('last_name', '').strip(),
                        'full_name': f"{alumno.get('name', '').strip()} {alumno.get('last_name', '').strip()}".strip(),
                        'email': alumno.get('email'),
                        'telefono': alumno.get('telefono'),
                        'status': alumno.get('status'),
                        'nombre_plan': alumno.get('nombre_plan'),
                        'canal': alumno.get('canal'),
                        'fecha_creacion': alumno.get('fecha_creacion'),
                        'asistencia_confirmada': alumno.get('asistencia_confirmada', 0),
                        'pago_pendiente': alumno.get('pago_pendiente', False),
                        'form_asistencia_url': alumno.get('form_asistencia_url'),
                        'mostrar_formulario': alumno.get('mostrar_formulario'),
                        'rating': alumno.get('rating'),
                        'imagen': alumno.get('imagen')
                    })
                
                return {
                    'class': class_info['text'],
                    'classId': class_id,
                    'reservations': formatted_reservations,
                    'totalReservations': len(formatted_reservations),
                    'limite': data.get('limite', 0),
                    'clase_online': data.get('clase_online', 0),
                    'clase_coach_id': data.get('clase_coach_id'),
                    'extractedAt': datetime.now().isoformat()
                }
                
            except Exception as api_error:
                logger.error(f"Error calling API: {str(api_error)}")
                return {}
            
        except Exception as e:
            logger.error(f"Error extracting reservations for class {class_info.get('text', 'unknown')}: {str(e)}", exc_info=True)
            return {}
    
    def scrape_checkin_for_date(self, date_str: str, navigate: bool = True) -> Dict:
        """
        Scrape all classes and their reservations for a specific date
        date_str format: "DD-MM-YYYY"
        navigate: If True, navigates to check-in page first. If False, assumes already on check-in page.
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"Scraping check-in for date: {date_str}")
            logger.info(f"{'='*60}\n")
            
            # Navigate to check-in page only if requested
            if navigate:
                logger.info(f"Navigating to check-in page: {self.config.CHECKIN_URL}")
                self.page.goto(self.config.CHECKIN_URL, wait_until='networkidle')
                
                # Wait for page to load
                self.page.wait_for_selector('.pace-done', timeout=self.config.TIMEOUT)
                self.page.wait_for_timeout(2000)
            
            # Select the date
            logger.info(f"Attempting to select date: {date_str}")
            date_selected = self.select_date_on_checkin(date_str)
            
            if not date_selected:
                logger.error(f"Failed to select date: {date_str}")
                self.page.screenshot(
                    path=str(self.config.SCREENSHOTS_DIR / f'date_selection_failed_{date_str.replace("-", "_")}.png'),
                    full_page=True
                )
                return {}
            
            logger.info(f"✓ Date selected successfully: {date_str}")
            
            # Get available classes for this date
            classes = self.get_available_classes_for_date()
            
            if not classes:
                logger.warning(f"No classes found for date: {date_str}")
                return {
                    'date': date_str,
                    'classes': {},
                    'totalClasses': 0,
                    'scrapedAt': datetime.now().isoformat()
                }
            
            date_data = {
                'date': date_str,
                'classes': {},
                'totalClasses': len(classes),
                'scrapedAt': datetime.now().isoformat()
            }
            
            # Process each class
            for idx, class_info in enumerate(classes):
                logger.info(f"\nProcessing class {idx + 1}/{len(classes)}: {class_info['text']}")
                
                class_data = self.select_class_and_extract_reservations(class_info, date_str)
                
                if class_data:
                    date_data['classes'][class_info['text']] = class_data
                    logger.info(f"✓ Completed: {class_data.get('totalReservations', 0)} reservations")
                else:
                    logger.error(f"✗ Failed to extract data for class: {class_info['text']}")
                
                # Small delay between classes
                self.page.wait_for_timeout(1000)
            
            logger.info(f"\n✓ Completed scraping for date {date_str}: {len(date_data['classes'])} classes")
            return date_data
            
        except Exception as e:
            logger.error(f"Error scraping check-in for date {date_str}: {str(e)}")
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / f'checkin_error_{date_str.replace("-", "_")}.png')
            )
            return {}
    
    def scrape_checkin_all_dates(self, start_day: int = 17, end_day: int = 22, month: int = 11, year: int = 2025) -> Dict:
        """
        Scrape check-in data for all dates from start_day to end_day
        Default: days 17-22 (6 days)
        Navigates to CHECKIN_URL once at the beginning and stays on that page
        Uses API endpoint to fetch reservation data directly
        """
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting check-in scraping for dates {start_day}-{end_day} of {month}/{year}")
            logger.info(f"{'='*80}\n")
            
            # Navigate to check-in page once at the beginning
            logger.info(f"Navigating to check-in page: {self.config.CHECKIN_URL}")
            try:
                self.page.goto(self.config.CHECKIN_URL, wait_until='networkidle', timeout=60000)
                logger.info(f"✓ Successfully navigated to {self.config.CHECKIN_URL}")
            except Exception as e:
                logger.error(f"Failed to navigate to check-in page: {str(e)}")
                self.page.screenshot(path=str(self.config.SCREENSHOTS_DIR / 'navigation_error.png'))
                raise
            
            # Verify we're on the correct page
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            if 'checkin' not in current_url.lower():
                logger.warning(f"Warning: Current URL doesn't contain 'checkin'. Expected: {self.config.CHECKIN_URL}")
            
            # Wait for page to load - try multiple selectors
            logger.info("Waiting for page to load...")
            try:
                self.page.wait_for_selector('.pace-done', timeout=self.config.TIMEOUT)
                logger.info("✓ Page loaded (pace-done found)")
            except:
                logger.warning("pace-done selector not found, trying alternative wait...")
                self.page.wait_for_load_state('networkidle', timeout=self.config.TIMEOUT)
                logger.info("✓ Page loaded (networkidle)")
            
            self.page.wait_for_timeout(3000)  # Extra wait for dynamic content
            
            # Take screenshot to verify we're on the right page
            self.page.screenshot(
                path=str(self.config.SCREENSHOTS_DIR / 'checkin_page_loaded.png'),
                full_page=True
            )
            logger.info("✓ Screenshot saved: checkin_page_loaded.png")
            
            all_data = {
                'scrapedAt': datetime.now().isoformat(),
                'dateRange': {
                    'startDay': start_day,
                    'endDay': end_day,
                    'month': month,
                    'year': year
                },
                'dates': {}
            }
            
            # Process each date (without navigating again)
            total_days = end_day - start_day + 1
            for day in range(start_day, end_day + 1):
                date_str = f"{day:02d}-{month:02d}-{year}"
                logger.info(f"\n{'#'*80}")
                logger.info(f"Processing date: {date_str} (Day {day - start_day + 1}/{total_days})")
                logger.info(f"{'#'*80}\n")
                
                try:
                    # Don't navigate again, we're already on the check-in page
                    date_data = self.scrape_checkin_for_date(date_str, navigate=False)
                except Exception as e:
                    logger.error(f"Error processing date {date_str}: {str(e)}", exc_info=True)
                    self.page.screenshot(
                        path=str(self.config.SCREENSHOTS_DIR / f'error_date_{date_str.replace("-", "_")}.png')
                    )
                    date_data = {}
                
                if date_data:
                    all_data['dates'][date_str] = date_data
                    
                    total_classes = date_data.get('totalClasses', 0)
                    total_reservations = sum(
                        class_data.get('totalReservations', 0)
                        for class_data in date_data.get('classes', {}).values()
                    )
                    logger.info(f"✓ Date {date_str}: {total_classes} classes, {total_reservations} total reservations")
                else:
                    logger.error(f"✗ Failed to scrape date: {date_str}")
                
                # Delay between dates
                self.page.wait_for_timeout(1000)
            
            # Calculate totals
            total_dates = len(all_data['dates'])
            total_classes = sum(
                date_data.get('totalClasses', 0)
                for date_data in all_data['dates'].values()
            )
            total_reservations = sum(
                sum(class_data.get('totalReservations', 0)
                    for class_data in date_data.get('classes', {}).values())
                for date_data in all_data['dates'].values()
            )
            
            all_data['summary'] = {
                'totalDates': total_dates,
                'totalClasses': total_classes,
                'totalReservations': total_reservations
            }
            
            logger.info(f"\n{'='*80}")
            logger.info("CHECK-IN SCRAPING SUMMARY")
            logger.info(f"{'='*80}")
            logger.info(f"Total dates processed: {total_dates}")
            logger.info(f"Total classes: {total_classes}")
            logger.info(f"Total reservations: {total_reservations}")
            logger.info(f"{'='*80}\n")
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error in scrape_checkin_all_dates: {str(e)}", exc_info=True)
            return {}
    
    def close(self):
        """Close browser and cleanup"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        
        logger.info("Browser closed")