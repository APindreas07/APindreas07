import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from config import config

logger = logging.getLogger(__name__)

class FundamentalAnalyzer:
    """Comprehensive fundamental analysis for stock investment decisions."""
    
    def __init__(self):
        self.ratios = {}
        self.industry_averages = {}
        
    def analyze_fundamentals(self, fundamental_data: Dict) -> Dict:
        """Analyze fundamental data and generate investment insights."""
        try:
            analysis = {
                'valuation_metrics': {},
                'profitability_metrics': {},
                'liquidity_metrics': {},
                'efficiency_metrics': {},
                'growth_metrics': {},
                'debt_metrics': {},
                'overall_score': 0.0,
                'recommendation': 'Neutral',
                'timestamp': datetime.now().isoformat()
            }
            
            info = fundamental_data.get('info', {})
            financials = fundamental_data.get('financials', pd.DataFrame())
            balance_sheet = fundamental_data.get('balance_sheet', pd.DataFrame())
            cashflow = fundamental_data.get('cashflow', pd.DataFrame())
            
            # Valuation Analysis
            analysis['valuation_metrics'] = self._analyze_valuation(info, financials)
            
            # Profitability Analysis
            analysis['profitability_metrics'] = self._analyze_profitability(financials, balance_sheet)
            
            # Liquidity Analysis
            analysis['liquidity_metrics'] = self._analyze_liquidity(balance_sheet)
            
            # Efficiency Analysis
            analysis['efficiency_metrics'] = self._analyze_efficiency(financials, balance_sheet)
            
            # Growth Analysis
            analysis['growth_metrics'] = self._analyze_growth(financials, cashflow)
            
            # Debt Analysis
            analysis['debt_metrics'] = self._analyze_debt(balance_sheet, financials)
            
            # Calculate overall score and recommendation
            analysis['overall_score'], analysis['recommendation'] = self._calculate_overall_score(analysis)
            
            logger.info(f"Fundamental analysis completed. Overall score: {analysis['overall_score']:.2f}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis: {str(e)}")
            return {
                'error': str(e),
                'recommendation': 'Neutral',
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_valuation(self, info: Dict, financials: pd.DataFrame) -> Dict:
        """Analyze valuation metrics."""
        valuation = {
            'pe_ratio': info.get('trailingPE', 0),
            'forward_pe': info.get('forwardPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'ps_ratio': info.get('priceToSalesTrailing12Months', 0),
            'ev_ebitda': info.get('enterpriseToEbitda', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'price_to_cash_flow': info.get('priceToCashflow', 0),
            'score': 0.0
        }
        
        # Score based on P/E ratio (lower is better for value)
        if valuation['pe_ratio'] > 0:
            if valuation['pe_ratio'] < 15:
                valuation['score'] += 0.3
            elif valuation['pe_ratio'] < 25:
                valuation['score'] += 0.2
            elif valuation['pe_ratio'] < 35:
                valuation['score'] += 0.1
            else:
                valuation['score'] -= 0.1
        
        # Score based on P/B ratio
        if valuation['pb_ratio'] > 0:
            if valuation['pb_ratio'] < 1.5:
                valuation['score'] += 0.2
            elif valuation['pb_ratio'] < 3:
                valuation['score'] += 0.1
            else:
                valuation['score'] -= 0.1
        
        # Score based on dividend yield
        if valuation['dividend_yield'] > 0.02:  # 2%
            valuation['score'] += 0.2
        elif valuation['dividend_yield'] > 0.01:  # 1%
            valuation['score'] += 0.1
        
        return valuation
    
    def _analyze_profitability(self, financials: pd.DataFrame, balance_sheet: pd.DataFrame) -> Dict:
        """Analyze profitability metrics."""
        profitability = {
            'gross_margin': 0.0,
            'operating_margin': 0.0,
            'net_margin': 0.0,
            'roe': 0.0,
            'roa': 0.0,
            'roic': 0.0,
            'score': 0.0
        }
        
        try:
            if not financials.empty:
                # Calculate margins from income statement
                revenue = financials.loc['Total Revenue'] if 'Total Revenue' in financials.index else pd.Series([0])
                gross_profit = financials.loc['Gross Profit'] if 'Gross Profit' in financials.index else pd.Series([0])
                operating_income = financials.loc['Operating Income'] if 'Operating Income' in financials.index else pd.Series([0])
                net_income = financials.loc['Net Income'] if 'Net Income' in financials.index else pd.Series([0])
                
                # Calculate margins
                if revenue.iloc[0] > 0:
                    profitability['gross_margin'] = (gross_profit.iloc[0] / revenue.iloc[0]) * 100
                    profitability['operating_margin'] = (operating_income.iloc[0] / revenue.iloc[0]) * 100
                    profitability['net_margin'] = (net_income.iloc[0] / revenue.iloc[0]) * 100
                
                # Calculate ROE and ROA
                if not balance_sheet.empty:
                    total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance_sheet.index else 0
                    total_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 0
                    
                    if total_equity > 0:
                        profitability['roe'] = (net_income.iloc[0] / total_equity) * 100
                    if total_assets > 0:
                        profitability['roa'] = (net_income.iloc[0] / total_assets) * 100
                
                # Score based on margins
                if profitability['gross_margin'] > 40:
                    profitability['score'] += 0.3
                elif profitability['gross_margin'] > 30:
                    profitability['score'] += 0.2
                elif profitability['gross_margin'] > 20:
                    profitability['score'] += 0.1
                
                if profitability['operating_margin'] > 15:
                    profitability['score'] += 0.3
                elif profitability['operating_margin'] > 10:
                    profitability['score'] += 0.2
                elif profitability['operating_margin'] > 5:
                    profitability['score'] += 0.1
                
                if profitability['net_margin'] > 10:
                    profitability['score'] += 0.3
                elif profitability['net_margin'] > 5:
                    profitability['score'] += 0.2
                elif profitability['net_margin'] > 2:
                    profitability['score'] += 0.1
                
                # Score based on ROE
                if profitability['roe'] > 15:
                    profitability['score'] += 0.3
                elif profitability['roe'] > 10:
                    profitability['score'] += 0.2
                elif profitability['roe'] > 5:
                    profitability['score'] += 0.1
                
        except Exception as e:
            logger.warning(f"Error calculating profitability metrics: {str(e)}")
        
        return profitability
    
    def _analyze_liquidity(self, balance_sheet: pd.DataFrame) -> Dict:
        """Analyze liquidity metrics."""
        liquidity = {
            'current_ratio': 0.0,
            'quick_ratio': 0.0,
            'cash_ratio': 0.0,
            'working_capital': 0.0,
            'score': 0.0
        }
        
        try:
            if not balance_sheet.empty:
                current_assets = balance_sheet.loc['Total Current Assets'].iloc[0] if 'Total Current Assets' in balance_sheet.index else 0
                current_liabilities = balance_sheet.loc['Total Current Liabilities'].iloc[0] if 'Total Current Liabilities' in balance_sheet.index else 0
                cash = balance_sheet.loc['Cash'].iloc[0] if 'Cash' in balance_sheet.index else 0
                inventory = balance_sheet.loc['Inventory'].iloc[0] if 'Inventory' in balance_sheet.index else 0
                
                # Calculate ratios
                if current_liabilities > 0:
                    liquidity['current_ratio'] = current_assets / current_liabilities
                    liquidity['quick_ratio'] = (current_assets - inventory) / current_liabilities
                    liquidity['cash_ratio'] = cash / current_liabilities
                
                liquidity['working_capital'] = current_assets - current_liabilities
                
                # Score based on current ratio
                if liquidity['current_ratio'] > 2:
                    liquidity['score'] += 0.3
                elif liquidity['current_ratio'] > 1.5:
                    liquidity['score'] += 0.2
                elif liquidity['current_ratio'] > 1:
                    liquidity['score'] += 0.1
                else:
                    liquidity['score'] -= 0.2
                
                # Score based on quick ratio
                if liquidity['quick_ratio'] > 1:
                    liquidity['score'] += 0.2
                elif liquidity['quick_ratio'] > 0.5:
                    liquidity['score'] += 0.1
                else:
                    liquidity['score'] -= 0.1
                
        except Exception as e:
            logger.warning(f"Error calculating liquidity metrics: {str(e)}")
        
        return liquidity
    
    def _analyze_efficiency(self, financials: pd.DataFrame, balance_sheet: pd.DataFrame) -> Dict:
        """Analyze efficiency metrics."""
        efficiency = {
            'asset_turnover': 0.0,
            'inventory_turnover': 0.0,
            'receivables_turnover': 0.0,
            'score': 0.0
        }
        
        try:
            if not financials.empty and not balance_sheet.empty:
                revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else 0
                total_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 0
                inventory = balance_sheet.loc['Inventory'].iloc[0] if 'Inventory' in balance_sheet.index else 0
                receivables = balance_sheet.loc['Net Receivables'].iloc[0] if 'Net Receivables' in balance_sheet.index else 0
                
                # Calculate turnover ratios
                if total_assets > 0:
                    efficiency['asset_turnover'] = revenue / total_assets
                if inventory > 0:
                    efficiency['inventory_turnover'] = revenue / inventory
                if receivables > 0:
                    efficiency['receivables_turnover'] = revenue / receivables
                
                # Score based on asset turnover
                if efficiency['asset_turnover'] > 1:
                    efficiency['score'] += 0.3
                elif efficiency['asset_turnover'] > 0.5:
                    efficiency['score'] += 0.2
                elif efficiency['asset_turnover'] > 0.2:
                    efficiency['score'] += 0.1
                
                # Score based on inventory turnover
                if efficiency['inventory_turnover'] > 5:
                    efficiency['score'] += 0.2
                elif efficiency['inventory_turnover'] > 2:
                    efficiency['score'] += 0.1
                
        except Exception as e:
            logger.warning(f"Error calculating efficiency metrics: {str(e)}")
        
        return efficiency
    
    def _analyze_growth(self, financials: pd.DataFrame, cashflow: pd.DataFrame) -> Dict:
        """Analyze growth metrics."""
        growth = {
            'revenue_growth': 0.0,
            'earnings_growth': 0.0,
            'free_cash_flow_growth': 0.0,
            'score': 0.0
        }
        
        try:
            if not financials.empty and len(financials.columns) >= 2:
                # Calculate year-over-year growth
                current_revenue = financials.loc['Total Revenue'].iloc[0] if 'Total Revenue' in financials.index else 0
                previous_revenue = financials.loc['Total Revenue'].iloc[1] if 'Total Revenue' in financials.index and len(financials.columns) > 1 else 0
                
                current_earnings = financials.loc['Net Income'].iloc[0] if 'Net Income' in financials.index else 0
                previous_earnings = financials.loc['Net Income'].iloc[1] if 'Net Income' in financials.index and len(financials.columns) > 1 else 0
                
                if previous_revenue > 0:
                    growth['revenue_growth'] = ((current_revenue - previous_revenue) / previous_revenue) * 100
                
                if previous_earnings > 0:
                    growth['earnings_growth'] = ((current_earnings - previous_earnings) / previous_earnings) * 100
                
                # Calculate FCF growth if available
                if not cashflow.empty and len(cashflow.columns) >= 2:
                    current_fcf = cashflow.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cashflow.index else 0
                    previous_fcf = cashflow.loc['Free Cash Flow'].iloc[1] if 'Free Cash Flow' in cashflow.index and len(cashflow.columns) > 1 else 0
                    
                    if previous_fcf > 0:
                        growth['free_cash_flow_growth'] = ((current_fcf - previous_fcf) / previous_fcf) * 100
                
                # Score based on growth rates
                if growth['revenue_growth'] > 10:
                    growth['score'] += 0.3
                elif growth['revenue_growth'] > 5:
                    growth['score'] += 0.2
                elif growth['revenue_growth'] > 0:
                    growth['score'] += 0.1
                else:
                    growth['score'] -= 0.1
                
                if growth['earnings_growth'] > 15:
                    growth['score'] += 0.3
                elif growth['earnings_growth'] > 10:
                    growth['score'] += 0.2
                elif growth['earnings_growth'] > 5:
                    growth['score'] += 0.1
                else:
                    growth['score'] -= 0.1
                
        except Exception as e:
            logger.warning(f"Error calculating growth metrics: {str(e)}")
        
        return growth
    
    def _analyze_debt(self, balance_sheet: pd.DataFrame, financials: pd.DataFrame) -> Dict:
        """Analyze debt metrics."""
        debt = {
            'debt_to_equity': 0.0,
            'debt_to_assets': 0.0,
            'interest_coverage': 0.0,
            'current_debt_ratio': 0.0,
            'score': 0.0
        }
        
        try:
            if not balance_sheet.empty:
                total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
                total_equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0] if 'Total Stockholder Equity' in balance_sheet.index else 0
                total_assets = balance_sheet.loc['Total Assets'].iloc[0] if 'Total Assets' in balance_sheet.index else 0
                current_debt = balance_sheet.loc['Short Term Debt'].iloc[0] if 'Short Term Debt' in balance_sheet.index else 0
                
                # Calculate debt ratios
                if total_equity > 0:
                    debt['debt_to_equity'] = total_debt / total_equity
                if total_assets > 0:
                    debt['debt_to_assets'] = total_debt / total_assets
                if current_debt > 0:
                    debt['current_debt_ratio'] = current_debt / total_assets
                
                # Calculate interest coverage
                if not financials.empty:
                    operating_income = financials.loc['Operating Income'].iloc[0] if 'Operating Income' in financials.index else 0
                    interest_expense = financials.loc['Interest Expense'].iloc[0] if 'Interest Expense' in financials.index else 0
                    
                    if interest_expense > 0:
                        debt['interest_coverage'] = operating_income / interest_expense
                
                # Score based on debt ratios
                if debt['debt_to_equity'] < 0.5:
                    debt['score'] += 0.3
                elif debt['debt_to_equity'] < 1:
                    debt['score'] += 0.2
                elif debt['debt_to_equity'] < 2:
                    debt['score'] += 0.1
                else:
                    debt['score'] -= 0.2
                
                if debt['interest_coverage'] > 5:
                    debt['score'] += 0.3
                elif debt['interest_coverage'] > 3:
                    debt['score'] += 0.2
                elif debt['interest_coverage'] > 1:
                    debt['score'] += 0.1
                else:
                    debt['score'] -= 0.2
                
        except Exception as e:
            logger.warning(f"Error calculating debt metrics: {str(e)}")
        
        return debt
    
    def _calculate_overall_score(self, analysis: Dict) -> Tuple[float, str]:
        """Calculate overall fundamental score and recommendation."""
        total_score = 0.0
        max_possible_score = 0.0
        
        # Weighted scoring system
        categories = {
            'valuation_metrics': 0.25,
            'profitability_metrics': 0.25,
            'liquidity_metrics': 0.15,
            'efficiency_metrics': 0.15,
            'growth_metrics': 0.10,
            'debt_metrics': 0.10
        }
        
        for category, weight in categories.items():
            if category in analysis and 'score' in analysis[category]:
                category_score = analysis[category]['score']
                total_score += category_score * weight
                max_possible_score += 2.0 * weight  # Assuming max score of 2.0 per category
        
        # Normalize score to 0-100 scale
        if max_possible_score > 0:
            normalized_score = (total_score / max_possible_score) * 100
        else:
            normalized_score = 50.0  # Neutral if no data
        
        # Determine recommendation
        if normalized_score >= 75:
            recommendation = "Strong BUY"
        elif normalized_score >= 60:
            recommendation = "BUY"
        elif normalized_score >= 40:
            recommendation = "Neutral"
        elif normalized_score >= 25:
            recommendation = "SELL"
        else:
            recommendation = "Strong SELL"
        
        return normalized_score, recommendation
    
    def compare_with_industry(self, company_metrics: Dict, industry_data: Dict) -> Dict:
        """Compare company metrics with industry averages."""
        comparison = {
            'valuation_comparison': {},
            'profitability_comparison': {},
            'liquidity_comparison': {},
            'overall_relative_score': 0.0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Compare valuation metrics
        if 'pe_ratio' in company_metrics.get('valuation_metrics', {}):
            company_pe = company_metrics['valuation_metrics']['pe_ratio']
            industry_pe = industry_data.get('avg_pe_ratio', 0)
            
            if industry_pe > 0:
                pe_ratio = company_pe / industry_pe
                if pe_ratio < 0.8:
                    comparison['valuation_comparison']['pe_ratio'] = "Undervalued"
                elif pe_ratio > 1.2:
                    comparison['valuation_comparison']['pe_ratio'] = "Overvalued"
                else:
                    comparison['valuation_comparison']['pe_ratio'] = "Fair Value"
        
        # Compare profitability metrics
        if 'roe' in company_metrics.get('profitability_metrics', {}):
            company_roe = company_metrics['profitability_metrics']['roe']
            industry_roe = industry_data.get('avg_roe', 0)
            
            if industry_roe > 0:
                roe_ratio = company_roe / industry_roe
                if roe_ratio > 1.2:
                    comparison['profitability_comparison']['roe'] = "Above Average"
                elif roe_ratio < 0.8:
                    comparison['profitability_comparison']['roe'] = "Below Average"
                else:
                    comparison['profitability_comparison']['roe'] = "Average"
        
        return comparison
    
    def generate_fundamental_report(self, analysis: Dict) -> Dict:
        """Generate a comprehensive fundamental analysis report."""
        report = {
            'summary': {
                'overall_score': analysis.get('overall_score', 0),
                'recommendation': analysis.get('recommendation', 'Neutral'),
                'strengths': [],
                'weaknesses': [],
                'key_metrics': {}
            },
            'detailed_analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        # Identify strengths and weaknesses
        for category, metrics in analysis.items():
            if isinstance(metrics, dict) and 'score' in metrics:
                if metrics['score'] > 0.5:
                    report['summary']['strengths'].append(f"Strong {category.replace('_', ' ').title()}")
                elif metrics['score'] < -0.2:
                    report['summary']['weaknesses'].append(f"Weak {category.replace('_', ' ').title()}")
        
        # Extract key metrics
        if 'valuation_metrics' in analysis:
            report['summary']['key_metrics']['P/E Ratio'] = analysis['valuation_metrics'].get('pe_ratio', 0)
            report['summary']['key_metrics']['P/B Ratio'] = analysis['valuation_metrics'].get('pb_ratio', 0)
        
        if 'profitability_metrics' in analysis:
            report['summary']['key_metrics']['ROE'] = analysis['profitability_metrics'].get('roe', 0)
            report['summary']['key_metrics']['Net Margin'] = analysis['profitability_metrics'].get('net_margin', 0)
        
        if 'liquidity_metrics' in analysis:
            report['summary']['key_metrics']['Current Ratio'] = analysis['liquidity_metrics'].get('current_ratio', 0)
        
        return report