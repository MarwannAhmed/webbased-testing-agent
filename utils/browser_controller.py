from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from typing import Optional
import time
from config import Config

class BrowserController:
    """
    Manages browser automation using Playwright.
    Provides a visible browser instance for real-time observation.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._start_time = None
        
    def launch(self):
        """Launch the browser instance"""
        if self.browser:
            return  # Already launched
            
        self.playwright = sync_playwright().start()
        
        # Select browser type
        if Config.BROWSER_TYPE == "firefox":
            browser_type = self.playwright.firefox
        elif Config.BROWSER_TYPE == "webkit":
            browser_type = self.playwright.webkit
        else:
            browser_type = self.playwright.chromium
            
        # Launch browser with visibility
        self.browser = browser_type.launch(
            headless=Config.HEADLESS,
            slow_mo=100  # Slow down by 100ms for better visibility
        )
        
        # Create browser context
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        
        # Create new page
        self.page = self.context.new_page()
        self.page.set_default_timeout(Config.BROWSER_TIMEOUT)
        
    def navigate(self, url: str) -> dict:
        """
        Navigate to a URL and return timing information
        
        Args:
            url: The URL to navigate to
            
        Returns:
            dict: Contains status, load_time, and any error
        """
        if not self.page:
            self.launch()
            
        self._start_time = time.time()
        
        try:
            # Navigate to URL
            response = self.page.goto(url, wait_until=Config.WAIT_UNTIL)
            load_time = time.time() - self._start_time
            
            return {
                "status": "success",
                "load_time": load_time,
                "http_status": response.status if response else None,
                "url": self.page.url,
                "title": self.page.title()
            }
        except Exception as e:
            load_time = time.time() - self._start_time
            return {
                "status": "error",
                "load_time": load_time,
                "error": str(e)
            }
    
    def get_page_content(self) -> str:
        """Get the HTML content of the current page"""
        if not self.page:
            raise Exception("Browser not launched. Call launch() first.")
        return self.page.content()
    
    def take_screenshot(self, path: Optional[str] = None, full_page: bool = True) -> bytes:
        """
        Take a screenshot of the current page
        
        Args:
            path: Optional file path to save screenshot
            full_page: Whether to capture full scrollable page
            
        Returns:
            bytes: Screenshot image data
        """
        if not self.page:
            raise Exception("Browser not launched. Call launch() first.")
            
        screenshot = self.page.screenshot(path=path, full_page=full_page)
        return screenshot
    
    def get_page_info(self) -> dict:
        """Get basic information about the current page"""
        if not self.page:
            return {}
            
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "viewport": self.page.viewport_size
        }
    
    def execute_script(self, script: str):
        """Execute JavaScript in the page context"""
        if not self.page:
            raise Exception("Browser not launched. Call launch() first.")
        return self.page.evaluate(script)
    
    def get_interactive_elements(self) -> list:
        """
        Extract interactive elements from the page
        
        Returns:
            list: List of dictionaries containing element information
        """
        if not self.page:
            raise Exception("Browser not launched. Call launch() first.")
            
        # JavaScript to extract interactive elements
        script = """
        () => {
            const elements = [];
            const selectors = [
                'a[href]',
                'button',
                'input',
                'select',
                'textarea',
                '[onclick]',
                '[role="button"]',
                '[role="link"]'
            ];
            
            const allElements = document.querySelectorAll(selectors.join(','));
            
            allElements.forEach((el, index) => {
                const rect = el.getBoundingClientRect();
                
                // Only include visible elements
                if (rect.width > 0 && rect.height > 0) {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || null,
                        id: el.id || null,
                        class: el.className || null,
                        name: el.name || null,
                        text: el.innerText?.substring(0, 100) || el.value || null,
                        href: el.href || null,
                        role: el.getAttribute('role') || null,
                        ariaLabel: el.getAttribute('aria-label') || null,
                        placeholder: el.placeholder || null,
                        visible: rect.width > 0 && rect.height > 0,
                        position: {
                            top: rect.top,
                            left: rect.left,
                            width: rect.width,
                            height: rect.height
                        }
                    });
                }
            });
            
            return elements;
        }
        """
        
        return self.execute_script(script)
    
    def close(self):
        """Close the browser and cleanup resources"""
        if self.page:
            self.page.close()
            self.page = None
            
        if self.context:
            self.context.close()
            self.context = None
            
        if self.browser:
            self.browser.close()
            self.browser = None
            
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
    
    def __enter__(self):
        """Context manager entry"""
        self.launch()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()