import minizinc
import random
import time
import os
import csv
import warnings
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings("ignore", message=".*model inconsistency detected.*")

# --- CONFIGURATION ---
TEMPLATE_FILE = "sorting_template.mzn"
SOLVER_NAME = "gecode"
TIMEOUT_SEC = 300
OUTPUT_ROOT = "results"

# Lock for thread-safe CSV and console writing
csv_lock = threading.Lock()
print_lock = threading.Lock()

# Dictionary of available strategies
STRATEGIES = {
    # Base strategies
    "default": "solve :: restart_luby(250) satisfy;",
    "firstfail": "solve :: restart_luby(250) :: int_search(all_moves, first_fail, indomain_random, complete) satisfy;",
    "domwdeg": "solve :: restart_luby(250) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",

    # Advanced variable selection strategies
    "smallest": "solve :: restart_luby(250) :: int_search(all_moves, smallest, indomain_min, complete) satisfy;",
    "mostconstrained": "solve :: restart_luby(250) :: int_search(all_moves, most_constrained, indomain_random, complete) satisfy;",
    "maxregret": "solve :: restart_luby(250) :: int_search(all_moves, max_regret, indomain_random, complete) satisfy;",
    "antifirstfail": "solve :: restart_luby(250) :: int_search(all_moves, anti_first_fail, indomain_random, complete) satisfy;",

    # Strategies with bisection instead of enumeration
    "domwdeg_split": "solve :: restart_luby(250) :: int_search(all_moves, dom_w_deg, indomain_split, complete) satisfy;",
    "firstfail_split": "solve :: restart_luby(250) :: int_search(all_moves, first_fail, indomain_split, complete) satisfy;",

    # Strategies with alternative restart policies
    "geometric": "solve :: restart_geometric(1.5, 100) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
    "linear": "solve :: restart_linear(250) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
    "norestart": "solve :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
}

# Mapping for output folder names
STRATEGY_FOLDER_NAMES = {
    "default": "01_Default_Restart",
    "firstfail": "02_Moves_FirstFail",
    "domwdeg": "03_Moves_DomWdeg",
    "smallest": "04_Smallest_Min",
    "mostconstrained": "05_MostConstrained",
    "maxregret": "06_MaxRegret",
    "antifirstfail": "07_AntiFirstFail",
    "domwdeg_split": "08_DomWdeg_Split",
    "firstfail_split": "09_FirstFail_Split",
    "geometric": "10_Geometric_Restart",
    "linear": "11_Linear_Restart",
    "norestart": "12_No_Restart",
}


def parse_args():
    """Configure and parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Comparative benchmark of search strategies for the sorting problem.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python benchmark_strategies.py --all                    # Run all strategies
  python benchmark_strategies.py default                  # Run only default
  python benchmark_strategies.py firstfail domwdeg        # Run firstfail and domwdeg
  python benchmark_strategies.py --list                   # Show available strategies
  python benchmark_strategies.py --all -s 5 10 -n 3       # Only N=5,10 with 3 instances

Available strategies:
  default, firstfail, domwdeg, smallest, mostconstrained, maxregret,
  antifirstfail, domwdeg_split, firstfail_split, geometric, linear, norestart
"""
    )

    parser.add_argument(
        "strategies",
        nargs="*",
        metavar="STRATEGY",
        help="Strategies to run (default, firstfail, domwdeg, ...)"
    )

    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all available strategies"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Show available strategies and exit"
    )

    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=TIMEOUT_SEC,
        help=f"Timeout in seconds per instance (default: {TIMEOUT_SEC})"
    )

    parser.add_argument(
        "--sizes", "-s",
        type=int,
        nargs="+",
        default=[5, 10, 15, 20, 25, 30],
        help="Vector sizes to test (default: 5 10 15 20 25 30)"
    )

    parser.add_argument(
        "--instances", "-n",
        type=int,
        default=10,
        help="Number of instances per size (default: 10)"
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel threads (default: number of selected strategies)"
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run in sequential mode (disables multithreading)"
    )

    return parser.parse_args()


