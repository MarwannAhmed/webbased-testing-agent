import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Load configuration from environment variables
    
    # Debug Mode
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"