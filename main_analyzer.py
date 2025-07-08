import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import json
import os

from config import config
from data_collector import DataCollector
from enhanced_finbert import EnhancedFinBERT
from technical_analyzer import TechnicalAnalyzer
from fundamental_analyzer import FundamentalAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainAnalyzer:
    """Main analyzer that combines all analysis types for comprehensive trading recommendations."""
    
    def __init__(self):
        self.data_collector = DataCollector()
        self.finbert_model = EnhancedFinBERT()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        
        # Load training history if available
        self.finbert_model.load_training_history()
        
        # Analysis results cache
        self.last_analysis = None
        self.analysis_history = []
        
    def run_comprehensive_analysis(self, symbol: str = None) -> Dict:
        """Run comprehensive analysis including technical, fundamental, and sentiment analysis."""
        symbol = symbol or config.STOCK_SYMBOL
        
        try:
            logger.info(f"Starting comprehensive analysis for {symbol}")
            
            # Collect data
            stock_data = self.data_collector.get_stock_data(symbol)
            fundamental_data = self.data_collector.get_fundamental_data(symbol)
            latest_price_data = self.data_collector.get_latest_price(symbol)
            
            # Technical Analysis
            technical_data = self.technical_analyzer.calculate_all_indicators(stock_data)
            technical_signals = self.technical_analyzer.generate_trading_signals(technical_data)
            technical_summary = self.technical_analyzer.get_summary_report(technical_data)
            
            # Fundamental Analysis
            fundamental_analysis = self.fundamental_analyzer.analyze_fundamentals(fundamental_data)
            fundamental_report = self.fundamental_analyzer.generate_fundamental_report(fundamental_analysis)
            
            # Sentiment Analysis (using sample news data for now)
            sentiment_analysis = self._analyze_sentiment(symbol)
            
            # Combine all analyses
            comprehensive_analysis = self._combine_analyses(
                technical_signals=technical_signals,
                fundamental_analysis=fundamental_analysis,
                sentiment_analysis=sentiment_analysis,
                latest_price=latest_price_data,
                technical_summary=technical_summary
            )
            
            # Store analysis results
            self.last_analysis = comprehensive_analysis
            self.analysis_history.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'analysis': comprehensive_analysis
            })
            
            # Save analysis to file
            self._save_analysis_results(comprehensive_analysis, symbol)
            
            logger.info(f"Comprehensive analysis completed for {symbol}")
            return comprehensive_analysis
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {str(e)}")
            return {
                'error': str(e),
                'recommendation': 'Neutral',
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_sentiment(self, symbol: str) -> Dict:
        """Analyze sentiment using FinBERT model."""
        try:
            # For now, we'll use sample news data
            # In a real implementation, you would fetch news from APIs
            sample_news = [
                {
                    'title': f'{symbol} reports strong quarterly earnings',
                    'description': 'The company exceeded analyst expectations with robust revenue growth.'
                },
                {
                    'title': f'{symbol} announces new product launch',
                    'description': 'Innovation continues to drive market leadership.'
                }
            ]
            
            sentiment_result = self.finbert_model.analyze_financial_news(sample_news)
            
            return {
                'overall_sentiment': sentiment_result['overall_sentiment'],
                'confidence': sentiment_result['confidence'],
                'news_count': sentiment_result['news_count'],
                'sentiment_distribution': sentiment_result['sentiment_distribution']
            }
            
        except Exception as e:
            logger.warning(f"Error in sentiment analysis: {str(e)}")
            return {
                'overall_sentiment': 'Neutral',
                'confidence': 0.0,
                'news_count': 0,
                'sentiment_distribution': {}
            }
    
    def _combine_analyses(self, technical_signals: Dict, fundamental_analysis: Dict, 
                         sentiment_analysis: Dict, latest_price: Dict, 
                         technical_summary: Dict) -> Dict:
        """Combine all analysis types into a comprehensive recommendation."""
        
        # Weighted scoring system
        weights = {
            'technical': 0.35,
            'fundamental': 0.40,
            'sentiment': 0.25
        }
        
        # Convert signals to numerical scores
        technical_score = self._convert_signal_to_score(technical_signals['overall_signal'])
        fundamental_score = fundamental_analysis.get('overall_score', 50) / 100  # Normalize to 0-1
        sentiment_score = self._convert_sentiment_to_score(sentiment_analysis['overall_sentiment'])
        
        # Calculate weighted average
        weighted_score = (
            technical_score * weights['technical'] +
            fundamental_score * weights['fundamental'] +
            sentiment_score * weights['sentiment']
        )
        
        # Determine final recommendation
        final_recommendation = self._get_final_recommendation(weighted_score)
        
        # Calculate confidence based on individual confidences
        technical_confidence = technical_signals.get('confidence', 0.5)
        fundamental_confidence = 0.8  # Assuming fundamental analysis is generally reliable
        sentiment_confidence = sentiment_analysis.get('confidence', 0.5)
        
        overall_confidence = (
            technical_confidence * weights['technical'] +
            fundamental_confidence * weights['fundamental'] +
            sentiment_confidence * weights['sentiment']
        )
        
        # Generate detailed analysis
        comprehensive_analysis = {
            'symbol': latest_price.get('symbol', ''),
            'current_price': latest_price.get('current_price', 0),
            'timestamp': datetime.now().isoformat(),
            
            'final_recommendation': final_recommendation,
            'confidence': overall_confidence,
            'weighted_score': weighted_score,
            
            'technical_analysis': {
                'signal': technical_signals['overall_signal'],
                'confidence': technical_confidence,
                'score': technical_score,
                'details': technical_signals.get('signals', {}),
                'summary': technical_summary
            },
            
            'fundamental_analysis': {
                'recommendation': fundamental_analysis.get('recommendation', 'Neutral'),
                'score': fundamental_analysis.get('overall_score', 50),
                'confidence': fundamental_confidence,
                'details': fundamental_analysis
            },
            
            'sentiment_analysis': {
                'sentiment': sentiment_analysis['overall_sentiment'],
                'confidence': sentiment_confidence,
                'score': sentiment_score,
                'details': sentiment_analysis
            },
            
            'weights_used': weights,
            'analysis_metadata': {
                'data_points_analyzed': len(technical_summary.get('technical_indicators', {})),
                'analysis_duration': 'real-time',
                'model_version': '1.0'
            }
        }
        
        return comprehensive_analysis
    
    def _convert_signal_to_score(self, signal: str) -> float:
        """Convert trading signal to numerical score."""
        signal_mapping = {
            'Strong BUY': 1.0,
            'BUY': 0.7,
            'Neutral': 0.5,
            'SELL': 0.3,
            'Strong SELL': 0.0
        }
        return signal_mapping.get(signal, 0.5)
    
    def _convert_sentiment_to_score(self, sentiment: str) -> float:
        """Convert sentiment to numerical score."""
        sentiment_mapping = {
            'Strong BUY': 1.0,
            'BUY': 0.7,
            'Neutral': 0.5,
            'SELL': 0.3,
            'Strong SELL': 0.0
        }
        return sentiment_mapping.get(sentiment, 0.5)
    
    def _get_final_recommendation(self, weighted_score: float) -> str:
        """Get final recommendation based on weighted score."""
        if weighted_score >= 0.8:
            return "Strong BUY"
        elif weighted_score >= 0.6:
            return "BUY"
        elif weighted_score >= 0.4:
            return "Neutral"
        elif weighted_score >= 0.2:
            return "SELL"
        else:
            return "Strong SELL"
    
    def _save_analysis_results(self, analysis: Dict, symbol: str):
        """Save analysis results to file."""
        try:
            filename = f"{symbol}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(config.DATA_DIR, filename)
            
            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            logger.info(f"Analysis results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving analysis results: {str(e)}")
    
    def get_analysis_summary(self, symbol: str = None) -> Dict:
        """Get a summary of the latest analysis."""
        symbol = symbol or config.STOCK_SYMBOL
        
        if self.last_analysis and self.last_analysis.get('symbol') == symbol:
            return {
                'symbol': symbol,
                'recommendation': self.last_analysis['final_recommendation'],
                'confidence': self.last_analysis['confidence'],
                'current_price': self.last_analysis['current_price'],
                'timestamp': self.last_analysis['timestamp'],
                'technical_signal': self.last_analysis['technical_analysis']['signal'],
                'fundamental_recommendation': self.last_analysis['fundamental_analysis']['recommendation'],
                'sentiment': self.last_analysis['sentiment_analysis']['sentiment']
            }
        else:
            return {
                'symbol': symbol,
                'message': 'No recent analysis available. Run comprehensive analysis first.',
                'timestamp': datetime.now().isoformat()
            }
    
    def get_analysis_history(self, symbol: str = None, limit: int = 10) -> List[Dict]:
        """Get analysis history for a symbol."""
        symbol = symbol or config.STOCK_SYMBOL
        
        filtered_history = [
            entry for entry in self.analysis_history 
            if entry['symbol'] == symbol
        ]
        
        return filtered_history[-limit:] if limit else filtered_history
    
    def retrain_model_if_needed(self, test_data: List[Tuple[str, int]] = None) -> Dict:
        """Retrain the FinBERT model if accuracy is below threshold."""
        try:
            if test_data is None:
                # Generate sample test data for demonstration
                test_data = [
                    ("Apple reports strong earnings growth", 1),
                    ("Apple stock drops on weak guidance", 2),
                    ("Apple announces new product line", 1),
                    ("Apple faces regulatory challenges", 2),
                    ("Apple beats market expectations", 1)
                ]
            
            # Evaluate current model performance
            performance = self.finbert_model.evaluate_model_performance(test_data)
            current_accuracy = performance['accuracy']
            
            logger.info(f"Current model accuracy: {current_accuracy:.4f}")
            
            # Check if retraining is needed
            if self.finbert_model.should_retrain(current_accuracy):
                logger.info("Model accuracy below threshold. Starting retraining...")
                
                # Retrain the model
                retrain_result = self.finbert_model.retrain_model(test_data)
                
                if retrain_result['success']:
                    logger.info(f"Model retraining completed. New accuracy: {retrain_result['final_accuracy']:.4f}")
                    return {
                        'retraining_performed': True,
                        'old_accuracy': current_accuracy,
                        'new_accuracy': retrain_result['final_accuracy'],
                        'improvement': retrain_result['final_accuracy'] - current_accuracy
                    }
                else:
                    logger.error(f"Model retraining failed: {retrain_result.get('error', 'Unknown error')}")
                    return {
                        'retraining_performed': False,
                        'error': retrain_result.get('error', 'Unknown error')
                    }
            else:
                logger.info("Model accuracy is acceptable. No retraining needed.")
                return {
                    'retraining_performed': False,
                    'current_accuracy': current_accuracy,
                    'reason': 'Accuracy above threshold'
                }
                
        except Exception as e:
            logger.error(f"Error in model retraining check: {str(e)}")
            return {
                'retraining_performed': False,
                'error': str(e)
            }
    
    def generate_trading_report(self, symbol: str = None) -> Dict:
        """Generate a comprehensive trading report."""
        symbol = symbol or config.STOCK_SYMBOL
        
        # Run analysis if not already done
        if not self.last_analysis or self.last_analysis.get('symbol') != symbol:
            self.run_comprehensive_analysis(symbol)
        
        if not self.last_analysis:
            return {'error': 'Unable to generate analysis'}
        
        analysis = self.last_analysis
        
        # Create trading report
        report = {
            'executive_summary': {
                'symbol': symbol,
                'current_price': analysis['current_price'],
                'recommendation': analysis['final_recommendation'],
                'confidence': analysis['confidence'],
                'timestamp': analysis['timestamp']
            },
            
            'detailed_analysis': {
                'technical': {
                    'signal': analysis['technical_analysis']['signal'],
                    'key_indicators': analysis['technical_analysis']['summary'].get('technical_indicators', {}),
                    'support_resistance': {
                        'support': analysis['technical_analysis']['summary'].get('support_levels', {}),
                        'resistance': analysis['technical_analysis']['summary'].get('resistance_levels', {})
                    }
                },
                
                'fundamental': {
                    'recommendation': analysis['fundamental_analysis']['recommendation'],
                    'score': analysis['fundamental_analysis']['score'],
                    'key_metrics': analysis['fundamental_analysis']['details'].get('valuation_metrics', {})
                },
                
                'sentiment': {
                    'overall_sentiment': analysis['sentiment_analysis']['sentiment'],
                    'confidence': analysis['sentiment_analysis']['confidence']
                }
            },
            
            'trading_advice': self._generate_trading_advice(analysis),
            
            'risk_assessment': {
                'risk_level': self._assess_risk_level(analysis),
                'key_risks': self._identify_key_risks(analysis),
                'risk_mitigation': self._suggest_risk_mitigation(analysis)
            },
            
            'next_steps': self._suggest_next_steps(analysis)
        }
        
        return report
    
    def _generate_trading_advice(self, analysis: Dict) -> Dict:
        """Generate specific trading advice based on analysis."""
        recommendation = analysis['final_recommendation']
        confidence = analysis['confidence']
        
        advice = {
            'action': recommendation,
            'confidence_level': 'High' if confidence > 0.7 else 'Medium' if confidence > 0.5 else 'Low',
            'timing': 'Immediate' if confidence > 0.8 else 'Within 1-2 days' if confidence > 0.6 else 'Monitor closely',
            'position_size': 'Full position' if confidence > 0.8 else 'Partial position' if confidence > 0.6 else 'Small position',
            'stop_loss': self._calculate_stop_loss(analysis),
            'target_price': self._calculate_target_price(analysis)
        }
        
        return advice
    
    def _assess_risk_level(self, analysis: Dict) -> str:
        """Assess overall risk level."""
        technical_confidence = analysis['technical_analysis']['confidence']
        fundamental_confidence = analysis['fundamental_analysis']['confidence']
        sentiment_confidence = analysis['sentiment_analysis']['confidence']
        
        avg_confidence = (technical_confidence + fundamental_confidence + sentiment_confidence) / 3
        
        if avg_confidence > 0.8:
            return "Low"
        elif avg_confidence > 0.6:
            return "Medium"
        else:
            return "High"
    
    def _identify_key_risks(self, analysis: Dict) -> List[str]:
        """Identify key risks based on analysis."""
        risks = []
        
        # Technical risks
        if analysis['technical_analysis']['confidence'] < 0.5:
            risks.append("Low technical analysis confidence")
        
        # Fundamental risks
        if analysis['fundamental_analysis']['score'] < 40:
            risks.append("Weak fundamental metrics")
        
        # Sentiment risks
        if analysis['sentiment_analysis']['confidence'] < 0.5:
            risks.append("Unclear market sentiment")
        
        # Market risks
        if analysis['confidence'] < 0.6:
            risks.append("Overall low confidence in recommendation")
        
        return risks
    
    def _suggest_risk_mitigation(self, analysis: Dict) -> List[str]:
        """Suggest risk mitigation strategies."""
        mitigations = []
        
        if analysis['confidence'] < 0.7:
            mitigations.append("Use smaller position sizes")
            mitigations.append("Set tighter stop losses")
        
        if analysis['technical_analysis']['confidence'] < 0.6:
            mitigations.append("Wait for stronger technical confirmation")
        
        if analysis['fundamental_analysis']['score'] < 50:
            mitigations.append("Focus on short-term trades")
        
        return mitigations
    
    def _suggest_next_steps(self, analysis: Dict) -> List[str]:
        """Suggest next steps for the investor."""
        steps = []
        
        recommendation = analysis['final_recommendation']
        
        if recommendation in ['Strong BUY', 'BUY']:
            steps.append("Consider entering a long position")
            steps.append("Set stop loss at recommended level")
            steps.append("Monitor for any negative news or technical breakdowns")
        elif recommendation in ['Strong SELL', 'SELL']:
            steps.append("Consider exiting long positions or shorting")
            steps.append("Set profit targets if shorting")
            steps.append("Monitor for positive catalysts")
        else:
            steps.append("Hold current positions")
            steps.append("Monitor for clearer signals")
            steps.append("Wait for better entry/exit opportunities")
        
        steps.append("Re-run analysis in 24 hours for updated recommendations")
        
        return steps
    
    def _calculate_stop_loss(self, analysis: Dict) -> float:
        """Calculate recommended stop loss level."""
        current_price = analysis['current_price']
        support_levels = analysis['technical_analysis']['summary'].get('support_levels', {})
        
        # Use nearest support level or 5% below current price
        s1 = support_levels.get('s1', current_price * 0.95)
        s2 = support_levels.get('s2', current_price * 0.90)
        
        # Choose the closer support level
        if abs(current_price - s1) < abs(current_price - s2):
            return s1
        else:
            return s2
    
    def _calculate_target_price(self, analysis: Dict) -> float:
        """Calculate target price based on analysis."""
        current_price = analysis['current_price']
        recommendation = analysis['final_recommendation']
        
        if recommendation in ['Strong BUY', 'BUY']:
            resistance_levels = analysis['technical_analysis']['summary'].get('resistance_levels', {})
            r1 = resistance_levels.get('r1', current_price * 1.05)
            r2 = resistance_levels.get('r2', current_price * 1.10)
            
            # Use R1 for BUY, R2 for Strong BUY
            if recommendation == 'Strong BUY':
                return r2
            else:
                return r1
        elif recommendation in ['Strong SELL', 'SELL']:
            support_levels = analysis['technical_analysis']['summary'].get('support_levels', {})
            s1 = support_levels.get('s1', current_price * 0.95)
            s2 = support_levels.get('s2', current_price * 0.90)
            
            # Use S1 for SELL, S2 for Strong SELL
            if recommendation == 'Strong SELL':
                return s2
            else:
                return s1
        else:
            return current_price  # No target for neutral