def list_strategies():
    """Show available strategies with descriptions"""
    print("\n=== AVAILABLE STRATEGIES ===\n")
    descriptions = {
        "default": "Gecode default heuristic with Luby restart",
        "firstfail": "Select variable with smallest domain (fail fast)",
        "domwdeg": "Domain/Weighted-Degree: learns from failures",
        "smallest": "Select variable with minimum value in domain",
        "mostconstrained": "first_fail + occurrence (more aggressive)",
        "maxregret": "Maximize difference between best and second-best value",
        "antifirstfail": "Select variable with largest domain",
        "domwdeg_split": "dom_w_deg with bisection instead of enumeration",
        "firstfail_split": "first_fail with bisection instead of enumeration",
        "geometric": "Geometric restart (1.5x each time) with dom_w_deg",
        "linear": "Linear restart (fixed increment) with dom_w_deg",
        "norestart": "dom_w_deg WITHOUT restart (baseline)",
    }
    for name in STRATEGIES.keys():
        desc = descriptions.get(name, "No description")
        print(f"  {name:<18} - {desc}")


def count_cycles(vec):
    """Calculate the number of cycles to determine the theoretical minimum k (CP_2025_10)"""
    n = len(vec)
    visited = [False] * n
    cycles = 0
    for i in range(n):
        if not visited[i]:
            cycles += 1
            curr = i
            while not visited[curr]:
                visited[curr] = True
                curr = vec[curr] - 1 # Value v is at position v-1
    return cycles


def solve_with_strategy(solver, n, start_v, strategy_code, timeout_sec=TIMEOUT_SEC):
    """Solve an instance with a specific strategy using iterative deepening."""
    with open(TEMPLATE_FILE, "r") as f:
        template_content = f.read()

    model_code = template_content.replace("{{SOLVE_STRATEGY}}", strategy_code)
    model = minizinc.Model()
    model.add_string(model_code)

    # Calculate theoretical k_min from cycle decomposition
    # In a minimum plan, k = N - number_of_cycles
    k_min = n - count_cycles(start_v)

    k = max(1, k_min)
    start_time_total = time.time()

    while True:
        instance = minizinc.Instance(solver, model)
        instance["n"] = n
        instance["start_v"] = start_v
        instance["k"] = k

        try:
            result = instance.solve(timeout=timedelta(seconds=timeout_sec))
            if result.status == minizinc.Status.SATISFIED:
                raw_time = result.statistics.get('time', 0)
                elapsed = raw_time.total_seconds() if isinstance(raw_time, timedelta) else float(raw_time)
                return k, elapsed, result
            elif result.status == minizinc.Status.UNSATISFIABLE:
                k += 1  # Increment k (theoretically k_min should suffice)
            else:
                return -1, float('inf'), None
        except Exception:
            return -1, float('inf'), None

        if (time.time() - start_time_total) > timeout_sec:
            return -1, float('inf'), None


def save_detailed_file(folder, idx, n, vec, strat_name, k, time_val, result, timeout_sec):
    """Save results in human-readable format"""
    filename = f"result_{idx:02d}_N{n}.txt"
    filepath = os.path.join(folder, filename)
    with open(filepath, "w") as f:
        f.write("="*60 + "\n")
        f.write(f"BENCHMARK ID: {idx} | SIZE: {n} | STRATEGY: {strat_name}\n")
        f.write("="*60 + "\n\n")
        f.write(f"Input Vector: {vec}\n\n")
        if k != -1 and result is not None:
            f.write(f"STATUS: SOLVED\nK: {k}\nTIME: {time_val:.4f}s\n")
            f.write("-" * 40 + "\nPLAN:\n" + str(result))
        else:
            f.write(f"STATUS: FAILED / TIMEOUT (> {timeout_sec}s)\n")


