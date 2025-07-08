import yfinance as yf
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import os
from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter to manage API calls."""
    
    def __init__(self, max_calls_per_minute: int, delay_seconds: float):
        self.max_calls_per_minute = max_calls_per_minute
        self.delay_seconds = delay_seconds
        self.call_times = []
    
    def wait_if_needed(self):
        """Wait if we've made too many calls recently."""
        now = time.time()
        # Remove calls older than 1 minute
        self.call_times = [t for t in self.call_times if now - t < 60]
        
        if len(self.call_times) >= self.max_calls_per_minute:
            sleep_time = 60 - (now - self.call_times[0]) + 1
            logger.info(f"Rate limit reached. Waiting {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        
        self.call_times.append(now)
        time.sleep(self.delay_seconds)

class YahooFinanceCollector:
    """Collects financial data from Yahoo Finance with rate limiting."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(
            config.MAX_API_CALLS_PER_MINUTE,
            config.API_CALL_DELAY_SECONDS
        )
        self.cache_file = os.path.join(config.DATA_DIR, f"{config.STOCK_SYMBOL}_cache.json")
        self.load_cache()
    
    def load_cache(self):
        """Load cached data if available."""
        self.cache = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info("Loaded cached data")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
    
    def save_cache(self):
        """Save data to cache."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2, default=str)
            logger.info("Saved data to cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_stock_data(self, symbol: str = None, period: str = "1y") -> Optional[pd.DataFrame]:
        """Get stock price data from Yahoo Finance."""
        symbol = symbol or config.STOCK_SYMBOL
        
        # Check cache first
        cache_key = f"price_data_{period}"
        if cache_key in self.cache:
            last_update = datetime.fromisoformat(self.cache[cache_key]['last_update'])
            if datetime.now() - last_update < timedelta(hours=config.PRICE_UPDATE_INTERVAL_HOURS):
                logger.info(f"Using cached price data for {symbol}")
                return pd.DataFrame(self.cache[cache_key]['data'])
        
        try:
            self.rate_limiter.wait_if_needed()
            logger.info(f"Fetching price data for {symbol}")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                logger.error(f"No data received for {symbol}")
                return None
            
            # Cache the data
            self.cache[cache_key] = {
                'data': data.to_dict('records'),
                'last_update': datetime.now().isoformat()
            }
            self.save_cache()
            
            logger.info(f"Successfully fetched {len(data)} data points for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return None
    
    def get_stock_info(self, symbol: str = None) -> Optional[Dict]:
        """Get basic stock information."""
        symbol = symbol or config.STOCK_SYMBOL
        
        cache_key = f"stock_info_{symbol}"
        if cache_key in self.cache:
            last_update = datetime.fromisoformat(self.cache[cache_key]['last_update'])
            if datetime.now() - last_update < timedelta(hours=24):
                return self.cache[cache_key]['data']
        
        try:
            self.rate_limiter.wait_if_needed()
            logger.info(f"Fetching stock info for {symbol}")
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Cache the info
            self.cache[cache_key] = {
                'data': info,
                'last_update': datetime.now().isoformat()
            }
            self.save_cache()
            
            return info
            
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None
    
    def get_news(self, symbol: str = None, limit: int = 20) -> List[Dict]:
        """Get news articles for the stock."""
        symbol = symbol or config.STOCK_SYMBOL
        
        cache_key = f"news_{symbol}"
        if cache_key in self.cache:
            last_update = datetime.fromisoformat(self.cache[cache_key]['last_update'])
            if datetime.now() - last_update < timedelta(hours=config.NEWS_UPDATE_INTERVAL_HOURS):
                logger.info(f"Using cached news for {symbol}")
                return self.cache[cache_key]['data']
        
        try:
            self.rate_limiter.wait_if_needed()
            logger.info(f"Fetching news for {symbol}")
            
            ticker = yf.Ticker(symbol)
            news = ticker.news
            
            if not news:
                logger.warning(f"No news found for {symbol}")
                return []
            
            # Process and cache news
            processed_news = []
            for article in news[:limit]:
                processed_news.append({
                    'title': article.get('title', ''),
                    'summary': article.get('summary', ''),
                    'publisher': article.get('publisher', ''),
                    'link': article.get('link', ''),
                    'published': article.get('providerPublishTime', ''),
                    'sentiment_score': 0  # Will be calculated later
                })
            
            self.cache[cache_key] = {
                'data': processed_news,
                'last_update': datetime.now().isoformat()
            }
            self.save_cache()
            
            logger.info(f"Successfully fetched {len(processed_news)} news articles for {symbol}")
            return processed_news
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []
    
    def get_earnings_data(self, symbol: str = None) -> Optional[Dict]:
        """Get earnings data for the stock."""
        symbol = symbol or config.STOCK_SYMBOL
        
        cache_key = f"earnings_{symbol}"
        if cache_key in self.cache:
            last_update = datetime.fromisoformat(self.cache[cache_key]['last_update'])
            if datetime.now() - last_update < timedelta(hours=24):
                return self.cache[cache_key]['data']
        
        try:
            self.rate_limiter.wait_if_needed()
            logger.info(f"Fetching earnings data for {symbol}")
            
            ticker = yf.Ticker(symbol)
            earnings = ticker.earnings
            
            if earnings is None or earnings.empty:
                logger.warning(f"No earnings data found for {symbol}")
                return None
            
            earnings_data = {
                'quarterly': earnings.to_dict('records'),
                'annual': ticker.earnings_annual.to_dict('records') if hasattr(ticker, 'earnings_annual') else []
            }
            
            self.cache[cache_key] = {
                'data': earnings_data,
                'last_update': datetime.now().isoformat()
            }
            self.save_cache()
            
            return earnings_data
            
        except Exception as e:
            logger.error(f"Error fetching earnings data for {symbol}: {e}")
            return None

# Global instance
data_collector = YahooFinanceCollector()