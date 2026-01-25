# Sorting as a Planning Problem (Project 5)

This repository contains the implementation of **Project 5** for the **Constraint Programming** course (2025). The project explores modeling the sorting of a vector as a discrete-time planning problem, identifying the minimum sequence of pairwise swaps required to reach a sorted state.

## Project Overview

The objective is to find the **minimum plan length $k$** to sort a permutation of $N$ integers. While basic CP models struggle with the combinatorial explosion of planning horizons, this solution implements state-of-the-art optimizations to achieve high performance even for $N=30$.

### Key Features
- **Dual Representation (Channeling)**: Uses both value-based and position-based views of the vector, synchronized via the `inverse` global constraint.
- **Generalized Arc Consistency (GAC)**: Forces domain-level filtering on permutations using Régin's algorithm.
- **Mathematical Pruning**:
  - **Parity Constraint**: Prunes the search space by ensuring the plan length $k$ matches the permutation's parity.
  - **Optimal Swap Property**: Restricts moves to those that fix at least one element, reducing the branching factor from $O(N^2)$ to $O(N)$.
- **Iterative Deepening Meta-Solver**: A Python-based engine that finds the global optimum for $k$.
- **Theoretical Lower Bounds**: Uses **Cycle Decomposition** to jump directly to the mathematically minimum possible $k$, bypassing the expensive UNSAT phase.
- **12 Search Strategies**: Comprehensive benchmarking of variable/value selection heuristics and restart policies.

## Repository Structure

| File | Role |
| :--- | :--- |
| `sorting.mzn` | Core MiniZinc model with advanced constraints (Inverse, GAC, Parity). |
| `sorting_template.mzn` | Parameterized model for benchmarking different search heuristics. |
| `benchmark.py` | Basic Iterative Deepening solver. |
| `benchmark_strategies.py` | Advanced experimental engine with 12 search strategies. |
| `plot.py` | Data visualization script (generates 11 different charts). |

## Prerequisites

### 1. MiniZinc & Solver
- [MiniZinc](https://www.minizinc.org/) (tested on v2.8+)
- **Gecode** (bundled with MiniZinc)

### 2. Python Environment
The meta-solver requires Python 3.10+ and the following libraries:
```bash
pip install -r requirements.txt
```

## Execution Workflow

### 1. Basic Benchmark
Run the basic benchmark to verify the correctness of the sorting.mzn model:
```bash
python benchmark.py
```

### 2. Strategy Benchmark
Run the advanced engine to compare different search strategies:

```bash
# Show available strategies
python benchmark_strategies.py --list

# Run ALL 12 strategies
python benchmark_strategies.py --all

# Run specific strategies
python benchmark_strategies.py default firstfail domwdeg

# Run with custom parameters
python benchmark_strategies.py --all --timeout 60 --sizes 5 10 15 --instances 5
```

#### Available Strategies

| Strategy | Variable Selection | Value Selection | Restart |
|----------|-------------------|-----------------|---------|
| `default` | Gecode default | default | Luby(250) |
| `firstfail` | first_fail | indomain_random | Luby(250) |
| `domwdeg` | dom_w_deg | indomain_random | Luby(250) |
| `smallest` | smallest | indomain_min | Luby(250) |
| `mostconstrained` | most_constrained | indomain_random | Luby(250) |
| `maxregret` | max_regret | indomain_random | Luby(250) |
| `antifirstfail` | anti_first_fail | indomain_random | Luby(250) |
| `domwdeg_split` | dom_w_deg | indomain_split | Luby(250) |
| `firstfail_split` | first_fail | indomain_split | Luby(250) |
| `geometric` | dom_w_deg | indomain_random | Geometric(1.5, 100) |
| `linear` | dom_w_deg | indomain_random | Linear(250) |
| `norestart` | dom_w_deg | indomain_random | None |

#### CLI Options

| Option | Description |
|--------|-------------|
| `--all`, `-a` | Run all available strategies |
| `--list`, `-l` | List available strategies and exit |
| `--timeout`, `-t` | Timeout in seconds per instance (default: 300) |
| `--sizes`, `-s` | Vector sizes to test (default: 5 10 15 20 25 30) |
| `--instances`, `-n` | Number of instances per size (default: 10) |

### 3. Generate Plots
Generate performance visualizations from benchmark results:
```bash
python plot.py <path_to_csv>

# Example:
python plot.py results/2026-01-24_14-30-45/summary_2026-01-24_14-30-45.csv
```

#### Generated Charts (11 total)

| File | Description |
|------|-------------|
| `01_tempo_vs_n.png` | Average solving time vs vector size |
| `02_successo_vs_n.png` | Number of solved instances per N |
| `03_boxplot_tempi.png` | Time distribution per strategy (boxplot) |
| `04_heatmap_tempo.png` | Heatmap of average time (Strategy × N) |
| `05_heatmap_successo.png` | Heatmap of success rate (Strategy × N) |
| `06_ranking_strategie.png` | Strategy ranking by average time |
| `07_violin_plot.png` | Detailed time distribution (violin plot) |
| `08_speedup.png` | Relative speedup vs baseline |
| `09_stabilita_strategie.png` | Time variability (standard deviation) |
| `10_k_vs_tempo.png` | Correlation between plan length K and time |
| `11_dashboard.png` | Summary dashboard (4-in-1) |

## Core Optimization Logic

The efficiency of this project relies on three pillars of Constraint Programming:

1. **Dual Representation (Channeling)**: By linking values to their positions through an inverse constraint, any domain reduction in one viewpoint is instantly reflected in the other.

2. **Generalized Arc Consistency (GAC)**: Using `alldifferent :: domain` (Régin's algorithm) to prune the search tree far more aggressively than standard binary constraints.

3. **Mathematical Pruning**: The Parity Constraint ensures that the solver never explores even k values for odd permutations (and vice-versa), effectively halving the search space during the "UNSAT" phase.

## Output Structure

```
results/
├── 2026-01-24_14-30-45/             # Timestamped run folder
│   ├── summary_2026-01-24_14-30-45.csv  # Results in CSV format
│   ├── 01_Default_Restart/          # Results for each strategy
│   │   ├── result_01_N5.txt
│   │   ├── result_02_N5.txt
│   │   └── ...
│   ├── 02_Moves_FirstFail/
│   └── ...
└── 2026-01-24_15-00-00/             # Another run...

graphs/
├── summary_2026-01-24_14-30-45/     # Graphs for specific CSV
│   ├── 01_line_comparison_by_size.png
│   ├── 02_success_by_size.png
│   └── ...
└── summary_2026-01-24_15-00-00/
```
