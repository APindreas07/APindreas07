import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from config import config
import re

logger = logging.getLogger(__name__)

class EnhancedFinBertAnalyzer:
    """Enhanced FinBERT sentiment analyzer with improved accuracy and confidence scoring."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.FINBERT_MODEL
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        try:
            logger.info(f"Loading FinBERT model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for better sentiment analysis."""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove special characters and normalize
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Truncate if too long (BERT has token limits)
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of a single text."""
        if not text:
            return {
                'sentiment': 'NEUTRAL',
                'confidence': 0.0,
                'scores': {'positive': 0.33, 'neutral': 0.34, 'negative': 0.33}
            }
        
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            # Tokenize
            inputs = self.tokenizer(
                processed_text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                scores = torch.softmax(logits, dim=1)[0]
                predicted_class = torch.argmax(scores).item()
                confidence = scores[predicted_class].item()
            
            # Map to sentiment labels
            sentiment_mapping = {
                0: "NEUTRAL",
                1: "POSITIVE", 
                2: "NEGATIVE"
            }
            
            sentiment = sentiment_mapping.get(predicted_class, "NEUTRAL")
            
            # Convert to buy/sell signals
            if sentiment == "POSITIVE" and confidence > self.confidence_threshold:
                signal = "Strong BUY"
            elif sentiment == "POSITIVE":
                signal = "BUY"
            elif sentiment == "NEGATIVE" and confidence > self.confidence_threshold:
                signal = "Strong SELL"
            elif sentiment == "NEGATIVE":
                signal = "SELL"
            else:
                signal = "NEUTRAL"
            
            return {
                'sentiment': sentiment,
                'signal': signal,
                'confidence': confidence,
                'scores': {
                    'positive': scores[1].item(),
                    'neutral': scores[0].item(),
                    'negative': scores[2].item()
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'sentiment': 'NEUTRAL',
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'scores': {'positive': 0.33, 'neutral': 0.34, 'negative': 0.33}
            }
    
    def analyze_news_batch(self, news_articles: List[Dict]) -> List[Dict]:
        """Analyze sentiment for a batch of news articles."""
        if not news_articles:
            return []
        
        analyzed_news = []
        
        for article in news_articles:
            # Combine title and summary for analysis
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            
            # Analyze sentiment
            sentiment_result = self.analyze_sentiment(text)
            
            # Add sentiment results to article
            analyzed_article = {
                **article,
                'sentiment_analysis': sentiment_result,
                'sentiment_score': sentiment_result['confidence'],
                'sentiment_signal': sentiment_result['signal']
            }
            
            analyzed_news.append(analyzed_article)
        
        return analyzed_news
    
    def get_aggregate_sentiment(self, analyzed_news: List[Dict]) -> Dict[str, any]:
        """Calculate aggregate sentiment from multiple news articles."""
        if not analyzed_news:
            return {
                'overall_sentiment': 'NEUTRAL',
                'overall_signal': 'NEUTRAL',
                'confidence': 0.0,
                'article_count': 0,
                'sentiment_distribution': {'Strong BUY': 0, 'BUY': 0, 'NEUTRAL': 0, 'SELL': 0, 'Strong SELL': 0}
            }
        
        # Count sentiment signals
        sentiment_counts = {'Strong BUY': 0, 'BUY': 0, 'NEUTRAL': 0, 'SELL': 0, 'Strong SELL': 0}
        total_confidence = 0.0
        valid_articles = 0
        
        for article in analyzed_news:
            signal = article.get('sentiment_signal', 'NEUTRAL')
            confidence = article.get('sentiment_score', 0.0)
            
            if signal in sentiment_counts:
                sentiment_counts[signal] += 1
                total_confidence += confidence
                valid_articles += 1
        
        if valid_articles == 0:
            return {
                'overall_sentiment': 'NEUTRAL',
                'overall_signal': 'NEUTRAL',
                'confidence': 0.0,
                'article_count': 0,
                'sentiment_distribution': sentiment_counts
            }
        
        # Calculate overall sentiment
        avg_confidence = total_confidence / valid_articles
        
        # Determine overall signal based on majority
        buy_signals = sentiment_counts['Strong BUY'] + sentiment_counts['BUY']
        sell_signals = sentiment_counts['Strong SELL'] + sentiment_counts['SELL']
        neutral_signals = sentiment_counts['NEUTRAL']
        
        total_signals = buy_signals + sell_signals + neutral_signals
        
        if total_signals == 0:
            overall_signal = 'NEUTRAL'
        elif buy_signals > sell_signals and buy_signals > neutral_signals:
            if sentiment_counts['Strong BUY'] > sentiment_counts['BUY']:
                overall_signal = 'Strong BUY'
            else:
                overall_signal = 'BUY'
        elif sell_signals > buy_signals and sell_signals > neutral_signals:
            if sentiment_counts['Strong SELL'] > sentiment_counts['SELL']:
                overall_signal = 'Strong SELL'
            else:
                overall_signal = 'SELL'
        else:
            overall_signal = 'NEUTRAL'
        
        # Calculate confidence based on signal strength
        if overall_signal in ['Strong BUY', 'Strong SELL']:
            confidence_multiplier = 1.2
        elif overall_signal in ['BUY', 'SELL']:
            confidence_multiplier = 1.0
        else:
            confidence_multiplier = 0.8
        
        final_confidence = min(0.95, avg_confidence * confidence_multiplier)
        
        return {
            'overall_sentiment': overall_signal,
            'overall_signal': overall_signal,
            'confidence': final_confidence,
            'article_count': valid_articles,
            'sentiment_distribution': sentiment_counts,
            'buy_ratio': buy_signals / total_signals if total_signals > 0 else 0,
            'sell_ratio': sell_signals / total_signals if total_signals > 0 else 0,
            'neutral_ratio': neutral_signals / total_signals if total_signals > 0 else 0
        }
    
    def analyze_earnings_sentiment(self, earnings_data: Dict) -> Dict[str, any]:
        """Analyze sentiment from earnings data."""
        if not earnings_data:
            return {
                'earnings_sentiment': 'NEUTRAL',
                'earnings_signal': 'NEUTRAL',
                'confidence': 0.0
            }
        
        # Analyze quarterly earnings
        quarterly_earnings = earnings_data.get('quarterly', [])
        if not quarterly_earnings:
            return {
                'earnings_sentiment': 'NEUTRAL',
                'earnings_signal': 'NEUTRAL',
                'confidence': 0.0
            }
        
        # Calculate earnings growth and surprises
        positive_surprises = 0
        negative_surprises = 0
        total_quarters = len(quarterly_earnings)
        
        for quarter in quarterly_earnings[-4:]:  # Last 4 quarters
            if 'Surprise' in quarter and quarter['Surprise'] is not None:
                surprise = quarter['Surprise']
                if surprise > 0:
                    positive_surprises += 1
                elif surprise < 0:
                    negative_surprises += 1
        
        # Determine earnings sentiment
        if positive_surprises > negative_surprises and positive_surprises >= 2:
            earnings_signal = 'BUY'
            confidence = min(0.8, 0.5 + (positive_surprises * 0.1))
        elif negative_surprises > positive_surprises and negative_surprises >= 2:
            earnings_signal = 'SELL'
            confidence = min(0.8, 0.5 + (negative_surprises * 0.1))
        else:
            earnings_signal = 'NEUTRAL'
            confidence = 0.5
        
        return {
            'earnings_sentiment': earnings_signal,
            'earnings_signal': earnings_signal,
            'confidence': confidence,
            'positive_surprises': positive_surprises,
            'negative_surprises': negative_surprises,
            'total_quarters_analyzed': total_quarters
        }

# Global instance
sentiment_analyzer = EnhancedFinBertAnalyzer()