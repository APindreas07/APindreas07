import os
from typing import List, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Configuration settings for the financial analysis application."""
    
    # Stock settings
    STOCK_SYMBOL: str = "AAPL"
    STOCK_NAME: str = "Apple Inc."
    
    # Data collection settings
    PRICE_UPDATE_INTERVAL_HOURS: int = 24  # Daily updates
    NEWS_UPDATE_INTERVAL_HOURS: int = 6    # Every 6 hours
    HISTORICAL_DATA_DAYS: int = 365        # 1 year of historical data
    
    # API rate limiting
    MAX_API_CALLS_PER_MINUTE: int = 10
    API_CALL_DELAY_SECONDS: float = 6.0
    
    # Model settings
    FINBERT_MODEL: str = "ProsusAI/finbert"
    CONFIDENCE_THRESHOLD: float = 0.75
    MIN_NEWS_ARTICLES: int = 5
    
    # Technical analysis parameters
    SMA_SHORT: int = 20
    SMA_LONG: int = 50
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70
    RSI_OVERSOLD: float = 30
    
    # Sentiment analysis weights
    NEWS_WEIGHT: float = 0.4
    TECHNICAL_WEIGHT: float = 0.3
    PRICE_MOMENTUM_WEIGHT: float = 0.3
    
    # File paths
    DATA_DIR: str = "data"
    LOGS_DIR: str = "logs"
    MODELS_DIR: str = "models"
    
    # Database settings (if needed)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///financial_data.db")
    
    @classmethod
    def get_stock_info(cls) -> Dict[str, Any]:
        """Get stock information dictionary."""
        return {
            "symbol": cls.STOCK_SYMBOL,
            "name": cls.STOCK_NAME,
            "update_interval": cls.PRICE_UPDATE_INTERVAL_HOURS
        }
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.DATA_DIR, cls.LOGS_DIR, cls.MODELS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global configuration instance
config = Config()