def generate_benchmarks(sizes, instances_per_size):
    """Generate benchmark instances"""
    benchmarks = []
    for n in sizes:
        for _ in range(instances_per_size):
            vec = list(range(1, n + 1))
            random.shuffle(vec)
            benchmarks.append((n, vec))
    return benchmarks


def run_strategy_benchmark(strat_name, tasks, timeout_sec, csv_path, run_dir):
    """
    Run benchmark for a single strategy on all instances.
    This function is executed in a separate thread.
    """
    solver = minizinc.Solver.lookup(SOLVER_NAME)
    strat_code = STRATEGIES[strat_name]
    folder_name = STRATEGY_FOLDER_NAMES[strat_name]
    folder_path = os.path.join(run_dir, folder_name)

    results = []

    for i, (n, vec) in enumerate(tasks):
        instance_id = i + 1

        k, t_elapsed, res_obj = solve_with_strategy(solver, n, vec, strat_code, timeout_sec)

        status_str = "OK" if k != -1 else "TIMEOUT"
        time_str = f"{t_elapsed:.4f}" if k != -1 else f">{timeout_sec}s"

        # Thread-safe print
        with print_lock:
            print(f"#{instance_id:<4} | {n:<3} | {strat_name:<25} | {str(k):<3} | {time_str:<10}")

        # Save detailed file
        save_detailed_file(folder_path, instance_id, n, vec, strat_name, k, t_elapsed, res_obj, timeout_sec)

        # Thread-safe CSV writing
        with csv_lock:
            with open(csv_path, "a", newline='') as csvfile:
                csv.writer(csvfile).writerow([
                    instance_id, n, strat_name, k,
                    (t_elapsed if k != -1 else timeout_sec), status_str
                ])

        results.append({
            'instance_id': instance_id,
            'n': n,
            'strategy': strat_name,
            'k': k,
            'time': t_elapsed,
            'status': status_str
        })

    return strat_name, results


def run_sequential(selected_strategies, tasks, timeout_sec, csv_path, run_dir):
    """Run benchmark in sequential mode (original behavior)"""
    solver = minizinc.Solver.lookup(SOLVER_NAME)

    for i, (n, vec) in enumerate(tasks):
        instance_id = i + 1
        for strat_name in selected_strategies:
            strat_code = STRATEGIES[strat_name]
            folder_name = STRATEGY_FOLDER_NAMES[strat_name]

            k, t_elapsed, res_obj = solve_with_strategy(solver, n, vec, strat_code, timeout_sec)

            status_str = "OK" if k != -1 else "TIMEOUT"
            time_str = f"{t_elapsed:.4f}" if k != -1 else f">{timeout_sec}s"
            print(f"#{instance_id:<4} | {n:<3} | {strat_name:<25} | {str(k):<3} | {time_str:<10}")

            save_detailed_file(
                os.path.join(run_dir, folder_name),
                instance_id, n, vec, strat_name, k, t_elapsed, res_obj, timeout_sec
            )

            with open(csv_path, "a", newline='') as csvfile:
                csv.writer(csvfile).writerow([
                    instance_id, n, strat_name, k,
                    (t_elapsed if k != -1 else timeout_sec), status_str
                ])
        print("-" * 85)


def run_parallel(selected_strategies, tasks, timeout_sec, csv_path, max_workers, run_dir):
    """Run benchmark in parallel mode (one thread per strategy)"""
    print(f"\nPARALLEL mode: {max_workers} threads (one strategy per thread)")
    print("-" * 85)

    completed = 0
    total_strategies = len(selected_strategies)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit one task per strategy
        future_to_strategy = {
            executor.submit(run_strategy_benchmark, strat_name, tasks, timeout_sec, csv_path, run_dir): strat_name
            for strat_name in selected_strategies
        }

        # Collect results as they complete
        for future in as_completed(future_to_strategy):
            strat_name = future_to_strategy[future]
            try:
                strategy, results = future.result()
                completed += 1

                # Calculate statistics for this strategy
                solved = sum(1 for r in results if r['status'] == 'OK')
                total = len(results)
                avg_time = sum(r['time'] for r in results if r['status'] == 'OK') / max(solved, 1)

                with print_lock:
                    print(f"\n[{completed}/{total_strategies}] Strategy '{strategy}' completed:")
                    print(f"   Solved: {solved}/{total} | Average time: {avg_time:.4f}s")

            except Exception as e:
                with print_lock:
                    print(f"\nError in strategy '{strat_name}': {e}")


