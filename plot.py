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
    plt.savefig(f"{OUTPUT_DIR}/01_tempo_vs_n.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/01_tempo_vs_n.png")

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
    plt.savefig(f"{OUTPUT_DIR}/02_successo_vs_n.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/02_successo_vs_n.png")

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
    plt.savefig(f"{OUTPUT_DIR}/03_boxplot_tempi.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/03_boxplot_tempi.png")

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
    plt.savefig(f"{OUTPUT_DIR}/04_heatmap_tempo.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/04_heatmap_tempo.png")

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
    plt.savefig(f"{OUTPUT_DIR}/05_heatmap_successo.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/05_heatmap_successo.png")

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
    plt.savefig(f"{OUTPUT_DIR}/06_ranking_strategie.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/06_ranking_strategie.png")

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
    plt.savefig(f"{OUTPUT_DIR}/07_violin_plot.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/07_violin_plot.png")

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
    plt.savefig(f"{OUTPUT_DIR}/08_speedup.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/08_speedup.png")

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
    plt.savefig(f"{OUTPUT_DIR}/09_stabilita_strategie.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/09_stabilita_strategie.png")

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
    plt.savefig(f"{OUTPUT_DIR}/10_k_vs_tempo.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/10_k_vs_tempo.png")

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
    plt.savefig(f"{OUTPUT_DIR}/11_dashboard.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR}/11_dashboard.png")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "="*60)
    print("SUMMARY OF GENERATED GRAPHS")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}/")
    print(f"Total graphs: 11")
    print("\nGenerated graphs:")
    print("  01_tempo_vs_n.png       - Average time vs size (line)")
    print("  02_successo_vs_n.png    - Solved instances per N (bar)")
    print("  03_boxplot_tempi.png    - Time distribution by strategy")
    print("  04_heatmap_tempo.png    - Time heatmap (Strategy x N)")
    print("  05_heatmap_successo.png - Success % heatmap (Strategy x N)")
    print("  06_ranking_strategie.png- Strategy ranking by avg time")
    print("  07_violin_plot.png      - Detailed distribution per N")
    print("  08_speedup.png          - Relative speedup vs baseline")
    print("  09_stabilita_strategie.png - Time variability (std dev)")
    print("  10_k_vs_tempo.png       - K vs Time correlation")
    print("  11_dashboard.png        - Summary dashboard")


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