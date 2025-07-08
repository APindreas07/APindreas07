#!/usr/bin/env python3
"""
Test script to verify the financial analysis application components.
"""

import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from config import config
        print("✅ Config imported successfully")
        
        from data_collector import data_collector
        print("✅ Data collector imported successfully")
        
        from technical_analyzer import technical_analyzer
        print("✅ Technical analyzer imported successfully")
        
        from sentiment_analyzer import sentiment_analyzer
        print("✅ Sentiment analyzer imported successfully")
        
        from financial_analyzer import financial_analyzer
        print("✅ Financial analyzer imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_data_collection():
    """Test data collection from Yahoo Finance."""
    print("\n📊 Testing data collection...")
    
    try:
        from data_collector import data_collector
        
        # Test stock data
        stock_data = data_collector.get_stock_data(period="1mo")
        if stock_data is not None and not stock_data.empty:
            print(f"✅ Stock data collected: {len(stock_data)} records")
            print(f"   Latest price: ${stock_data['Close'].iloc[-1]:.2f}")
        else:
            print("❌ Failed to collect stock data")
            return False
        
        # Test stock info
        stock_info = data_collector.get_stock_info()
        if stock_info:
            print(f"✅ Stock info collected: {stock_info.get('longName', 'Unknown')}")
        else:
            print("❌ Failed to collect stock info")
            return False
        
        # Test news (may be empty, that's okay)
        news = data_collector.get_news(limit=5)
        print(f"✅ News collected: {len(news)} articles")
        
        return True
        
    except Exception as e:
        print(f"❌ Data collection error: {e}")
        return False

def test_technical_analysis():
    """Test technical analysis."""
    print("\n📈 Testing technical analysis...")
    
    try:
        from data_collector import data_collector
        from technical_analyzer import technical_analyzer
        
        # Get some data
        stock_data = data_collector.get_stock_data(period="3mo")
        if stock_data is None or stock_data.empty:
            print("❌ No data available for technical analysis")
            return False
        
        # Perform technical analysis
        technical_results = technical_analyzer.analyze_all_indicators(stock_data)
        
        if 'error' in technical_results:
            print(f"❌ Technical analysis error: {technical_results['error']}")
            return False
        
        print(f"✅ Technical analysis completed")
        print(f"   Recommendation: {technical_results.get('recommendation', 'Unknown')}")
        print(f"   Confidence: {technical_results.get('confidence', 0)*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical analysis error: {e}")
        return False

def test_sentiment_analysis():
    """Test sentiment analysis."""
    print("\n🧠 Testing sentiment analysis...")
    
    try:
        from sentiment_analyzer import sentiment_analyzer
        
        # Test with sample text
        test_text = "Apple reported strong quarterly earnings with revenue growth exceeding expectations."
        sentiment_result = sentiment_analyzer.analyze_sentiment(test_text)
        
        print(f"✅ Sentiment analysis completed")
        print(f"   Sentiment: {sentiment_result.get('sentiment', 'Unknown')}")
        print(f"   Signal: {sentiment_result.get('signal', 'Unknown')}")
        print(f"   Confidence: {sentiment_result.get('confidence', 0)*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Sentiment analysis error: {e}")
        return False

def test_full_analysis():
    """Test complete financial analysis."""
    print("\n🎯 Testing complete financial analysis...")
    
    try:
        from financial_analyzer import financial_analyzer
        
        # Perform complete analysis
        analysis_result = financial_analyzer.perform_complete_analysis()
        
        if 'error' in analysis_result:
            print(f"❌ Analysis error: {analysis_result['error']}")
            return False
        
        print(f"✅ Complete analysis completed")
        print(f"   Recommendation: {analysis_result.get('final_recommendation', 'Unknown')}")
        print(f"   Confidence: {analysis_result.get('confidence', 0)*100:.1f}%")
        print(f"   Timing: {analysis_result.get('timing', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete analysis error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Financial Analysis Application Test Suite")
    print("=" * 50)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Testing stock: {config.STOCK_SYMBOL}")
    
    tests = [
        ("Import Test", test_imports),
        ("Data Collection Test", test_data_collection),
        ("Technical Analysis Test", test_technical_analysis),
        ("Sentiment Analysis Test", test_sentiment_analysis),
        ("Complete Analysis Test", test_full_analysis),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        print("\n🚀 You can now run:")
        print("   python main.py                    # Single analysis")
        print("   python main.py --server           # Web dashboard")
        print("   python main.py --continuous       # Continuous monitoring")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        from config import config
        main()
    except ImportError as e:
        print(f"❌ Failed to import config: {e}")
        print("Please ensure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)