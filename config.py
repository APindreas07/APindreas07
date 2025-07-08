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
    
    # API settings
    YAHOO_FINANCE_BASE_URL: str = "https://query1.finance.yahoo.com"
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    
    # Data collection settings
    PRICE_UPDATE_INTERVAL_HOURS: int = 24  # Daily updates
    NEWS_UPDATE_INTERVAL_HOURS: int = 6    # Every 6 hours
    HISTORICAL_DATA_DAYS: int = 365        # 1 year of historical data
    
    # Analysis settings
    SENTIMENT_CONFIDENCE_THRESHOLD: float = 0.75
    TECHNICAL_INDICATORS: List[str] = None
    FUNDAMENTAL_METRICS: List[str] = None
    
    # Model settings
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"
    RETRAIN_THRESHOLD_ACCURACY: float = 0.65
    MIN_DATA_POINTS_FOR_RETRAIN: int = 100
    
    # File paths
    DATA_DIR: str = "data"
    MODELS_DIR: str = "models"
    LOGS_DIR: str = "logs"
    
    # Cache settings
    CACHE_DURATION_MINUTES: int = 60
    MAX_CACHE_SIZE: int = 1000
    
    def __post_init__(self):
        """Initialize default values for lists."""
        if self.TECHNICAL_INDICATORS is None:
            self.TECHNICAL_INDICATORS = [
                "SMA_20", "SMA_50", "SMA_200",
                "RSI", "MACD", "BB_upper", "BB_lower",
                "Volume_SMA", "Price_Change", "Volume_Change"
            ]
        
        if self.FUNDAMENTAL_METRICS is None:
            self.FUNDAMENTAL_METRICS = [
                "PE_Ratio", "PB_Ratio", "ROE", "ROA",
                "Debt_to_Equity", "Current_Ratio", "Profit_Margin"
            ]
        
        # Create necessary directories
        for directory in [self.DATA_DIR, self.MODELS_DIR, self.LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)

# Global configuration instance
config = Config()