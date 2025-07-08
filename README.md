# 📈 Financial Analysis Application

A comprehensive real-time financial analysis application that combines Yahoo Finance data with FinBERT sentiment analysis to provide accurate buy/sell recommendations for stocks.

## 🎯 Features

- **Real-time Data**: Fetches live stock data from Yahoo Finance
- **Technical Analysis**: Comprehensive technical indicators (SMA, RSI, MACD, Bollinger Bands, etc.)
- **Sentiment Analysis**: Advanced FinBERT-based news and earnings sentiment analysis
- **Smart Recommendations**: Combines multiple analysis factors for accurate buy/sell signals
- **Rate Limiting**: Efficient API call management to avoid rate limits
- **Caching**: Intelligent data caching to reduce API calls
- **Web Dashboard**: Beautiful web interface for real-time monitoring
- **Command Line**: Standalone CLI for analysis and monitoring
- **Continuous Monitoring**: Automated periodic analysis

## 🚀 Quick Start

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd financial-analysis-app
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run a quick analysis:**
```bash
python main.py
```

### Usage Options

#### 1. Single Analysis
```bash
python main.py
```
Performs a one-time analysis and displays results in the terminal.

#### 2. Web Dashboard
```bash
python main.py --server
```
Starts the web server. Open your browser to `http://localhost:8000`

#### 3. Continuous Monitoring
```bash
python main.py --continuous
```
Runs analysis every hour automatically.

```bash
python main.py --monitor 30
```
Runs analysis every 30 minutes.

#### 4. View Summary
```bash
python main.py --summary
```
Shows summary of recent analyses.

## 📊 Analysis Components

### Technical Analysis
- **Simple Moving Averages (SMA)**: 20-day and 50-day crossovers
- **Relative Strength Index (RSI)**: Overbought/oversold conditions
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Price volatility and trend analysis
- **Price Momentum**: Short-term price movement analysis
- **Volume Analysis**: Trading volume patterns

### Sentiment Analysis
- **News Sentiment**: Analyzes recent news articles using FinBERT
- **Earnings Sentiment**: Evaluates earnings surprises and trends
- **Aggregate Scoring**: Combines multiple sentiment sources

### Recommendation System
- **Weighted Scoring**: Combines technical, sentiment, and momentum factors
- **Confidence Levels**: Provides confidence scores for each recommendation
- **Timing Guidance**: Suggests optimal timing (IMMEDIATE, SOON, MONITOR, WAIT)

## 🎯 Output Signals

The application provides five recommendation levels:
- **Strong BUY**: High confidence buy signal
- **BUY**: Moderate buy signal
- **NEUTRAL**: Hold or wait
- **SELL**: Moderate sell signal
- **Strong SELL**: High confidence sell signal

## ⚙️ Configuration

Edit `config.py` to customize:
- Stock symbol (default: AAPL)
- Update intervals
- API rate limits
- Analysis weights
- Technical indicator parameters

```python
# Example configuration
STOCK_SYMBOL = "AAPL"
PRICE_UPDATE_INTERVAL_HOURS = 24  # Daily updates
NEWS_UPDATE_INTERVAL_HOURS = 6    # Every 6 hours
MAX_API_CALLS_PER_MINUTE = 10     # Rate limiting
```

## 📁 Project Structure

```
financial-analysis-app/
├── main.py                 # Main entry point
├── api_server.py          # Web server and API
├── config.py              # Configuration settings
├── data_collector.py      # Yahoo Finance data collection
├── technical_analyzer.py  # Technical analysis engine
├── sentiment_analyzer.py  # FinBERT sentiment analysis
├── financial_analyzer.py  # Main analysis orchestrator
├── requirements.txt       # Python dependencies
├── data/                 # Cached data and analysis results
├── logs/                 # Application logs
└── models/               # Saved models (if any)
```

## 🔧 API Endpoints

When running the web server, the following endpoints are available:

- `GET /` - Main dashboard
- `POST /api/analyze` - Perform analysis
- `GET /api/summary` - Get analysis summary
- `GET /api/market-data` - Get current market data
- `GET /api/health` - Health check
- `GET /api/config` - Get configuration

## 📈 Example Output

```
================================================================================
📈 FINANCIAL ANALYSIS REPORT - AAPL
================================================================================

🎯 FINAL RECOMMENDATION: BUY
📊 Confidence: 72.5%
⏰ Timing: SOON

💰 MARKET DATA:
   Current Price: $175.43
   Price Change: +2.15%
   Volume Ratio: 1.23x

🔍 COMPONENT ANALYSIS:
   Technical Analysis: BUY (Confidence: 68.2%)
   News Sentiment: BUY (Confidence: 75.1%)
   Earnings Sentiment: NEUTRAL (Confidence: 52.3%)
   Price Momentum: BUY (Confidence: 71.8%)

📈 TECHNICAL INDICATORS:
   SMA: BUY (Strong)
   RSI: BUY (Weak)
   MACD: BUY (Strong)
   BOLLINGER: NEUTRAL (Weak)
   MOMENTUM: BUY (Strong)

📰 NEWS SENTIMENT:
   Articles Analyzed: 15
   Strong BUY: 3
   BUY: 8
   NEUTRAL: 3
   SELL: 1

⏰ Analysis completed at: 2024-01-15T14:30:00
================================================================================
```

## 🛡️ Rate Limiting & Caching

The application includes intelligent rate limiting and caching:

- **API Rate Limiting**: Prevents hitting Yahoo Finance rate limits
- **Data Caching**: Caches price data for 24 hours, news for 6 hours
- **Efficient Updates**: Only fetches new data when needed
- **Error Handling**: Graceful handling of API failures

## 🔍 Monitoring & Logging

- **Comprehensive Logging**: All activities logged to `logs/financial_analysis.log`
- **Analysis History**: Saves detailed analysis results for review
- **Performance Metrics**: Tracks analysis accuracy and performance
- **Error Tracking**: Monitors and reports API failures

## 🚨 Important Notes

1. **Free Data Source**: Uses Yahoo Finance (free, no API key required)
2. **Rate Limits**: Respects Yahoo Finance rate limits automatically
3. **Accuracy**: Combines multiple analysis methods for better accuracy
4. **Disclaimer**: This is for educational purposes. Always do your own research before investing.

## 🐛 Troubleshooting

### Common Issues

1. **No data received**: Check internet connection and Yahoo Finance availability
2. **Model loading errors**: Ensure all dependencies are installed correctly
3. **Rate limit errors**: The app handles this automatically, but you may need to wait
4. **Memory issues**: Reduce analysis frequency or clear cached data

### Debug Mode

Run with verbose logging:
```bash
python main.py --verbose
```

## 📝 License

This project is for educational purposes. Please ensure compliance with Yahoo Finance's terms of service.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

**Disclaimer**: This application is for educational and research purposes only. It should not be considered as financial advice. Always conduct your own research and consult with financial professionals before making investment decisions.
