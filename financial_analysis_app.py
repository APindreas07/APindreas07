#!/usr/bin/env python3
"""
Enhanced Financial Analysis Application
Combines Yahoo Finance data, improved FinBERT sentiment analysis, and technical analysis
to provide comprehensive buy/sell recommendations with timing for AAPL stock.
"""

import json
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

from recommendation_engine import RecommendationEngine
from data_collector import DataCollector
from enhanced_sentiment_analyzer import EnhancedSentimentAnalyzer
from technical_analyzer import TechnicalAnalyzer

class FinancialAnalysisApp:
    """Main application class for comprehensive financial analysis."""
    
    def __init__(self, symbol: str = "AAPL", verbose: bool = False):
        self.symbol = symbol.upper()
        self.verbose = verbose
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize recommendation engine
        try:
            self.recommendation_engine = RecommendationEngine(symbol)
            self.logger.info(f"Initialized financial analysis for {self.symbol}")
        except Exception as e:
            self.logger.error(f"Failed to initialize recommendation engine: {e}")
            raise
    
    def run_full_analysis(self) -> Dict:
        """Run comprehensive analysis and return results."""
        self.logger.info(f"Starting full analysis for {self.symbol}")
        
        try:
            # Generate comprehensive analysis
            analysis = self.recommendation_engine.generate_comprehensive_analysis()
            
            if analysis.get('error'):
                self.logger.error(f"Analysis failed: {analysis.get('error_message')}")
                return analysis
            
            # Log key metrics
            self._log_key_metrics(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
            return {
                'error': True,
                'error_message': str(e),
                'symbol': self.symbol,
                'timestamp': datetime.now().isoformat()
            }
    
    def _log_key_metrics(self, analysis: Dict):
        """Log key metrics for monitoring."""
        rec = analysis.get('recommendation', {})
        tech = analysis.get('technical_analysis', {})
        sent = analysis.get('sentiment_analysis', {})
        
        self.logger.info(f"=== ANALYSIS SUMMARY for {self.symbol} ===")
        self.logger.info(f"Recommendation: {rec.get('recommendation', 'N/A')} ({rec.get('confidence', 'N/A')} confidence)")
        self.logger.info(f"Current Price: ${analysis.get('current_price', 'N/A'):.2f}")
        self.logger.info(f"Technical Score: {tech.get('technical_score', {}).get('score', 'N/A'):.3f}")
        self.logger.info(f"Sentiment: {sent.get('overall_sentiment', 'N/A')} from {sent.get('article_count', 0)} articles")
        self.logger.info(f"Risk Level: {analysis.get('risk_assessment', {}).get('risk_level', 'N/A')}")
        
        # API usage
        api_stats = analysis.get('api_usage', {})
        self.logger.info(f"API Usage: {api_stats.get('calls_today', 0)}/{api_stats.get('max_daily_calls', 1000)} calls")
    
    def get_quick_recommendation(self) -> str:
        """Get a quick recommendation."""
        return self.recommendation_engine.get_quick_recommendation()
    
    def display_analysis(self, analysis: Dict, format_type: str = "detailed"):
        """Display analysis results in various formats."""
        if analysis.get('error'):
            print(f"❌ Error: {analysis.get('error_message', 'Unknown error')}")
            return
        
        if format_type == "quick":
            self._display_quick_summary(analysis)
        elif format_type == "detailed":
            self._display_detailed_analysis(analysis)
        elif format_type == "json":
            print(json.dumps(analysis, indent=2, default=str))
        else:
            self._display_quick_summary(analysis)
    
    def _display_quick_summary(self, analysis: Dict):
        """Display a quick summary of the analysis."""
        rec = analysis.get('recommendation', {})
        timing = analysis.get('timing_analysis', {})
        risk = analysis.get('risk_assessment', {})
        
        print(f"\n🔍 FINANCIAL ANALYSIS for {self.symbol}")
        print(f"📊 Current Price: ${analysis.get('current_price', 0):.2f}")
        print(f"📈 Recommendation: {rec.get('recommendation', 'N/A')} ({rec.get('confidence', 'N/A')} confidence)")
        print(f"⚠️  Risk Level: {risk.get('risk_level', 'N/A')}")
        print(f"⏰ Best Action Time: {timing.get('recommended_action_time', 'N/A')}")
        
        # Key reasoning
        reasoning = rec.get('reasoning', [])
        if reasoning:
            print(f"\n📝 Key Points:")
            for i, reason in enumerate(reasoning[:3], 1):
                print(f"   {i}. {reason}")
    
    def _display_detailed_analysis(self, analysis: Dict):
        """Display detailed analysis results."""
        print(f"\n{'='*60}")
        print(f"🔍 COMPREHENSIVE FINANCIAL ANALYSIS for {self.symbol}")
        print(f"📅 Generated: {analysis.get('timestamp', 'N/A')}")
        print(f"{'='*60}")
        
        # Main recommendation
        rec = analysis.get('recommendation', {})
        print(f"\n📈 FINAL RECOMMENDATION")
        print(f"   Decision: {rec.get('recommendation', 'N/A')}")
        print(f"   Confidence: {rec.get('confidence', 'N/A')}")
        print(f"   Score: {rec.get('final_score', 0):.3f}/1.000")
        print(f"   Agreement: {rec.get('agreement_score', 0):.3f}/1.000")
        
        # Component scores
        scores = rec.get('component_scores', {})
        print(f"\n📊 COMPONENT ANALYSIS")
        print(f"   Technical: {scores.get('technical', 0):.3f}")
        print(f"   Sentiment: {scores.get('sentiment', 0):.3f}")
        print(f"   Fundamental: {scores.get('fundamental', 0):.3f}")
        
        # Technical analysis
        tech = analysis.get('technical_analysis', {})
        print(f"\n🔧 TECHNICAL ANALYSIS")
        print(f"   Trend: {tech.get('trend', 'N/A')} (strength: {tech.get('trend_strength', 0):.3f})")
        print(f"   RSI: {tech.get('momentum', {}).get('rsi', 'N/A'):.1f}")
        print(f"   Price Change (1d): {tech.get('price_change_1d', 0)*100:+.2f}%")
        print(f"   Price Change (5d): {tech.get('price_change_5d', 0)*100:+.2f}%")
        
        # Sentiment analysis
        sent = analysis.get('sentiment_analysis', {})
        print(f"\n💭 SENTIMENT ANALYSIS")
        print(f"   Overall: {sent.get('overall_sentiment', 'N/A')}")
        print(f"   Confidence: {sent.get('confidence', 0):.3f}")
        print(f"   Articles Analyzed: {sent.get('article_count', 0)}")
        
        dist = sent.get('sentiment_distribution', {})
        if dist:
            print(f"   Distribution: Positive {dist.get('positive', 0)*100:.1f}% | "
                  f"Negative {dist.get('negative', 0)*100:.1f}% | "
                  f"Neutral {dist.get('neutral', 0)*100:.1f}%")
        
        # Risk assessment
        risk = analysis.get('risk_assessment', {})
        print(f"\n⚠️  RISK ASSESSMENT")
        print(f"   Risk Level: {risk.get('risk_level', 'N/A')}")
        print(f"   Risk Score: {risk.get('risk_score', 0):.3f}")
        
        risk_factors = risk.get('risk_factors', [])
        if risk_factors:
            print(f"   Risk Factors:")
            for factor in risk_factors:
                print(f"     • {factor}")
        
        # Position sizing
        position = analysis.get('position_sizing', {})
        print(f"\n💰 POSITION SIZING")
        print(f"   Recommended: {position.get('recommended_position_percent', 0):.1f}% of portfolio")
        print(f"   Risk Adjusted: {position.get('risk_adjusted', False)}")
        
        # Timing analysis
        timing = analysis.get('timing_analysis', {})
        print(f"\n⏰ TIMING ANALYSIS")
        print(f"   Market Open: {timing.get('is_market_hours', False)}")
        print(f"   Volume Factor: {timing.get('volume_factor', 1.0):.2f}x average")
        print(f"   Recommended Time: {timing.get('recommended_action_time', 'N/A')}")
        
        # Entry/Exit signals
        entry_signals = timing.get('entry_signals', [])
        exit_signals = timing.get('exit_signals', [])
        
        if entry_signals:
            print(f"\n📥 ENTRY SIGNALS")
            for signal in entry_signals:
                print(f"   {signal.get('action', 'N/A')}: {signal.get('reason', 'N/A')} "
                      f"(confidence: {signal.get('confidence', 0):.3f})")
        
        if exit_signals:
            print(f"\n📤 EXIT SIGNALS")
            for signal in exit_signals:
                print(f"   {signal.get('action', 'N/A')}: {signal.get('reason', 'N/A')}")
        
        # Reasoning
        reasoning = rec.get('reasoning', [])
        if reasoning:
            print(f"\n📝 REASONING")
            for i, reason in enumerate(reasoning, 1):
                print(f"   {i}. {reason}")
        
        # API and model stats
        api_stats = analysis.get('api_usage', {})
        model_stats = analysis.get('model_performance', {})
        
        print(f"\n📡 SYSTEM STATUS")
        print(f"   API Calls Today: {api_stats.get('calls_today', 0)}/{api_stats.get('max_daily_calls', 1000)}")
        print(f"   Model Accuracy: {model_stats.get('current_accuracy', 'N/A')}")
        print(f"   Performance Trend: {model_stats.get('performance_trend', 'N/A')}")
    
    def monitor_continuous(self, interval_hours: int = 6):
        """Monitor stock continuously with specified interval."""
        import time
        
        self.logger.info(f"Starting continuous monitoring for {self.symbol} (interval: {interval_hours}h)")
        
        try:
            while True:
                # Run analysis
                analysis = self.run_full_analysis()
                
                # Display quick summary
                self._display_quick_summary(analysis)
                
                # Check for significant changes or alerts
                self._check_alerts(analysis)
                
                # Wait for next interval
                self.logger.info(f"Sleeping for {interval_hours} hours...")
                time.sleep(interval_hours * 3600)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Error in continuous monitoring: {e}")
    
    def _check_alerts(self, analysis: Dict):
        """Check for important alerts and notifications."""
        if analysis.get('error'):
            return
        
        alerts = []
        
        # High confidence recommendations
        rec = analysis.get('recommendation', {})
        if rec.get('confidence') == 'HIGH':
            alerts.append(f"🚨 HIGH CONFIDENCE {rec.get('recommendation', 'N/A')} signal!")
        
        # Extreme RSI
        rsi = analysis.get('technical_analysis', {}).get('momentum', {}).get('rsi', 50)
        if rsi > 80:
            alerts.append(f"⚠️  Extremely overbought (RSI: {rsi:.1f})")
        elif rsi < 20:
            alerts.append(f"⚠️  Extremely oversold (RSI: {rsi:.1f})")
        
        # High volatility
        risk = analysis.get('risk_assessment', {})
        if risk.get('risk_level') == 'HIGH':
            alerts.append(f"⚠️  HIGH RISK conditions detected")
        
        # API usage alerts
        api_stats = analysis.get('api_usage', {})
        usage_pct = api_stats.get('usage_percentage', 0)
        if usage_pct > 80:
            alerts.append(f"📡 API usage at {usage_pct:.1f}% - approaching limit")
        
        # Print alerts
        for alert in alerts:
            print(f"\n{alert}")
            self.logger.warning(alert)

def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(
        description="Enhanced Financial Analysis Application with FinBERT and Technical Analysis"
    )
    
    parser.add_argument(
        '--symbol', '-s',
        default='AAPL',
        help='Stock symbol to analyze (default: AAPL)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['quick', 'detailed', 'json'],
        default='detailed',
        help='Output format (default: detailed)'
    )
    
    parser.add_argument(
        '--monitor', '-m',
        action='store_true',
        help='Enable continuous monitoring mode'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=6,
        help='Monitoring interval in hours (default: 6)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Get quick recommendation only'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize application
        app = FinancialAnalysisApp(symbol=args.symbol, verbose=args.verbose)
        
        if args.quick:
            # Quick recommendation
            rec = app.get_quick_recommendation()
            print(f"{args.symbol}: {rec}")
            
        elif args.monitor:
            # Continuous monitoring
            app.monitor_continuous(interval_hours=args.interval)
            
        else:
            # Single analysis
            analysis = app.run_full_analysis()
            app.display_analysis(analysis, format_type=args.format)
    
    except KeyboardInterrupt:
        print("\n👋 Analysis interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()