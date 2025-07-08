# 🚀 Financial Analysis Application - Apple (AAPL) Stock

A comprehensive financial analysis system that combines technical, fundamental, and sentiment analysis to provide intelligent trading recommendations for Apple (AAPL) stock.

## 🎯 Features

### 📊 **Comprehensive Analysis**
- **Technical Analysis**: 20+ technical indicators including RSI, MACD, Bollinger Bands, Moving Averages
- **Fundamental Analysis**: Valuation metrics, profitability ratios, liquidity analysis, growth metrics
- **Sentiment Analysis**: Enhanced FinBERT model for financial text sentiment analysis
- **Combined Recommendations**: Weighted scoring system for final trading decisions

### 🤖 **AI-Powered Sentiment Analysis**
- Enhanced FinBERT model with improved accuracy
- Automatic model retraining when accuracy drops
- Real-time sentiment analysis of financial news
- Confidence scoring for all predictions

### 📈 **Real-Time Data**
- Yahoo Finance integration with caching and rate limiting
- Daily price updates (configurable)
- Efficient API call management
- Historical data analysis

### 🛡️ **Risk Management**
- Comprehensive risk assessment
- Stop-loss and target price calculations
- Position sizing recommendations
- Risk mitigation strategies

### 🔧 **Advanced Features**
- RESTful API with FastAPI
- Rate limiting and monitoring
- Comprehensive logging
- Data persistence and history tracking

## 📋 Requirements

- Python 3.8+
- Internet connection for Yahoo Finance data
- 4GB+ RAM (for FinBERT model)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

#### Option A: Command Line Analysis
```bash
python run_analysis.py
```

#### Option B: API Server
```bash
python api_server.py
```

The API will be available at `http://localhost:8000`

### 3. View API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📊 Analysis Components

### Technical Analysis
- **Moving Averages**: SMA 5, 10, 20, 50, 100, 200
- **Momentum Indicators**: RSI, MACD, Stochastic, Williams %R
- **Volatility Indicators**: Bollinger Bands, ATR, Keltner Channels
- **Volume Indicators**: OBV, Volume ROC, Chaikin Money Flow
- **Trend Indicators**: ADX, Parabolic SAR, Ichimoku Cloud
- **Support/Resistance**: Pivot Points, Dynamic levels

### Fundamental Analysis
- **Valuation Metrics**: P/E, P/B, P/S, EV/EBITDA ratios
- **Profitability Metrics**: Gross/Operating/Net margins, ROE, ROA
- **Liquidity Metrics**: Current/Quick/Cash ratios, Working capital
- **Efficiency Metrics**: Asset/Inventory/Receivables turnover
- **Growth Metrics**: Revenue/Earnings/FCF growth rates
- **Debt Metrics**: Debt-to-equity, Interest coverage ratios

### Sentiment Analysis
- **FinBERT Model**: Pre-trained financial sentiment classifier
- **News Analysis**: Real-time financial news sentiment
- **Confidence Scoring**: Probability-based sentiment strength
- **Batch Processing**: Efficient multiple text analysis

## 🔌 API Endpoints

### Core Analysis
- `POST /analyze` - Run comprehensive analysis
- `GET /summary/{symbol}` - Get analysis summary
- `GET /analysis/{symbol}` - Get detailed analysis
- `GET /report/{symbol}` - Generate trading report

### Data Endpoints
- `GET /price/{symbol}` - Current stock price
- `GET /technical/{symbol}` - Technical indicators
- `GET /fundamental/{symbol}` - Fundamental metrics
- `GET /history/{symbol}` - Analysis history

### Sentiment Analysis
- `POST /sentiment` - Analyze single text
- `POST /sentiment/batch` - Analyze multiple texts

### Model Management
- `POST /retrain` - Retrain FinBERT model
- `GET /model/info` - Model information
- `GET /stats` - API usage statistics

## 📈 Trading Recommendations

The system provides five levels of recommendations:

1. **Strong BUY** (≥80% confidence)
2. **BUY** (60-79% confidence)
3. **Neutral** (40-59% confidence)
4. **SELL** (20-39% confidence)
5. **Strong SELL** (<20% confidence)

