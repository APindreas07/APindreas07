#!/usr/bin/env python3
"""
Test script for the Enhanced Financial Analysis Application
Verifies all components work correctly with sample data.
"""

import sys
import logging
from datetime import datetime
import traceback

def test_data_collector():
    """Test the data collection functionality."""
    print("Testing Data Collector...")
    try:
        from data_collector import DataCollector
        
        collector = DataCollector("AAPL")
        
        # Test stock data collection
        price_data = collector.get_stock_data(period="1mo")
        print(f"✅ Stock data: {len(price_data)} days retrieved")
        
        # Test news data collection
        news_data = collector.get_news_sentiment_data()
        print(f"✅ News data: {len(news_data)} articles retrieved")
        
        # Test company info
        company_info = collector.get_company_info()
        print(f"✅ Company info: {len(company_info)} fields retrieved")
        
        # Test API usage stats
        api_stats = collector.get_api_usage_stats()
        print(f"✅ API stats: {api_stats['calls_today']} calls used today")
        
        return True
    except Exception as e:
        print(f"❌ Data Collector failed: {e}")
        return False

def test_sentiment_analyzer():
    """Test the sentiment analysis functionality."""
    print("\nTesting Enhanced Sentiment Analyzer...")
    try:
        from enhanced_sentiment_analyzer import EnhancedSentimentAnalyzer
        
        analyzer = EnhancedSentimentAnalyzer()
        
        # Test individual sentiment analysis
        test_texts = [
            "Apple reports record quarterly revenue and strong iPhone sales",
            "Concerns about supply chain disruptions affecting Apple production",
            "Neutral market conditions with mixed analyst opinions"
        ]
        
        for i, text in enumerate(test_texts):
            result = analyzer.ensemble_analyze(text)
            sentiment = analyzer.classify_investment_sentiment(text)
            print(f"✅ Text {i+1}: {sentiment} (confidence: {result['confidence']:.3f})")
        
        # Test news batch analysis
        sample_news = [
            {"title": "Apple hits new record high", "summary": "Strong earnings drive stock price up"},
            {"title": "Tech selloff continues", "summary": "Market volatility affects major tech stocks"}
        ]
        
        batch_result = analyzer.analyze_news_batch(sample_news)
        print(f"✅ News batch analysis: {batch_result['overall_sentiment']}")
        
        # Test model stats
        stats = analyzer.get_model_stats()
        print(f"✅ Model stats retrieved: {stats['total_evaluations']} evaluations")
        
        return True
    except Exception as e:
        print(f"❌ Sentiment Analyzer failed: {e}")
        traceback.print_exc()
        return False

def test_technical_analyzer():
    """Test the technical analysis functionality."""
    print("\nTesting Technical Analyzer...")
    try:
        from technical_analyzer import TechnicalAnalyzer
        from data_collector import DataCollector
        
        analyzer = TechnicalAnalyzer()
        collector = DataCollector("AAPL")
        
        # Get some price data
        price_data = collector.get_stock_data(period="3mo")
        
        if price_data.empty:
            print("⚠️  No price data available for technical analysis")
            return False
        
        # Test price action analysis
        analysis = analyzer.analyze_price_action(price_data)
        print(f"✅ Technical analysis: {analysis['technical_score']['recommendation']}")
        print(f"✅ Trend: {analysis['trend']} (strength: {analysis['trend_strength']:.3f})")
        print(f"✅ RSI: {analysis['momentum']['rsi']:.1f}")
        
        # Test entry/exit signals
        signals = analyzer.generate_entry_exit_signals(price_data)
        print(f"✅ Entry signals: {len(signals['entry_signals'])}")
        print(f"✅ Exit signals: {len(signals['exit_signals'])}")
        
        return True
    except Exception as e:
        print(f"❌ Technical Analyzer failed: {e}")
        traceback.print_exc()
        return False

def test_recommendation_engine():
    """Test the recommendation engine functionality."""
    print("\nTesting Recommendation Engine...")
    try:
        from recommendation_engine import RecommendationEngine
        
        engine = RecommendationEngine("AAPL")
        
        # Test quick recommendation
        quick_rec = engine.get_quick_recommendation()
        print(f"✅ Quick recommendation: {quick_rec}")
        
        # Test comprehensive analysis (this might take a moment)
        print("   Running comprehensive analysis...")
        analysis = engine.generate_comprehensive_analysis()
        
        if analysis.get('error'):
            print(f"❌ Analysis error: {analysis.get('error_message')}")
            return False
        
        rec = analysis.get('recommendation', {})
        print(f"✅ Comprehensive analysis: {rec.get('recommendation')} ({rec.get('confidence')} confidence)")
        print(f"✅ Final score: {rec.get('final_score', 0):.3f}")
        print(f"✅ Agreement score: {rec.get('agreement_score', 0):.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Recommendation Engine failed: {e}")
        traceback.print_exc()
        return False

def test_main_application():
    """Test the main application interface."""
    print("\nTesting Main Application...")
    try:
        from financial_analysis_app import FinancialAnalysisApp
        
        app = FinancialAnalysisApp("AAPL", verbose=False)
        
        # Test quick recommendation
        quick_rec = app.get_quick_recommendation()
        print(f"✅ App quick recommendation: {quick_rec}")
        
        # Test full analysis
        print("   Running full analysis...")
        analysis = app.run_full_analysis()
        
        if analysis.get('error'):
            print(f"❌ App analysis error: {analysis.get('error_message')}")
            return False
        
        print(f"✅ App analysis successful: {analysis['recommendation']['recommendation']}")
        
        return True
    except Exception as e:
        print(f"❌ Main Application failed: {e}")
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("🚀 Starting Enhanced Financial Analysis Application Tests")
    print("=" * 60)
    
    tests = [
        ("Data Collector", test_data_collector),
        ("Sentiment Analyzer", test_sentiment_analyzer),
        ("Technical Analyzer", test_technical_analyzer),
        ("Recommendation Engine", test_recommendation_engine),
        ("Main Application", test_main_application)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        return False

if __name__ == "__main__":
    # Reduce logging noise during testing
    logging.getLogger().setLevel(logging.WARNING)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)