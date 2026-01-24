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

# --- CONFIGURAZIONE ---
TEMPLATE_FILE = "sorting_template.mzn"
SOLVER_NAME = "gecode"
TIMEOUT_SEC = 300
OUTPUT_ROOT = "results"

# Lock per scrittura thread-safe su CSV e console
csv_lock = threading.Lock()
print_lock = threading.Lock()

# Dizionario delle strategie disponibili
STRATEGIES = {
    # Strategie base
    "default": "solve :: restart_luby(250) satisfy;",
    "firstfail": "solve :: restart_luby(250) :: int_search(all_moves, first_fail, indomain_random, complete) satisfy;",
    "domwdeg": "solve :: restart_luby(250) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",

    # Strategie avanzate di selezione variabile
    "smallest": "solve :: restart_luby(250) :: int_search(all_moves, smallest, indomain_min, complete) satisfy;",
    "mostconstrained": "solve :: restart_luby(250) :: int_search(all_moves, most_constrained, indomain_random, complete) satisfy;",
    "maxregret": "solve :: restart_luby(250) :: int_search(all_moves, max_regret, indomain_random, complete) satisfy;",
    "antifirstfail": "solve :: restart_luby(250) :: int_search(all_moves, anti_first_fail, indomain_random, complete) satisfy;",

    # Strategie con bisection invece di enumerazione
    "domwdeg_split": "solve :: restart_luby(250) :: int_search(all_moves, dom_w_deg, indomain_split, complete) satisfy;",
    "firstfail_split": "solve :: restart_luby(250) :: int_search(all_moves, first_fail, indomain_split, complete) satisfy;",

    # Strategie con restart alternativi
    "geometric": "solve :: restart_geometric(1.5, 100) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
    "linear": "solve :: restart_linear(250) :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
    "norestart": "solve :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;",
}

