#!/usr/bin/env python3
"""
Main entry point for the Financial Analysis Application.
This script can run the analysis standalone or start the web server.
"""

import argparse
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any

from config import config
from financial_analyzer import financial_analyzer
from data_collector import data_collector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'{config.LOGS_DIR}/financial_analysis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_analysis_results(analysis: Dict[str, Any]):
    """Print analysis results in a formatted way."""
    print("\n" + "="*80)
    print(f"📈 FINANCIAL ANALYSIS REPORT - {config.STOCK_SYMBOL}")
    print("="*80)
    
    # Main recommendation
    recommendation = analysis.get('final_recommendation', 'NEUTRAL')
    confidence = analysis.get('confidence', 0.0) * 100
    timing = analysis.get('timing', 'MONITOR')
    
    print(f"\n🎯 FINAL RECOMMENDATION: {recommendation}")
    print(f"📊 Confidence: {confidence:.1f}%")
    print(f"⏰ Timing: {timing}")
    
    # Market data
    market_data = analysis.get('market_data', {})
    if market_data and 'error' not in market_data:
        print(f"\n💰 MARKET DATA:")
        print(f"   Current Price: ${market_data.get('current_price', 0):.2f}")
        print(f"   Price Change: {market_data.get('price_change_percent', 0):+.2f}%")
        print(f"   Volume Ratio: {market_data.get('volume_ratio', 0):.2f}x")
    
    # Component analysis
    component_analysis = analysis.get('component_analysis', {})
    if component_analysis:
        print(f"\n🔍 COMPONENT ANALYSIS:")
        
        technical = component_analysis.get('technical', {})
        if technical:
            print(f"   Technical Analysis: {technical.get('signal', 'NEUTRAL')} "
                  f"(Confidence: {technical.get('confidence', 0)*100:.1f}%)")
        
        news_sentiment = component_analysis.get('news_sentiment', {})
        if news_sentiment:
            print(f"   News Sentiment: {news_sentiment.get('signal', 'NEUTRAL')} "
                  f"(Confidence: {news_sentiment.get('confidence', 0)*100:.1f}%)")
        
        earnings_sentiment = component_analysis.get('earnings_sentiment', {})
        if earnings_sentiment:
            print(f"   Earnings Sentiment: {earnings_sentiment.get('signal', 'NEUTRAL')} "
                  f"(Confidence: {earnings_sentiment.get('confidence', 0)*100:.1f}%)")
        
        price_momentum = component_analysis.get('price_momentum', {})
        if price_momentum:
            print(f"   Price Momentum: {price_momentum.get('signal', 'NEUTRAL')} "
                  f"(Confidence: {price_momentum.get('confidence', 0)*100:.1f}%)")
    
    # Technical analysis details
    technical_analysis = analysis.get('technical_analysis', {})
    if technical_analysis and 'signals' in technical_analysis:
        print(f"\n📈 TECHNICAL INDICATORS:")
        signals = technical_analysis['signals']
        
        for indicator, signal_data in signals.items():
            signal = signal_data.get('signal', 'NEUTRAL')
            strength = signal_data.get('strength', 'Weak')
            print(f"   {indicator.upper()}: {signal} ({strength})")
    
    # Sentiment analysis details
    sentiment_analysis = analysis.get('sentiment_analysis', {})
    if sentiment_analysis:
        news_sentiment = sentiment_analysis.get('news_sentiment', {})
        if news_sentiment:
            print(f"\n📰 NEWS SENTIMENT:")
            print(f"   Articles Analyzed: {news_sentiment.get('article_count', 0)}")
            distribution = news_sentiment.get('sentiment_distribution', {})
            for sentiment, count in distribution.items():
                if count > 0:
                    print(f"   {sentiment}: {count}")
    
    print(f"\n⏰ Analysis completed at: {analysis.get('analysis_timestamp', 'Unknown')}")
    print("="*80)

