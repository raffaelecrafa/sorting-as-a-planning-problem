# Sorting as a Planning Problem (Project 5)

This repository contains the implementation of **Project 5** for the **Constraint Programming** course (2025). The project explores modeling the sorting of a vector as a discrete-time planning problem, identifying the minimum sequence of pairwise swaps required to reach a sorted state.

## 📋 Project Overview

The objective is to find the **minimum plan length $k$** to sort a permutation of $N$ integers. While basic CP models struggle with the combinatorial explosion of planning horizons, this solution implements state-of-the-art optimizations to achieve high performance even for $N=30$.

### Key Features
- **Dual Representation (Channeling)**: Uses both value-based and position-based views of the vector, synchronized via the `inverse` global constraint.
- **Generalized Arc Consistency (GAC)**: Forces domain-level filtering on permutations using Régin's algorithm.
- **Mathematical Pruning**:
  - **Parity Constraint**: Prunes the search space by ensuring the plan length $k$ matches the permutation's parity.
  - **Optimal Swap Property**: Restricts moves to those that fix at least one element, reducing the branching factor from $O(N^2)$ to $O(N)$.
- **Iterative Deepening Meta-Solver**: A Python-based engine that finds the global optimum for $k$.
- **Theoretical Lower Bounds**: Uses **Cycle Decomposition** to jump directly to the mathematically minimum possible $k$, bypassing the expensive UNSAT phase.

## 📂 Repository Structure

| File | Role |
| :--- | :--- |
| `sorting.mzn` | Core MiniZinc model with advanced constraints (Inverse, GAC, Parity). |
| `sorting_template.mzn` | Parameterized model for benchmarking different search heuristics. |
| `benchmark.py` | Basic Iterative Deepening solver. |
| `benchmark_strategies.py` | Advanced experimental engine with cycle decomposition and Luby restarts. |
| `plot.py` | Data visualization script to generate performance graphs from CSV results. |

## 🛠 Prerequisites

### 1. MiniZinc & Solver
- [MiniZinc](https://www.minizinc.org/) (tested on v2.8+)
- **Gecode** (bundled with MiniZinc)

### 2. Python Environment
The meta-solver requires Python 3.10+ and the following libraries:
```bash
pip install -r requirements.txt
```

## 🚀 Execution Workflow

### 1. Run the basic benchmark to verify the correctness of the sorting.mzn model and the iterative deepening logic:
```
python benchmark.py
```

### 2. Run the advanced engine to compare different heuristics (FirstFail vs DomWdeg vs Default):
```
python benchmark_strategies.py
```

### 3. Generate plots:
```
python plot.py
```

## 🧠 Core Optimization Logic
The efficiency of this project relies on three pillars of Constraint Programming:

  1. Dual Representation (Channeling): By linking values to their positions through an inverse constraint, any domain reduction in one viewpoint is instantly reflected in the other.

  2. Generalized Arc Consistency (GAC): Using alldifferent :: domain (Régin's algorithm) to prune the search tree far more aggressively than standard binary constraints.

  3. Mathematical Pruning: The Parity Constraint ensures that the solver never explores even k values for odd permutations (and vice-versa), effectively halving the search space during the "UNSAT" phase.

----------------------------------------------------------

Author: Raffaele Crafa

Course: Constraint Programming 2025

University: Università di Parma
