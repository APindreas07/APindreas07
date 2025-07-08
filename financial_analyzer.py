import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import os

from config import config
from data_collector import data_collector
from technical_analyzer import technical_analyzer
from sentiment_analyzer import sentiment_analyzer

logger = logging.getLogger(__name__)

class FinancialAnalyzer:
    """Main financial analyzer that combines technical and sentiment analysis."""
    
    def __init__(self):
        self.news_weight = config.NEWS_WEIGHT
        self.technical_weight = config.TECHNICAL_WEIGHT
        self.price_momentum_weight = config.PRICE_MOMENTUM_WEIGHT
        
        # Ensure directories exist
        config.create_directories()
        
        # Initialize analysis history
        self.analysis_history_file = os.path.join(config.DATA_DIR, f"{config.STOCK_SYMBOL}_analysis_history.json")
        self.load_analysis_history()
    
    def load_analysis_history(self):
        """Load previous analysis results."""
        self.analysis_history = []
        if os.path.exists(self.analysis_history_file):
            try:
                with open(self.analysis_history_file, 'r') as f:
                    self.analysis_history = json.load(f)
                logger.info(f"Loaded {len(self.analysis_history)} previous analyses")
            except Exception as e:
                logger.warning(f"Failed to load analysis history: {e}")
    
    def save_analysis_history(self):
        """Save analysis results to history."""
        try:
            with open(self.analysis_history_file, 'w') as f:
                json.dump(self.analysis_history, f, indent=2, default=str)
            logger.info("Saved analysis to history")
        except Exception as e:
            logger.error(f"Failed to save analysis history: {e}")
    
    def get_current_market_data(self) -> Dict[str, any]:
        """Get current market data for the stock."""
        try:
            # Get stock data
            stock_data = data_collector.get_stock_data()
            if stock_data is None or stock_data.empty:
                return {'error': 'Failed to fetch stock data'}
            
            # Get stock info
            stock_info = data_collector.get_stock_info()
            
            # Get current price and basic metrics
            current_price = stock_data['Close'].iloc[-1]
            previous_price = stock_data['Close'].iloc[-2] if len(stock_data) > 1 else current_price
            price_change = current_price - previous_price
            price_change_percent = (price_change / previous_price) * 100 if previous_price > 0 else 0
            
            # Calculate volume metrics
            current_volume = stock_data['Volume'].iloc[-1]
            avg_volume = stock_data['Volume'].rolling(window=20).mean().iloc[-1]
            
            return {
                'current_price': current_price,
                'previous_price': previous_price,
                'price_change': price_change,
                'price_change_percent': price_change_percent,
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1.0,
                'stock_info': stock_info,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting current market data: {e}")
            return {'error': f'Error getting market data: {e}'}
    
    def perform_technical_analysis(self, stock_data: pd.DataFrame) -> Dict[str, any]:
        """Perform comprehensive technical analysis."""
        try:
            if stock_data is None or stock_data.empty:
                return {'error': 'No stock data available for technical analysis'}
            
            # Get technical analysis results
            technical_results = technical_analyzer.analyze_all_indicators(stock_data)
            
            # Add additional technical metrics
            current_price = stock_data['Close'].iloc[-1]
            high_52w = stock_data['High'].max()
            low_52w = stock_data['Low'].min()
            
            technical_results['price_metrics'] = {
                'current_price': current_price,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'price_vs_high': (current_price / high_52w) * 100 if high_52w > 0 else 0,
                'price_vs_low': (current_price / low_52w) * 100 if low_52w > 0 else 0
            }
            
            return technical_results
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return {'error': f'Technical analysis error: {e}'}
    
    def perform_sentiment_analysis(self) -> Dict[str, any]:
        """Perform comprehensive sentiment analysis."""
        try:
            # Get news articles
            news_articles = data_collector.get_news()
            
            # Get earnings data
            earnings_data = data_collector.get_earnings_data()
            
            # Analyze news sentiment
            analyzed_news = sentiment_analyzer.analyze_news_batch(news_articles)
            news_sentiment = sentiment_analyzer.get_aggregate_sentiment(analyzed_news)
            
            # Analyze earnings sentiment
            earnings_sentiment = sentiment_analyzer.analyze_earnings_sentiment(earnings_data)
            
            return {
                'news_sentiment': news_sentiment,
                'earnings_sentiment': earnings_sentiment,
                'analyzed_news': analyzed_news,
                'earnings_data': earnings_data
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return {'error': f'Sentiment analysis error: {e}'}
    
    def combine_analysis_results(self, technical_results: Dict, sentiment_results: Dict, market_data: Dict) -> Dict[str, any]:
        """Combine technical and sentiment analysis for final recommendation."""
        try:
            # Initialize weights
            technical_weight = self.technical_weight
            news_weight = self.news_weight
            momentum_weight = self.price_momentum_weight
            
            # Get technical recommendation
            technical_signal = technical_results.get('recommendation', 'NEUTRAL')
            technical_confidence = technical_results.get('confidence', 0.5)
            
            # Get news sentiment
            news_signal = sentiment_results.get('news_sentiment', {}).get('overall_signal', 'NEUTRAL')
            news_confidence = sentiment_results.get('news_sentiment', {}).get('confidence', 0.5)
            
            # Get earnings sentiment
            earnings_signal = sentiment_results.get('earnings_sentiment', {}).get('earnings_signal', 'NEUTRAL')
            earnings_confidence = sentiment_results.get('earnings_sentiment', {}).get('confidence', 0.5)
            
            # Calculate price momentum signal
            price_change_percent = market_data.get('price_change_percent', 0)
            if price_change_percent > 2:
                momentum_signal = 'BUY'
                momentum_confidence = min(0.8, 0.5 + (price_change_percent * 0.05))
            elif price_change_percent < -2:
                momentum_signal = 'SELL'
                momentum_confidence = min(0.8, 0.5 + (abs(price_change_percent) * 0.05))
            else:
                momentum_signal = 'NEUTRAL'
                momentum_confidence = 0.5
            
            # Convert signals to numerical scores
            signal_scores = {
                'Strong BUY': 2,
                'BUY': 1,
                'NEUTRAL': 0,
                'SELL': -1,
                'Strong SELL': -2
            }
            
            technical_score = signal_scores.get(technical_signal, 0) * technical_confidence
            news_score = signal_scores.get(news_signal, 0) * news_confidence
            earnings_score = signal_scores.get(earnings_signal, 0) * earnings_confidence
            momentum_score = signal_scores.get(momentum_signal, 0) * momentum_confidence
            
            # Calculate weighted score
            total_weight = technical_weight + news_weight + momentum_weight
            weighted_score = (
                technical_score * technical_weight +
                news_score * news_weight +
                momentum_score * momentum_weight
            ) / total_weight
            
            # Add earnings as additional factor
            if earnings_confidence > 0.6:
                weighted_score += earnings_score * 0.2
                total_weight += 0.2
            
            # Determine final recommendation
            if weighted_score > 1.0:
                final_recommendation = 'Strong BUY'
                confidence = min(0.95, 0.7 + (weighted_score - 1.0) * 0.25)
            elif weighted_score > 0.3:
                final_recommendation = 'BUY'
                confidence = min(0.85, 0.5 + weighted_score * 0.35)
            elif weighted_score < -1.0:
                final_recommendation = 'Strong SELL'
                confidence = min(0.95, 0.7 + (abs(weighted_score) - 1.0) * 0.25)
            elif weighted_score < -0.3:
                final_recommendation = 'SELL'
                confidence = min(0.85, 0.5 + abs(weighted_score) * 0.35)
            else:
                final_recommendation = 'NEUTRAL'
                confidence = 0.5 + abs(weighted_score) * 0.3
            
            # Determine timing recommendation
            timing = self.get_timing_recommendation(technical_results, sentiment_results, market_data)
            
            return {
                'final_recommendation': final_recommendation,
                'confidence': confidence,
                'weighted_score': weighted_score,
                'timing': timing,
                'component_analysis': {
                    'technical': {
                        'signal': technical_signal,
                        'confidence': technical_confidence,
                        'weight': technical_weight
                    },
                    'news_sentiment': {
                        'signal': news_signal,
                        'confidence': news_confidence,
                        'weight': news_weight
                    },
                    'earnings_sentiment': {
                        'signal': earnings_signal,
                        'confidence': earnings_confidence,
                        'weight': 0.2 if earnings_confidence > 0.6 else 0
                    },
                    'price_momentum': {
                        'signal': momentum_signal,
                        'confidence': momentum_confidence,
                        'weight': momentum_weight
                    }
                },
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error combining analysis results: {e}")
            return {
                'final_recommendation': 'NEUTRAL',
                'confidence': 0.0,
                'error': f'Error combining results: {e}'
            }
    
    def get_timing_recommendation(self, technical_results: Dict, sentiment_results: Dict, market_data: Dict) -> str:
        """Determine optimal timing for the recommendation."""
        try:
            # Check for immediate opportunities
            technical_signals = technical_results.get('signals', {})
            
            # Check for strong technical signals
            strong_signals = 0
            for signal_type, signal_data in technical_signals.items():
                if signal_data.get('strength') == 'Strong':
                    strong_signals += 1
            
            # Check volume
            volume_ratio = market_data.get('volume_ratio', 1.0)
            
            # Check price momentum
            price_change_percent = market_data.get('price_change_percent', 0)
            
            if strong_signals >= 3 and volume_ratio > 1.5:
                return "IMMEDIATE"
            elif strong_signals >= 2 and abs(price_change_percent) > 3:
                return "IMMEDIATE"
            elif strong_signals >= 2:
                return "SOON"
            elif strong_signals >= 1:
                return "MONITOR"
            else:
                return "WAIT"
                
        except Exception as e:
            logger.error(f"Error determining timing: {e}")
            return "MONITOR"
    
    def perform_complete_analysis(self) -> Dict[str, any]:
        """Perform complete financial analysis."""
        try:
            logger.info(f"Starting complete analysis for {config.STOCK_SYMBOL}")
            
            # Get market data
            market_data = self.get_current_market_data()
            if 'error' in market_data:
                return market_data
            
            # Get stock data for technical analysis
            stock_data = data_collector.get_stock_data()
            if stock_data is None or stock_data.empty:
                return {'error': 'No stock data available'}
            
            # Perform technical analysis
            technical_results = self.perform_technical_analysis(stock_data)
            if 'error' in technical_results:
                return technical_results
            
            # Perform sentiment analysis
            sentiment_results = self.perform_sentiment_analysis()
            if 'error' in sentiment_results:
                return sentiment_results
            
            # Combine results
            final_analysis = self.combine_analysis_results(technical_results, sentiment_results, market_data)
            
            # Add market data to final analysis
            final_analysis['market_data'] = market_data
            final_analysis['technical_analysis'] = technical_results
            final_analysis['sentiment_analysis'] = sentiment_results
            
            # Save to history
            self.analysis_history.append(final_analysis)
            if len(self.analysis_history) > 100:  # Keep last 100 analyses
                self.analysis_history = self.analysis_history[-100:]
            self.save_analysis_history()
            
            logger.info(f"Analysis complete. Recommendation: {final_analysis['final_recommendation']}")
            return final_analysis
            
        except Exception as e:
            logger.error(f"Error in complete analysis: {e}")
            return {'error': f'Analysis failed: {e}'}
    
    def get_analysis_summary(self) -> Dict[str, any]:
        """Get a summary of recent analyses."""
        if not self.analysis_history:
            return {'message': 'No analysis history available'}
        
        recent_analyses = self.analysis_history[-10:]  # Last 10 analyses
        
        recommendations = [analysis.get('final_recommendation', 'NEUTRAL') for analysis in recent_analyses]
        confidences = [analysis.get('confidence', 0.0) for analysis in recent_analyses]
        
        # Calculate trends
        recommendation_counts = {}
        for rec in recommendations:
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        avg_confidence = np.mean(confidences) if confidences else 0.0
        
        return {
            'total_analyses': len(self.analysis_history),
            'recent_analyses': len(recent_analyses),
            'recommendation_distribution': recommendation_counts,
            'average_confidence': avg_confidence,
            'latest_recommendation': recommendations[-1] if recommendations else 'NEUTRAL',
            'latest_confidence': confidences[-1] if confidences else 0.0
        }

# Global instance
financial_analyzer = FinancialAnalyzer()