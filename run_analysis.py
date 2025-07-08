#!/usr/bin/env python3
"""
Financial Analysis Application Runner

This script demonstrates the capabilities of the comprehensive financial analysis system
for Apple (AAPL) stock with technical, fundamental, and sentiment analysis.
"""

import json
import logging
from datetime import datetime
from main_analyzer import MainAnalyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the financial analysis."""
    print("=" * 80)
    print("🚀 FINANCIAL ANALYSIS APPLICATION - APPLE (AAPL) STOCK")
    print("=" * 80)
    print()
    
    try:
        # Initialize the main analyzer
        print("📊 Initializing Financial Analysis System...")
        analyzer = MainAnalyzer()
        print("✅ System initialized successfully!")
        print()
        
        # Run comprehensive analysis
        print("🔍 Running Comprehensive Analysis for AAPL...")
        print("-" * 60)
        
        analysis_result = analyzer.run_comprehensive_analysis("AAPL")
        
        if 'error' in analysis_result:
            print(f"❌ Error during analysis: {analysis_result['error']}")
            return
        
        # Display results
        print("📈 ANALYSIS RESULTS")
        print("=" * 60)
        
        # Executive Summary
        print(f"📋 SYMBOL: {analysis_result['symbol']}")
        print(f"💰 CURRENT PRICE: ${analysis_result['current_price']:.2f}")
        print(f"🎯 RECOMMENDATION: {analysis_result['final_recommendation']}")
        print(f"🎚️  CONFIDENCE: {analysis_result['confidence']:.2%}")
        print(f"⏰ TIMESTAMP: {analysis_result['timestamp']}")
        print()
        
        # Technical Analysis
        print("📊 TECHNICAL ANALYSIS")
        print("-" * 30)
        tech_analysis = analysis_result['technical_analysis']
        print(f"Signal: {tech_analysis['signal']}")
        print(f"Confidence: {tech_analysis['confidence']:.2%}")
        print(f"Score: {tech_analysis['score']:.2f}")
        
        # Show key technical indicators
        tech_summary = tech_analysis['summary']
        if 'technical_indicators' in tech_summary:
            indicators = tech_summary['technical_indicators']
            print(f"RSI: {indicators.get('rsi', 'N/A'):.2f}")
            print(f"MACD: {indicators.get('macd', 'N/A'):.4f}")
            print(f"Bollinger Position: {indicators.get('bollinger_position', 'N/A'):.2f}")
        print()
        
        # Fundamental Analysis
        print("🏢 FUNDAMENTAL ANALYSIS")
        print("-" * 30)
        fund_analysis = analysis_result['fundamental_analysis']
        print(f"Recommendation: {fund_analysis['recommendation']}")
        print(f"Score: {fund_analysis['score']:.1f}/100")
        print(f"Confidence: {fund_analysis['confidence']:.2%}")
        
        # Show key fundamental metrics
        fund_details = fund_analysis['details']
        if 'valuation_metrics' in fund_details:
            valuation = fund_details['valuation_metrics']
            print(f"P/E Ratio: {valuation.get('pe_ratio', 'N/A'):.2f}")
            print(f"P/B Ratio: {valuation.get('pb_ratio', 'N/A'):.2f}")
            print(f"Dividend Yield: {valuation.get('dividend_yield', 0):.2%}")
        print()
        
        # Sentiment Analysis
        print("💭 SENTIMENT ANALYSIS")
        print("-" * 30)
        sent_analysis = analysis_result['sentiment_analysis']
        print(f"Overall Sentiment: {sent_analysis['sentiment']}")
        print(f"Confidence: {sent_analysis['confidence']:.2%}")
        print(f"Score: {sent_analysis['score']:.2f}")
        print()
        
        # Generate and display trading report
        print("📋 GENERATING TRADING REPORT...")
        print("-" * 60)
        
        trading_report = analyzer.generate_trading_report("AAPL")
        
        if 'error' not in trading_report:
            # Executive Summary
            exec_summary = trading_report['executive_summary']
            print("🎯 EXECUTIVE SUMMARY")
            print(f"Recommendation: {exec_summary['recommendation']}")
            print(f"Confidence: {exec_summary['confidence']:.2%}")
            print()
            
            # Trading Advice
            advice = trading_report['trading_advice']
            print("💡 TRADING ADVICE")
            print(f"Action: {advice['action']}")
            print(f"Confidence Level: {advice['confidence_level']}")
            print(f"Timing: {advice['timing']}")
            print(f"Position Size: {advice['position_size']}")
            print(f"Stop Loss: ${advice['stop_loss']:.2f}")
            print(f"Target Price: ${advice['target_price']:.2f}")
            print()
            
            # Risk Assessment
            risk_assessment = trading_report['risk_assessment']
            print("⚠️  RISK ASSESSMENT")
            print(f"Risk Level: {risk_assessment['risk_level']}")
            print("Key Risks:")
            for risk in risk_assessment['key_risks']:
                print(f"  • {risk}")
            print("Risk Mitigation:")
            for mitigation in risk_assessment['risk_mitigation']:
                print(f"  • {mitigation}")
            print()
            
            # Next Steps
            print("📝 NEXT STEPS")
            for i, step in enumerate(trading_report['next_steps'], 1):
                print(f"{i}. {step}")
            print()
        
        # Model Information
        print("🤖 MODEL INFORMATION")
        print("-" * 30)
        model_info = analyzer.finbert_model.get_model_info()
        print(f"Model: {model_info['model_name']}")
        print(f"Device: {model_info['device']}")
        print(f"Training History: {model_info['training_history_length']} sessions")
        if model_info['average_accuracy'] > 0:
            print(f"Average Accuracy: {model_info['average_accuracy']:.2%}")
        print()
        
        # Check if model retraining is needed
        print("🔄 CHECKING MODEL PERFORMANCE...")
        retrain_result = analyzer.retrain_model_if_needed()
        
        if retrain_result['retraining_performed']:
            print("✅ Model retraining completed!")
            print(f"Old Accuracy: {retrain_result['old_accuracy']:.2%}")
            print(f"New Accuracy: {retrain_result['new_accuracy']:.2%}")
            print(f"Improvement: {retrain_result['improvement']:.2%}")
        else:
            print("ℹ️  Model accuracy is acceptable. No retraining needed.")
            if 'current_accuracy' in retrain_result:
                print(f"Current Accuracy: {retrain_result['current_accuracy']:.2%}")
        print()
        
        # Save results to file
        print("💾 SAVING RESULTS...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'analysis': analysis_result,
                'trading_report': trading_report,
                'model_info': model_info,
                'retrain_result': retrain_result
            }, f, indent=2, default=str)
        
        print(f"✅ Results saved to {filename}")
        print()
        
        # Final summary
        print("=" * 80)
        print("🎉 ANALYSIS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📊 SUMMARY:")
        print(f"• Stock: {analysis_result['symbol']}")
        print(f"• Price: ${analysis_result['current_price']:.2f}")
        print(f"• Recommendation: {analysis_result['final_recommendation']}")
        print(f"• Confidence: {analysis_result['confidence']:.2%}")
        print(f"• Technical Signal: {tech_analysis['signal']}")
        print(f"• Fundamental Score: {fund_analysis['score']:.1f}/100")
        print(f"• Sentiment: {sent_analysis['sentiment']}")
        print()
        print("🚀 Ready to make informed trading decisions!")
        print()
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"❌ Error: {str(e)}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    main()