def run_standalone_analysis():
    """Run a single analysis and display results."""
    try:
        logger.info(f"Starting standalone analysis for {config.STOCK_SYMBOL}")
        
        # Perform complete analysis
        analysis_result = financial_analyzer.perform_complete_analysis()
        
        if 'error' in analysis_result:
            logger.error(f"Analysis failed: {analysis_result['error']}")
            print(f"❌ Analysis failed: {analysis_result['error']}")
            return False
        
        # Print results
        print_analysis_results(analysis_result)
        
        # Save detailed results to file
        output_file = f"{config.DATA_DIR}/{config.STOCK_SYMBOL}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        
        logger.info(f"Analysis results saved to {output_file}")
        print(f"\n💾 Detailed results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in standalone analysis: {e}")
        print(f"❌ Error: {e}")
        return False

def run_continuous_monitoring(interval_minutes: int = 60):
    """Run continuous monitoring with periodic analysis."""
    import time
    import schedule
    
    logger.info(f"Starting continuous monitoring for {config.STOCK_SYMBOL} every {interval_minutes} minutes")
    print(f"🔄 Starting continuous monitoring for {config.STOCK_SYMBOL}")
    print(f"⏰ Analysis interval: {interval_minutes} minutes")
    print("Press Ctrl+C to stop\n")
    
    def run_analysis():
        print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running analysis...")
        success = run_standalone_analysis()
        if success:
            print("✅ Analysis completed successfully\n")
        else:
            print("❌ Analysis failed\n")
    
    # Schedule the analysis
    schedule.every(interval_minutes).minutes.do(run_analysis)
    
    # Run initial analysis
    run_analysis()
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
        logger.info("Continuous monitoring stopped by user")

def show_summary():
    """Show analysis summary."""
    try:
        summary = financial_analyzer.get_analysis_summary()
        
        print("\n" + "="*60)
        print(f"📊 ANALYSIS SUMMARY - {config.STOCK_SYMBOL}")
        print("="*60)
        
        if 'message' in summary:
            print(f"\n{summary['message']}")
            return
        
        print(f"\n📈 Total Analyses: {summary.get('total_analyses', 0)}")
        print(f"🕐 Recent Analyses: {summary.get('recent_analyses', 0)}")
        print(f"📊 Average Confidence: {summary.get('average_confidence', 0)*100:.1f}%")
        print(f"🎯 Latest Recommendation: {summary.get('latest_recommendation', 'NEUTRAL')}")
        print(f"📊 Latest Confidence: {summary.get('latest_confidence', 0)*100:.1f}%")
        
        distribution = summary.get('recommendation_distribution', {})
        if distribution:
            print(f"\n📊 Recent Recommendation Distribution:")
            for recommendation, count in distribution.items():
                print(f"   {recommendation}: {count}")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error showing summary: {e}")
        print(f"❌ Error showing summary: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Financial Analysis Application using Yahoo Finance and FinBERT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run single analysis
  python main.py --continuous       # Run continuous monitoring
  python main.py --monitor 30       # Monitor every 30 minutes
  python main.py --summary          # Show analysis summary
  python main.py --server           # Start web server
        """
    )
    
    parser.add_argument(
        '--continuous', 
        action='store_true',
        help='Run continuous monitoring'
    )
    
    parser.add_argument(
        '--monitor',
        type=int,
        metavar='MINUTES',
        help='Run continuous monitoring with custom interval (minutes)'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show analysis summary'
    )
    
    parser.add_argument(
        '--server',
        action='store_true',
        help='Start web server'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ensure directories exist
    config.create_directories()
    
    try:
        if args.server:
            # Start web server
            logger.info("Starting web server...")
            print("🌐 Starting web server...")
            print("📱 Open your browser to: http://localhost:8000")
            print("🛑 Press Ctrl+C to stop the server\n")
            
            import uvicorn
            uvicorn.run(
                "api_server:app",
                host="0.0.0.0",
                port=8000,
                reload=False,
                log_level="info"
            )
            
        elif args.summary:
            # Show summary
            show_summary()
            
        elif args.continuous or args.monitor:
            # Run continuous monitoring
            interval = args.monitor if args.monitor else 60
            run_continuous_monitoring(interval)
            
        else:
            # Run single analysis
            success = run_standalone_analysis()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()