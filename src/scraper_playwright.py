
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
    
    def start_browser(self, use_saved_session=False):
        """Initialize browser"""
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=self.config.HEADLESS,
            slow_mo=100
        )
        
        session_file = self.config.BASE_DIR / 'session.json'
        storage_state = None
        
        if use_saved_session and session_file.exists():
            logger.info("Using saved session...")
            with open(session_file, 'r') as f:
                storage_state = json.load(f)
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            storage_state=storage_state
        )
        
        self.page = self.context.new_page()
        
        if storage_state:
            self.is_logged_in = True
            logger.info("Logged in using saved session")
        
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
                            /[A-Z][a-z]+\s+[A-Z][a-z]+/.test(text) // Matches "FirstName LastName"
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