### Example Response
```json
{
  "symbol": "AAPL",
  "recommendation": "BUY",
  "confidence": 0.75,
  "current_price": 175.50,
  "technical_signal": "BUY",
  "fundamental_recommendation": "BUY",
  "sentiment": "BUY",
  "trading_advice": {
    "action": "BUY",
    "confidence_level": "High",
    "timing": "Within 1-2 days",
    "position_size": "Partial position",
    "stop_loss": 165.25,
    "target_price": 185.75
  }
}
```

## ⚙️ Configuration

Edit `config.py` to customize:

- **Stock Symbol**: Change from AAPL to any symbol
- **Update Intervals**: Modify data refresh frequency
- **Analysis Weights**: Adjust technical/fundamental/sentiment weights
- **Model Settings**: Configure FinBERT parameters
- **API Limits**: Set rate limiting and caching

## 🔧 Advanced Usage

### Custom Analysis
```python
from main_analyzer import MainAnalyzer

analyzer = MainAnalyzer()

# Run analysis for any symbol
result = analyzer.run_comprehensive_analysis("MSFT")

# Get trading report
report = analyzer.generate_trading_report("MSFT")

# Check model performance
retrain_result = analyzer.retrain_model_if_needed()
```

### API Integration
```python
import requests

# Run analysis via API
response = requests.post("http://localhost:8000/analyze", 
                        json={"symbol": "AAPL"})
analysis = response.json()

# Get sentiment analysis
sentiment = requests.post("http://localhost:8000/sentiment", 
                         json={"text": "Apple reports strong earnings"})
```

## 📊 Performance Monitoring

### Model Accuracy
- Automatic accuracy monitoring
- Retraining triggers when accuracy < 65%
- Training history tracking
- Performance improvement metrics

### API Monitoring
- Request rate limiting (100/hour per client)
- Response time tracking
- Error rate monitoring
- Usage statistics

## 🛡️ Risk Management

### Built-in Safeguards
- **Data Validation**: All inputs validated
- **Error Handling**: Comprehensive exception handling
- **Rate Limiting**: Prevents API abuse
- **Caching**: Reduces API calls and improves performance

### Trading Risk Assessment
- **Risk Levels**: Low/Medium/High based on confidence
- **Key Risks**: Identified for each analysis
- **Mitigation Strategies**: Suggested risk management approaches
- **Stop Loss**: Calculated support levels

## 📁 Project Structure

```
financial-analysis/
├── config.py              # Configuration settings
├── data_collector.py      # Yahoo Finance data collection
├── enhanced_finbert.py    # Enhanced FinBERT sentiment analysis
├── technical_analyzer.py  # Technical analysis engine
├── fundamental_analyzer.py # Fundamental analysis engine
├── main_analyzer.py       # Main analysis orchestrator
├── api_server.py          # FastAPI server
├── run_analysis.py        # Command-line runner
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── data/                 # Data storage
├── models/               # Saved models
└── logs/                 # Application logs
```

## 🔄 Data Flow

1. **Data Collection**: Yahoo Finance API → Cached storage
2. **Technical Analysis**: Price data → Technical indicators → Trading signals
3. **Fundamental Analysis**: Financial statements → Ratios → Scores
4. **Sentiment Analysis**: News text → FinBERT → Sentiment scores
5. **Combination**: Weighted scoring → Final recommendation
6. **Output**: Trading report with risk assessment

## 🚨 Important Notes

### Disclaimer
This application is for educational and research purposes only. It does not constitute financial advice. Always consult with a qualified financial advisor before making investment decisions.

### Data Sources
- **Yahoo Finance**: Free, real-time stock data
- **FinBERT Model**: Pre-trained financial sentiment classifier
- **Sample News**: Currently uses sample data (can be extended with news APIs)

### Limitations
- Focused on Apple (AAPL) stock (easily configurable for other symbols)
- Sentiment analysis uses sample news data
- Historical accuracy not guaranteed
- Market conditions can change rapidly

## 🔮 Future Enhancements

- [ ] Real-time news API integration
- [ ] Multi-stock portfolio analysis
- [ ] Machine learning model improvements
- [ ] Web dashboard interface
- [ ] Email/SMS alerts
- [ ] Backtesting capabilities
- [ ] Options analysis
- [ ] Cryptocurrency support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the logs in the `logs/` directory
2. Review the API documentation at `/docs`
3. Ensure all dependencies are installed
4. Verify internet connectivity for data fetching

---

**Happy Trading! 📈💰**
