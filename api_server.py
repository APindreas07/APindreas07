from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import logging
import asyncio
from datetime import datetime
import json

from config import config
from financial_analyzer import financial_analyzer
from data_collector import data_collector

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Financial Analysis API",
    description="Real-time financial analysis using Yahoo Finance data and FinBERT sentiment analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AnalysisRequest(BaseModel):
    symbol: Optional[str] = config.STOCK_SYMBOL
    force_refresh: Optional[bool] = False

class AnalysisResponse(BaseModel):
    symbol: str
    recommendation: str
    confidence: float
    timing: str
    timestamp: str
    market_data: Dict[str, Any]
    technical_analysis: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Financial Analysis Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 30px;
                backdrop-filter: blur(10px);
            }
            h1 {
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .stock-info {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                text-align: center;
            }
            .recommendation {
                font-size: 2em;
                font-weight: bold;
                margin: 20px 0;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .strong-buy { background: rgba(76, 175, 80, 0.8); }
            .buy { background: rgba(139, 195, 74, 0.8); }
            .neutral { background: rgba(255, 152, 0, 0.8); }
            .sell { background: rgba(244, 67, 54, 0.8); }
            .strong-sell { background: rgba(211, 47, 47, 0.8); }
            .metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .metric-card {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                padding: 20px;
                text-align: center;
            }
            .metric-value {
                font-size: 1.5em;
                font-weight: bold;
                margin: 10px 0;
            }
            .btn {
                background: rgba(255, 255, 255, 0.3);
                border: none;
                color: white;
                padding: 15px 30px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1.1em;
                margin: 10px;
                transition: all 0.3s ease;
            }
            .btn:hover {
                background: rgba(255, 255, 255, 0.5);
                transform: translateY(-2px);
            }
            .loading {
                text-align: center;
                font-size: 1.2em;
                margin: 20px 0;
            }
            .error {
                background: rgba(244, 67, 54, 0.8);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📈 Financial Analysis Dashboard</h1>
            <div class="stock-info">
                <h2>${config.STOCK_SYMBOL} - {config.STOCK_NAME}</h2>
                <button class="btn" onclick="performAnalysis()">🔄 Refresh Analysis</button>
                <button class="btn" onclick="getSummary()">📊 View Summary</button>
            </div>
            
            <div id="loading" class="loading" style="display: none;">
                🔄 Analyzing market data and sentiment...
            </div>
            
            <div id="error" class="error" style="display: none;"></div>
            
            <div id="results" style="display: none;">
                <div id="recommendation" class="recommendation"></div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <h3>Current Price</h3>
                        <div id="current-price" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>Price Change</h3>
                        <div id="price-change" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>Confidence</h3>
                        <div id="confidence" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>Timing</h3>
                        <div id="timing" class="metric-value">-</div>
                    </div>
                </div>
                
                <div class="metrics">
                    <div class="metric-card">
                        <h3>Technical Analysis</h3>
                        <div id="technical-signal" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>News Sentiment</h3>
                        <div id="news-sentiment" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>Earnings Sentiment</h3>
                        <div id="earnings-sentiment" class="metric-value">-</div>
                    </div>
                    <div class="metric-card">
                        <h3>Volume Ratio</h3>
                        <div id="volume-ratio" class="metric-value">-</div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            async function performAnalysis() {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';
                document.getElementById('error').style.display = 'none';
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            symbol: '${config.STOCK_SYMBOL}',
                            force_refresh: false
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    displayResults(data);
                } catch (error) {
                    document.getElementById('error').textContent = 'Error: ' + error.message;
                    document.getElementById('error').style.display = 'block';
                } finally {
                    document.getElementById('loading').style.display = 'none';
                }
            }
            
            async function getSummary() {
                try {
                    const response = await fetch('/api/summary');
                    const data = await response.json();
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    
                    alert('Analysis Summary:\\n' +
                          'Total Analyses: ' + data.total_analyses + '\\n' +
                          'Latest Recommendation: ' + data.latest_recommendation + '\\n' +
                          'Average Confidence: ' + (data.average_confidence * 100).toFixed(1) + '%\\n' +
                          'Recent Distribution: ' + JSON.stringify(data.recommendation_distribution, null, 2));
                } catch (error) {
                    alert('Error getting summary: ' + error.message);
                }
            }
            
            function displayResults(data) {
                const recommendation = data.final_recommendation;
                const confidence = (data.confidence * 100).toFixed(1);
                const timing = data.timing;
                
                // Set recommendation with appropriate styling
                const recElement = document.getElementById('recommendation');
                recElement.textContent = recommendation;
                recElement.className = 'recommendation ' + recommendation.toLowerCase().replace(' ', '-');
                
                // Set metrics
                document.getElementById('current-price').textContent = '$' + data.market_data.current_price.toFixed(2);
                document.getElementById('price-change').textContent = 
                    (data.market_data.price_change_percent >= 0 ? '+' : '') + 
                    data.market_data.price_change_percent.toFixed(2) + '%';
                document.getElementById('confidence').textContent = confidence + '%';
                document.getElementById('timing').textContent = timing;
                
                // Set component analysis
                document.getElementById('technical-signal').textContent = 
                    data.component_analysis.technical.signal;
                document.getElementById('news-sentiment').textContent = 
                    data.component_analysis.news_sentiment.signal;
                document.getElementById('earnings-sentiment').textContent = 
                    data.component_analysis.earnings_sentiment.signal;
                document.getElementById('volume-ratio').textContent = 
                    data.market_data.volume_ratio.toFixed(2) + 'x';
                
                document.getElementById('results').style.display = 'block';
            }
            
            // Auto-refresh every 5 minutes
            setInterval(performAnalysis, 300000);
            
            // Initial load
            performAnalysis();
        </script>
    </body>
    </html>
    """

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest):
    """Perform complete financial analysis for a stock."""
    try:
        logger.info(f"Analysis request received for {request.symbol}")
        
        # Perform the analysis
        analysis_result = financial_analyzer.perform_complete_analysis()
        
        if 'error' in analysis_result:
            raise HTTPException(status_code=500, detail=analysis_result['error'])
        
        return AnalysisResponse(
            symbol=request.symbol,
            recommendation=analysis_result['final_recommendation'],
            confidence=analysis_result['confidence'],
            timing=analysis_result['timing'],
            timestamp=analysis_result['analysis_timestamp'],
            market_data=analysis_result['market_data'],
            technical_analysis=analysis_result['technical_analysis'],
            sentiment_analysis=analysis_result['sentiment_analysis']
        )
        
    except Exception as e:
        logger.error(f"Error in analysis endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary")
async def get_analysis_summary():
    """Get summary of recent analyses."""
    try:
        summary = financial_analyzer.get_analysis_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/market-data")
async def get_market_data():
    """Get current market data."""
    try:
        market_data = financial_analyzer.get_current_market_data()
        if 'error' in market_data:
            raise HTTPException(status_code=500, detail=market_data['error'])
        return market_data
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "stock_symbol": config.STOCK_SYMBOL
    }

@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    return {
        "stock_symbol": config.STOCK_SYMBOL,
        "stock_name": config.STOCK_NAME,
        "price_update_interval_hours": config.PRICE_UPDATE_INTERVAL_HOURS,
        "news_update_interval_hours": config.NEWS_UPDATE_INTERVAL_HOURS,
        "max_api_calls_per_minute": config.MAX_API_CALLS_PER_MINUTE
    }

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )