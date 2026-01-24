import minizinc
import random
from datetime import timedelta
import time
import os
import shutil

# --- CONFIGURAZIONE ---
MODEL_FILE = "sorting.mzn"
SOLVER_NAME = "gecode"  
TIMEOUT_SEC = 300       # 5 minuti
OUTPUT_DIR = "result_benchmark"

def solve_sorting_instance(model, solver, n, start_v):
    """
    Tenta di risolvere l'istanza incrementando k finché non trova soluzione.
    Ritorna: k, result, elapsed_time
    """
    print(f"--- Risolvendo vettore di dimensione {n}: {start_v} ---")
    
    k = 1
    found = False
    start_time_total = time.time()
    
    while not found:
        # Crea un'istanza passando il modello GIÀ CARICATO
        instance = minizinc.Instance(solver, model)
        
        # Assegna i dati
        instance["n"] = n
        instance["start_v"] = start_v
        instance["k"] = k
        
        print(f"  Test k={k}...", end=" ", flush=True)
        
        try:
            result = instance.solve(timeout=timedelta(seconds=TIMEOUT_SEC))
            
            if result.status == minizinc.Status.SATISFIED:
                # --- CALCOLO DEL TEMPO ---
                raw_time = result.statistics.get('time', 0)
                if isinstance(raw_time, timedelta):
                    elapsed = raw_time.total_seconds()
                else:
                    elapsed = float(raw_time)
                # ------------------------

                print(f"TROVATO! ({elapsed:.2f}s)")
                return k, result, elapsed
                
            elif result.status == minizinc.Status.UNSATISFIABLE:
                print("UNSAT. Incremento k.")
                k += 1
            else:
                print(f"Status: {result.status}")
                break
                
        except Exception as e:
            print(f"\nErrore durante il solve: {e}")
            break
            
        if (time.time() - start_time_total) > TIMEOUT_SEC:
             print("  TIMEOUT TOTALE.")
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
    Salva i risultati in un file di testo leggibile.
    """
    filename = f"result_{index:02d}_N{n}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, "w") as f:
        f.write("="*50 + "\n")
        f.write(f"BENCHMARK INSTANCE #{index}\n")
        f.write("="*50 + "\n\n")
        
        f.write(f"Dimensione Vettore (N): {n}\n")
        f.write(f"Vettore Iniziale    : {vec}\n\n")
        
        if k != -1 and result is not None:
            f.write(f"Stato: RISOLTO (OPTIMAL)\n")
            f.write(f"Lunghezza Piano (K) : {k}\n")
            f.write(f"Tempo di Esecuzione : {time_taken:.4f} secondi\n")
            f.write("-" * 30 + "\n")
            f.write("PIANO DI ORDINAMENTO:\n")
            f.write("-" * 30 + "\n")
            # Scrive l'output formattato definito nel file .mzn (output [...])
            f.write(str(result))
        else:
            f.write(f"Stato: FALLITO / TIMEOUT\n")
            f.write(f"Tempo Trascorso: > {TIMEOUT_SEC} secondi\n")
            
    # print(f"  -> Salvato in {filepath}")

if __name__ == "__main__":
    # 0. Creazione cartella output
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Cartella '{OUTPUT_DIR}' creata.")

    # Verifica esistenza file .mzn
    if not os.path.exists(MODEL_FILE):
        print(f"ERRORE: Non trovo il file {MODEL_FILE} nella cartella corrente.")
        exit(1)

    # 1. Carica il modello UNA VOLTA SOLA qui
    try:
        model = minizinc.Model(MODEL_FILE)
        solver = minizinc.Solver.lookup(SOLVER_NAME)
    except Exception as e:
        print(f"Errore caricamento MiniZinc: {e}")
        exit(1)
    
    print("Generazione benchmark...")
    tasks = generate_benchmarks()
    
    print(f"Generate {len(tasks)} istanze. Inizio esecuzione e salvataggio file...")
    print("-" * 30)
    
    results_summary = []
    
    # Esegue TUTTI i task (rimosso il limite [:3])
    for i, (n, vec) in enumerate(tasks): 
        # Risolvi
        best_k, res, elapsed = solve_sorting_instance(model, solver, n, vec)
        
        # Salva su file
        save_result_to_file(i+1, n, vec, best_k, elapsed, res)
        
        results_summary.append({
            "id": i+1,
            "n": n,
            "k": best_k,
            "time": elapsed
        })
        print("-" * 30)

    print(f"\n--- COMPLETATO ---")
    print(f"I risultati dettagliati sono nella cartella '{OUTPUT_DIR}'")