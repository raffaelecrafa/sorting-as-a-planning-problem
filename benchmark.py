import minizinc
import random
from datetime import timedelta
import time
import os
import shutil

# --- CONFIGURATION ---
MODEL_FILE = "sorting.mzn"
SOLVER_NAME = "gecode"
TIMEOUT_SEC = 300       # 5 minutes
OUTPUT_DIR = "result_benchmark"


# =============================================================================
# LOWER BOUND CALCULATION VIA CYCLE DECOMPOSITION
# =============================================================================
# Theory: A permutation can be decomposed into disjoint cycles.
#         The minimum number of swaps to sort it is: K_min = N - num_cycles
#
# Example: [2, 3, 1, 5, 4]
#          Cycle 1: 1 -> 2 -> 3 -> 1 (length 3)
#          Cycle 2: 4 -> 5 -> 4 (length 2)
#          num_cycles = 2, so K_min = 5 - 2 = 3
# =============================================================================

def count_cycles(perm):
    """
    Count the number of cycles in the permutation.
    perm: 1-indexed list (perm[0] is position 1)
    Returns: number of disjoint cycles
    """
    n = len(perm)
    visited = [False] * n
    num_cycles = 0

    for i in range(n):
        if not visited[i]:
            num_cycles += 1
            j = i
            while not visited[j]:
                visited[j] = True
                # perm is 1-indexed, so perm[j] - 1 to get 0-based index
                j = perm[j] - 1

    return num_cycles


def count_inversions(perm):
    """
    Count the number of inversions in the permutation.
    An inversion is a pair (i, j) with i < j but perm[i] > perm[j].
    """
    n = len(perm)
    inv = 0
    for i in range(n):
        for j in range(i + 1, n):
            if perm[i] > perm[j]:
                inv += 1
    return inv


def compute_starting_k(perm):
    """
    Calculate the initial value of K using the theoretical lower bound.
    Also applies parity correction.
    """
    n = len(perm)
    num_cycles = count_cycles(perm)
    k_min = n - num_cycles  # Lower bound from group theory

    # Parity correction: K must have the same parity as inversions
    initial_inv = count_inversions(perm)
    if (k_min % 2) != (initial_inv % 2):
        k_min += 1

    return k_min


def solve_sorting_instance(model, solver, n, start_v):
    """
    Attempt to solve the instance by incrementing k until a solution is found.
    Uses the theoretical lower bound (N - num_cycles) as starting point.
    Returns: k, result, elapsed_time
    """
    print(f"--- Solving vector of size {n}: {start_v} ---")

    # Calculate initial K from theoretical lower bound (with parity correction)
    k = compute_starting_k(start_v)
    print(f"  Theoretical lower bound: k={k} (n={n}, cycles={count_cycles(start_v)})")

    found = False
    start_time_total = time.time()

    while not found:
        # Create an instance passing the ALREADY LOADED model
        instance = minizinc.Instance(solver, model)

        # Assign data
        instance["n"] = n
        instance["start_v"] = start_v
        instance["k"] = k

        print(f"  Test k={k}...", end=" ", flush=True)

        try:
            result = instance.solve(timeout=timedelta(seconds=TIMEOUT_SEC))

            if result.status == minizinc.Status.SATISFIED:
                # --- TIME CALCULATION ---
                raw_time = result.statistics.get('time', 0)
                if isinstance(raw_time, timedelta):
                    elapsed = raw_time.total_seconds()
                else:
                    elapsed = float(raw_time)
                # ------------------------

                print(f"FOUND! ({elapsed:.2f}s)")
                return k, result, elapsed

            elif result.status == minizinc.Status.UNSATISFIABLE:
                print("UNSAT. Incrementing k.")
                k += 1
            else:
                print(f"Status: {result.status}")
                break

        except Exception as e:
            print(f"\nError during solve: {e}")
            break

        if (time.time() - start_time_total) > TIMEOUT_SEC:
             print("  TOTAL TIMEOUT.")
             return -1, None, TIMEOUT_SEC

    return -1, None, 0.0

def generate_benchmarks():
    benchmarks = []
    # Come da specifica: n=5,10,15,20,25,30
    sizes = [5, 10, 15, 20, 25, 30]
    for n in sizes:
        for _ in range(10): # 10 permutazioni per ogni n
            vec = list(range(1, n + 1))
            random.shuffle(vec)
            benchmarks.append((n, vec))
    return benchmarks

def save_result_to_file(index, n, vec, k, time_taken, result):
    """
    Save results to a human-readable text file.
    """
    filename = f"result_{index:02d}_N{n}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w") as f:
        f.write("="*50 + "\n")
        f.write(f"BENCHMARK INSTANCE #{index}\n")
        f.write("="*50 + "\n\n")

        f.write(f"Vector Size (N): {n}\n")
        f.write(f"Initial Vector : {vec}\n\n")

        if k != -1 and result is not None:
            f.write(f"Status: SOLVED (OPTIMAL)\n")
            f.write(f"Plan Length (K): {k}\n")
            f.write(f"Execution Time : {time_taken:.4f} seconds\n")
            f.write("-" * 30 + "\n")
            f.write("SORTING PLAN:\n")
            f.write("-" * 30 + "\n")
            # Write formatted output defined in .mzn file (output [...])
            f.write(str(result))
        else:
            f.write(f"Status: FAILED / TIMEOUT\n")
            f.write(f"Elapsed Time: > {TIMEOUT_SEC} seconds\n")

    # print(f"  -> Saved to {filepath}")

if __name__ == "__main__":
    # 0. Create output folder
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Folder '{OUTPUT_DIR}' created.")

    # Check .mzn file exists
    if not os.path.exists(MODEL_FILE):
        print(f"ERROR: Cannot find {MODEL_FILE} in current folder.")
        exit(1)

    # 1. Load model ONCE here
    try:
        model = minizinc.Model(MODEL_FILE)
        solver = minizinc.Solver.lookup(SOLVER_NAME)
    except Exception as e:
        print(f"Error loading MiniZinc: {e}")
        exit(1)

    print("Generating benchmarks...")
    tasks = generate_benchmarks()

    print(f"Generated {len(tasks)} instances. Starting execution and saving files...")
    print("-" * 30)

    results_summary = []

    # Execute ALL tasks (removed [:3] limit)
    for i, (n, vec) in enumerate(tasks):
        # Solve
        best_k, res, elapsed = solve_sorting_instance(model, solver, n, vec)

        # Save to file
        save_result_to_file(i+1, n, vec, best_k, elapsed, res)

        results_summary.append({
            "id": i+1,
            "n": n,
            "k": best_k,
            "time": elapsed
        })
        print("-" * 30)

    print(f"\n--- COMPLETED ---")
    print(f"Detailed results are in the '{OUTPUT_DIR}' folder")