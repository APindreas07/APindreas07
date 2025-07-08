import yfinance as yf
import pandas as pd
import numpy as np
import requests
import feedparser
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

class DataCollector:
    """Handles data collection from Yahoo Finance with intelligent API management."""
    
    def __init__(self, symbol: str = "AAPL", cache_dir: str = "cache"):
        self.symbol = symbol
        self.cache_dir = cache_dir
        self.last_price_update = None
        self.last_news_update = None
        self.price_cache_duration = timedelta(hours=24)  # Daily updates as requested
        self.news_cache_duration = timedelta(hours=6)   # 4 times per day for news
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # API call tracking
        self.api_calls_today = 0
        self.max_daily_calls = 1000
        
    def _should_update_prices(self) -> bool:
        """Check if price data needs updating (daily basis)."""
        if self.last_price_update is None:
            return True
        return datetime.now() - self.last_price_update > self.price_cache_duration
    
    def _should_update_news(self) -> bool:
        """Check if news data needs updating (4 times daily)."""
        if self.last_news_update is None:
            return True
        return datetime.now() - self.last_news_update > self.news_cache_duration
    
    def _track_api_call(self):
        """Track API calls to prevent exceeding limits."""
        self.api_calls_today += 1
        if self.api_calls_today >= self.max_daily_calls:
            self.logger.warning(f"Approaching daily API limit: {self.api_calls_today}/{self.max_daily_calls}")
    
    def get_stock_data(self, period: str = "1y") -> pd.DataFrame:
        """Get stock price data with caching."""
        cache_file = f"{self.cache_dir}/{self.symbol}_prices_{period}.json"
        
        # Check if we can use cached data
        if not self._should_update_prices() and os.path.exists(cache_file):
            self.logger.info(f"Using cached price data for {self.symbol}")
            return pd.read_json(cache_file)
        
        try:
            self._track_api_call()
            self.logger.info(f"Fetching fresh price data for {self.symbol}")
            
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=period)
            
            if not data.empty:
                # Cache the data
                data.to_json(cache_file)
                self.last_price_update = datetime.now()
                
                # Add technical indicators
                data = self._add_technical_indicators(data)
                
                self.logger.info(f"Successfully fetched {len(data)} days of price data")
                return data
            else:
                self.logger.error(f"No data returned for {self.symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error fetching stock data: {e}")
            # Try to return cached data if available
            if os.path.exists(cache_file):
                return pd.read_json(cache_file)
            return pd.DataFrame()
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical analysis indicators to the price data."""
        try:
            # Moving averages
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['EMA_12'] = data['Close'].ewm(span=12).mean()
            data['EMA_26'] = data['Close'].ewm(span=26).mean()
            
            # MACD
            data['MACD'] = data['EMA_12'] - data['EMA_26']
            data['MACD_signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_histogram'] = data['MACD'] - data['MACD_signal']
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            data['BB_middle'] = data['Close'].rolling(window=20).mean()
            bb_std = data['Close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
            data['BB_lower'] = data['BB_middle'] - (bb_std * 2)
            
            # Volume indicators
            data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
            data['Volume_ratio'] = data['Volume'] / data['Volume_SMA']
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error adding technical indicators: {e}")
            return data
    
    def get_news_sentiment_data(self) -> List[Dict]:
        """Get recent news with intelligent caching."""
        cache_file = f"{self.cache_dir}/{self.symbol}_news.json"
        
        # Check if we can use cached news
        if not self._should_update_news() and os.path.exists(cache_file):
            self.logger.info(f"Using cached news data for {self.symbol}")
            with open(cache_file, 'r') as f:
                return json.load(f)
        
        try:
            self._track_api_call()
            self.logger.info(f"Fetching fresh news data for {self.symbol}")
            
            ticker = yf.Ticker(self.symbol)
            news = ticker.news
            
            processed_news = []
            for article in news[:10]:  # Limit to 10 most recent articles
                processed_article = {
                    'title': article.get('title', ''),
                    'summary': article.get('summary', ''),
                    'published': article.get('providerPublishTime', 0),
                    'source': article.get('publisher', ''),
                    'url': article.get('link', '')
                }
                processed_news.append(processed_article)
            
            # Cache the news
            with open(cache_file, 'w') as f:
                json.dump(processed_news, f)
            
            self.last_news_update = datetime.now()
            self.logger.info(f"Successfully fetched {len(processed_news)} news articles")
            
            return processed_news
            
        except Exception as e:
            self.logger.error(f"Error fetching news data: {e}")
            # Try to return cached data if available
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
            return []
    
    def get_company_info(self) -> Dict:
        """Get company information and fundamentals."""
        cache_file = f"{self.cache_dir}/{self.symbol}_info.json"
        
        # Company info updates less frequently
        if os.path.exists(cache_file):
            modified_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - modified_time < timedelta(days=7):
                with open(cache_file, 'r') as f:
                    return json.load(f)
        
        try:
            self._track_api_call()
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # Extract key fundamental data
            company_data = {
                'symbol': info.get('symbol'),
                'name': info.get('longName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'marketCap': info.get('marketCap'),
                'enterpriseValue': info.get('enterpriseValue'),
                'peRatio': info.get('trailingPE'),
                'forwardPE': info.get('forwardPE'),
                'pegRatio': info.get('pegRatio'),
                'priceToBook': info.get('priceToBook'),
                'debtToEquity': info.get('debtToEquity'),
                'returnOnEquity': info.get('returnOnEquity'),
                'revenueGrowth': info.get('revenueGrowth'),
                'earningsGrowth': info.get('earningsGrowth'),
                'currentPrice': info.get('currentPrice'),
                'targetMeanPrice': info.get('targetMeanPrice'),
                'recommendationMean': info.get('recommendationMean'),
                'dividendYield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow')
            }
            
            # Cache the data
            with open(cache_file, 'w') as f:
                json.dump(company_data, f)
            
            return company_data
            
        except Exception as e:
            self.logger.error(f"Error fetching company info: {e}")
            return {}
    
    def get_api_usage_stats(self) -> Dict:
        """Get current API usage statistics."""
        return {
            'calls_today': self.api_calls_today,
            'max_daily_calls': self.max_daily_calls,
            'usage_percentage': (self.api_calls_today / self.max_daily_calls) * 100,
            'last_price_update': self.last_price_update,
            'last_news_update': self.last_news_update
        }