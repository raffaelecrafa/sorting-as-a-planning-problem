import minizinc
import random
import time
import os
import csv
import warnings
from datetime import timedelta

warnings.filterwarnings("ignore", message=".*model inconsistency detected.*")

# --- CONFIGURAZIONE ---
TEMPLATE_FILE = "sorting_template.mzn"
SOLVER_NAME = "gecode"  
TIMEOUT_SEC = 300
OUTPUT_ROOT = "result_benchmark_strategies"
SUMMARY_CSV = "summary_results.csv"

STRATEGIES = {
    "1_Default_Restart": "solve :: restart_luby(250) satisfy;",
    "2_Moves_FirstFail": "solve :: restart_luby(250) :: int_search(all_moves, first_fail, indomain_random, complete) satisfy;",
    "3_Moves_DomWdeg": "solve :: restart_luby(250) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;"
}

def count_cycles(vec):
    """Calcola il numero di cicli per determinare il k minimo teorico (CP_2025_10)"""
    n = len(vec)
    visited = [False] * n
    cycles = 0
    for i in range(n):
        if not visited[i]:
            cycles += 1
            curr = i
            while not visited[curr]:
                visited[curr] = True
                curr = vec[curr] - 1 # Il valore v e in posizione v-1
    return cycles

def solve_with_strategy(solver, n, start_v, strategy_code):
    with open(TEMPLATE_FILE, "r") as f:
        template_content = f.read()
    
    model_code = template_content.replace("{{SOLVE_STRATEGY}}", strategy_code)
    model = minizinc.Model()
    model.add_string(model_code)
    
    # --- IL SEGRETO PER N=30 ---
    # In un piano minimo, k deve essere N - numero_cicli
    k_min = n - count_cycles(start_v)
    
    k = max(1, k_min)
    found = False
    start_time_total = time.time()
    
    while not found:
        instance = minizinc.Instance(solver, model)
        instance["n"] = n
        instance["start_v"] = start_v
        instance["k"] = k
        
        try:
            result = instance.solve(timeout=timedelta(seconds=TIMEOUT_SEC))
            if result.status == minizinc.Status.SATISFIED:
                raw_time = result.statistics.get('time', 0)
                elapsed = raw_time.total_seconds() if isinstance(raw_time, timedelta) else float(raw_time)
                return k, elapsed, result
            elif result.status == minizinc.Status.UNSATISFIABLE:
                k += 1 # In teoria per scambi arbitrari k_min e sempre sufficiente
            else:
                return -1, float('inf'), None
        except Exception:
            return -1, float('inf'), None
            
        if (time.time() - start_time_total) > TIMEOUT_SEC:
             return -1, float('inf'), None
    return -1, float('inf'), None


def generate_full_benchmarks():
    """Genera le 60 istanze richieste dal progetto"""
    benchmarks = []
    sizes = [5, 10, 15, 20, 25, 30] 
    for n in sizes:
        for _ in range(10):
            vec = list(range(1, n + 1))
            random.shuffle(vec)
            benchmarks.append((n, vec))
    return benchmarks

def save_detailed_file(folder, idx, n, vec, strat_name, k, time_val, result):
    """Salva i risultati in formato leggibile per l'uomo"""
    filename = f"result_{idx:02d}_N{n}.txt"
    filepath = os.path.join(folder, filename)
    with open(filepath, "w") as f:
        f.write("="*60 + "\n")
        f.write(f"BENCHMARK ID: {idx} | DIMENSIONE: {n} | STRATEGIA: {strat_name}\n")
        f.write("="*60 + "\n\n")
        f.write(f"Input Vector: {vec}\n\n")
        if k != -1 and result is not None:
            f.write(f"STATO: RISOLTO\nK: {k}\nTEMPO: {time_val:.4f}s\n")
            f.write("-" * 40 + "\nPIANO:\n" + str(result))
        else:
            f.write(f"STATO: FALLITO / TIMEOUT (> {TIMEOUT_SEC}s)\n")

if __name__ == "__main__":
    if not os.path.exists(TEMPLATE_FILE):
        print(f"ERRORE: Manca {TEMPLATE_FILE}")
        exit(1)

    if not os.path.exists(OUTPUT_ROOT):
        os.makedirs(OUTPUT_ROOT)
    
    for strat_name in STRATEGIES.keys():
        path = os.path.join(OUTPUT_ROOT, strat_name)
        if not os.path.exists(path):
            os.makedirs(path)

    solver = minizinc.Solver.lookup(SOLVER_NAME)
    tasks = generate_full_benchmarks()
    
    csv_path = os.path.join(OUTPUT_ROOT, SUMMARY_CSV)
    with open(csv_path, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ID", "N", "Strategy", "K", "Time", "Status"])

    print(f"=== INIZIO BENCHMARK COMPARATIVO SU {len(tasks)} ISTANZE ===")
    print("-" * 85)
    print(f"{'Inst':<5} | {'N':<3} | {'Strategy':<25} | {'K':<3} | {'Time (s)':<10}")
    print("-" * 85)

    for i, (n, vec) in enumerate(tasks):
        instance_id = i + 1
        for strat_name, strat_code in STRATEGIES.items():
            k, t_elapsed, res_obj = solve_with_strategy(solver, n, vec, strat_code)
            
            status_str = "OK" if k != -1 else "TIMEOUT"
            time_str = f"{t_elapsed:.4f}" if k != -1 else ">300s"
            print(f"#{instance_id:<4} | {n:<3} | {strat_name:<25} | {str(k):<3} | {time_str:<10}")
            
            save_detailed_file(os.path.join(OUTPUT_ROOT, strat_name), instance_id, n, vec, strat_name, k, t_elapsed, res_obj)
            
            with open(csv_path, "a", newline='') as csvfile:
                csv.writer(csvfile).writerow([instance_id, n, strat_name, k, (t_elapsed if k != -1 else TIMEOUT_SEC), status_str])
        print("-" * 85)

    print(f"\n=== COMPLETATO: Risultati in '{OUTPUT_ROOT}' ===")