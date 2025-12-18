import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Load configuration from environment variables
    
    # Debug Mode
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # Browser Configuration
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")  # chromium, firefox, or webkit
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # milliseconds
    
    # Page Load Configuration
    WAIT_UNTIL = os.getenv("WAIT_UNTIL", "networkidle")  # load, domcontentloaded, networkidle