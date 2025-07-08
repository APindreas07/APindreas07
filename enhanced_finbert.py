import torch
import torch.nn as nn
import torch.optim as optim
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from config import config

logger = logging.getLogger(__name__)

class EnhancedFinBERT:
    """Enhanced FinBERT model with improved accuracy and retraining capabilities."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.FINBERT_MODEL_NAME
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        
        # Training history
        self.training_history = []
        self.accuracy_history = []
        
        # Sentiment mapping
        self.sentiment_mapping = {
            0: "Neutral",
            1: "BUY", 
            2: "SELL"
        }
        
        # Confidence thresholds for strong signals
        self.strong_buy_threshold = 0.80
        self.strong_sell_threshold = 0.80
        
    def classify_sentiment(self, text: str) -> Dict[str, any]:
        """Classify sentiment with confidence scores and detailed analysis."""
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text, 
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
                probabilities = torch.softmax(logits, dim=1)[0]
                
            # Get predicted class and confidence
            predicted_class = torch.argmax(probabilities).item()
            confidence = probabilities[predicted_class].item()
            
            # Map to sentiment labels
            base_sentiment = self.sentiment_mapping.get(predicted_class, "Neutral")
            
            # Determine if it's a strong signal
            if base_sentiment == "BUY" and confidence > self.strong_buy_threshold:
                final_sentiment = "Strong BUY"
            elif base_sentiment == "SELL" and confidence > self.strong_sell_threshold:
                final_sentiment = "Strong SELL"
            else:
                final_sentiment = base_sentiment
            
            # Get all class probabilities
            class_probabilities = {
                "Neutral": probabilities[0].item(),
                "BUY": probabilities[1].item(),
                "SELL": probabilities[2].item()
            }
            
            result = {
                "sentiment": final_sentiment,
                "confidence": confidence,
                "base_sentiment": base_sentiment,
                "class_probabilities": class_probabilities,
                "text_length": len(text),
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sentiment classification: {str(e)}")
            return {
                "sentiment": "Neutral",
                "confidence": 0.0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def batch_classify(self, texts: List[str]) -> List[Dict]:
        """Classify multiple texts efficiently."""
        results = []
        for text in texts:
            result = self.classify_sentiment(text)
            results.append(result)
        return results
    
    def analyze_financial_news(self, news_data: List[Dict]) -> Dict:
        """Analyze financial news and provide aggregated sentiment."""
        if not news_data:
            return {"overall_sentiment": "Neutral", "confidence": 0.0, "news_count": 0}
        
        sentiments = []
        confidences = []
        
        for news_item in news_data:
            title = news_item.get('title', '')
            description = news_item.get('description', '')
            content = f"{title}. {description}"
            
            result = self.classify_sentiment(content)
            sentiments.append(result['sentiment'])
            confidences.append(result['confidence'])
        
        # Aggregate results
        sentiment_counts = {}
        for sentiment in sentiments:
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Determine overall sentiment
        if sentiment_counts:
            overall_sentiment = max(sentiment_counts, key=sentiment_counts.get)
            avg_confidence = np.mean(confidences)
        else:
            overall_sentiment = "Neutral"
            avg_confidence = 0.0
        
        return {
            "overall_sentiment": overall_sentiment,
            "confidence": avg_confidence,
            "news_count": len(news_data),
            "sentiment_distribution": sentiment_counts,
            "individual_results": list(zip(sentiments, confidences))
        }
    
    def retrain_model(self, training_data: List[Tuple[str, int]], 
                     validation_data: List[Tuple[str, int]] = None) -> Dict:
        """Retrain the model with new data."""
        try:
            logger.info("Starting model retraining...")
            
            # Prepare training data
            texts, labels = zip(*training_data)
            
            # Split data if validation data not provided
            if validation_data is None:
                train_texts, val_texts, train_labels, val_labels = train_test_split(
                    texts, labels, test_size=0.2, random_state=42
                )
            else:
                val_texts, val_labels = zip(*validation_data)
                train_texts, train_labels = texts, labels
            
            # Tokenize training data
            train_encodings = self.tokenizer(
                train_texts, 
                truncation=True, 
                padding=True, 
                max_length=512,
                return_tensors="pt"
            )
            val_encodings = self.tokenizer(
                val_texts, 
                truncation=True, 
                padding=True, 
                max_length=512,
                return_tensors="pt"
            )
            
            # Convert to tensors
            train_labels = torch.tensor(train_labels)
            val_labels = torch.tensor(val_labels)
            
            # Move to device
            train_encodings = {k: v.to(self.device) for k, v in train_encodings.items()}
            val_encodings = {k: v.to(self.device) for k, v in val_encodings.items()}
            train_labels = train_labels.to(self.device)
            val_labels = val_labels.to(self.device)
            
            # Training setup
            optimizer = optim.AdamW(self.model.parameters(), lr=2e-5)
            criterion = nn.CrossEntropyLoss()
            
            # Training loop
            epochs = 3
            best_accuracy = 0.0
            
            for epoch in range(epochs):
                # Training
                self.model.train()
                optimizer.zero_grad()
                
                outputs = self.model(**train_encodings)
                loss = criterion(outputs.logits, train_labels)
                loss.backward()
                optimizer.step()
                
                # Validation
                self.model.eval()
                with torch.no_grad():
                    val_outputs = self.model(**val_encodings)
                    val_predictions = torch.argmax(val_outputs.logits, dim=1)
                    val_accuracy = accuracy_score(val_labels.cpu(), val_predictions.cpu())
                
                logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {loss.item():.4f}, Val Accuracy: {val_accuracy:.4f}")
                
                if val_accuracy > best_accuracy:
                    best_accuracy = val_accuracy
                    # Save best model
                    self.save_model("best_model")
            
            # Record training history
            training_record = {
                "timestamp": datetime.now().isoformat(),
                "epochs": epochs,
                "final_accuracy": best_accuracy,
                "training_samples": len(train_texts),
                "validation_samples": len(val_texts)
            }
            self.training_history.append(training_record)
            self.accuracy_history.append(best_accuracy)
            
            # Save training history
            self.save_training_history()
            
            logger.info(f"Model retraining completed. Best accuracy: {best_accuracy:.4f}")
            
            return {
                "success": True,
                "final_accuracy": best_accuracy,
                "training_samples": len(train_texts),
                "validation_samples": len(val_texts)
            }
            
        except Exception as e:
            logger.error(f"Error during model retraining: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def evaluate_model_performance(self, test_data: List[Tuple[str, int]]) -> Dict:
        """Evaluate model performance on test data."""
        texts, true_labels = zip(*test_data)
        
        predictions = []
        confidences = []
        
        for text in texts:
            result = self.classify_sentiment(text)
            # Map sentiment back to numeric label
            sentiment_to_label = {"Neutral": 0, "BUY": 1, "SELL": 2}
            pred_label = sentiment_to_label.get(result['base_sentiment'], 0)
            predictions.append(pred_label)
            confidences.append(result['confidence'])
        
        # Calculate metrics
        accuracy = accuracy_score(true_labels, predictions)
        
        # Classification report
        report = classification_report(
            true_labels, 
            predictions, 
            target_names=['Neutral', 'BUY', 'SELL'],
            output_dict=True
        )
        
        return {
            "accuracy": accuracy,
            "average_confidence": np.mean(confidences),
            "classification_report": report,
            "predictions": predictions,
            "true_labels": true_labels,
            "confidences": confidences
        }
    
    def should_retrain(self, current_accuracy: float) -> bool:
        """Determine if model should be retrained based on accuracy."""
        if len(self.accuracy_history) == 0:
            return False
        
        # Check if accuracy has dropped significantly
        recent_accuracy = np.mean(self.accuracy_history[-5:]) if len(self.accuracy_history) >= 5 else self.accuracy_history[-1]
        
        if current_accuracy < config.RETRAIN_THRESHOLD_ACCURACY:
            return True
        
        if current_accuracy < recent_accuracy - 0.1:  # 10% drop
            return True
        
        return False
    
    def save_model(self, filename: str):
        """Save the model to disk."""
        model_path = os.path.join(config.MODELS_DIR, filename)
        self.model.save_pretrained(model_path)
        self.tokenizer.save_pretrained(model_path)
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, filename: str):
        """Load model from disk."""
        model_path = os.path.join(config.MODELS_DIR, filename)
        if os.path.exists(model_path):
            self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Model loaded from {model_path}")
        else:
            logger.warning(f"Model path {model_path} not found")
    
    def save_training_history(self):
        """Save training history to file."""
        history_path = os.path.join(config.MODELS_DIR, "training_history.json")
        with open(history_path, 'w') as f:
            json.dump(self.training_history, f, indent=2)
    
    def load_training_history(self):
        """Load training history from file."""
        history_path = os.path.join(config.MODELS_DIR, "training_history.json")
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                self.training_history = json.load(f)
                self.accuracy_history = [record['final_accuracy'] for record in self.training_history]
    
    def get_model_info(self) -> Dict:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "device": str(self.device),
            "training_history_length": len(self.training_history),
            "average_accuracy": np.mean(self.accuracy_history) if self.accuracy_history else 0.0,
            "last_training": self.training_history[-1] if self.training_history else None
        }