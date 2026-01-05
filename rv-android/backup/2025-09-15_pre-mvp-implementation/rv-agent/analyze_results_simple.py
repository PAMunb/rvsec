#!/usr/bin/env python3
"""
Simple Results Analyzer (no external dependencies)
Analyzes CSV results from extensive or overnight executions
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict, Counter

def analyze_csv_results(csv_file):
    """Analyze CSV results and generate summary."""
    
    print(f"📊 Analyzing results from: {csv_file}")
    print("=" * 60)
    
    # Load data
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return
    
    total_tests = len(data)
    successful_tests = sum(1 for row in data if row['success'] == 'True')
    failed_tests = sum(1 for row in data if row['success'] == 'False')
    parse_failures = sum(1 for row in data if row['parsing_success'] == 'False')
    
    overall_success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"🎯 OVERALL RESULTS:")
    print(f"   Total tests: {total_tests:,}")
    print(f"   Successful: {successful_tests:,} ({overall_success_rate:.1f}%)")
    print(f"   Failed: {failed_tests:,} ({(failed_tests/total_tests)*100:.1f}%)")
    print(f"   Parse failures: {parse_failures:,} ({(parse_failures/total_tests)*100:.1f}%)")
    
    # Success metrics
    successful_rows = [row for row in data if row['success'] == 'True']
    if successful_rows:
        distances = [float(row['distance']) for row in successful_rows if row['distance']]
        response_times = [float(row['response_time']) for row in successful_rows if row['response_time']]
        
        avg_distance = sum(distances) / len(distances) if distances else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        perfect_hits = sum(1 for d in distances if d == 0.0)
        
        print(f"\n🎯 SUCCESS METRICS:")
        print(f"   Average distance: {avg_distance:.1f}px")
        print(f"   Average response time: {avg_response_time:.1f}s")
        print(f"   Perfect hits (0px): {perfect_hits:,} ({(perfect_hits/len(successful_rows))*100:.1f}%)")
    
    # Parameter analysis
    param_combinations = defaultdict(lambda: {'total': 0, 'success': 0, 'times': [], 'distances': []})
    
    for row in data:
        if all(key in row for key in ['temperature', 'top_p', 'top_k']):
            param_key = f"T{row['temperature']}_P{row['top_p']}_K{row['top_k']}"
            param_combinations[param_key]['total'] += 1
            
            if row['success'] == 'True':
                param_combinations[param_key]['success'] += 1
                if row['distance']:
                    param_combinations[param_key]['distances'].append(float(row['distance']))
            
            if row['response_time']:
                param_combinations[param_key]['times'].append(float(row['response_time']))
    
    if len(param_combinations) > 1:
        print(f"\n🧪 PARAMETER ANALYSIS:")
        print(f"   Parameter combinations tested: {len(param_combinations)}")
        
        # Sort by success rate
        sorted_params = sorted(param_combinations.items(), 
                             key=lambda x: x[1]['success']/x[1]['total'] if x[1]['total'] > 0 else 0, 
                             reverse=True)
        
        print(f"   📊 TOP 5 PARAMETER COMBINATIONS:")
        for i, (param_key, stats) in enumerate(sorted_params[:5]):
            success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
            avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
            print(f"   {i+1}. {param_key}: {success_rate:.1f}% ({stats['success']}/{stats['total']}) - {avg_time:.1f}s avg")
    
    # App performance breakdown
    app_performance = defaultdict(lambda: {'total': 0, 'success': 0, 'elements': []})
    
    for row in data:
        if 'app' in row:
            app = row['app']
            app_performance[app]['total'] += 1
            
            if row['success'] == 'True':
                app_performance[app]['success'] += 1
            
            if row['available_elements']:
                try:
                    app_performance[app]['elements'].append(int(row['available_elements']))
                except:
                    pass
    
    if len(app_performance) > 1:
        print(f"\n📱 APP PERFORMANCE BREAKDOWN:")
        print(f"   Apps tested: {len(app_performance)}")
        
        # Sort by success rate
        sorted_apps = sorted(app_performance.items(),
                           key=lambda x: x[1]['success']/x[1]['total'] if x[1]['total'] > 0 else 0,
                           reverse=True)
        
        for app, stats in sorted_apps[:10]:
            app_short = app.split('.')[-1] if '.' in app else app
            success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
            avg_elements = sum(stats['elements']) / len(stats['elements']) if stats['elements'] else 0
            print(f"   {app_short}: {success_rate:.1f}% ({stats['success']}/{stats['total']}) - {avg_elements:.1f} avg elements")
    
    # Element complexity analysis
    complexity_buckets = defaultdict(lambda: {'total': 0, 'success': 0})
    
    for row in data:
        if row['available_elements']:
            try:
                num_elements = int(row['available_elements'])
                if num_elements <= 5:
                    bucket = 'Simple (1-5)'
                elif num_elements <= 10:
                    bucket = 'Medium (6-10)'
                elif num_elements <= 20:
                    bucket = 'Complex (11-20)'
                elif num_elements <= 50:
                    bucket = 'Very Complex (21-50)'
                else:
                    bucket = 'Extreme (50+)'
                
                complexity_buckets[bucket]['total'] += 1
                if row['success'] == 'True':
                    complexity_buckets[bucket]['success'] += 1
            except:
                pass
    
    if complexity_buckets:
        print(f"\n🔢 COMPLEXITY ANALYSIS:")
        bucket_order = ['Simple (1-5)', 'Medium (6-10)', 'Complex (11-20)', 'Very Complex (21-50)', 'Extreme (50+)']
        
        for bucket in bucket_order:
            if bucket in complexity_buckets and complexity_buckets[bucket]['total'] > 0:
                stats = complexity_buckets[bucket]
                success_rate = (stats['success'] / stats['total']) * 100
                print(f"   {bucket}: {success_rate:.1f}% ({stats['success']}/{stats['total']})")
    
    # Time analysis
    all_times = [float(row['response_time']) for row in data if row['response_time']]
    if all_times:
        all_times.sort()
        avg_time = sum(all_times) / len(all_times)
        median_time = all_times[len(all_times)//2]
        min_time = min(all_times)
        max_time = max(all_times)
        fast_responses = sum(1 for t in all_times if t < 2)
        slow_responses = sum(1 for t in all_times if t > 5)
        
        print(f"\n⏱️  PERFORMANCE ANALYSIS:")
        print(f"   Average response time: {avg_time:.1f}s")
        print(f"   Median response time: {median_time:.1f}s")
        print(f"   Min response time: {min_time:.1f}s")
        print(f"   Max response time: {max_time:.1f}s")
        print(f"   Fast responses (<2s): {fast_responses:,} ({(fast_responses/len(all_times))*100:.1f}%)")
        print(f"   Slow responses (>5s): {slow_responses:,} ({(slow_responses/len(all_times))*100:.1f}%)")
    
    return {
        'total_tests': total_tests,
        'success_rate': overall_success_rate,
        'avg_distance': avg_distance if 'avg_distance' in locals() else None,
        'avg_time': sum(all_times) / len(all_times) if all_times else None
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_results_simple.py <csv_file>")
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