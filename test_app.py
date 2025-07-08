#!/usr/bin/env python3
"""
Test script for the Financial Analysis Application
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
        print("✅ config.py imported successfully")
        
        from data_collector import DataCollector
        print("✅ data_collector.py imported successfully")
        
        from enhanced_finbert import EnhancedFinBERT
        print("✅ enhanced_finbert.py imported successfully")
        
        from technical_analyzer import TechnicalAnalyzer
        print("✅ technical_analyzer.py imported successfully")
        
        from fundamental_analyzer import FundamentalAnalyzer
        print("✅ fundamental_analyzer.py imported successfully")
        
        from main_analyzer import MainAnalyzer
        print("✅ main_analyzer.py imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False

def test_data_collector():
    """Test data collection functionality."""
    print("\n📊 Testing data collector...")
    
    try:
        from data_collector import DataCollector
        
        collector = DataCollector()
        
        # Test getting latest price
        price_data = collector.get_latest_price("AAPL")
        print(f"✅ Latest price data retrieved: ${price_data.get('current_price', 'N/A')}")
        
        # Test getting stock data
        stock_data = collector.get_stock_data("AAPL", period="1mo")
        print(f"✅ Stock data retrieved: {len(stock_data)} data points")
        
        return True
        
    except Exception as e:
        print(f"❌ Data collector error: {str(e)}")
        return False

def test_technical_analyzer():
    """Test technical analysis functionality."""
    print("\n📈 Testing technical analyzer...")
    
    try:
        from technical_analyzer import TechnicalAnalyzer
        from data_collector import DataCollector
        
        collector = DataCollector()
        analyzer = TechnicalAnalyzer()
        
        # Get sample data
        stock_data = collector.get_stock_data("AAPL", period="1mo")
        
        # Calculate indicators
        technical_data = analyzer.calculate_all_indicators(stock_data)
        print(f"✅ Technical indicators calculated: {len(technical_data.columns)} indicators")
        
        # Generate signals
        signals = analyzer.generate_trading_signals(technical_data)
        print(f"✅ Trading signals generated: {signals['overall_signal']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Technical analyzer error: {str(e)}")
        return False

def test_fundamental_analyzer():
    """Test fundamental analysis functionality."""
    print("\n🏢 Testing fundamental analyzer...")
    
    try:
        from fundamental_analyzer import FundamentalAnalyzer
        from data_collector import DataCollector
        
        collector = DataCollector()
        analyzer = FundamentalAnalyzer()
        
        # Get fundamental data
        fundamental_data = collector.get_fundamental_data("AAPL")
        
        # Analyze fundamentals
        analysis = analyzer.analyze_fundamentals(fundamental_data)
        print(f"✅ Fundamental analysis completed: {analysis.get('recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fundamental analyzer error: {str(e)}")
        return False

def test_sentiment_analyzer():
    """Test sentiment analysis functionality."""
    print("\n💭 Testing sentiment analyzer...")
    
    try:
        from enhanced_finbert import EnhancedFinBERT
        
        analyzer = EnhancedFinBERT()
        
        # Test sentiment classification
        test_text = "Apple reports strong quarterly earnings with record revenue growth"
        result = analyzer.classify_sentiment(test_text)
        print(f"✅ Sentiment analysis completed: {result['sentiment']} (confidence: {result['confidence']:.2%})")
        
        return True
        
    except Exception as e:
        print(f"❌ Sentiment analyzer error: {str(e)}")
        return False

def test_main_analyzer():
    """Test main analyzer functionality."""
    print("\n🎯 Testing main analyzer...")
    
    try:
        from main_analyzer import MainAnalyzer
        
        analyzer = MainAnalyzer()
        
        # Test getting analysis summary
        summary = analyzer.get_analysis_summary("AAPL")
        print(f"✅ Analysis summary retrieved: {summary.get('recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Main analyzer error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 FINANCIAL ANALYSIS APPLICATION - TEST SUITE")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Import Test", test_imports),
        ("Data Collector Test", test_data_collector),
        ("Technical Analyzer Test", test_technical_analyzer),
        ("Fundamental Analyzer Test", test_fundamental_analyzer),
        ("Sentiment Analyzer Test", test_sentiment_analyzer),
        ("Main Analyzer Test", test_main_analyzer),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"🔍 Running {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    print()
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Application is ready to use.")
        print("\n🚀 Next steps:")
        print("1. Run 'python run_analysis.py' for command-line analysis")
        print("2. Run 'python api_server.py' to start the API server")
        print("3. Visit http://localhost:8000/docs for API documentation")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()