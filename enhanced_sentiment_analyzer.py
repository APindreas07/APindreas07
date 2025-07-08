import os
import torch
import pandas as pd
import numpy as np
import joblib
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import warnings
warnings.filterwarnings('ignore')

class EnhancedSentimentAnalyzer:
    """Enhanced FinBERT-based sentiment analyzer with ensemble methods and retraining capabilities."""
    
    def __init__(self, model_dir: str = "models", retrain_threshold: float = 0.7):
        self.model_dir = model_dir
        self.retrain_threshold = retrain_threshold
        self.model_performance_history = []
        self.last_retrain_date = None
        
        # Create models directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self._initialize_models()
        
        # Load or create ensemble model
        self._load_or_create_ensemble()
        
    def _initialize_models(self):
        """Initialize all sentiment analysis models."""
        try:
            # FinBERT model
            self.finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            self.finbert_model.eval()
            
            # Alternative financial sentiment model
            self.finbert_pipeline = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert"
            )
            
            # VADER sentiment analyzer for social media text
            self.vader_analyzer = SentimentIntensityAnalyzer()
            
            self.logger.info("Successfully initialized all sentiment models")
            
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
            raise
    
    def _load_or_create_ensemble(self):
        """Load existing ensemble model or create a new one."""
        ensemble_path = os.path.join(self.model_dir, "ensemble_model.joblib")
        
        if os.path.exists(ensemble_path):
            try:
                self.ensemble_model = joblib.load(ensemble_path)
                self.logger.info("Loaded existing ensemble model")
            except Exception as e:
                self.logger.warning(f"Error loading ensemble model: {e}. Creating new one.")
                self._create_ensemble_model()
        else:
            self._create_ensemble_model()
    
    def _create_ensemble_model(self):
        """Create a new ensemble model for combining different sentiment scores."""
        # Simple logistic regression for combining sentiment scores
        self.ensemble_model = LogisticRegression(random_state=42)
        
        # We'll train this with initial data or retrain as needed
        self.logger.info("Created new ensemble model")
    
    def analyze_finbert(self, text: str) -> Dict:
        """Analyze sentiment using FinBERT model."""
        try:
            inputs = self.finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
                logits = outputs.logits
                scores = torch.softmax(logits, dim=1)[0]
                
            # FinBERT labels: 0=positive, 1=negative, 2=neutral
            labels = ['positive', 'negative', 'neutral']
            confidence_scores = {
                'positive': scores[0].item(),
                'negative': scores[1].item(), 
                'neutral': scores[2].item()
            }
            
            predicted_label = labels[torch.argmax(scores).item()]
            max_confidence = max(confidence_scores.values())
            
            return {
                'label': predicted_label,
                'confidence': max_confidence,
                'scores': confidence_scores
            }
            
        except Exception as e:
            self.logger.error(f"Error in FinBERT analysis: {e}")
            return {'label': 'neutral', 'confidence': 0.5, 'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}}
    
    def analyze_vader(self, text: str) -> Dict:
        """Analyze sentiment using VADER."""
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            
            # Convert VADER scores to our format
            if scores['compound'] >= 0.05:
                label = 'positive'
            elif scores['compound'] <= -0.05:
                label = 'negative'
            else:
                label = 'neutral'
                
            return {
                'label': label,
                'confidence': abs(scores['compound']),
                'scores': {
                    'positive': scores['pos'],
                    'negative': scores['neg'],
                    'neutral': scores['neu'],
                    'compound': scores['compound']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in VADER analysis: {e}")
            return {'label': 'neutral', 'confidence': 0.5, 'scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}}
    
    def analyze_textblob(self, text: str) -> Dict:
        """Analyze sentiment using TextBlob."""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                label = 'positive'
            elif polarity < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
                
            confidence = abs(polarity)
            
            return {
                'label': label,
                'confidence': confidence,
                'scores': {
                    'polarity': polarity,
                    'subjectivity': blob.sentiment.subjectivity
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in TextBlob analysis: {e}")
            return {'label': 'neutral', 'confidence': 0.5, 'scores': {'polarity': 0.0, 'subjectivity': 0.5}}
    
    def ensemble_analyze(self, text: str) -> Dict:
        """Combine multiple sentiment analysis methods for better accuracy."""
        # Get individual analyses
        finbert_result = self.analyze_finbert(text)
        vader_result = self.analyze_vader(text)
        textblob_result = self.analyze_textblob(text)
        
        # Combine scores with weights based on model performance
        finbert_weight = 0.6  # Higher weight for domain-specific model
        vader_weight = 0.3
        textblob_weight = 0.1
        
        # Calculate weighted sentiment scores
        sentiment_scores = {
            'positive': (
                finbert_result['scores'].get('positive', 0) * finbert_weight +
                (1 if vader_result['label'] == 'positive' else 0) * vader_weight +
                (1 if textblob_result['label'] == 'positive' else 0) * textblob_weight
            ),
            'negative': (
                finbert_result['scores'].get('negative', 0) * finbert_weight +
                (1 if vader_result['label'] == 'negative' else 0) * vader_weight +
                (1 if textblob_result['label'] == 'negative' else 0) * textblob_weight
            ),
            'neutral': (
                finbert_result['scores'].get('neutral', 0) * finbert_weight +
                (1 if vader_result['label'] == 'neutral' else 0) * vader_weight +
                (1 if textblob_result['label'] == 'neutral' else 0) * textblob_weight
            )
        }
        
        # Determine final label and confidence
        final_label = max(sentiment_scores, key=sentiment_scores.get)
        final_confidence = sentiment_scores[final_label]
        
        return {
            'label': final_label,
            'confidence': final_confidence,
            'ensemble_scores': sentiment_scores,
            'individual_results': {
                'finbert': finbert_result,
                'vader': vader_result,
                'textblob': textblob_result
            }
        }
    
    def classify_investment_sentiment(self, text: str) -> str:
        """Classify text into investment-grade sentiment categories."""
        result = self.ensemble_analyze(text)
        
        label = result['label']
        confidence = result['confidence']
        
        # Map to investment categories based on confidence
        if label == 'positive':
            if confidence > 0.8:
                return "Strong Buy"
            elif confidence > 0.6:
                return "Buy"
            else:
                return "Neutral"
        elif label == 'negative':
            if confidence > 0.8:
                return "Strong Sell"
            elif confidence > 0.6:
                return "Sell"
            else:
                return "Neutral"
        else:
            return "Neutral"
    
    def analyze_news_batch(self, news_articles: List[Dict]) -> Dict:
        """Analyze sentiment for a batch of news articles."""
        if not news_articles:
            return {
                'overall_sentiment': 'Neutral',
                'confidence': 0.5,
                'article_count': 0,
                'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
            }
        
        sentiments = []
        confidences = []
        
        for article in news_articles:
            # Combine title and summary for analysis
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            
            if text.strip():
                result = self.ensemble_analyze(text)
                sentiments.append(result['label'])
                confidences.append(result['confidence'])
        
        if not sentiments:
            return {
                'overall_sentiment': 'Neutral',
                'confidence': 0.5,
                'article_count': 0,
                'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0}
            }
        
        # Calculate overall sentiment
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        
        total_articles = len(sentiments)
        sentiment_distribution = {k: v/total_articles for k, v in sentiment_counts.items()}
        
        # Determine overall sentiment
        overall_sentiment = max(sentiment_distribution, key=sentiment_distribution.get)
        overall_confidence = np.mean(confidences)
        
        # Convert to investment recommendation
        investment_sentiment = self._convert_to_investment_sentiment(
            overall_sentiment, overall_confidence, sentiment_distribution
        )
        
        return {
            'overall_sentiment': investment_sentiment,
            'confidence': overall_confidence,
            'article_count': total_articles,
            'sentiment_distribution': sentiment_distribution,
            'raw_sentiment': overall_sentiment
        }
    
    def _convert_to_investment_sentiment(self, sentiment: str, confidence: float, distribution: Dict) -> str:
        """Convert raw sentiment to investment recommendation."""
        positive_ratio = distribution.get('positive', 0)
        negative_ratio = distribution.get('negative', 0)
        
        if sentiment == 'positive':
            if positive_ratio > 0.7 and confidence > 0.8:
                return "Strong Buy"
            elif positive_ratio > 0.5 and confidence > 0.6:
                return "Buy"
            else:
                return "Neutral"
        elif sentiment == 'negative':
            if negative_ratio > 0.7 and confidence > 0.8:
                return "Strong Sell"
            elif negative_ratio > 0.5 and confidence > 0.6:
                return "Sell"
            else:
                return "Neutral"
        else:
            return "Neutral"
    
    def evaluate_model_performance(self, test_data: List[Dict]) -> float:
        """Evaluate current model performance and determine if retraining is needed."""
        if not test_data:
            return 0.5
        
        correct_predictions = 0
        total_predictions = len(test_data)
        
        for item in test_data:
            text = item.get('text', '')
            true_label = item.get('label', 'neutral')
            
            predicted = self.ensemble_analyze(text)['label']
            
            if predicted == true_label:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions
        self.model_performance_history.append({
            'date': datetime.now(),
            'accuracy': accuracy,
            'sample_size': total_predictions
        })
        
        self.logger.info(f"Model accuracy: {accuracy:.3f} on {total_predictions} samples")
        
        # Check if retraining is needed
        if accuracy < self.retrain_threshold:
            self.logger.warning(f"Model accuracy {accuracy:.3f} below threshold {self.retrain_threshold}. Retraining recommended.")
            self._initiate_retraining()
        
        return accuracy
    
    def _initiate_retraining(self):
        """Initiate model retraining process."""
        self.logger.info("Initiating model retraining...")
        
        # For now, we'll reset the ensemble model
        # In a production environment, you would implement more sophisticated retraining
        self._create_ensemble_model()
        self.last_retrain_date = datetime.now()
        
        self.logger.info("Model retraining completed")
    
    def get_model_stats(self) -> Dict:
        """Get current model performance statistics."""
        if not self.model_performance_history:
            return {
                'current_accuracy': None,
                'average_accuracy': None,
                'total_evaluations': 0,
                'last_retrain_date': self.last_retrain_date,
                'retrain_threshold': self.retrain_threshold
            }
        
        recent_accuracy = self.model_performance_history[-1]['accuracy']
        average_accuracy = np.mean([h['accuracy'] for h in self.model_performance_history])
        
        return {
            'current_accuracy': recent_accuracy,
            'average_accuracy': average_accuracy,
            'total_evaluations': len(self.model_performance_history),
            'last_retrain_date': self.last_retrain_date,
            'retrain_threshold': self.retrain_threshold,
            'performance_trend': self._calculate_performance_trend()
        }
    
    def _calculate_performance_trend(self) -> str:
        """Calculate if model performance is improving or declining."""
        if len(self.model_performance_history) < 2:
            return "insufficient_data"
        
        recent_scores = [h['accuracy'] for h in self.model_performance_history[-5:]]
        
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
        
        if trend > 0.01:
            return "improving"
        elif trend < -0.01:
            return "declining"
        else:
            return "stable"
    
    def save_model(self):
        """Save the current ensemble model."""
        try:
            ensemble_path = os.path.join(self.model_dir, "ensemble_model.joblib")
            joblib.dump(self.ensemble_model, ensemble_path)
            
            # Save performance history
            history_path = os.path.join(self.model_dir, "performance_history.joblib")
            joblib.dump(self.model_performance_history, history_path)
            
            self.logger.info("Model saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")