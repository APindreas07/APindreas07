import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class TechnicalAnalyzer:
    """Technical analysis module for analyzing price patterns and generating trading signals."""
    
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Signal thresholds
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.macd_threshold = 0.01
        
    def analyze_price_action(self, data: pd.DataFrame) -> Dict:
        """Analyze overall price action and trends."""
        if data.empty or len(data) < 50:
            return {'trend': 'neutral', 'strength': 0.5, 'signals': []}
        
        latest = data.iloc[-1]
        signals = []
        
        # Trend analysis using moving averages
        trend_signals = self._analyze_trend(data)
        signals.extend(trend_signals['signals'])
        
        # Momentum analysis
        momentum_signals = self._analyze_momentum(data)
        signals.extend(momentum_signals['signals'])
        
        # Volume analysis
        volume_signals = self._analyze_volume(data)
        signals.extend(volume_signals['signals'])
        
        # Support and resistance
        sr_signals = self._analyze_support_resistance(data)
        signals.extend(sr_signals['signals'])
        
        # Overall technical score
        technical_score = self._calculate_technical_score(signals)
        
        return {
            'trend': trend_signals['trend'],
            'trend_strength': trend_signals['strength'],
            'momentum': momentum_signals,
            'volume_analysis': volume_signals,
            'support_resistance': sr_signals,
            'technical_score': technical_score,
            'signals': signals,
            'current_price': latest['Close'],
            'price_change_1d': self._calculate_price_change(data, 1),
            'price_change_5d': self._calculate_price_change(data, 5),
            'price_change_20d': self._calculate_price_change(data, 20)
        }
    
    def _analyze_trend(self, data: pd.DataFrame) -> Dict:
        """Analyze trend using multiple moving averages."""
        latest = data.iloc[-1]
        signals = []
        
        # Moving average analysis
        sma_20 = latest.get('SMA_20', latest['Close'])
        sma_50 = latest.get('SMA_50', latest['Close'])
        current_price = latest['Close']
        
        # Price vs moving averages
        if current_price > sma_20 > sma_50:
            trend = 'bullish'
            strength = 0.8
            signals.append({'type': 'trend', 'signal': 'bullish', 'strength': 0.8, 'description': 'Price above all moving averages'})
        elif current_price < sma_20 < sma_50:
            trend = 'bearish'
            strength = 0.8
            signals.append({'type': 'trend', 'signal': 'bearish', 'strength': 0.8, 'description': 'Price below all moving averages'})
        elif current_price > sma_20:
            trend = 'bullish'
            strength = 0.6
            signals.append({'type': 'trend', 'signal': 'bullish', 'strength': 0.6, 'description': 'Price above short-term MA'})
        elif current_price < sma_20:
            trend = 'bearish'
            strength = 0.6
            signals.append({'type': 'trend', 'signal': 'bearish', 'strength': 0.6, 'description': 'Price below short-term MA'})
        else:
            trend = 'neutral'
            strength = 0.5
        
        # Golden Cross / Death Cross
        if 'SMA_50' in data.columns and len(data) >= 2:
            prev_sma_20 = data.iloc[-2].get('SMA_20', 0)
            prev_sma_50 = data.iloc[-2].get('SMA_50', 0)
            
            if sma_20 > sma_50 and prev_sma_20 <= prev_sma_50:
                signals.append({'type': 'crossover', 'signal': 'bullish', 'strength': 0.9, 'description': 'Golden Cross detected'})
            elif sma_20 < sma_50 and prev_sma_20 >= prev_sma_50:
                signals.append({'type': 'crossover', 'signal': 'bearish', 'strength': 0.9, 'description': 'Death Cross detected'})
        
        return {
            'trend': trend,
            'strength': strength,
            'signals': signals
        }
    
    def _analyze_momentum(self, data: pd.DataFrame) -> Dict:
        """Analyze momentum indicators (RSI, MACD)."""
        latest = data.iloc[-1]
        signals = []
        
        # RSI analysis
        rsi = latest.get('RSI', 50)
        if rsi < self.rsi_oversold:
            signals.append({'type': 'momentum', 'signal': 'bullish', 'strength': 0.7, 'description': f'RSI oversold ({rsi:.1f})'})
        elif rsi > self.rsi_overbought:
            signals.append({'type': 'momentum', 'signal': 'bearish', 'strength': 0.7, 'description': f'RSI overbought ({rsi:.1f})'})
        
        # MACD analysis
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        macd_histogram = latest.get('MACD_histogram', 0)
        
        if macd > macd_signal and macd_histogram > self.macd_threshold:
            signals.append({'type': 'momentum', 'signal': 'bullish', 'strength': 0.6, 'description': 'MACD bullish crossover'})
        elif macd < macd_signal and macd_histogram < -self.macd_threshold:
            signals.append({'type': 'momentum', 'signal': 'bearish', 'strength': 0.6, 'description': 'MACD bearish crossover'})
        
        # MACD divergence (simplified)
        if len(data) >= 10:
            price_trend = self._calculate_price_trend(data, 10)
            macd_trend = self._calculate_macd_trend(data, 10)
            
            if price_trend > 0 and macd_trend < 0:
                signals.append({'type': 'divergence', 'signal': 'bearish', 'strength': 0.7, 'description': 'Bearish MACD divergence'})
            elif price_trend < 0 and macd_trend > 0:
                signals.append({'type': 'divergence', 'signal': 'bullish', 'strength': 0.7, 'description': 'Bullish MACD divergence'})
        
        return {
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram,
            'signals': signals
        }
    
    def _analyze_volume(self, data: pd.DataFrame) -> Dict:
        """Analyze volume patterns."""
        latest = data.iloc[-1]
        signals = []
        
        volume_ratio = latest.get('Volume_ratio', 1.0)
        
        # High volume breakout
        if volume_ratio > 2.0:
            price_change = self._calculate_price_change(data, 1)
            if price_change > 0.02:  # 2% positive move with high volume
                signals.append({'type': 'volume', 'signal': 'bullish', 'strength': 0.8, 'description': 'High volume breakout'})
            elif price_change < -0.02:  # 2% negative move with high volume
                signals.append({'type': 'volume', 'signal': 'bearish', 'strength': 0.8, 'description': 'High volume breakdown'})
        
        # Volume trend analysis
        if len(data) >= 5:
            recent_volume_trend = self._calculate_volume_trend(data, 5)
            if recent_volume_trend > 0.1:
                signals.append({'type': 'volume', 'signal': 'bullish', 'strength': 0.5, 'description': 'Increasing volume trend'})
            elif recent_volume_trend < -0.1:
                signals.append({'type': 'volume', 'signal': 'bearish', 'strength': 0.5, 'description': 'Decreasing volume trend'})
        
        return {
            'volume_ratio': volume_ratio,
            'volume_trend': recent_volume_trend if 'recent_volume_trend' in locals() else 0,
            'signals': signals
        }
    
    def _analyze_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Analyze support and resistance levels."""
        signals = []
        
        if len(data) < 20:
            return {'signals': signals, 'support': None, 'resistance': None}
        
        # Calculate support and resistance using pivot points
        highs = data['High'].rolling(window=5, center=True).max()
        lows = data['Low'].rolling(window=5, center=True).min()
        
        # Find recent support and resistance levels
        resistance_levels = []
        support_levels = []
        
        for i in range(5, len(data) - 5):
            if data.iloc[i]['High'] == highs.iloc[i]:
                resistance_levels.append(data.iloc[i]['High'])
            if data.iloc[i]['Low'] == lows.iloc[i]:
                support_levels.append(data.iloc[i]['Low'])
        
        current_price = data.iloc[-1]['Close']
        
        # Find nearest support and resistance
        resistance_levels = [r for r in resistance_levels if r > current_price]
        support_levels = [s for s in support_levels if s < current_price]
        
        nearest_resistance = min(resistance_levels) if resistance_levels else None
        nearest_support = max(support_levels) if support_levels else None
        
        # Check for breakouts
        if nearest_resistance and current_price > nearest_resistance * 0.999:
            signals.append({'type': 'breakout', 'signal': 'bullish', 'strength': 0.8, 'description': f'Resistance breakout at ${nearest_resistance:.2f}'})
        
        if nearest_support and current_price < nearest_support * 1.001:
            signals.append({'type': 'breakdown', 'signal': 'bearish', 'strength': 0.8, 'description': f'Support breakdown at ${nearest_support:.2f}'})
        
        return {
            'support': nearest_support,
            'resistance': nearest_resistance,
            'signals': signals
        }
    
    def _calculate_technical_score(self, signals: List[Dict]) -> Dict:
        """Calculate overall technical score from all signals."""
        if not signals:
            return {'score': 0.5, 'recommendation': 'Neutral', 'confidence': 0.5}
        
        bullish_score = 0
        bearish_score = 0
        total_weight = 0
        
        for signal in signals:
            weight = signal.get('strength', 0.5)
            total_weight += weight
            
            if signal['signal'] == 'bullish':
                bullish_score += weight
            elif signal['signal'] == 'bearish':
                bearish_score += weight
        
        if total_weight == 0:
            return {'score': 0.5, 'recommendation': 'Neutral', 'confidence': 0.5}
        
        # Normalize scores
        bullish_ratio = bullish_score / total_weight
        bearish_ratio = bearish_score / total_weight
        
        # Calculate final score (0 = strong bearish, 1 = strong bullish)
        final_score = bullish_ratio / (bullish_ratio + bearish_ratio) if (bullish_ratio + bearish_ratio) > 0 else 0.5
        confidence = abs(final_score - 0.5) * 2  # Convert to 0-1 confidence scale
        
        # Generate recommendation
        if final_score > 0.7:
            recommendation = 'Strong Buy'
        elif final_score > 0.6:
            recommendation = 'Buy'
        elif final_score < 0.3:
            recommendation = 'Strong Sell'
        elif final_score < 0.4:
            recommendation = 'Sell'
        else:
            recommendation = 'Neutral'
        
        return {
            'score': final_score,
            'recommendation': recommendation,
            'confidence': confidence,
            'bullish_signals': len([s for s in signals if s['signal'] == 'bullish']),
            'bearish_signals': len([s for s in signals if s['signal'] == 'bearish']),
            'total_signals': len(signals)
        }
    
    def _calculate_price_change(self, data: pd.DataFrame, periods: int) -> float:
        """Calculate price change over specified periods."""
        if len(data) < periods + 1:
            return 0.0
        
        current_price = data.iloc[-1]['Close']
        past_price = data.iloc[-(periods + 1)]['Close']
        
        return (current_price - past_price) / past_price
    
    def _calculate_price_trend(self, data: pd.DataFrame, periods: int) -> float:
        """Calculate price trend over specified periods."""
        if len(data) < periods:
            return 0.0
        
        recent_data = data.tail(periods)
        prices = recent_data['Close'].values
        
        # Simple linear regression slope
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        return slope / np.mean(prices)  # Normalize by average price
    
    def _calculate_macd_trend(self, data: pd.DataFrame, periods: int) -> float:
        """Calculate MACD trend over specified periods."""
        if len(data) < periods or 'MACD' not in data.columns:
            return 0.0
        
        recent_data = data.tail(periods)
        macd_values = recent_data['MACD'].values
        
        # Simple linear regression slope
        x = np.arange(len(macd_values))
        slope = np.polyfit(x, macd_values, 1)[0]
        
        return slope
    
    def _calculate_volume_trend(self, data: pd.DataFrame, periods: int) -> float:
        """Calculate volume trend over specified periods."""
        if len(data) < periods:
            return 0.0
        
        recent_data = data.tail(periods)
        volumes = recent_data['Volume'].values
        
        # Simple linear regression slope
        x = np.arange(len(volumes))
        slope = np.polyfit(x, volumes, 1)[0]
        
        return slope / np.mean(volumes)  # Normalize by average volume
    
    def generate_entry_exit_signals(self, data: pd.DataFrame) -> Dict:
        """Generate specific entry and exit signals with timing."""
        analysis = self.analyze_price_action(data)
        
        entry_signals = []
        exit_signals = []
        
        # Entry signals based on technical analysis
        if analysis['technical_score']['score'] > 0.7:
            entry_signals.append({
                'action': 'BUY',
                'confidence': analysis['technical_score']['confidence'],
                'reason': 'Strong bullish technical signals',
                'target_price': None,
                'stop_loss': self._calculate_stop_loss(data, 'long')
            })
        elif analysis['technical_score']['score'] < 0.3:
            entry_signals.append({
                'action': 'SELL',
                'confidence': analysis['technical_score']['confidence'],
                'reason': 'Strong bearish technical signals',
                'target_price': None,
                'stop_loss': self._calculate_stop_loss(data, 'short')
            })
        
        # Exit signals based on momentum and trend changes
        current_rsi = analysis['momentum']['rsi']
        if current_rsi > 80:
            exit_signals.append({
                'action': 'SELL',
                'reason': 'Extreme overbought conditions',
                'urgency': 'HIGH'
            })
        elif current_rsi < 20:
            exit_signals.append({
                'action': 'BUY_COVER',
                'reason': 'Extreme oversold conditions',
                'urgency': 'HIGH'
            })
        
        return {
            'entry_signals': entry_signals,
            'exit_signals': exit_signals,
            'market_condition': self._assess_market_condition(analysis)
        }
    
    def _calculate_stop_loss(self, data: pd.DataFrame, position_type: str) -> float:
        """Calculate stop loss level based on recent volatility."""
        if len(data) < 20:
            return None
        
        current_price = data.iloc[-1]['Close']
        atr = self._calculate_atr(data, 14)
        
        if position_type == 'long':
            return current_price - (2 * atr)  # 2 ATR below current price
        else:  # short position
            return current_price + (2 * atr)  # 2 ATR above current price
    
    def _calculate_atr(self, data: pd.DataFrame, periods: int) -> float:
        """Calculate Average True Range for volatility measurement."""
        if len(data) < periods + 1:
            return 0.0
        
        high = data['High']
        low = data['Low']
        close = data['Close'].shift(1)
        
        true_range = pd.concat([
            high - low,
            abs(high - close),
            abs(low - close)
        ], axis=1).max(axis=1)
        
        return true_range.rolling(window=periods).mean().iloc[-1]
    
    def _assess_market_condition(self, analysis: Dict) -> str:
        """Assess overall market condition."""
        score = analysis['technical_score']['score']
        trend_strength = analysis['trend_strength']
        
        if score > 0.7 and trend_strength > 0.7:
            return 'STRONG_BULLISH'
        elif score > 0.6:
            return 'BULLISH'
        elif score < 0.3 and trend_strength > 0.7:
            return 'STRONG_BEARISH'
        elif score < 0.4:
            return 'BEARISH'
        else:
            return 'NEUTRAL'