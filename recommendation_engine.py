import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from data_collector import DataCollector
from enhanced_sentiment_analyzer import EnhancedSentimentAnalyzer
from technical_analyzer import TechnicalAnalyzer
import warnings
warnings.filterwarnings('ignore')

class RecommendationEngine:
    """Main recommendation engine that combines sentiment and technical analysis."""
    
    def __init__(self, symbol: str = "AAPL"):
        self.symbol = symbol
        
        # Initialize components
        self.data_collector = DataCollector(symbol)
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Weights for different analysis components
        self.weights = {
            'technical': 0.6,      # Technical analysis gets higher weight
            'sentiment': 0.3,      # Sentiment analysis
            'fundamental': 0.1     # Basic fundamental analysis
        }
        
        # Risk management parameters
        self.max_position_size = 0.1  # 10% max position
        self.risk_tolerance = 0.02    # 2% risk per trade
        
    def generate_comprehensive_analysis(self) -> Dict:
        """Generate comprehensive analysis combining all components."""
        self.logger.info(f"Starting comprehensive analysis for {self.symbol}")
        
        try:
            # Collect data
            price_data = self.data_collector.get_stock_data()
            news_data = self.data_collector.get_news_sentiment_data()
            company_info = self.data_collector.get_company_info()
            
            if price_data.empty:
                self.logger.error("No price data available")
                return self._generate_error_response("No price data available")
            
            # Perform analyses
            technical_analysis = self.technical_analyzer.analyze_price_action(price_data)
            sentiment_analysis = self.sentiment_analyzer.analyze_news_batch(news_data)
            fundamental_analysis = self._analyze_fundamentals(company_info)
            
            # Generate combined recommendation
            final_recommendation = self._combine_analyses(
                technical_analysis, sentiment_analysis, fundamental_analysis
            )
            
            # Generate timing recommendations
            timing_analysis = self._analyze_timing(price_data, technical_analysis)
            
            # Risk assessment
            risk_assessment = self._assess_risk(price_data, technical_analysis, sentiment_analysis)
            
            # Position sizing
            position_size = self._calculate_position_size(risk_assessment)
            
            return {
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat(),
                'current_price': technical_analysis['current_price'],
                'recommendation': final_recommendation,
                'technical_analysis': technical_analysis,
                'sentiment_analysis': sentiment_analysis,
                'fundamental_analysis': fundamental_analysis,
                'timing_analysis': timing_analysis,
                'risk_assessment': risk_assessment,
                'position_sizing': position_size,
                'api_usage': self.data_collector.get_api_usage_stats(),
                'model_performance': self.sentiment_analyzer.get_model_stats()
            }
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {e}")
            return self._generate_error_response(str(e))
    
    def _analyze_fundamentals(self, company_info: Dict) -> Dict:
        """Analyze fundamental metrics for the company."""
        if not company_info:
            return {
                'score': 0.5,
                'recommendation': 'Neutral',
                'metrics': {},
                'signals': []
            }
        
        signals = []
        fundamental_score = 0.5
        
        # P/E Ratio analysis
        pe_ratio = company_info.get('peRatio')
        if pe_ratio:
            if pe_ratio < 15:
                signals.append('Low P/E ratio - potentially undervalued')
                fundamental_score += 0.1
            elif pe_ratio > 30:
                signals.append('High P/E ratio - potentially overvalued')
                fundamental_score -= 0.1
        
        # Growth metrics
        revenue_growth = company_info.get('revenueGrowth')
        earnings_growth = company_info.get('earningsGrowth')
        
        if revenue_growth and revenue_growth > 0.1:
            signals.append('Strong revenue growth')
            fundamental_score += 0.1
        
        if earnings_growth and earnings_growth > 0.1:
            signals.append('Strong earnings growth')
            fundamental_score += 0.1
        
        # Debt analysis
        debt_to_equity = company_info.get('debtToEquity')
        if debt_to_equity and debt_to_equity < 0.3:
            signals.append('Low debt levels')
            fundamental_score += 0.05
        elif debt_to_equity and debt_to_equity > 1.0:
            signals.append('High debt levels')
            fundamental_score -= 0.1
        
        # ROE analysis
        roe = company_info.get('returnOnEquity')
        if roe and roe > 0.15:
            signals.append('Strong return on equity')
            fundamental_score += 0.1
        
        # Analyst recommendations
        recommendation_mean = company_info.get('recommendationMean')
        if recommendation_mean:
            if recommendation_mean <= 2.0:
                signals.append('Strong analyst buy ratings')
                fundamental_score += 0.1
            elif recommendation_mean >= 4.0:
                signals.append('Weak analyst ratings')
                fundamental_score -= 0.1
        
        # Generate recommendation
        if fundamental_score > 0.7:
            recommendation = 'Strong Buy'
        elif fundamental_score > 0.6:
            recommendation = 'Buy'
        elif fundamental_score < 0.3:
            recommendation = 'Strong Sell'
        elif fundamental_score < 0.4:
            recommendation = 'Sell'
        else:
            recommendation = 'Neutral'
        
        return {
            'score': fundamental_score,
            'recommendation': recommendation,
            'metrics': {
                'pe_ratio': pe_ratio,
                'revenue_growth': revenue_growth,
                'earnings_growth': earnings_growth,
                'debt_to_equity': debt_to_equity,
                'return_on_equity': roe,
                'analyst_rating': recommendation_mean
            },
            'signals': signals
        }
    
    def _combine_analyses(self, technical: Dict, sentiment: Dict, fundamental: Dict) -> Dict:
        """Combine different analyses using weighted scoring."""
        
        # Convert recommendations to numerical scores
        def recommendation_to_score(rec: str) -> float:
            mapping = {
                'Strong Sell': 0.0,
                'Sell': 0.2,
                'Neutral': 0.5,
                'Buy': 0.8,
                'Strong Buy': 1.0
            }
            return mapping.get(rec, 0.5)
        
        # Get scores from each analysis
        technical_score = technical['technical_score']['score']
        sentiment_score = sentiment.get('confidence', 0.5)
        if sentiment.get('overall_sentiment') in ['Strong Sell', 'Sell']:
            sentiment_score = 1 - sentiment_score
        elif sentiment.get('overall_sentiment') in ['Strong Buy', 'Buy']:
            pass  # Keep as is
        else:
            sentiment_score = 0.5
            
        fundamental_score = fundamental['score']
        
        # Calculate weighted final score
        final_score = (
            technical_score * self.weights['technical'] +
            sentiment_score * self.weights['sentiment'] +
            fundamental_score * self.weights['fundamental']
        )
        
        # Determine confidence based on agreement between analyses
        agreement_score = self._calculate_agreement(technical_score, sentiment_score, fundamental_score)
        
        # Generate final recommendation
        if final_score > 0.75 and agreement_score > 0.7:
            final_recommendation = 'Strong Buy'
            confidence = 'HIGH'
        elif final_score > 0.65:
            final_recommendation = 'Buy'
            confidence = 'MEDIUM' if agreement_score > 0.6 else 'LOW'
        elif final_score < 0.25 and agreement_score > 0.7:
            final_recommendation = 'Strong Sell'
            confidence = 'HIGH'
        elif final_score < 0.35:
            final_recommendation = 'Sell'
            confidence = 'MEDIUM' if agreement_score > 0.6 else 'LOW'
        else:
            final_recommendation = 'Neutral'
            confidence = 'MEDIUM'
        
        return {
            'recommendation': final_recommendation,
            'confidence': confidence,
            'final_score': final_score,
            'agreement_score': agreement_score,
            'component_scores': {
                'technical': technical_score,
                'sentiment': sentiment_score,
                'fundamental': fundamental_score
            },
            'reasoning': self._generate_reasoning(technical, sentiment, fundamental, final_recommendation)
        }
    
    def _calculate_agreement(self, tech_score: float, sent_score: float, fund_score: float) -> float:
        """Calculate how much the different analyses agree with each other."""
        scores = [tech_score, sent_score, fund_score]
        mean_score = np.mean(scores)
        variance = np.var(scores)
        
        # Lower variance = higher agreement
        agreement = 1 - min(variance * 4, 1.0)  # Normalize to 0-1 scale
        return agreement
    
    def _generate_reasoning(self, technical: Dict, sentiment: Dict, fundamental: Dict, recommendation: str) -> List[str]:
        """Generate human-readable reasoning for the recommendation."""
        reasoning = []
        
        # Technical reasoning
        tech_rec = technical['technical_score']['recommendation']
        if tech_rec in ['Strong Buy', 'Buy']:
            reasoning.append(f"Technical analysis shows {tech_rec.lower()} signals with {technical['technical_score']['bullish_signals']} bullish indicators")
        elif tech_rec in ['Strong Sell', 'Sell']:
            reasoning.append(f"Technical analysis shows {tech_rec.lower()} signals with {technical['technical_score']['bearish_signals']} bearish indicators")
        
        # Sentiment reasoning
        sent_rec = sentiment.get('overall_sentiment', 'Neutral')
        article_count = sentiment.get('article_count', 0)
        if article_count > 0:
            reasoning.append(f"News sentiment analysis from {article_count} articles indicates {sent_rec.lower()}")
        
        # Fundamental reasoning
        fund_rec = fundamental['recommendation']
        if fund_rec != 'Neutral':
            reasoning.append(f"Fundamental analysis suggests {fund_rec.lower()} based on company metrics")
        
        # Price movement context
        price_change_1d = technical.get('price_change_1d', 0) * 100
        if abs(price_change_1d) > 2:
            direction = "up" if price_change_1d > 0 else "down"
            reasoning.append(f"Stock is {direction} {abs(price_change_1d):.1f}% today")
        
        return reasoning
    
    def _analyze_timing(self, price_data: pd.DataFrame, technical_analysis: Dict) -> Dict:
        """Analyze optimal timing for trades."""
        entry_exit_signals = self.technical_analyzer.generate_entry_exit_signals(price_data)
        
        # Market hours analysis (simplified)
        current_time = datetime.now()
        market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        is_market_hours = market_open <= current_time <= market_close
        
        # Volume profile analysis
        if len(price_data) >= 20:
            recent_volume = price_data.tail(20)['Volume'].mean()
            current_volume = price_data.iloc[-1]['Volume']
            volume_factor = current_volume / recent_volume
        else:
            volume_factor = 1.0
        
        # Timing recommendation
        timing_score = 0.5
        timing_factors = []
        
        if is_market_hours:
            timing_score += 0.2
            timing_factors.append("Market is open")
        else:
            timing_factors.append("Market is closed - consider pre/after-market risks")
        
        if volume_factor > 1.5:
            timing_score += 0.2
            timing_factors.append("Higher than average volume")
        elif volume_factor < 0.5:
            timing_score -= 0.1
            timing_factors.append("Lower than average volume")
        
        # RSI timing
        rsi = technical_analysis['momentum']['rsi']
        if 40 <= rsi <= 60:
            timing_score += 0.1
            timing_factors.append("RSI in neutral zone - good for entries")
        
        return {
            'timing_score': timing_score,
            'is_market_hours': is_market_hours,
            'volume_factor': volume_factor,
            'entry_signals': entry_exit_signals['entry_signals'],
            'exit_signals': entry_exit_signals['exit_signals'],
            'timing_factors': timing_factors,
            'recommended_action_time': self._get_recommended_action_time()
        }
    
    def _get_recommended_action_time(self) -> str:
        """Get recommended time to take action."""
        current_time = datetime.now()
        
        # If market is open
        if 9 <= current_time.hour < 16:
            if current_time.hour < 10:
                return "Consider waiting for market stabilization (after 10 AM)"
            elif current_time.hour >= 15:
                return "Consider action early next session (avoid last hour volatility)"
            else:
                return "Good time for action during stable market hours"
        else:
            next_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            if current_time.hour >= 16:
                next_open += timedelta(days=1)
            return f"Wait for market open at {next_open.strftime('%Y-%m-%d %H:%M')}"
    
    def _assess_risk(self, price_data: pd.DataFrame, technical: Dict, sentiment: Dict) -> Dict:
        """Assess overall risk for the trade."""
        risk_factors = []
        risk_score = 0.5  # Start with medium risk
        
        # Volatility assessment
        if len(price_data) >= 20:
            returns = price_data['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            
            if volatility > 0.4:  # High volatility
                risk_score += 0.2
                risk_factors.append(f"High volatility ({volatility:.1%})")
            elif volatility < 0.15:  # Low volatility
                risk_score -= 0.1
                risk_factors.append(f"Low volatility ({volatility:.1%})")
        
        # Technical risk factors
        rsi = technical['momentum']['rsi']
        if rsi > 80 or rsi < 20:
            risk_score += 0.1
            risk_factors.append("Extreme RSI levels indicate high reversal risk")
        
        # Sentiment disagreement
        agreement = self._calculate_agreement(
            technical['technical_score']['score'],
            sentiment.get('confidence', 0.5),
            0.5  # Default fundamental score
        )
        
        if agreement < 0.5:
            risk_score += 0.2
            risk_factors.append("Low agreement between analysis methods")
        
        # News volume risk
        news_count = sentiment.get('article_count', 0)
        if news_count > 15:
            risk_score += 0.1
            risk_factors.append("High news volume may indicate increased volatility")
        
        # Normalize risk score
        risk_score = max(0.0, min(1.0, risk_score))
        
        if risk_score > 0.7:
            risk_level = "HIGH"
        elif risk_score > 0.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'volatility': volatility if 'volatility' in locals() else None
        }
    
    def _calculate_position_size(self, risk_assessment: Dict) -> Dict:
        """Calculate recommended position size based on risk."""
        base_position = self.max_position_size
        risk_score = risk_assessment['risk_score']
        
        # Adjust position size based on risk
        risk_multiplier = 1 - risk_score
        recommended_position = base_position * risk_multiplier
        
        # Ensure minimum position size
        recommended_position = max(recommended_position, 0.01)  # Minimum 1%
        
        return {
            'recommended_position_percent': recommended_position * 100,
            'max_position_percent': self.max_position_size * 100,
            'risk_adjusted': True,
            'risk_multiplier': risk_multiplier
        }
    
    def _generate_error_response(self, error_message: str) -> Dict:
        """Generate error response when analysis fails."""
        return {
            'symbol': self.symbol,
            'timestamp': datetime.now().isoformat(),
            'error': True,
            'error_message': error_message,
            'recommendation': {
                'recommendation': 'Neutral',
                'confidence': 'LOW',
                'final_score': 0.5,
                'reasoning': ['Analysis failed - insufficient data']
            }
        }
    
    def get_quick_recommendation(self) -> str:
        """Get a quick recommendation without full analysis."""
        try:
            analysis = self.generate_comprehensive_analysis()
            if analysis.get('error'):
                return "Neutral - Analysis Error"
            
            rec = analysis['recommendation']['recommendation']
            conf = analysis['recommendation']['confidence']
            return f"{rec} ({conf} confidence)"
            
        except Exception as e:
            self.logger.error(f"Error in quick recommendation: {e}")
            return "Neutral - Error"