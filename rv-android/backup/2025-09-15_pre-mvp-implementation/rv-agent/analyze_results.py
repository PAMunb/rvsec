#!/usr/bin/env python3
"""
Quick Results Analyzer
Analyzes CSV results from extensive or overnight executions
"""

import pandas as pd
import sys
from pathlib import Path

def analyze_csv_results(csv_file):
    """Analyze CSV results and generate summary."""
    
    print(f"📊 Analyzing results from: {csv_file}")
    print("=" * 60)
    
    # Load data
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return
    
    total_tests = len(df)
    successful_tests = len(df[df['success'] == True])
    failed_tests = len(df[df['success'] == False])
    parse_failures = len(df[df['parsing_success'] == False])
    
    overall_success_rate = (successful_tests / total_tests) * 100
    
    print(f"🎯 OVERALL RESULTS:")
    print(f"   Total tests: {total_tests:,}")
    print(f"   Successful: {successful_tests:,} ({overall_success_rate:.1f}%)")
    print(f"   Failed: {failed_tests:,} ({(failed_tests/total_tests)*100:.1f}%)")
    print(f"   Parse failures: {parse_failures:,} ({(parse_failures/total_tests)*100:.1f}%)")
    
    # Success metrics
    successful_df = df[df['success'] == True]
    if len(successful_df) > 0:
        avg_distance = successful_df['distance'].mean()
        avg_response_time = successful_df['response_time'].mean()
        
        print(f"\n🎯 SUCCESS METRICS:")
        print(f"   Average distance: {avg_distance:.1f}px")
        print(f"   Average response time: {avg_response_time:.1f}s")
        print(f"   Perfect hits (0px): {len(successful_df[successful_df['distance'] == 0]):,} ({(len(successful_df[successful_df['distance'] == 0])/len(successful_df))*100:.1f}%)")
    
    # Parameter analysis (if multiple parameter sets exist)
    if 'temperature' in df.columns and 'top_p' in df.columns and 'top_k' in df.columns:
        unique_params = df.groupby(['temperature', 'top_p', 'top_k']).size().reset_index(name='count')
        
        if len(unique_params) > 1:
            print(f"\n🧪 PARAMETER ANALYSIS:")
            print(f"   Parameter combinations tested: {len(unique_params)}")
            
            # Top performing parameters
            param_performance = df.groupby(['temperature', 'top_p', 'top_k']).agg({
                'success': ['count', 'sum', 'mean'],
                'response_time': 'mean',
                'distance': lambda x: x[df.loc[x.index, 'success'] == True].mean()
            }).round(3)
            
            param_performance.columns = ['total_tests', 'successful_tests', 'success_rate', 'avg_time', 'avg_distance']
            param_performance = param_performance.sort_values('success_rate', ascending=False)
            
            print(f"   📊 TOP 5 PARAMETER COMBINATIONS:")
            for i, (params, row) in enumerate(param_performance.head().iterrows()):
                temp, top_p, top_k = params
                print(f"   {i+1}. T{temp}_P{top_p}_K{top_k}: {row['success_rate']*100:.1f}% ({row['successful_tests']:.0f}/{row['total_tests']:.0f})")
    
    # App performance breakdown
    if 'app' in df.columns:
        app_performance = df.groupby('app').agg({
            'success': ['count', 'sum', 'mean'],
            'available_elements': 'mean'
        }).round(3)
        
        app_performance.columns = ['total_tests', 'successful_tests', 'success_rate', 'avg_elements']
        app_performance = app_performance.sort_values('success_rate', ascending=False)
        
        print(f"\n📱 APP PERFORMANCE BREAKDOWN:")
        print(f"   Apps tested: {len(app_performance)}")
        for app, row in app_performance.head(10).iterrows():
            app_short = app.split('.')[-1] if '.' in app else app
            print(f"   {app_short}: {row['success_rate']*100:.1f}% ({row['successful_tests']:.0f}/{row['total_tests']:.0f}) - {row['avg_elements']:.1f} avg elements")
    
    # Element complexity analysis
    if 'available_elements' in df.columns:
        print(f"\n🔢 COMPLEXITY ANALYSIS:")
        df['complexity_bucket'] = pd.cut(df['available_elements'], bins=[0, 5, 10, 20, 50, 100], labels=['Simple (1-5)', 'Medium (6-10)', 'Complex (11-20)', 'Very Complex (21-50)', 'Extreme (50+)'])
        
        complexity_analysis = df.groupby('complexity_bucket').agg({
            'success': ['count', 'sum', 'mean']
        }).round(3)
        
        complexity_analysis.columns = ['total_tests', 'successful_tests', 'success_rate']
        
        for bucket, row in complexity_analysis.iterrows():
            if pd.notna(bucket) and row['total_tests'] > 0:
                print(f"   {bucket}: {row['success_rate']*100:.1f}% ({row['successful_tests']:.0f}/{row['total_tests']:.0f})")
    
    # Time analysis
    if 'response_time' in df.columns:
        print(f"\n⏱️  PERFORMANCE ANALYSIS:")
        print(f"   Average response time: {df['response_time'].mean():.1f}s")
        print(f"   Median response time: {df['response_time'].median():.1f}s")
        print(f"   Min response time: {df['response_time'].min():.1f}s")
        print(f"   Max response time: {df['response_time'].max():.1f}s")
        print(f"   Fast responses (<2s): {len(df[df['response_time'] < 2]):,} ({(len(df[df['response_time'] < 2])/total_tests)*100:.1f}%)")
        print(f"   Slow responses (>5s): {len(df[df['response_time'] > 5]):,} ({(len(df[df['response_time'] > 5])/total_tests)*100:.1f}%)")
    
    return {
        'total_tests': total_tests,
        'success_rate': overall_success_rate,
        'avg_distance': avg_distance if 'avg_distance' in locals() else None,
        'avg_time': df['response_time'].mean() if 'response_time' in df.columns else None
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_results.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    results = analyze_csv_results(csv_file)
    
    # Final summary
    print(f"\n🏆 FINAL SUMMARY:")
    print(f"   Overall success rate: {results['success_rate']:.1f}%")
    if results['avg_distance'] is not None:
        print(f"   Average precision: {results['avg_distance']:.1f}px")
    if results['avg_time'] is not None:
        print(f"   Average speed: {results['avg_time']:.1f}s")
    
    # Recommendation
    if results['success_rate'] >= 75:
        recommendation = "🎉 EXCELLENT - Production ready!"
    elif results['success_rate'] >= 65:
        recommendation = "✅ GOOD - Production viable"
    elif results['success_rate'] >= 50:
        recommendation = "⚠️  MODERATE - Needs optimization"
    else:
        recommendation = "❌ POOR - Major improvements needed"
    
    print(f"   Recommendation: {recommendation}")