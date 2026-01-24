import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- CONFIGURAZIONE ---
CSV_FILE = "result_benchmark_strategies/summary_results.csv"
OUTPUT_DIR = "grafici_progetto"

def generate_performance_plots():
    if not os.path.exists(CSV_FILE):
        print(f"Errore: non trovo {CSV_FILE}")
        return

    # Caricamento dati
    df = pd.read_csv(CSV_FILE)

    # Creazione cartella output
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Setup stile
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({'font.size': 12})

    # --- GRAFICO 1: TEMPO MEDIO vs N ---
    plt.figure(figsize=(10, 6))
    # Calcoliamo la media del tempo per ogni N e Strategia
    avg_time = df.groupby(['N', 'Strategy'])['Time'].mean().reset_index()
    
    line_plot = sns.lineplot(data=avg_time, x='N', y='Time', hue='Strategy', marker='o', linewidth=2.5)
    plt.title('Prestazioni Medie: Tempo di Risoluzione vs Dimensione Vettore')
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Tempo Medio (secondi)')
    plt.yscale('log') # Scala logaritmica utile per evidenziare esplosione combinatoria
    plt.legend(title='Strategia di Ricerca', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/tempo_vs_n.png")
    print(f"Grafico salvato: {OUTPUT_DIR}/tempo_vs_n.png")

    # --- GRAFICO 2: SUCCESSO vs N ---
    plt.figure(figsize=(10, 6))
    # Calcoliamo quante istanze hanno Status "OK" per ogni N e Strategia
    success_rate = df[df['Status'] == 'OK'].groupby(['N', 'Strategy']).size().reset_index(name='SolvedCount')
    
    bar_plot = sns.barplot(data=success_rate, x='N', y='SolvedCount', hue='Strategy')
    plt.title('Affidabilità: Numero di Istanze Risolte (su 10)')
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Istanze Completate')
    plt.ylim(0, 11)
    plt.legend(title='Strategia di Ricerca', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/successo_vs_n.png")
    print(f"Grafico salvato: {OUTPUT_DIR}/successo_vs_n.png")

if __name__ == "__main__":
    generate_performance_plots()