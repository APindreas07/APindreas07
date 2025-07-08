import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from config import config

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """Comprehensive technical analysis for stock trading decisions."""
    
    def __init__(self):
        self.indicators = {}
        self.signals = {}
        
    def calculate_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators for the given data."""
        try:
            # Make a copy to avoid modifying original data
            df = data.copy()
            
            # Moving Averages
            df = self._add_moving_averages(df)
            
            # Momentum Indicators
            df = self._add_momentum_indicators(df)
            
            # Volatility Indicators
            df = self._add_volatility_indicators(df)
            
            # Volume Indicators
            df = self._add_volume_indicators(df)
            
            # Trend Indicators
            df = self._add_trend_indicators(df)
            
            # Support and Resistance
            df = self._add_support_resistance(df)
            
            logger.info("All technical indicators calculated successfully")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return data
    
    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add various moving averages."""
        # Simple Moving Averages
        df['SMA_5'] = df['Close'].rolling(window=5).mean()
        df['SMA_10'] = df['Close'].rolling(window=10).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_100'] = df['Close'].rolling(window=100).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # Exponential Moving Averages
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
        
        # Weighted Moving Average
        df['WMA_20'] = df['Close'].rolling(window=20).apply(
            lambda x: np.dot(x, np.arange(1, len(x) + 1)) / np.sum(np.arange(1, len(x) + 1))
        )
        
        return df
    
    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators."""
        # RSI (Relative Strength Index)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Stochastic Oscillator
        low_min = df['Low'].rolling(window=14).min()
        high_max = df['High'].rolling(window=14).max()
        df['Stoch_K'] = 100 * ((df['Close'] - low_min) / (high_max - low_min))
        df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
        
        # Williams %R
        df['Williams_R'] = -100 * ((high_max - df['Close']) / (high_max - low_min))
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Rate of Change
        df['ROC'] = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)) * 100
        
        return df
    
    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility indicators."""
        # Bollinger Bands
        df['BB_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        df['BB_position'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # Average True Range (ATR)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        df['ATR'] = true_range.rolling(window=14).mean()
        
        # Keltner Channels
        df['KC_middle'] = df['Close'].rolling(window=20).mean()
        df['KC_upper'] = df['KC_middle'] + (df['ATR'] * 2)
        df['KC_lower'] = df['KC_middle'] - (df['ATR'] * 2)
        
        return df
    
    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based indicators."""
        # Volume SMA
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        
        # On-Balance Volume (OBV)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        
        # Volume Rate of Change
        df['Volume_ROC'] = ((df['Volume'] - df['Volume'].shift(10)) / df['Volume'].shift(10)) * 100
        
        # Chaikin Money Flow
        mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low'])
        mfm = mfm.replace([np.inf, -np.inf], 0)
        mfv = mfm * df['Volume']
        df['CMF'] = mfv.rolling(window=20).sum() / df['Volume'].rolling(window=20).sum()
        
        # Money Flow Index
        typical_price = (df['High'] + df['Low'] + df['Close']) / 3
        money_flow = typical_price * df['Volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()
        
        mfi_ratio = positive_flow / negative_flow
        df['MFI'] = 100 - (100 / (1 + mfi_ratio))
        
        return df
    
    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend indicators."""
        # ADX (Average Directional Index)
        plus_dm = df['High'].diff()
        minus_dm = df['Low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = self._calculate_true_range(df)
        plus_di = 100 * (plus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        minus_di = 100 * (minus_dm.rolling(window=14).mean() / tr.rolling(window=14).mean())
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['ADX'] = dx.rolling(window=14).mean()
        
        # Parabolic SAR
        df['PSAR'] = self._calculate_psar(df)
        
        # Ichimoku Cloud
        df = self._add_ichimoku_indicators(df)
        
        return df
    
    def _add_support_resistance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add support and resistance levels."""
        # Pivot Points
        df['PP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['R1'] = 2 * df['PP'] - df['Low']
        df['S1'] = 2 * df['PP'] - df['High']
        df['R2'] = df['PP'] + (df['High'] - df['Low'])
        df['S2'] = df['PP'] - (df['High'] - df['Low'])
        
        # Dynamic Support/Resistance (using recent highs and lows)
        df['Resistance_20'] = df['High'].rolling(window=20).max()
        df['Support_20'] = df['Low'].rolling(window=20).min()
        
        return df
    
    def _calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """Calculate True Range for ADX."""
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        return np.maximum(high_low, np.maximum(high_close, low_close))
    
    def _calculate_psar(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Parabolic SAR."""
        psar = df['Close'].copy()
        psar.iloc[0] = df['Low'].iloc[0]
        
        af = 0.02  # Acceleration factor
        ep = df['High'].iloc[0]  # Extreme point
        
        for i in range(1, len(df)):
            if df['Close'].iloc[i] > ep:
                ep = df['High'].iloc[i]
                af = min(af + 0.02, 0.2)
            else:
                ep = df['Low'].iloc[i]
                af = 0.02
            
            psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
            
            # Adjust PSAR based on price action
            if df['Close'].iloc[i] > psar.iloc[i]:
                psar.iloc[i] = min(psar.iloc[i], df['Low'].iloc[i-1], df['Low'].iloc[i-2])
            else:
                psar.iloc[i] = max(psar.iloc[i], df['High'].iloc[i-1], df['High'].iloc[i-2])
        
        return psar
    
    def _add_ichimoku_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Ichimoku Cloud indicators."""
        # Tenkan-sen (Conversion Line)
        high_9 = df['High'].rolling(window=9).max()
        low_9 = df['Low'].rolling(window=9).min()
        df['Tenkan_sen'] = (high_9 + low_9) / 2
        
        # Kijun-sen (Base Line)
        high_26 = df['High'].rolling(window=26).max()
        low_26 = df['Low'].rolling(window=26).min()
        df['Kijun_sen'] = (high_26 + low_26) / 2
        
        # Senkou Span A (Leading Span A)
        df['Senkou_span_A'] = ((df['Tenkan_sen'] + df['Kijun_sen']) / 2).shift(26)
        
        # Senkou Span B (Leading Span B)
        high_52 = df['High'].rolling(window=52).max()
        low_52 = df['Low'].rolling(window=52).min()
        df['Senkou_span_B'] = ((high_52 + low_52) / 2).shift(26)
        
        # Chikou Span (Lagging Span)
        df['Chikou_span'] = df['Close'].shift(-26)
        
        return df
    
    def generate_trading_signals(self, df: pd.DataFrame) -> Dict[str, any]:
        """Generate comprehensive trading signals based on technical indicators."""
        signals = {
            'overall_signal': 'Neutral',
            'confidence': 0.0,
            'signals': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Get latest data point
            latest = df.iloc[-1]
            previous = df.iloc[-2] if len(df) > 1 else latest
            
            signal_strength = 0
            total_signals = 0
            
            # Moving Average Signals
            ma_signals = self._analyze_moving_averages(latest, previous)
            signals['signals']['moving_averages'] = ma_signals
            signal_strength += ma_signals['strength']
            total_signals += 1
            
            # RSI Signals
            rsi_signals = self._analyze_rsi(latest)
            signals['signals']['rsi'] = rsi_signals
            signal_strength += rsi_signals['strength']
            total_signals += 1
            
            # MACD Signals
            macd_signals = self._analyze_macd(latest, previous)
            signals['signals']['macd'] = macd_signals
            signal_strength += macd_signals['strength']
            total_signals += 1
            
            # Bollinger Bands Signals
            bb_signals = self._analyze_bollinger_bands(latest)
            signals['signals']['bollinger_bands'] = bb_signals
            signal_strength += bb_signals['strength']
            total_signals += 1
            
            # Volume Signals
            volume_signals = self._analyze_volume(latest, previous)
            signals['signals']['volume'] = volume_signals
            signal_strength += volume_signals['strength']
            total_signals += 1
            
            # Support/Resistance Signals
            sr_signals = self._analyze_support_resistance(latest)
            signals['signals']['support_resistance'] = sr_signals
            signal_strength += sr_signals['strength']
            total_signals += 1
            
            # Calculate overall signal
            if total_signals > 0:
                avg_strength = signal_strength / total_signals
                signals['confidence'] = abs(avg_strength)
                
                if avg_strength > 0.3:
                    signals['overall_signal'] = 'Strong BUY' if avg_strength > 0.6 else 'BUY'
                elif avg_strength < -0.3:
                    signals['overall_signal'] = 'Strong SELL' if avg_strength < -0.6 else 'SELL'
                else:
                    signals['overall_signal'] = 'Neutral'
            
            logger.info(f"Trading signals generated: {signals['overall_signal']} (confidence: {signals['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error generating trading signals: {str(e)}")
            signals['error'] = str(e)
        
        return signals
    
    def _analyze_moving_averages(self, latest: pd.Series, previous: pd.Series) -> Dict:
        """Analyze moving average signals."""
        signals = {'strength': 0, 'details': []}
        
        # Price vs SMA signals
        if latest['Close'] > latest['SMA_20']:
            signals['strength'] += 0.2
            signals['details'].append("Price above SMA 20")
        else:
            signals['strength'] -= 0.2
            signals['details'].append("Price below SMA 20")
        
        if latest['Close'] > latest['SMA_50']:
            signals['strength'] += 0.3
            signals['details'].append("Price above SMA 50")
        else:
            signals['strength'] -= 0.3
            signals['details'].append("Price below SMA 50")
        
        # Golden/Death Cross
        if latest['SMA_20'] > latest['SMA_50'] and previous['SMA_20'] <= previous['SMA_50']:
            signals['strength'] += 0.5
            signals['details'].append("Golden Cross (SMA 20 crossed above SMA 50)")
        elif latest['SMA_20'] < latest['SMA_50'] and previous['SMA_20'] >= previous['SMA_50']:
            signals['strength'] -= 0.5
            signals['details'].append("Death Cross (SMA 20 crossed below SMA 50)")
        
        return signals
    
    def _analyze_rsi(self, latest: pd.Series) -> Dict:
        """Analyze RSI signals."""
        signals = {'strength': 0, 'details': []}
        rsi = latest['RSI']
        
        if rsi < 30:
            signals['strength'] += 0.4
            signals['details'].append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 40:
            signals['strength'] += 0.2
            signals['details'].append(f"RSI approaching oversold ({rsi:.1f})")
        elif rsi > 70:
            signals['strength'] -= 0.4
            signals['details'].append(f"RSI overbought ({rsi:.1f})")
        elif rsi > 60:
            signals['strength'] -= 0.2
            signals['details'].append(f"RSI approaching overbought ({rsi:.1f})")
        
        return signals
    
    def _analyze_macd(self, latest: pd.Series, previous: pd.Series) -> Dict:
        """Analyze MACD signals."""
        signals = {'strength': 0, 'details': []}
        
        # MACD line vs Signal line
        if latest['MACD'] > latest['MACD_Signal']:
            signals['strength'] += 0.3
            signals['details'].append("MACD above signal line")
        else:
            signals['strength'] -= 0.3
            signals['details'].append("MACD below signal line")
        
        # MACD crossover
        if (latest['MACD'] > latest['MACD_Signal'] and 
            previous['MACD'] <= previous['MACD_Signal']):
            signals['strength'] += 0.4
            signals['details'].append("MACD bullish crossover")
        elif (latest['MACD'] < latest['MACD_Signal'] and 
              previous['MACD'] >= previous['MACD_Signal']):
            signals['strength'] -= 0.4
            signals['details'].append("MACD bearish crossover")
        
        return signals
    
    def _analyze_bollinger_bands(self, latest: pd.Series) -> Dict:
        """Analyze Bollinger Bands signals."""
        signals = {'strength': 0, 'details': []}
        
        price = latest['Close']
        bb_upper = latest['BB_upper']
        bb_lower = latest['BB_lower']
        bb_position = latest['BB_position']
        
        if price < bb_lower:
            signals['strength'] += 0.4
            signals['details'].append("Price below lower Bollinger Band (oversold)")
        elif price > bb_upper:
            signals['strength'] -= 0.4
            signals['details'].append("Price above upper Bollinger Band (overbought)")
        elif bb_position < 0.2:
            signals['strength'] += 0.2
            signals['details'].append("Price near lower Bollinger Band")
        elif bb_position > 0.8:
            signals['strength'] -= 0.2
            signals['details'].append("Price near upper Bollinger Band")
        
        return signals
    
    def _analyze_volume(self, latest: pd.Series, previous: pd.Series) -> Dict:
        """Analyze volume signals."""
        signals = {'strength': 0, 'details': []}
        
        volume_ratio = latest['Volume'] / latest['Volume_SMA']
        price_change = (latest['Close'] - previous['Close']) / previous['Close']
        
        # Volume confirmation
        if volume_ratio > 1.5 and price_change > 0:
            signals['strength'] += 0.3
            signals['details'].append("High volume with price increase")
        elif volume_ratio > 1.5 and price_change < 0:
            signals['strength'] -= 0.3
            signals['details'].append("High volume with price decrease")
        
        # OBV trend
        if latest['OBV'] > previous['OBV']:
            signals['strength'] += 0.2
            signals['details'].append("OBV increasing")
        else:
            signals['strength'] -= 0.2
            signals['details'].append("OBV decreasing")
        
        return signals
    
    def _analyze_support_resistance(self, latest: pd.Series) -> Dict:
        """Analyze support and resistance signals."""
        signals = {'strength': 0, 'details': []}
        
        price = latest['Close']
        
        # Support levels
        if price > latest['S1'] and price < latest['PP']:
            signals['strength'] += 0.2
            signals['details'].append("Price above support level S1")
        
        # Resistance levels
        if price < latest['R1'] and price > latest['PP']:
            signals['strength'] -= 0.2
            signals['details'].append("Price below resistance level R1")
        
        # Breakout signals
        if price > latest['R1']:
            signals['strength'] += 0.4
            signals['details'].append("Price broke above resistance R1")
        elif price < latest['S1']:
            signals['strength'] -= 0.4
            signals['details'].append("Price broke below support S1")
        
        return signals
    
    def get_summary_report(self, df: pd.DataFrame) -> Dict:
        """Generate a summary report of technical analysis."""
        if df.empty:
            return {"error": "No data available for analysis"}
        
        latest = df.iloc[-1]
        
        report = {
            "current_price": latest['Close'],
            "price_change_1d": ((latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100) if len(df) > 1 else 0,
            "price_change_5d": ((latest['Close'] - df.iloc[-6]['Close']) / df.iloc[-6]['Close'] * 100) if len(df) > 5 else 0,
            "technical_indicators": {
                "rsi": latest.get('RSI', 0),
                "macd": latest.get('MACD', 0),
                "bollinger_position": latest.get('BB_position', 0),
                "volume_ratio": latest['Volume'] / latest.get('Volume_SMA', 1),
                "sma_20": latest.get('SMA_20', 0),
                "sma_50": latest.get('SMA_50', 0)
            },
            "support_levels": {
                "s1": latest.get('S1', 0),
                "s2": latest.get('S2', 0)
            },
            "resistance_levels": {
                "r1": latest.get('R1', 0),
                "r2": latest.get('R2', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return report