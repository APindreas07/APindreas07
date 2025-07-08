import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from config import config

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Performs technical analysis on stock price data."""
    
    def __init__(self):
        self.sma_short = config.SMA_SHORT
        self.sma_long = config.SMA_LONG
        self.rsi_period = config.RSI_PERIOD
        self.rsi_overbought = config.RSI_OVERBOUGHT
        self.rsi_oversold = config.RSI_OVERSOLD
    
    def calculate_sma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return data['Close'].rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data['Close'].ewm(span=period).mean()
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = self.calculate_sma(data, period)
        std = data['Close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band, sma, lower_band
    
    def calculate_stochastic(self, data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        lowest_low = data['Low'].rolling(window=k_period).min()
        highest_high = data['High'].rolling(window=k_period).max()
        k_percent = 100 * ((data['Close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent
    
    def calculate_price_momentum(self, data: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate price momentum."""
        return data['Close'].pct_change(periods=period)
    
    def calculate_volume_analysis(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate volume moving average."""
        return data['Volume'].rolling(window=period).mean()
    
    def get_sma_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get SMA crossover signals."""
        sma_short = self.calculate_sma(data, self.sma_short)
        sma_long = self.calculate_sma(data, self.sma_long)
        
        # Get latest values
        current_short = sma_short.iloc[-1]
        current_long = sma_long.iloc[-1]
        prev_short = sma_short.iloc[-2] if len(sma_short) > 1 else current_short
        prev_long = sma_long.iloc[-2] if len(sma_long) > 1 else current_long
        
        # Determine signal
        if current_short > current_long and prev_short <= prev_long:
            signal = "BUY"
            strength = "Strong"
        elif current_short < current_long and prev_short >= prev_long:
            signal = "SELL"
            strength = "Strong"
        elif current_short > current_long:
            signal = "BUY"
            strength = "Weak"
        else:
            signal = "SELL"
            strength = "Weak"
        
        return {
            'signal': signal,
            'strength': strength,
            'short_sma': current_short,
            'long_sma': current_long,
            'short_sma_prev': prev_short,
            'long_sma_prev': prev_long
        }
    
    def get_rsi_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get RSI signals."""
        rsi = self.calculate_rsi(data, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < self.rsi_oversold:
            signal = "BUY"
            strength = "Strong"
        elif current_rsi > self.rsi_overbought:
            signal = "SELL"
            strength = "Strong"
        elif current_rsi < 45:
            signal = "BUY"
            strength = "Weak"
        elif current_rsi > 55:
            signal = "SELL"
            strength = "Weak"
        else:
            signal = "NEUTRAL"
            strength = "Weak"
        
        return {
            'signal': signal,
            'strength': strength,
            'rsi_value': current_rsi,
            'oversold_threshold': self.rsi_oversold,
            'overbought_threshold': self.rsi_overbought
        }
    
    def get_macd_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get MACD signals."""
        macd_line, signal_line, histogram = self.calculate_macd(data)
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        
        prev_macd = macd_line.iloc[-2] if len(macd_line) > 1 else current_macd
        prev_signal = signal_line.iloc[-2] if len(signal_line) > 1 else current_signal
        
        # MACD crossover signals
        if current_macd > current_signal and prev_macd <= prev_signal:
            signal = "BUY"
            strength = "Strong"
        elif current_macd < current_signal and prev_macd >= prev_signal:
            signal = "SELL"
            strength = "Strong"
        elif current_macd > current_signal:
            signal = "BUY"
            strength = "Weak"
        else:
            signal = "SELL"
            strength = "Weak"
        
        return {
            'signal': signal,
            'strength': strength,
            'macd_line': current_macd,
            'signal_line': current_signal,
            'histogram': current_histogram
        }
    
    def get_bollinger_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get Bollinger Bands signals."""
        upper, middle, lower = self.calculate_bollinger_bands(data)
        current_price = data['Close'].iloc[-1]
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        
        # Calculate position within bands
        band_width = current_upper - current_lower
        position = (current_price - current_lower) / band_width if band_width > 0 else 0.5
        
        if current_price <= current_lower:
            signal = "BUY"
            strength = "Strong"
        elif current_price >= current_upper:
            signal = "SELL"
            strength = "Strong"
        elif position < 0.3:
            signal = "BUY"
            strength = "Weak"
        elif position > 0.7:
            signal = "SELL"
            strength = "Weak"
        else:
            signal = "NEUTRAL"
            strength = "Weak"
        
        return {
            'signal': signal,
            'strength': strength,
            'current_price': current_price,
            'upper_band': current_upper,
            'lower_band': current_lower,
            'position_in_band': position
        }
    
    def get_price_momentum_signals(self, data: pd.DataFrame) -> Dict[str, any]:
        """Get price momentum signals."""
        momentum = self.calculate_price_momentum(data)
        current_momentum = momentum.iloc[-1]
        
        if current_momentum > 0.05:  # 5% positive momentum
            signal = "BUY"
            strength = "Strong"
        elif current_momentum < -0.05:  # 5% negative momentum
            signal = "SELL"
            strength = "Strong"
        elif current_momentum > 0.02:
            signal = "BUY"
            strength = "Weak"
        elif current_momentum < -0.02:
            signal = "SELL"
            strength = "Weak"
        else:
            signal = "NEUTRAL"
            strength = "Weak"
        
        return {
            'signal': signal,
            'strength': strength,
            'momentum': current_momentum,
            'momentum_percentage': current_momentum * 100
        }
    
    def analyze_all_indicators(self, data: pd.DataFrame) -> Dict[str, any]:
        """Analyze all technical indicators and provide comprehensive signals."""
        if data.empty or len(data) < max(self.sma_long, self.rsi_period):
            return {
                'error': 'Insufficient data for technical analysis',
                'recommendation': 'NEUTRAL',
                'confidence': 0.0
            }
        
        # Get all signals
        sma_signals = self.get_sma_signals(data)
        rsi_signals = self.get_rsi_signals(data)
        macd_signals = self.get_macd_signals(data)
        bollinger_signals = self.get_bollinger_signals(data)
        momentum_signals = self.get_price_momentum_signals(data)
        
        # Count signals
        buy_signals = 0
        sell_signals = 0
        strong_buy = 0
        strong_sell = 0
        
        signals = [sma_signals, rsi_signals, macd_signals, bollinger_signals, momentum_signals]
        
        for signal in signals:
            if signal['signal'] == 'BUY':
                buy_signals += 1
                if signal['strength'] == 'Strong':
                    strong_buy += 1
            elif signal['signal'] == 'SELL':
                sell_signals += 1
                if signal['strength'] == 'Strong':
                    strong_sell += 1
        
        # Determine overall recommendation
        total_signals = len(signals)
        buy_ratio = buy_signals / total_signals
        sell_ratio = sell_signals / total_signals
        
        if buy_ratio > 0.6 and strong_buy >= 2:
            recommendation = "Strong BUY"
            confidence = min(0.9, buy_ratio + (strong_buy * 0.1))
        elif buy_ratio > 0.5:
            recommendation = "BUY"
            confidence = buy_ratio
        elif sell_ratio > 0.6 and strong_sell >= 2:
            recommendation = "Strong SELL"
            confidence = min(0.9, sell_ratio + (strong_sell * 0.1))
        elif sell_ratio > 0.5:
            recommendation = "SELL"
            confidence = sell_ratio
        else:
            recommendation = "NEUTRAL"
            confidence = 0.5
        
        return {
            'recommendation': recommendation,
            'confidence': confidence,
            'signals': {
                'sma': sma_signals,
                'rsi': rsi_signals,
                'macd': macd_signals,
                'bollinger': bollinger_signals,
                'momentum': momentum_signals
            },
            'summary': {
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'strong_buy': strong_buy,
                'strong_sell': strong_sell,
                'total_signals': total_signals
            }
        }

# Global instance
technical_analyzer = TechnicalAnalyzer()