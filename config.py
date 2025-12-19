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

    # LLM Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    GEMINI_MAX_TOKENS = int(os.getenv("GEMINI_MAX_TOKENS", "8192"))