# Mapping per i nomi delle cartelle di output
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
    """Configura e parsa gli argomenti da linea di comando"""
    parser = argparse.ArgumentParser(
        description="Benchmark comparativo delle strategie di ricerca per il problema di sorting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python benchmark_strategies.py --all                    # Esegue tutte le strategie
  python benchmark_strategies.py default                  # Esegue solo default
  python benchmark_strategies.py firstfail domwdeg        # Esegue firstfail e domwdeg
  python benchmark_strategies.py --list                   # Mostra strategie disponibili
  python benchmark_strategies.py --all -s 5 10 -n 3       # Solo N=5,10 con 3 istanze

Strategie disponibili:
  default, firstfail, domwdeg, smallest, mostconstrained, maxregret,
  antifirstfail, domwdeg_split, firstfail_split, geometric, linear, norestart
"""
    )

    parser.add_argument(
        "strategies",
        nargs="*",
        metavar="STRATEGY",
        help="Strategie da eseguire (default, firstfail, domwdeg, ...)"
    )

    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Esegue tutte le strategie disponibili"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Mostra le strategie disponibili ed esce"
    )

    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=TIMEOUT_SEC,
        help=f"Timeout in secondi per istanza (default: {TIMEOUT_SEC})"
    )

    parser.add_argument(
        "--sizes", "-s",
        type=int,
        nargs="+",
        default=[5, 10, 15, 20, 25, 30],
        help="Dimensioni dei vettori da testare (default: 5 10 15 20 25 30)"
    )

    parser.add_argument(
        "--instances", "-n",
        type=int,
        default=10,
        help="Numero di istanze per ogni dimensione (default: 10)"
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Numero di thread paralleli (default: numero di strategie selezionate)"
    )

    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Esegue in modalità sequenziale (disabilita multithreading)"
    )

    return parser.parse_args()


def list_strategies():
    """Mostra le strategie disponibili con descrizione"""
    print("\n=== STRATEGIE DISPONIBILI ===\n")
    descriptions = {
        "default": "Euristica di default Gecode con Luby restart",
        "firstfail": "Seleziona variabile con dominio più piccolo (fail fast)",
        "domwdeg": "Domain/Weighted-Degree: impara dai fallimenti",
        "smallest": "Seleziona variabile con valore minimo nel dominio",
        "mostconstrained": "first_fail + occurrence (più aggressivo)",
        "maxregret": "Massimizza differenza tra miglior e secondo valore",
        "antifirstfail": "Seleziona variabile con dominio più grande",
        "domwdeg_split": "dom_w_deg con bisection invece di enumerazione",
        "firstfail_split": "first_fail con bisection invece di enumerazione",
        "geometric": "Restart geometrico (1.5x ogni volta) con dom_w_deg",
        "linear": "Restart lineare (incremento fisso) con dom_w_deg",
        "norestart": "dom_w_deg SENZA restart (baseline)",
    }
    for name in STRATEGIES.keys():
        desc = descriptions.get(name, "Nessuna descrizione")
        print(f"  {name:<18} - {desc}")


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


def solve_with_strategy(solver, n, start_v, strategy_code, timeout_sec=TIMEOUT_SEC):
    """Risolve un'istanza con una strategia specifica usando iterative deepening."""
    with open(TEMPLATE_FILE, "r") as f:
        template_content = f.read()

    model_code = template_content.replace("{{SOLVE_STRATEGY}}", strategy_code)
    model = minizinc.Model()
    model.add_string(model_code)

    # Calcola k_min teorico dalla decomposizione in cicli
    # In un piano minimo, k = N - numero_cicli
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
                k += 1  # Incrementa k (teoricamente k_min dovrebbe bastare)
            else:
                return -1, float('inf'), None
        except Exception:
            return -1, float('inf'), None

        if (time.time() - start_time_total) > timeout_sec:
            return -1, float('inf'), None


def save_detailed_file(folder, idx, n, vec, strat_name, k, time_val, result, timeout_sec):
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
            f.write(f"STATO: FALLITO / TIMEOUT (> {timeout_sec}s)\n")


def generate_benchmarks(sizes, instances_per_size):
    """Genera le istanze di benchmark"""
    benchmarks = []
    for n in sizes:
        for _ in range(instances_per_size):
            vec = list(range(1, n + 1))
            random.shuffle(vec)
            benchmarks.append((n, vec))
    return benchmarks


def run_strategy_benchmark(strat_name, tasks, timeout_sec, csv_path, run_dir):
    """
    Esegue il benchmark per una singola strategia su tutte le istanze.
    Questa funzione viene eseguita in un thread separato.
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

        # Stampa thread-safe
        with print_lock:
            print(f"#{instance_id:<4} | {n:<3} | {strat_name:<25} | {str(k):<3} | {time_str:<10}")

        # Salva file dettagliato
        save_detailed_file(folder_path, instance_id, n, vec, strat_name, k, t_elapsed, res_obj, timeout_sec)

        # Scrittura CSV thread-safe
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
    """Esegue il benchmark in modalità sequenziale (comportamento originale)"""
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
    """Esegue il benchmark in modalità parallela (un thread per strategia)"""
    print(f"\nModalità PARALLELA: {max_workers} thread (una strategia per thread)")
    print("-" * 85)

    completed = 0
    total_strategies = len(selected_strategies)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Sottometti un task per ogni strategia
        future_to_strategy = {
            executor.submit(run_strategy_benchmark, strat_name, tasks, timeout_sec, csv_path, run_dir): strat_name
            for strat_name in selected_strategies
        }

        # Raccogli i risultati man mano che completano
        for future in as_completed(future_to_strategy):
            strat_name = future_to_strategy[future]
            try:
                strategy, results = future.result()
                completed += 1

                # Calcola statistiche per questa strategia
                solved = sum(1 for r in results if r['status'] == 'OK')
                total = len(results)
                avg_time = sum(r['time'] for r in results if r['status'] == 'OK') / max(solved, 1)

                with print_lock:
                    print(f"\n[{completed}/{total_strategies}] Strategia '{strategy}' completata:")
                    print(f"   Risolte: {solved}/{total} | Tempo medio: {avg_time:.4f}s")

            except Exception as e:
                with print_lock:
                    print(f"\nErrore nella strategia '{strat_name}': {e}")


if __name__ == "__main__":
    args = parse_args()

    # Mostra lista strategie ed esci
    if args.list:
        list_strategies()
        exit(0)

    # Determina quali strategie eseguire
    if args.all:
        selected_strategies = list(STRATEGIES.keys())
    elif args.strategies:
        # Valida le strategie specificate
        invalid = [s for s in args.strategies if s not in STRATEGIES]
        if invalid:
            print(f"Errore: strategie non valide: {', '.join(invalid)}")
            print(f"Strategie disponibili: {', '.join(STRATEGIES.keys())}")
            exit(1)
        selected_strategies = args.strategies
    else:
        # Se nessuna strategia specificata, mostra help
        print("Errore: specifica almeno una strategia o usa --all")
        print("Usa --help per vedere le opzioni disponibili")
        print("Usa --list per vedere le strategie disponibili")
        exit(1)

    # Rimuovi duplicati mantenendo l'ordine
    selected_strategies = list(dict.fromkeys(selected_strategies))

    timeout_sec = args.timeout

    # Determina numero di worker
    if args.workers:
        max_workers = args.workers
    else:
        max_workers = len(selected_strategies)

    if not os.path.exists(TEMPLATE_FILE):
        print(f"ERRORE: Manca {TEMPLATE_FILE}")
        exit(1)

    if not os.path.exists(OUTPUT_ROOT):
        os.makedirs(OUTPUT_ROOT)

    # Genera timestamp per questa esecuzione
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = os.path.join(OUTPUT_ROOT, timestamp)
    os.makedirs(run_dir)

    # Crea cartelle solo per le strategie selezionate
    for strat_name in selected_strategies:
        folder_name = STRATEGY_FOLDER_NAMES[strat_name]
        path = os.path.join(run_dir, folder_name)
        if not os.path.exists(path):
            os.makedirs(path)

    tasks = generate_benchmarks(args.sizes, args.instances)

    # Nome CSV con timestamp
    csv_filename = f"summary_{timestamp}.csv"
    csv_path = os.path.join(run_dir, csv_filename)
    with open(csv_path, "w", newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ID", "N", "Strategy", "K", "Time", "Status"])

    print(f"\n=== BENCHMARK COMPARATIVO ===")
    print(f"Timestamp: {timestamp}")
    print(f"Strategie: {', '.join(selected_strategies)}")
    print(f"Dimensioni: {args.sizes}")
    print(f"Istanze per dimensione: {args.instances}")
    print(f"Timeout: {timeout_sec}s")
    print(f"Totale test: {len(tasks)} istanze × {len(selected_strategies)} strategie = {len(tasks) * len(selected_strategies)} esecuzioni")

    if args.sequential:
        print(f"Modalità: SEQUENZIALE")
        print("-" * 85)
        print(f"{'Inst':<5} | {'N':<3} | {'Strategy':<25} | {'K':<3} | {'Time (s)':<10}")
        print("-" * 85)

        start_time = time.time()
        run_sequential(selected_strategies, tasks, timeout_sec, csv_path, run_dir)
        total_time = time.time() - start_time
    else:
        print(f"Modalità: PARALLELA ({max_workers} thread)")
        print("-" * 85)
        print(f"{'Inst':<5} | {'N':<3} | {'Strategy':<25} | {'K':<3} | {'Time (s)':<10}")
        print("-" * 85)

        start_time = time.time()
        run_parallel(selected_strategies, tasks, timeout_sec, csv_path, max_workers, run_dir)
        total_time = time.time() - start_time

    print(f"\n=== COMPLETATO ===")
    print(f"Tempo totale: {total_time:.2f}s")
    print(f"Risultati salvati in: {run_dir}/")
    print(f"Riepilogo CSV: {csv_path}")
    print(f"\nPer generare i grafici:")
    print(f"  python plot.py {csv_path}")