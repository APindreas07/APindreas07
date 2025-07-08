import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os
from typing import Dict, List, Optional, Tuple
import logging
from config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    """Efficient data collector for Yahoo Finance with caching and rate limiting."""
    
    def __init__(self):
        self.cache = {}
        self.last_api_call = {}
        self.rate_limit_delay = 1  # seconds between API calls
        
    def _get_cache_key(self, symbol: str, data_type: str, **kwargs) -> str:
        """Generate cache key for data."""
        return f"{symbol}_{data_type}_{hash(str(kwargs))}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        
        cache_time, _ = self.cache[cache_key]
        cache_age = (datetime.now() - cache_time).total_seconds() / 60
        return cache_age < config.CACHE_DURATION_MINUTES
    
    def _rate_limit(self, api_type: str):
        """Implement rate limiting for API calls."""
        if api_type in self.last_api_call:
            time_since_last = time.time() - self.last_api_call[api_type]
            if time_since_last < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - time_since_last)
        self.last_api_call[api_type] = time.time()
    
    def get_stock_data(self, symbol: str = None, period: str = "1y") -> pd.DataFrame:
        """Get historical stock data with caching."""
        symbol = symbol or config.STOCK_SYMBOL
        cache_key = self._get_cache_key(symbol, "stock_data", period=period)
        
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached stock data for {symbol}")
            return self.cache[cache_key][1]
        
        self._rate_limit("yahoo_finance")
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                raise ValueError(f"No data received for {symbol}")
            
            # Add technical indicators
            data = self._add_technical_indicators(data)
            
            # Cache the data
            self.cache[cache_key] = (datetime.now(), data)
            
            # Clean old cache entries
            self._clean_cache()
            
            logger.info(f"Successfully fetched stock data for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
            raise
    
    def get_fundamental_data(self, symbol: str = None) -> Dict:
        """Get fundamental data for the stock."""
        symbol = symbol or config.STOCK_SYMBOL
        cache_key = self._get_cache_key(symbol, "fundamental_data")
        
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached fundamental data for {symbol}")
            return self.cache[cache_key][1]
        
        self._rate_limit("yahoo_finance")
        try:
            ticker = yf.Ticker(symbol)
            
            # Get various fundamental data
            info = ticker.info
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            fundamental_data = {
                'info': info,
                'financials': financials,
                'balance_sheet': balance_sheet,
                'cashflow': cashflow,
                'timestamp': datetime.now()
            }
            
            # Cache the data
            self.cache[cache_key] = (datetime.now(), fundamental_data)
            
            logger.info(f"Successfully fetched fundamental data for {symbol}")
            return fundamental_data
            
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {str(e)}")
            raise
    
    def get_latest_price(self, symbol: str = None) -> Dict:
        """Get the latest stock price and basic info."""
        symbol = symbol or config.STOCK_SYMBOL
        cache_key = self._get_cache_key(symbol, "latest_price")
        
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key][1]
        
        self._rate_limit("yahoo_finance")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            latest_data = {
                'symbol': symbol,
                'current_price': info.get('currentPrice', 0),
                'previous_close': info.get('previousClose', 0),
                'open': info.get('open', 0),
                'day_high': info.get('dayHigh', 0),
                'day_low': info.get('dayLow', 0),
                'volume': info.get('volume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'timestamp': datetime.now()
            }
            
            # Cache the data
            self.cache[cache_key] = (datetime.now(), latest_data)
            
            return latest_data
            
        except Exception as e:
            logger.error(f"Error fetching latest price for {symbol}: {str(e)}")
            raise
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the stock data."""
        # Simple Moving Averages
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
        data['SMA_50'] = data['Close'].rolling(window=50).mean()
        data['SMA_200'] = data['Close'].rolling(window=200).mean()
        
        # RSI (Relative Strength Index)
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['Close'].ewm(span=12).mean()
        exp2 = data['Close'].ewm(span=26).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
        
        # Bollinger Bands
        data['BB_middle'] = data['Close'].rolling(window=20).mean()
        bb_std = data['Close'].rolling(window=20).std()
        data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
        data['BB_lower'] = data['BB_middle'] - (bb_std * 2)
        
        # Volume indicators
        data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
        data['Price_Change'] = data['Close'].pct_change()
        data['Volume_Change'] = data['Volume'].pct_change()
        
        return data
    
    def _clean_cache(self):
        """Remove old cache entries to prevent memory issues."""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, (cache_time, _) in self.cache.items():
            cache_age = (current_time - cache_time).total_seconds() / 60
            if cache_age > config.CACHE_DURATION_MINUTES or len(self.cache) > config.MAX_CACHE_SIZE:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def save_data_to_file(self, data: pd.DataFrame, filename: str):
        """Save data to file for persistence."""
        filepath = os.path.join(config.DATA_DIR, filename)
        data.to_csv(filepath)
        logger.info(f"Data saved to {filepath}")
    
    def load_data_from_file(self, filename: str) -> pd.DataFrame:
        """Load data from file."""
        filepath = os.path.join(config.DATA_DIR, filename)
        if os.path.exists(filepath):
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            logger.info(f"Data loaded from {filepath}")
            return data
        else:
            logger.warning(f"File {filepath} not found")
            return pd.DataFrame()