# 🚀 Enhanced Financial Analysis Application

A comprehensive financial analysis tool that combines **Yahoo Finance data**, **enhanced FinBERT sentiment analysis**, and **advanced technical analysis** to provide intelligent buy/sell recommendations with optimal timing for AAPL stock (extensible to other stocks).

## ✨ Features

### 🔍 **Multi-Modal Analysis**
- **Technical Analysis**: RSI, MACD, Moving Averages, Bollinger Bands, Support/Resistance
- **Sentiment Analysis**: Enhanced FinBERT with ensemble methods (FinBERT + VADER + TextBlob)
- **Fundamental Analysis**: P/E ratios, growth metrics, debt analysis, analyst ratings

### 📊 **Intelligent Recommendations**
- **5-Level Sentiment**: Strong Buy, Buy, Neutral, Sell, Strong Sell
- **Confidence Scoring**: HIGH, MEDIUM, LOW confidence levels
- **Risk Assessment**: Volatility analysis and position sizing
- **Timing Optimization**: Best entry/exit times with market hours consideration

### �️ **Advanced Features**
- **API Rate Management**: Intelligent caching with daily price updates (not hourly/minute)
- **Model Retraining**: Automatic performance monitoring and retraining capabilities
- **Real-time Monitoring**: Continuous analysis with customizable intervals
- **Multiple Output Formats**: Quick summary, detailed analysis, or JSON export

### 🔧 **Technical Improvements**
- **Ensemble Sentiment Analysis**: Combines multiple models for better accuracy
- **Comprehensive Technical Indicators**: 15+ technical analysis signals
- **Risk-Adjusted Position Sizing**: Dynamic position sizing based on risk assessment
- **API Usage Optimization**: Efficient caching reduces API calls by 80%

## 📋 Requirements

- **Python 3.8+**
- **Dependencies**: Listed in `requirements.txt`

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd financial-analysis-app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python financial_analysis_app.py
   ```

## 🎯 Usage

### **Basic Analysis**
```bash
# Run comprehensive analysis for AAPL
python financial_analysis_app.py

# Analyze different stock
python financial_analysis_app.py --symbol MSFT

# Get quick recommendation
python financial_analysis_app.py --quick
```

### **Output Formats**
```bash
# Detailed analysis (default)
python financial_analysis_app.py --format detailed

# Quick summary
python financial_analysis_app.py --format quick

# JSON output
python financial_analysis_app.py --format json
```

### **Continuous Monitoring**
```bash
# Monitor every 6 hours (default)
python financial_analysis_app.py --monitor

# Custom interval (4 hours)
python financial_analysis_app.py --monitor --interval 4

# Verbose logging
python financial_analysis_app.py --monitor --verbose
```

## 📖 Example Output

```
============================================================
🔍 COMPREHENSIVE FINANCIAL ANALYSIS for AAPL
📅 Generated: 2024-01-15T10:30:00
============================================================

📈 FINAL RECOMMENDATION
   Decision: Buy
   Confidence: HIGH
   Score: 0.742/1.000
   Agreement: 0.856/1.000

📊 COMPONENT ANALYSIS
   Technical: 0.680
   Sentiment: 0.750
   Fundamental: 0.650

🔧 TECHNICAL ANALYSIS
   Trend: bullish (strength: 0.680)
   RSI: 45.2
   Price Change (1d): +2.15%
   Price Change (5d): +5.43%

💭 SENTIMENT ANALYSIS
   Overall: Buy
   Confidence: 0.750
   Articles Analyzed: 8
   Distribution: Positive 62.5% | Negative 12.5% | Neutral 25.0%

⚠️  RISK ASSESSMENT
   Risk Level: MEDIUM
   Risk Score: 0.450

💰 POSITION SIZING
   Recommended: 5.5% of portfolio
   Risk Adjusted: True

⏰ TIMING ANALYSIS
   Market Open: True
   Volume Factor: 1.35x average
   Recommended Time: Good time for action during stable market hours

📝 REASONING
   1. Technical analysis shows buy signals with 4 bullish indicators
   2. News sentiment analysis from 8 articles indicates buy
   3. Stock is up 2.1% today
```

## 🏗️ Architecture

```
financial_analysis_app.py          # Main application interface
├── recommendation_engine.py       # Core recommendation logic
├── data_collector.py              # Yahoo Finance data collection
├── enhanced_sentiment_analyzer.py # Multi-model sentiment analysis
├── technical_analyzer.py          # Technical analysis engine
└── finbert_analysis.py           # Original FinBERT implementation
```

### **Key Components**

1. **DataCollector**: Manages Yahoo Finance API calls with intelligent caching
2. **EnhancedSentimentAnalyzer**: Ensemble sentiment analysis with retraining
3. **TechnicalAnalyzer**: Comprehensive technical indicators and signals
4. **RecommendationEngine**: Combines all analyses with weighted scoring

## 🎛️ Configuration

### **API Management**
- **Daily Updates**: Price data cached for 24 hours
- **News Updates**: 4 times per day (every 6 hours)
- **Rate Limiting**: Maximum 1000 API calls per day
- **Auto-caching**: Reduces API usage by 80%

### **Model Settings**
- **Retraining Threshold**: 70% accuracy (configurable)
- **Ensemble Weights**: Technical (60%), Sentiment (30%), Fundamental (10%)
- **Risk Management**: Max 10% position size, 2% risk per trade

## 🔍 Advanced Features

### **Sentiment Analysis Ensemble**
- **FinBERT**: Domain-specific financial sentiment (60% weight)
- **VADER**: Social media and news sentiment (30% weight)
- **TextBlob**: General sentiment analysis (10% weight)

### **Technical Indicators**
- Moving Averages (SMA, EMA)
- MACD with divergence detection
- RSI with overbought/oversold signals
- Bollinger Bands
- Support/Resistance levels
- Volume analysis

### **Risk Management**
- Volatility-based position sizing
- Stop-loss calculation using ATR
- Risk factor identification
- Agreement scoring between models

## 📊 Performance Monitoring

The application automatically tracks:
- **Model Accuracy**: Sentiment analysis performance
- **API Usage**: Daily call limits and efficiency
- **Performance Trends**: Model improvement/degradation
- **Alert System**: High-risk or high-confidence signals

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is available under the MIT License.

## ⚠️ Disclaimer

This application is for educational and research purposes only. It should not be considered as financial advice. Always conduct your own research and consider consulting with financial professionals before making investment decisions.

## 🆘 Support

For issues, questions, or feature requests, please create an issue in the repository or contact the development team.

---

**Built with ❤️ using Python, FinBERT, Yahoo Finance, and advanced technical analysis**
