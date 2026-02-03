import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import argparse
from matplotlib.ticker import LogLocator, FuncFormatter

# --- CONFIGURATION ---
OUTPUT_ROOT = "graphs"

def log2_formatter(x, pos):
    """Formatter to display powers of 2 on the axis"""
    if x <= 0:
        return ''
    exp = np.log2(x)
    if exp == int(exp):
        return f'$2^{{{int(exp)}}}$'
    return f'{x:.3g}'


def setup_log2_scale(ax, axis='y'):
    """Configure base-2 logarithmic scale for an axis"""
    if axis == 'y':
        ax.set_yscale('log', base=2)
        ax.yaxis.set_major_formatter(FuncFormatter(log2_formatter))
    else:
        ax.set_xscale('log', base=2)
        ax.xaxis.set_major_formatter(FuncFormatter(log2_formatter))


def generate_performance_plots(csv_file):
    if not os.path.exists(csv_file):
        print(f"Error: cannot find {csv_file}")
        return

    # Load data
    df = pd.read_csv(csv_file)

    # Extract base name from CSV file to create subfolder
    csv_basename = os.path.splitext(os.path.basename(csv_file))[0]
    OUTPUT_DIR = os.path.join(OUTPUT_ROOT, csv_basename)

    # Create output folder
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Setup style
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.size': 12})

    # Consistent color palette for all strategies
    strategies = df['Strategy'].unique()
    palette = dict(zip(strategies, sns.color_palette("husl", len(strategies))))

    # =========================================================================
    # GRAPH 1: AVERAGE TIME vs N (Line Plot)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    avg_time = df.groupby(['N', 'Strategy'])['Time'].mean().reset_index()

    ax = sns.lineplot(data=avg_time, x='N', y='Time', hue='Strategy',
                 marker='o', linewidth=2.5, palette=palette)
    plt.title('Average Performance: Solving Time vs Vector Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Average Time (seconds)')
    setup_log2_scale(plt.gca(), 'y')
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/01_tempo_vs_n.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/01_tempo_vs_n.pdf")

    # =========================================================================
    # GRAPH 2: SUCCESS vs N (Bar Plot)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    success_rate = df[df['Status'] == 'OK'].groupby(['N', 'Strategy']).size().reset_index(name='SolvedCount')

    sns.barplot(data=success_rate, x='N', y='SolvedCount', hue='Strategy', palette=palette)
    plt.title('Reliability: Number of Solved Instances (out of 10)', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Completed Instances')
    plt.ylim(0, 11)
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/02_successo_vs_n.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/02_successo_vs_n.pdf")

    # =========================================================================
    # GRAPH 3: BOXPLOT OF TIMES BY STRATEGY
    # Shows the distribution of times (median, quartiles, outliers)
    # =========================================================================
    plt.figure(figsize=(14, 7))
    # Filter only solved instances to avoid timeouts distorting the graph
    df_solved = df[df['Status'] == 'OK']

    sns.boxplot(data=df_solved, x='Strategy', y='Time', hue='Strategy', palette=palette, legend=False)
    plt.title('Distribution of Solving Times by Strategy', fontsize=14)
    plt.xlabel('Strategy')
    plt.ylabel('Time (seconds)')
    setup_log2_scale(plt.gca(), 'y')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/03_boxplot_tempi.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/03_boxplot_tempi.pdf")

    # =========================================================================
    # GRAPH 4: HEATMAP OF AVERAGE TIME (Strategy x N)
    # Compact visualization to compare all combinations
    # =========================================================================
    plt.figure(figsize=(12, 8))
    pivot_time = df.pivot_table(values='Time', index='Strategy', columns='N', aggfunc='mean')

    # Use log scale for colors
    sns.heatmap(pivot_time, annot=True, fmt='.2f', cmap='YlOrRd',
                cbar_kws={'label': 'Average Time (s)'})
    plt.title('Heatmap: Average Time by Strategy and Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Strategy')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/04_heatmap_tempo.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/04_heatmap_tempo.pdf")

    # =========================================================================
    # GRAPH 5: HEATMAP OF SUCCESS RATE (Strategy x N)
    # =========================================================================
    plt.figure(figsize=(12, 8))
    # Calculate success percentage
    success_pivot = df.pivot_table(
        values='Status',
        index='Strategy',
        columns='N',
        aggfunc=lambda x: (x == 'OK').sum() / len(x) * 100
    )

    sns.heatmap(success_pivot, annot=True, fmt='.0f', cmap='RdYlGn',
                vmin=0, vmax=100, cbar_kws={'label': 'Success Rate (%)'})
    plt.title('Heatmap: Success Percentage by Strategy and Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Strategy')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/05_heatmap_successo.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/05_heatmap_successo.pdf")

    # =========================================================================
    # GRAPH 6: STRATEGY RANKING (Total Average Time)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    # Calculate total average time per strategy (only solved instances)
    ranking = df_solved.groupby('Strategy')['Time'].mean().sort_values()

    colors = [palette[s] for s in ranking.index]
    bars = plt.barh(ranking.index, ranking.values, color=colors)
    plt.xlabel('Average Time (seconds)')
    plt.ylabel('Strategy')
    plt.title('Strategy Ranking: Average Solving Time', fontsize=14)

    # Add values on bars
    for bar, val in zip(bars, ranking.values):
        plt.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.3f}s', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/06_ranking_strategie.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/06_ranking_strategie.pdf")

    # =========================================================================
    # GRAPH 7: VIOLIN PLOT (Detailed distribution by N)
    # =========================================================================
    plt.figure(figsize=(14, 8))

    sns.violinplot(data=df_solved, x='N', y='Time', hue='Strategy',
                   palette=palette, inner='quartile', cut=0)
    plt.title('Time Distribution by Size (Violin Plot)', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Time (seconds)')
    setup_log2_scale(plt.gca(), 'y')
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/07_violin_plot.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/07_violin_plot.pdf")

    # =========================================================================
    # GRAPH 8: SPEEDUP RELATIVE TO BASELINE
    # Shows how much each strategy is faster/slower compared to "default"
    # =========================================================================
    plt.figure(figsize=(12, 7))

    # Calculate average time per strategy and N
    pivot = df_solved.pivot_table(values='Time', index='N', columns='Strategy', aggfunc='mean')

    # Use 'default' as baseline, if not available use the first column
    baseline = 'default' if 'default' in pivot.columns else pivot.columns[0]

    # Calculate speedup (baseline / strategy)
    speedup = pivot.div(pivot[baseline], axis=0)
    speedup = speedup.drop(columns=[baseline])  # Remove baseline (always = 1)

    for col in speedup.columns:
        plt.plot(speedup.index, speedup[col], marker='o', label=col, linewidth=2)

    plt.axhline(y=1, color='gray', linestyle='--', linewidth=1, label=f'{baseline} (baseline)')
    plt.title(f'Relative Speedup compared to "{baseline}"', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel(f'Speedup (time_{baseline} / time_strategy)')
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/08_speedup.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/08_speedup.pdf")

    # =========================================================================
    # GRAPH 9: VARIANCE COMPARISON (Strategy Stability)
    # =========================================================================
    plt.figure(figsize=(12, 7))

    # Calculate standard deviation per strategy
    std_by_strategy = df_solved.groupby('Strategy')['Time'].std().sort_values()

    colors = [palette[s] for s in std_by_strategy.index]
    bars = plt.barh(std_by_strategy.index, std_by_strategy.values, color=colors)
    plt.xlabel('Time Standard Deviation (seconds)')
    plt.ylabel('Strategy')
    plt.title('Strategy Stability: Variability of Solving Times', fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/09_stabilita_strategie.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/09_stabilita_strategie.pdf")

    # =========================================================================
    # GRAPH 10: SCATTER PLOT K vs TIME
    # Shows correlation between difficulty (K) and time
    # =========================================================================
    plt.figure(figsize=(12, 7))

    sns.scatterplot(data=df_solved, x='K', y='Time', hue='Strategy',
                    style='Strategy', palette=palette, alpha=0.7, s=80)
    plt.title('Correlation: Plan Length (K) vs Solving Time', fontsize=14)
    plt.xlabel('Plan Length (K = number of swaps)')
    plt.ylabel('Time (seconds)')
    setup_log2_scale(plt.gca(), 'y')
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/10_k_vs_tempo.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/10_k_vs_tempo.pdf")

    # =========================================================================
    # GRAPH 11: SUMMARY DASHBOARD
    # A summary graph with multiple metrics
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Top-left: Average time per N
    ax1 = axes[0, 0]
    for strat in strategies[:5]:  # Only first 5 for readability
        data = avg_time[avg_time['Strategy'] == strat]
        ax1.plot(data['N'], data['Time'], marker='o', label=strat, linewidth=2)
    setup_log2_scale(ax1, 'y')
    ax1.set_xlabel('N')
    ax1.set_ylabel('Time (s)')
    ax1.set_title('Average Time vs N (Top 5)')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Top-right: Ranking
    ax2 = axes[0, 1]
    ranking_top = ranking.head(10)
    colors_top = [palette.get(s, 'gray') for s in ranking_top.index]
    ax2.barh(ranking_top.index, ranking_top.values, color=colors_top)
    ax2.set_xlabel('Average Time (s)')
    ax2.set_title('Top 10 Fastest Strategies')

    # Bottom-left: Success per N
    ax3 = axes[1, 0]
    success_by_n = df.groupby('N').apply(lambda x: (x['Status'] == 'OK').mean() * 100)
    ax3.bar(success_by_n.index, success_by_n.values, color='steelblue')
    ax3.set_xlabel('N')
    ax3.set_ylabel('% Success')
    ax3.set_title('Global Success Rate per N')
    ax3.set_ylim(0, 105)

    # Bottom-right: K Distribution
    ax4 = axes[1, 1]
    sns.histplot(data=df_solved, x='K', hue='N', multiple='stack', ax=ax4, palette='viridis')
    ax4.set_xlabel('Plan Length (K)')
    ax4.set_ylabel('Count')
    ax4.set_title('Plan Length Distribution per N')

    plt.suptitle('Benchmark Summary Dashboard', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/11_dashboard.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/11_dashboard.pdf")

    # =========================================================================
    # GRAPH 12: HEATMAP OF AVERAGE K (Strategy x N)
    # Shows the average plan length (K) for each strategy and size
    # =========================================================================
    plt.figure(figsize=(12, 8))
    pivot_k = df_solved.pivot_table(values='K', index='Strategy', columns='N', aggfunc='mean')

    sns.heatmap(pivot_k, annot=True, fmt='.2f', cmap='YlGnBu',
                cbar_kws={'label': 'Average K (plan length)'})
    plt.title('Heatmap: Average Plan Length (K) by Strategy and Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Strategy')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/12_heatmap_k.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/12_heatmap_k.pdf")

    # =========================================================================
    # GRAPH 13: BOXPLOT OF K BY STRATEGY
    # Shows the distribution of plan lengths across all instances per strategy
    # =========================================================================
    plt.figure(figsize=(14, 7))
    sns.boxplot(data=df_solved, x='Strategy', y='K', hue='Strategy', palette=palette, legend=False)
    plt.title('Distribution of Plan Length (K) by Strategy', fontsize=14)
    plt.xlabel('Strategy')
    plt.ylabel('Plan Length (K)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/13_boxplot_k.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/13_boxplot_k.pdf")

    # =========================================================================
    # GRAPH 14: AVERAGE K PER STRATEGY (Bar Plot)
    # Ranking of strategies by average plan length
    # =========================================================================
    plt.figure(figsize=(12, 7))
    avg_k_by_strategy = df_solved.groupby('Strategy')['K'].mean().sort_values()

    colors = [palette[s] for s in avg_k_by_strategy.index]
    bars = plt.barh(avg_k_by_strategy.index, avg_k_by_strategy.values, color=colors)
    plt.xlabel('Average Plan Length (K)')
    plt.ylabel('Strategy')
    plt.title('Strategy Ranking: Average Plan Length', fontsize=14)

    # Add values on bars
    for bar, val in zip(bars, avg_k_by_strategy.values):
        plt.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/14_ranking_k.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/14_ranking_k.pdf")

    # =========================================================================
    # GRAPH 15: VIOLIN PLOT OF K BY N
    # Shows the distribution of K values for each size
    # =========================================================================
    plt.figure(figsize=(12, 7))
    sns.violinplot(data=df_solved, x='N', y='K', hue='N', palette='Set2', inner='quartile', legend=False)
    plt.title('Plan Length Distribution by Vector Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Plan Length (K)')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/15_violin_k_by_n.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/15_violin_k_by_n.pdf")

    # =========================================================================
    # GRAPH 16: K vs N (Line Plot with Strategy)
    # Shows how K grows with N for different strategies
    # =========================================================================
    plt.figure(figsize=(12, 7))
    avg_k_per_n = df_solved.groupby(['N', 'Strategy'])['K'].mean().reset_index()

    sns.lineplot(data=avg_k_per_n, x='N', y='K', hue='Strategy',
                marker='o', linewidth=2.5, palette=palette)
    plt.title('Average Plan Length vs Vector Size', fontsize=14)
    plt.xlabel('Vector Size (N)')
    plt.ylabel('Average Plan Length (K)')
    plt.legend(title='Strategy', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/16_k_vs_n.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/16_k_vs_n.pdf")

    # =========================================================================
    # GRAPH 17: MIN/MAX/AVG K PER STRATEGY
    # Shows the range of K values (min, max, average) for each strategy
    # =========================================================================
    plt.figure(figsize=(14, 7))
    k_stats = df_solved.groupby('Strategy')['K'].agg(['min', 'max', 'mean']).sort_values('mean')

    x = np.arange(len(k_stats))
    width = 0.25

    bars1 = plt.bar(x - width, k_stats['min'], width, label='Min K', alpha=0.8, color='#2ecc71')
    bars2 = plt.bar(x, k_stats['mean'], width, label='Avg K', alpha=0.8, color='#3498db')
    bars3 = plt.bar(x + width, k_stats['max'], width, label='Max K', alpha=0.8, color='#e74c3c')

    plt.xlabel('Strategy')
    plt.ylabel('Plan Length (K)')
    plt.title('Min/Max/Average Plan Length by Strategy', fontsize=14)
    plt.xticks(x, k_stats.index, rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/17_k_minmaxavg.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/17_k_minmaxavg.pdf")

    # =========================================================================
    # GRAPH 18: K VALUE FREQUENCY HEATMAP (Strategy x K values)
    # Shows how many times each K value appears for each strategy
    # =========================================================================
    plt.figure(figsize=(14, 8))
    # Create a cross-tabulation of Strategy and K values
    k_freq = pd.crosstab(df_solved['Strategy'], df_solved['K'])

    sns.heatmap(k_freq, cmap='YlOrRd', cbar_kws={'label': 'Frequency'}, linewidths=0.5)
    plt.title('Frequency Heatmap: K Values Distribution per Strategy', fontsize=14)
    plt.xlabel('Plan Length (K)')
    plt.ylabel('Strategy')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/18_k_frequency_heatmap.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/18_k_frequency_heatmap.pdf")

    # =========================================================================
    # GRAPH 19: K RANGE PLOT (Min-Max span with average point)
    # Shows the range of K values for each strategy with markers
    # =========================================================================
    plt.figure(figsize=(12, 8))
    k_stats_sorted = k_stats.sort_values('mean')
    y_pos = np.arange(len(k_stats_sorted))

    # Plot the range (min to max) as horizontal lines
    for i, (strategy, row) in enumerate(k_stats_sorted.iterrows()):
        plt.plot([row['min'], row['max']], [i, i], 'o-', linewidth=3,
                markersize=8, color=palette.get(strategy, 'gray'), alpha=0.6)
        # Add mean as a distinct marker
        plt.plot(row['mean'], i, 'D', markersize=10,
                color=palette.get(strategy, 'gray'), zorder=5)

    plt.yticks(y_pos, k_stats_sorted.index)
    plt.xlabel('Plan Length (K)')
    plt.ylabel('Strategy')
    plt.title('K Value Range by Strategy (Min-Max with Average)', fontsize=14)
    plt.grid(True, alpha=0.3, axis='x')

    # Add custom legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='gray', markerfacecolor='gray',
                              markersize=8, linestyle='-', label='Min-Max Range'),
                       Line2D([0], [0], marker='D', color='w', markerfacecolor='gray',
                              markersize=10, label='Average')]
    plt.legend(handles=legend_elements, loc='best')

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/19_k_range_plot.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/19_k_range_plot.pdf")

    # =========================================================================
    # GRAPH 20: K DISTRIBUTION AS HISTOGRAMS (All 12 strategies)
    # Shows histogram of K values for all strategies
    # =========================================================================
    all_strategies = sorted(df_solved['Strategy'].unique())
    n_strategies = len(all_strategies)
    fig, axes = plt.subplots(4, 3, figsize=(14, 16))
    axes = axes.flatten()

    for idx, strategy in enumerate(all_strategies):
        data = df_solved[df_solved['Strategy'] == strategy]['K']
        ax = axes[idx]
        ax.hist(data, bins=range(int(data.min()), int(data.max()) + 2),
               color=palette[strategy], alpha=0.7, edgecolor='black')
        ax.set_title(f'{strategy}\n(Min:{data.min():.0f}, Max:{data.max():.0f}, Mean:{data.mean():.2f})',
                    fontsize=10)
        ax.set_xlabel('Plan Length (K)')
        ax.set_ylabel('Frequency')
        ax.grid(True, alpha=0.3)

    # Hide unused subplots (if any)
    for idx in range(n_strategies, len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle('K Distribution Histograms: All 12 Strategies', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/20_k_histograms_all12.pdf", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/20_k_histograms_all12.pdf")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "="*60)
    print("SUMMARY OF GENERATED GRAPHS")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}/")
    print(f"Total graphs: 20")
    print("\nGenerated graphs:")
    print("  01_tempo_vs_n.pdf         - Average time vs size (line)")
    print("  02_successo_vs_n.pdf      - Solved instances per N (bar)")
    print("  03_boxplot_tempi.pdf      - Time distribution by strategy")
    print("  04_heatmap_tempo.pdf      - Time heatmap (Strategy x N)")
    print("  05_heatmap_successo.pdf   - Success % heatmap (Strategy x N)")
    print("  06_ranking_strategie.pdf  - Strategy ranking by avg time")
    print("  07_violin_plot.pdf        - Detailed distribution per N")
    print("  08_speedup.pdf            - Relative speedup vs baseline")
    print("  09_stabilita_strategie.pdf - Time variability (std dev)")
    print("  10_k_vs_tempo.pdf         - K vs Time correlation")
    print("  11_dashboard.pdf          - Summary dashboard")
    print("  12_heatmap_k.pdf          - K heatmap (Strategy x N)")
    print("  13_boxplot_k.pdf          - K distribution by strategy")
    print("  14_ranking_k.pdf          - Strategy ranking by avg K")
    print("  15_violin_k_by_n.pdf      - K distribution per N")
    print("  16_k_vs_n.pdf             - Average K vs N (line)")
    print("  17_k_minmaxavg.pdf        - Min/Max/Avg K per strategy")
    print("  18_k_frequency_heatmap.pdf- K frequency heatmap (Strategy x K)")
    print("  19_k_range_plot.pdf       - K range plot (Min-Max)")
    print("  20_k_histograms_top6.pdf  - K histograms for top 6 strategies")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate performance graphs from benchmark results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python plot.py results/summary_2024-01-24_15-30-00.csv
  python plot.py result_benchmark_strategies/summary_results.csv
"""
    )

    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to the CSV file with benchmark results"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_performance_plots(args.csv_file)