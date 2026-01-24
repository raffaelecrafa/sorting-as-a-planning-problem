import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
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

    # Palette colori consistente per tutte le strategie
    strategies = df['Strategy'].unique()
    palette = dict(zip(strategies, sns.color_palette("husl", len(strategies))))

    # =========================================================================
    # GRAFICO 1: TEMPO MEDIO vs N (Line Plot)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    avg_time = df.groupby(['N', 'Strategy'])['Time'].mean().reset_index()

    sns.lineplot(data=avg_time, x='N', y='Time', hue='Strategy',
                 marker='o', linewidth=2.5, palette=palette)
    plt.title('Prestazioni Medie: Tempo di Risoluzione vs Dimensione Vettore', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Tempo Medio (secondi)')
    plt.yscale('log')
    plt.legend(title='Strategia', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/01_tempo_vs_n.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/01_tempo_vs_n.png")

    # =========================================================================
    # GRAFICO 2: SUCCESSO vs N (Bar Plot)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    success_rate = df[df['Status'] == 'OK'].groupby(['N', 'Strategy']).size().reset_index(name='SolvedCount')

    sns.barplot(data=success_rate, x='N', y='SolvedCount', hue='Strategy', palette=palette)
    plt.title('Affidabilità: Numero di Istanze Risolte (su 10)', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Istanze Completate')
    plt.ylim(0, 11)
    plt.legend(title='Strategia', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/02_successo_vs_n.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/02_successo_vs_n.png")

    # =========================================================================
    # GRAFICO 3: BOXPLOT TEMPI PER STRATEGIA
    # Mostra la distribuzione dei tempi (mediana, quartili, outlier)
    # =========================================================================
    plt.figure(figsize=(14, 7))
    # Filtra solo istanze risolte per evitare che i timeout distorcano il grafico
    df_solved = df[df['Status'] == 'OK']

    sns.boxplot(data=df_solved, x='Strategy', y='Time', palette=palette)
    plt.title('Distribuzione Tempi di Risoluzione per Strategia', fontsize=14)
    plt.xlabel('Strategia')
    plt.ylabel('Tempo (secondi)')
    plt.yscale('log')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/03_boxplot_tempi.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/03_boxplot_tempi.png")

    # =========================================================================
    # GRAFICO 4: HEATMAP TEMPO MEDIO (Strategia x N)
    # Visualizzazione compatta per confrontare tutte le combinazioni
    # =========================================================================
    plt.figure(figsize=(12, 8))
    pivot_time = df.pivot_table(values='Time', index='Strategy', columns='N', aggfunc='mean')

    # Usa scala log per i colori
    sns.heatmap(pivot_time, annot=True, fmt='.2f', cmap='YlOrRd',
                cbar_kws={'label': 'Tempo Medio (s)'})
    plt.title('Heatmap: Tempo Medio per Strategia e Dimensione', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Strategia')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/04_heatmap_tempo.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/04_heatmap_tempo.png")

    # =========================================================================
    # GRAFICO 5: HEATMAP TASSO DI SUCCESSO (Strategia x N)
    # =========================================================================
    plt.figure(figsize=(12, 8))
    # Calcola percentuale di successo
    success_pivot = df.pivot_table(
        values='Status',
        index='Strategy',
        columns='N',
        aggfunc=lambda x: (x == 'OK').sum() / len(x) * 100
    )

    sns.heatmap(success_pivot, annot=True, fmt='.0f', cmap='RdYlGn',
                vmin=0, vmax=100, cbar_kws={'label': 'Tasso Successo (%)'})
    plt.title('Heatmap: Percentuale di Successo per Strategia e Dimensione', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Strategia')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/05_heatmap_successo.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/05_heatmap_successo.png")

    # =========================================================================
    # GRAFICO 6: RANKING STRATEGIE (Tempo Medio Totale)
    # =========================================================================
    plt.figure(figsize=(12, 7))
    # Calcola tempo medio totale per strategia (solo istanze risolte)
    ranking = df_solved.groupby('Strategy')['Time'].mean().sort_values()

    colors = [palette[s] for s in ranking.index]
    bars = plt.barh(ranking.index, ranking.values, color=colors)
    plt.xlabel('Tempo Medio (secondi)')
    plt.ylabel('Strategia')
    plt.title('Ranking Strategie: Tempo Medio di Risoluzione', fontsize=14)

    # Aggiungi valori sulle barre
    for bar, val in zip(bars, ranking.values):
        plt.text(val + 0.01, bar.get_y() + bar.get_height()/2,
                f'{val:.3f}s', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/06_ranking_strategie.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/06_ranking_strategie.png")

    # =========================================================================
    # GRAFICO 7: VIOLIN PLOT (Distribuzione dettagliata per N)
    # =========================================================================
    plt.figure(figsize=(14, 8))

    sns.violinplot(data=df_solved, x='N', y='Time', hue='Strategy',
                   palette=palette, inner='quartile', cut=0)
    plt.title('Distribuzione Tempi per Dimensione (Violin Plot)', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel('Tempo (secondi)')
    plt.yscale('log')
    plt.legend(title='Strategia', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/07_violin_plot.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/07_violin_plot.png")

    # =========================================================================
    # GRAFICO 8: SPEEDUP RISPETTO A BASELINE
    # Mostra quanto ogni strategia è più veloce/lenta rispetto a "default"
    # =========================================================================
    plt.figure(figsize=(12, 7))

    # Calcola tempo medio per strategia e N
    pivot = df_solved.pivot_table(values='Time', index='N', columns='Strategy', aggfunc='mean')

    # Usa 'default' come baseline, se non esiste usa la prima colonna
    baseline = 'default' if 'default' in pivot.columns else pivot.columns[0]

    # Calcola speedup (baseline / strategia)
    speedup = pivot.div(pivot[baseline], axis=0)
    speedup = speedup.drop(columns=[baseline])  # Rimuovi baseline (sempre = 1)

    for col in speedup.columns:
        plt.plot(speedup.index, speedup[col], marker='o', label=col, linewidth=2)

    plt.axhline(y=1, color='gray', linestyle='--', linewidth=1, label=f'{baseline} (baseline)')
    plt.title(f'Speedup Relativo rispetto a "{baseline}"', fontsize=14)
    plt.xlabel('Dimensione del Vettore (N)')
    plt.ylabel(f'Speedup (tempo_{baseline} / tempo_strategia)')
    plt.legend(title='Strategia', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/08_speedup.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/08_speedup.png")

    # =========================================================================
    # GRAFICO 9: CONFRONTO VARIANZA (Stabilità delle strategie)
    # =========================================================================
    plt.figure(figsize=(12, 7))

    # Calcola deviazione standard per strategia
    std_by_strategy = df_solved.groupby('Strategy')['Time'].std().sort_values()

    colors = [palette[s] for s in std_by_strategy.index]
    bars = plt.barh(std_by_strategy.index, std_by_strategy.values, color=colors)
    plt.xlabel('Deviazione Standard del Tempo (secondi)')
    plt.ylabel('Strategia')
    plt.title('Stabilità Strategie: Variabilità dei Tempi di Risoluzione', fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/09_stabilita_strategie.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/09_stabilita_strategie.png")

    # =========================================================================
    # GRAFICO 10: SCATTER PLOT K vs TEMPO
    # Mostra correlazione tra difficoltà (K) e tempo
    # =========================================================================
    plt.figure(figsize=(12, 7))

    sns.scatterplot(data=df_solved, x='K', y='Time', hue='Strategy',
                    style='Strategy', palette=palette, alpha=0.7, s=80)
    plt.title('Correlazione: Lunghezza Piano (K) vs Tempo di Risoluzione', fontsize=14)
    plt.xlabel('Lunghezza Piano (K = numero di swap)')
    plt.ylabel('Tempo (secondi)')
    plt.yscale('log')
    plt.legend(title='Strategia', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/10_k_vs_tempo.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/10_k_vs_tempo.png")

    # =========================================================================
    # GRAFICO 11: SUMMARY DASHBOARD
    # Un grafico riassuntivo con multiple metriche
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Top-left: Tempo medio per N
    ax1 = axes[0, 0]
    for strat in strategies[:5]:  # Solo prime 5 per leggibilità
        data = avg_time[avg_time['Strategy'] == strat]
        ax1.plot(data['N'], data['Time'], marker='o', label=strat, linewidth=2)
    ax1.set_yscale('log')
    ax1.set_xlabel('N')
    ax1.set_ylabel('Tempo (s)')
    ax1.set_title('Tempo Medio vs N (Top 5)')
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Top-right: Ranking
    ax2 = axes[0, 1]
    ranking_top = ranking.head(10)
    colors_top = [palette.get(s, 'gray') for s in ranking_top.index]
    ax2.barh(ranking_top.index, ranking_top.values, color=colors_top)
    ax2.set_xlabel('Tempo Medio (s)')
    ax2.set_title('Top 10 Strategie più Veloci')

    # Bottom-left: Successo per N
    ax3 = axes[1, 0]
    success_by_n = df.groupby('N').apply(lambda x: (x['Status'] == 'OK').mean() * 100)
    ax3.bar(success_by_n.index, success_by_n.values, color='steelblue')
    ax3.set_xlabel('N')
    ax3.set_ylabel('% Successo')
    ax3.set_title('Tasso di Successo Globale per N')
    ax3.set_ylim(0, 105)

    # Bottom-right: Distribuzione K
    ax4 = axes[1, 1]
    sns.histplot(data=df_solved, x='K', hue='N', multiple='stack', ax=ax4, palette='viridis')
    ax4.set_xlabel('Lunghezza Piano (K)')
    ax4.set_ylabel('Conteggio')
    ax4.set_title('Distribuzione Lunghezza Piani per N')

    plt.suptitle('Dashboard Riepilogativo Benchmark', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/11_dashboard.png", dpi=150)
    plt.close()
    print(f"✓ Salvato: {OUTPUT_DIR}/11_dashboard.png")

    # =========================================================================
    # RIEPILOGO FINALE
    # =========================================================================
    print("\n" + "="*60)
    print("RIEPILOGO GRAFICI GENERATI")
    print("="*60)
    print(f"Directory output: {OUTPUT_DIR}/")
    print(f"Totale grafici: 11")
    print("\nGrafici generati:")
    print("  01_tempo_vs_n.png       - Tempo medio vs dimensione (line)")
    print("  02_successo_vs_n.png    - Istanze risolte per N (bar)")
    print("  03_boxplot_tempi.png    - Distribuzione tempi per strategia")
    print("  04_heatmap_tempo.png    - Heatmap tempo (Strategia x N)")
    print("  05_heatmap_successo.png - Heatmap % successo (Strategia x N)")
    print("  06_ranking_strategie.png- Ranking strategie per tempo medio")
    print("  07_violin_plot.png      - Distribuzione dettagliata per N")
    print("  08_speedup.png          - Speedup relativo vs baseline")
    print("  09_stabilita_strategie.png - Variabilità tempi (std dev)")
    print("  10_k_vs_tempo.png       - Correlazione K vs Tempo")
    print("  11_dashboard.png        - Dashboard riepilogativo")


if __name__ == "__main__":
    generate_performance_plots()