if __name__ == "__main__":
    args = parse_args()

    # Show strategy list and exit
    if args.list:
        list_strategies()
        exit(0)

    # Determine which strategies to run
    if args.all:
        selected_strategies = list(STRATEGIES.keys())
    elif args.strategies:
        # Validate specified strategies
        invalid = [s for s in args.strategies if s not in STRATEGIES]
        if invalid:
            print(f"Error: invalid strategies: {', '.join(invalid)}")
            print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
            exit(1)
        selected_strategies = args.strategies
    else:
        # If no strategy specified, show help
        print("Error: specify at least one strategy or use --all")
        print("Use --help to see available options")
        print("Use --list to see available strategies")
        exit(1)

    # Remove duplicates while maintaining order
    selected_strategies = list(dict.fromkeys(selected_strategies))

    timeout_sec = args.timeout

    # Determine number of workers
    if args.workers:
        max_workers = args.workers
    else:
        max_workers = len(selected_strategies)

    if not os.path.exists(TEMPLATE_FILE):
        print(f"ERROR: Missing {TEMPLATE_FILE}")
        exit(1)

    if not os.path.exists(OUTPUT_ROOT):
        os.makedirs(OUTPUT_ROOT)

    # Generate timestamp for this run
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(OUTPUT_ROOT, timestamp)
    os.makedirs(run_dir)

    # Create folders only for selected strategies
    for strat_name in selected_strategies:
        folder_name = STRATEGY_FOLDER_NAMES[strat_name]
        path = os.path.join(run_dir, folder_name)
        if not os.path.exists(path):
            os.makedirs(path)

    tasks = generate_benchmarks(args.sizes, args.instances)

    # CSV name with timestamp
    csv_filename = f"summary_{timestamp}.csv"
    csv_path = os.path.join(run_dir, csv_filename)
    with open(csv_path, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ID", "N", "Strategy", "K", "Time", "Status"])

    print(f"\n=== COMPARATIVE BENCHMARK ===")
    print(f"Timestamp: {timestamp}")
    print(f"Strategies: {', '.join(selected_strategies)}")
    print(f"Sizes: {args.sizes}")
    print(f"Instances per size: {args.instances}")
    print(f"Timeout: {timeout_sec}s")
    print(f"Total tests: {len(tasks)} instances x {len(selected_strategies)} strategies = {len(tasks) * len(selected_strategies)} executions")

    if args.sequential:
        print(f"Mode: SEQUENTIAL")
        print("-" * 85)
        print(f"{'Inst':<5} | {'N':<3} | {'Strategy':<25} | {'K':<3} | {'Time (s)':<10}")
        print("-" * 85)

        start_time = time.time()
        run_sequential(selected_strategies, tasks, timeout_sec, csv_path, run_dir)
        total_time = time.time() - start_time
    else:
        print(f"Mode: PARALLEL ({max_workers} threads)")
        print("-" * 85)
        print(f"{'Inst':<5} | {'N':<3} | {'Strategy':<25} | {'K':<3} | {'Time (s)':<10}")
        print("-" * 85)

        start_time = time.time()
        run_parallel(selected_strategies, tasks, timeout_sec, csv_path, max_workers, run_dir)
        total_time = time.time() - start_time

    print(f"\n=== COMPLETED ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Results saved in: {run_dir}/")
    print(f"Summary CSV: {csv_path}")
    print(f"\nTo generate plots:")
    print(f"  python plot.py {csv_path}")