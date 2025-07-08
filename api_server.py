from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
import time
import json
from datetime import datetime, timedelta
import asyncio

from config import config
from main_analyzer import MainAnalyzer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Financial Analysis API",
    description="Comprehensive stock analysis API with technical, fundamental, and sentiment analysis",
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

# Initialize main analyzer
analyzer = MainAnalyzer()

# Rate limiting
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.max_requests = 100  # requests per hour
        self.window = 3600  # 1 hour in seconds
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the window
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if now - req_time < self.window
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True
        
        return False

rate_limiter = RateLimiter()

# Pydantic models
class AnalysisRequest(BaseModel):
    symbol: str = "AAPL"
    include_retraining: bool = False

class RetrainingRequest(BaseModel):
    test_data: Optional[List[Dict[str, any]]] = None

class AnalysisResponse(BaseModel):
    symbol: str
    recommendation: str
    confidence: float
    current_price: float
    timestamp: str
    technical_signal: str
    fundamental_recommendation: str
    sentiment: str

# Dependency for rate limiting
def check_rate_limit(client_id: str = "default"):
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later."
        )
    return client_id

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Main analysis endpoint
@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(check_rate_limit)
):
    """
    Run comprehensive analysis for a stock symbol.
    
    This endpoint performs technical, fundamental, and sentiment analysis
    to provide trading recommendations.
    """
    try:
        logger.info(f"Analysis request received for {request.symbol}")
        
        # Run comprehensive analysis
        analysis_result = analyzer.run_comprehensive_analysis(request.symbol)
        
        if 'error' in analysis_result:
            raise HTTPException(status_code=500, detail=analysis_result['error'])
        
        # Schedule retraining if requested
        if request.include_retraining:
            background_tasks.add_task(analyzer.retrain_model_if_needed)
        
        # Return analysis summary
        summary = analyzer.get_analysis_summary(request.symbol)
        
        return AnalysisResponse(
            symbol=summary['symbol'],
            recommendation=summary['recommendation'],
            confidence=summary['confidence'],
            current_price=summary['current_price'],
            timestamp=summary['timestamp'],
            technical_signal=summary['technical_signal'],
            fundamental_recommendation=summary['fundamental_recommendation'],
            sentiment=summary['sentiment']
        )
        
    except Exception as e:
        logger.error(f"Error in analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get analysis summary endpoint
@app.get("/summary/{symbol}")
async def get_analysis_summary(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Get the latest analysis summary for a stock symbol."""
    try:
        summary = analyzer.get_analysis_summary(symbol)
        return summary
    except Exception as e:
        logger.error(f"Error getting analysis summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get detailed analysis endpoint
@app.get("/analysis/{symbol}")
async def get_detailed_analysis(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Get detailed analysis results for a stock symbol."""
    try:
        # Run analysis if not already done
        if not analyzer.last_analysis or analyzer.last_analysis.get('symbol') != symbol:
            analyzer.run_comprehensive_analysis(symbol)
        
        if not analyzer.last_analysis:
            raise HTTPException(status_code=404, detail="Analysis not available")
        
        return analyzer.last_analysis
    except Exception as e:
        logger.error(f"Error getting detailed analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Generate trading report endpoint
@app.get("/report/{symbol}")
async def generate_trading_report(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Generate a comprehensive trading report for a stock symbol."""
    try:
        report = analyzer.generate_trading_report(symbol)
        return report
    except Exception as e:
        logger.error(f"Error generating trading report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get analysis history endpoint
@app.get("/history/{symbol}")
async def get_analysis_history(
    symbol: str,
    limit: int = 10,
    client_id: str = Depends(check_rate_limit)
):
    """Get analysis history for a stock symbol."""
    try:
        history = analyzer.get_analysis_history(symbol, limit)
        return {
            "symbol": symbol,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Model retraining endpoint
@app.post("/retrain")
async def retrain_model(
    request: RetrainingRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(check_rate_limit)
):
    """Retrain the FinBERT model if needed."""
    try:
        # Convert test data format if provided
        test_data = None
        if request.test_data:
            test_data = [
                (item['text'], item['label']) 
                for item in request.test_data
            ]
        
        # Run retraining check
        result = analyzer.retrain_model_if_needed(test_data)
        return result
    except Exception as e:
        logger.error(f"Error in model retraining: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get model information endpoint
@app.get("/model/info")
async def get_model_info(client_id: str = Depends(check_rate_limit)):
    """Get information about the current FinBERT model."""
    try:
        model_info = analyzer.finbert_model.get_model_info()
        return model_info
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get current stock price endpoint
@app.get("/price/{symbol}")
async def get_current_price(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Get current stock price and basic information."""
    try:
        price_data = analyzer.data_collector.get_latest_price(symbol)
        return price_data
    except Exception as e:
        logger.error(f"Error getting current price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get technical indicators endpoint
@app.get("/technical/{symbol}")
async def get_technical_indicators(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Get technical indicators for a stock symbol."""
    try:
        stock_data = analyzer.data_collector.get_stock_data(symbol)
        technical_data = analyzer.technical_analyzer.calculate_all_indicators(stock_data)
        
        # Get latest values
        latest = technical_data.iloc[-1] if not technical_data.empty else {}
        
        indicators = {}
        for col in technical_data.columns:
            if col not in ['Open', 'High', 'Low', 'Close', 'Volume']:
                indicators[col] = latest.get(col, 0)
        
        return {
            "symbol": symbol,
            "indicators": indicators,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting technical indicators: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get fundamental metrics endpoint
@app.get("/fundamental/{symbol}")
async def get_fundamental_metrics(
    symbol: str,
    client_id: str = Depends(check_rate_limit)
):
    """Get fundamental metrics for a stock symbol."""
    try:
        fundamental_data = analyzer.data_collector.get_fundamental_data(symbol)
        analysis = analyzer.fundamental_analyzer.analyze_fundamentals(fundamental_data)
        
        return {
            "symbol": symbol,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting fundamental metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Sentiment analysis endpoint
@app.post("/sentiment")
async def analyze_sentiment(
    text: str,
    client_id: str = Depends(check_rate_limit)
):
    """Analyze sentiment of financial text using FinBERT."""
    try:
        result = analyzer.finbert_model.classify_sentiment(text)
        return {
            "text": text,
            "sentiment": result['sentiment'],
            "confidence": result['confidence'],
            "class_probabilities": result.get('class_probabilities', {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Batch sentiment analysis endpoint
@app.post("/sentiment/batch")
async def analyze_sentiment_batch(
    texts: List[str],
    client_id: str = Depends(check_rate_limit)
):
    """Analyze sentiment of multiple financial texts."""
    try:
        results = analyzer.finbert_model.batch_classify(texts)
        return {
            "texts": texts,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in batch sentiment analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# API statistics endpoint
@app.get("/stats")
async def get_api_stats():
    """Get API usage statistics."""
    try:
        return {
            "total_requests": sum(len(requests) for requests in rate_limiter.requests.values()),
            "active_clients": len(rate_limiter.requests),
            "rate_limit": {
                "max_requests": rate_limiter.max_requests,
                "window_seconds": rate_limiter.window
            },
            "analysis_count": len(analyzer.analysis_history),
            "last_analysis": analyzer.last_analysis['timestamp'] if analyzer.last_analysis else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting API stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Financial Analysis API starting up...")
    
    # Test the analyzer
    try:
        logger.info("Testing analyzer initialization...")
        # This will load the FinBERT model
        test_result = analyzer.finbert_model.classify_sentiment("Test message")
        logger.info("Analyzer initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing analyzer: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Financial Analysis API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)