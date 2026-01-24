# Sorting come Problema di Pianificazione Discreta

## Progetto 5 - Constraint Programming

---

## 📋 Indice

1. [Introduzione](#introduzione)
2. [Definizione del Problema](#definizione-del-problema)
3. [Esempio Passo-Passo](#esempio-passo-passo)
4. [Formalizzazione Matematica](#formalizzazione-matematica)
5. [Vincoli del Modello](#vincoli-del-modello)
6. [Strategie di Ricerca](#strategie-di-ricerca)
7. [Architettura del Sistema](#architettura-del-sistema)
8. [Glossario](#glossario)

---

## Introduzione

Questo progetto modella il problema dell'**ordinamento** come un problema di **pianificazione discreta** utilizzando la **Programmazione a Vincoli (CP)**.

L'obiettivo non è semplicemente ordinare un vettore, ma trovare il **numero minimo di scambi** (swap) necessari per trasformare una permutazione disordinata in una sequenza ordinata.

### Perché usare CP per il Sorting?

Algoritmi classici come Bubble Sort o Selection Sort non garantiscono il minimo numero di scambi. La CP ci permette di:
- **Modellare** il problema come ricerca nello spazio degli stati
- **Propagare** vincoli per eliminare soluzioni impossibili
- **Garantire** l'ottimalità della soluzione trovata

---

## Definizione del Problema

### Input
- **N**: dimensione del vettore
- **start_v**: permutazione iniziale degli interi `1..N`

### Output
- **K**: numero minimo di scambi necessari
- **Piano**: sequenza di K scambi `(idx1, idx2)` che trasforma `start_v` in `[1, 2, 3, ..., N]`

### Formalizzazione come Sistema di Transizione

```
┌─────────────────────────────────────────────────────────────┐
│                   SPAZIO DEGLI STATI                        │
├─────────────────────────────────────────────────────────────┤
│  Stato Iniziale (t=0): [2, 3, 1, 5, 4]                      │
│                          │                                  │
│                 Swap(2,3)│                                  │
│                          ▼                                  │
│  Stato t=1:            [2, 1, 3, 5, 4]                      │
│                          │                                  │
│                 Swap(1,2)│                                  │
│                          ▼                                  │
│  Stato t=2:            [1, 2, 3, 5, 4]                      │
│                          │                                  │
│                 Swap(4,5)│                                  │
│                          ▼                                  │
│  Stato Finale (t=K):   [1, 2, 3, 4, 5]  ✓ ORDINATO          │
└─────────────────────────────────────────────────────────────┘
```

---

## Esempio Passo-Passo

### Problema
```
Input:  [2, 3, 1, 5, 4]
Output: [1, 2, 3, 4, 5]
```

### Analisi Manuale

**Passo 1: Contare le inversioni**

Un'**inversione** è una coppia `(i, j)` con `i < j` ma `v[i] > v[j]`.

```
Vettore: [2, 3, 1, 5, 4]
Posizioni: 1  2  3  4  5

Inversioni:
- (1,3): 2 > 1  ✓
- (2,3): 3 > 1  ✓
- (4,5): 5 > 4  ✓

Totale inversioni: 3 (DISPARI)
```

**Passo 2: Determinare K minimo con la decomposizione in cicli**

#### Cos'è un Ciclo in una Permutazione?

Un **ciclo** descrive una "catena" di elementi che devono ruotare tra loro per tornare alle posizioni corrette.

**Come trovare i cicli - Metodo passo-passo:**

1. Parti dalla posizione 1
2. Guarda quale valore c'è → vai a quella posizione
3. Ripeti finché non torni alla posizione di partenza
4. Hai trovato un ciclo! Passa alla prossima posizione non ancora visitata

**Esempio dettagliato con `[2, 3, 1, 5, 4]`:**

```
Posizione:   1   2   3   4   5
Valore:     [2] [3] [1] [5] [4]
             │   │   │   │   │
Dovrebbe    [1] [2] [3] [4] [5]   ← Vettore ordinato (goal)
essere:
```

**Trovare il Ciclo 1:** Partiamo dalla posizione 1

```
   Posizione 1 contiene 2
        │
        ▼
   Posizione 2 contiene 3
        │
        ▼
   Posizione 3 contiene 1
        │
        ▼
   Torna a posizione 1 → CICLO CHIUSO!

   Ciclo 1: (1 → 2 → 3 → 1)   Lunghezza: 3
```

Interpretazione: Il valore 1 deve andare in pos. 1, ma è in pos. 3. Il valore 3 deve andare in pos. 3, ma è in pos. 2. Il valore 2 deve andare in pos. 2, ma è in pos. 1. Questi 3 elementi devono "ruotare".

**Trovare il Ciclo 2:** Posizioni 1,2,3 già visitate. Partiamo da posizione 4

```
   Posizione 4 contiene 5
        │
        ▼
   Posizione 5 contiene 4
        │
        ▼
   Torna a posizione 4 → CICLO CHIUSO!

   Ciclo 2: (4 → 5 → 4)   Lunghezza: 2
```

Interpretazione: Il valore 4 è in pos. 5, il valore 5 è in pos. 4. Devono scambiarsi.

**Riepilogo cicli:**
```
┌─────────────────────────────────────────────────────────────┐
│  Permutazione: [2, 3, 1, 5, 4]                              │
│                                                             │
│  Ciclo 1: (1 → 2 → 3 → 1)     3 elementi coinvolti         │
│           ┌───────────┐                                     │
│           │  ┌──┐     │                                     │
│           ▼  │  ▼     │                                     │
│           1 ─┘  2 ──► 3                                     │
│                                                             │
│  Ciclo 2: (4 ↔ 5)             2 elementi coinvolti         │
│           4 ◄──► 5                                          │
│                                                             │
│  Numero totale di cicli: 2                                  │
└─────────────────────────────────────────────────────────────┘
```

**Perché i cicli determinano K minimo?**

- Un ciclo di lunghezza L richiede esattamente **L - 1 swap** per essere risolto
- Ciclo 1 (lunghezza 3): servono 3 - 1 = **2 swap**
- Ciclo 2 (lunghezza 2): servono 2 - 1 = **1 swap**
- Totale: 2 + 1 = **3 swap**

**Formula teorica:**
$$K_{min} = \sum_{c} (L_c - 1) = \sum_{c} L_c - \text{num\_cicli} = N - \text{num\_cicli}$$

Nel nostro caso:
$$K_{min} = N - \text{numero\_cicli} = 5 - 2 = 3$$

**Passo 3: Trovare il piano ottimale**

Ad ogni passo, scegliamo uno swap che **fissa almeno un elemento** nella sua posizione corretta:

| Step | Stato Corrente | Swap | Nuovo Stato | Elemento Fissato |
|------|---------------|------|-------------|------------------|
| 0 | `[2, 3, 1, 5, 4]` | (2, 3) | `[2, 1, 3, 5, 4]` | 3 in pos. 3 ✓ |
| 1 | `[2, 1, 3, 5, 4]` | (1, 2) | `[1, 2, 3, 5, 4]` | 1 in pos. 1, 2 in pos. 2 ✓ |
| 2 | `[1, 2, 3, 5, 4]` | (4, 5) | `[1, 2, 3, 4, 5]` | 4 in pos. 4, 5 in pos. 5 ✓ |

**Risultato: Piano trovato con K = 3 scambi** ✓

---

## Formalizzazione Matematica

### Variabili Decisionali

| Variabile | Dominio | Significato |
|-----------|---------|-------------|
| `v[t, p]` | `1..N` | Valore in posizione `p` al timestep `t` |
| `pos[t, i]` | `1..N` | Posizione del valore `i` al timestep `t` (modello duale) |
| `idx1[t]` | `1..N` | Prima posizione dello swap al passo `t` |
| `idx2[t]` | `1..N` | Seconda posizione dello swap al passo `t` |

### Spazio degli Stati

- **Stato iniziale**: `v[0, p] = start_v[p]` per ogni `p`
- **Stato finale**: `v[K, p] ≤ v[K, p+1]` per ogni `p ∈ 1..N-1` (ordinato)
- **Numero totale di stati**: K+1 (da t=0 a t=K)

### Transizione di Stato (Swap)

Per ogni timestep `t ∈ 0..K-1`:
```
v[t+1, idx1[t]] = v[t, idx2[t]]   (scambia)
v[t+1, idx2[t]] = v[t, idx1[t]]   (scambia)
v[t+1, p] = v[t, p]               per ogni p ≠ idx1[t], idx2[t] (Frame Axiom)
```

---

## Vincoli del Modello

### 1. Condizioni al Contorno

```minizinc
constraint forall(p in 1..n) (v[0, p] = start_v[p]);
constraint forall(p in 1..n-1) (v[k, p] <= v[k, p+1]);
```

**Scopo**: Fissare lo stato iniziale alla permutazione di input e garantire che lo stato finale sia ordinato.

---

### 2. Vincolo di Parità

```minizinc
int: initial_inv = sum(i, j in 1..n where i < j)(bool2int(start_v[i] > start_v[j]));
constraint (k mod 2) == (initial_inv mod 2);
```

**Scopo**: Ogni swap inverte la parità del numero di inversioni. Se la permutazione iniziale ha un numero **dispari** di inversioni, K deve essere dispari (e viceversa).

**Effetto**: Taglia il **50%** dei valori di K impossibili senza esplorarli.

**Dimostrazione**:
- Uno swap `(i, j)` con `i < j` modifica le inversioni di ±1 (inverte una coppia)
- Partendo da `initial_inv` inversioni, dopo K swap abbiamo `initial_inv ± K` inversioni
- Lo stato ordinato ha 0 inversioni (pari)
- Quindi `(initial_inv + K) mod 2 = 0`, ovvero `K mod 2 = initial_inv mod 2`

---

### 3. Channeling con Inverse (Modello Ridondante)

```minizinc
constraint forall(t in 0..k) (
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\
    alldifferent([v[t, p] | p in 1..n]) :: domain
);
```

**Scopo**: Creare una **rappresentazione duale** che collega valori e posizioni.

**Vincolo `inverse`**:
- Se `v[t, p] = i` allora `pos[t, i] = p` (e viceversa)
- Ogni riduzione di dominio in una vista si propaga immediatamente all'altra

**Annotazione `:: domain`**: Attiva l'algoritmo di Régin per la **Generalized Arc Consistency (GAC)**, garantendo la massima propagazione.

```
ESEMPIO:
v[0, ..] = [2, 3, 1, 5, 4]

inverse ⟹

pos[0, ..] = [3, 1, 2, 5, 4]
             │  │  │  │  │
             │  │  │  │  └─ valore 5 è in posizione 4
             │  │  │  └──── valore 4 è in posizione 5
             │  │  └─────── valore 3 è in posizione 2
             │  └────────── valore 2 è in posizione 1
             └───────────── valore 1 è in posizione 3
```

---

### 4. Logica dello Swap Ottimale

```minizinc
constraint forall(t in 0..k-1) (
    idx1[t] < idx2[t] /\
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);
```

**Componenti del vincolo**:

| Parte | Significato |
|-------|-------------|
| `idx1[t] < idx2[t]` | **Symmetry breaking**: evita swap duplicati `(3,5)` e `(5,3)` |
| `v[t, idx2[t]] = idx1[t] ∨ v[t, idx1[t]] = idx2[t]` | **Proprietà di ottimalità**: ogni swap deve fissare almeno un elemento |
| `v[t+1, idx1[t]] = v[t, idx2[t]]` | Meccanica dello swap |
| `v[t+1, p] = v[t, p]` | **Frame Axiom**: tutto ciò che non è coinvolto rimane invariato |

**Proprietà di Ottimalità (Teoria dei Gruppi)**:

In un piano di lunghezza minima, ogni swap deve "avvicinare" almeno un elemento alla sua posizione finale. Questo significa che:
- `v[t, idx2[t]] = idx1[t]`: il valore in posizione `idx2` è esattamente `idx1`, quindi dopo lo swap sarà nella posizione corretta
- OPPURE `v[t, idx1[t]] = idx2[t]`: il valore in posizione `idx1` è esattamente `idx2`

**Effetto**: Riduce il branching factor da O(N²) a O(N).

---

### 5. Rottura delle Simmetrie Aggiuntive

```minizinc
constraint forall(t in 0..k-2) (
    (idx1[t] != idx1[t+1] \/ idx2[t] != idx2[t+1]) /\
    let {
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        disjoint -> (idx1[t] < idx1[t+1])
    )
);
```

**Scopo**: Eliminare soluzioni simmetriche che rappresentano lo stesso piano.

**Prima parte**: `(idx1[t] != idx1[t+1] ∨ idx2[t] != idx2[t+1])`
- Vieta swap identici consecutivi (inutili: si annullano a vicenda)

**Seconda parte**: Ordinamento lessicografico degli swap disgiunti
- Due swap sono **disgiunti** se non condividono alcuna posizione
- Swap disgiunti possono essere eseguiti in qualsiasi ordine
- Il vincolo forza un ordine canonico: `idx1[t] < idx1[t+1]`

```
ESEMPIO di simmetria eliminata:
Piano A: Swap(1,3), Swap(4,5)  ← accettato (1 < 4)
Piano B: Swap(4,5), Swap(1,3)  ← rifiutato (4 > 1)

Entrambi producono lo stesso risultato, ma solo A è ammesso.
```

---

## Strategie di Ricerca

Il file `sorting_template.mzn` supporta diverse strategie di ricerca tramite placeholder `{{SOLVE_STRATEGY}}`. Una strategia è composta da tre componenti:

1. **Selezione della variabile** (`var_choice`): quale variabile assegnare per prima
2. **Selezione del valore** (`val_choice`): quale valore assegnare alla variabile
3. **Strategia di restart**: quando ripartire da capo per evitare zone "morte"

---

### Strategie di Selezione Variabile

#### first_fail
```minizinc
int_search(all_moves, first_fail, ...)
```
Seleziona la variabile con il **dominio più piccolo**. L'idea è "fallire velocemente": se una variabile ha poche scelte, meglio provarle subito per scoprire eventuali conflitti.

**Quando usarla**: Strategia generale molto efficace, buon default.

#### dom_w_deg (Domain over Weighted Degree)
```minizinc
int_search(all_moves, dom_w_deg, ...)
```
Calcola il rapporto **dominio / grado pesato**, dove il grado pesato aumenta ogni volta che una variabile è coinvolta in un fallimento. Seleziona la variabile con il rapporto più basso.

**Quando usarla**: Problemi difficili dove serve "imparare" dalla ricerca. Spesso la migliore in assoluto.

#### smallest
```minizinc
int_search(all_moves, smallest, ...)
```
Seleziona la variabile il cui **valore minimo nel dominio è il più piccolo**. Utile quando i valori bassi sono preferibili.

**Quando usarla**: Problemi dove le soluzioni tendono ad avere valori piccoli.

#### most_constrained
```minizinc
int_search(all_moves, most_constrained, ...)
```
Combina `first_fail` con il numero di vincoli attivi: tra variabili con lo stesso dominio, sceglie quella coinvolta in più vincoli.

**Quando usarla**: Alternativa più aggressiva a first_fail.

#### max_regret
```minizinc
int_search(all_moves, max_regret, ...)
```
Seleziona la variabile con la **massima differenza tra il miglior valore e il secondo miglior valore**. Se c'è grande differenza, quella scelta è "critica".

**Quando usarla**: Problemi di scheduling e ottimizzazione.

#### anti_first_fail
```minizinc
int_search(all_moves, anti_first_fail, ...)
```
Opposto di first_fail: seleziona la variabile con il **dominio più grande**. Esplora prima le scelte con più opzioni.

**Quando usarla**: Per confronto o quando si vuole esplorare ampiamente.

---

### Strategie di Selezione Valore

#### indomain_random
```minizinc
int_search(..., indomain_random, ...)
```
Sceglie un **valore casuale** dal dominio. Introduce diversità nella ricerca.

**Quando usarla**: Con restart, per esplorare zone diverse ad ogni ripartenza.

#### indomain_min / indomain_max
```minizinc
int_search(..., indomain_min, ...)
```
Sceglie il **valore minimo** (o massimo) del dominio. Deterministico e prevedibile.

**Quando usarla**: Quando i valori piccoli (o grandi) sono probabilmente corretti.

#### indomain_split
```minizinc
int_search(..., indomain_split, ...)
```
**Bisection binaria**: invece di assegnare un valore, divide il dominio a metà e prova prima la metà inferiore. Riduce il dominio logaritmicamente invece che linearmente.

**Quando usarla**: Domini grandi, può ridurre drasticamente il branching.

---

### Strategie di Restart

#### restart_luby(scale)
```minizinc
solve :: restart_luby(250) ...
```
Sequenza di Luby: `[1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8, ...]`

Dopo `scale × L` fallimenti (dove L è l'elemento corrente), il solver riparte dalla radice. La sequenza di Luby è **ottimale in media** per problemi di cui non si conosce la difficoltà.

**Quando usarla**: Scelta di default, molto robusta.

#### restart_geometric(base, scale)
```minizinc
solve :: restart_geometric(1.5, 100) ...
```
Il limite di fallimenti cresce geometricamente: `scale, scale×base, scale×base², ...`
Con `base=1.5, scale=100`: 100, 150, 225, 337, ...

**Quando usarla**: Quando si vuole iniziare con restart aggressivi e poi rallentare.

#### restart_linear(scale)
```minizinc
solve :: restart_linear(250) ...
```
Il limite cresce linearmente: `scale, 2×scale, 3×scale, ...`

**Quando usarla**: Crescita più prevedibile rispetto a Luby.

#### Nessun restart
```minizinc
solve :: int_search(...) satisfy;
```
Ricerca completa senza ripartenze. Può bloccarsi in zone difficili.

**Quando usarla**: Come baseline per valutare l'impatto dei restart.

---

### Strategie Implementate nel Benchmark

| Nome | Var Choice | Val Choice | Restart |
|------|------------|------------|---------|
| `default` | (default Gecode) | (default) | Luby(250) |
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
| `norestart` | dom_w_deg | indomain_random | Nessuno |

---

## Architettura del Sistema

```
┌────────────────────────────────────────────────────────────────────┐
│                         LIVELLO PYTHON                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────┐        ┌─────────────────────────────┐   │
│  │   benchmark.py      │        │   benchmark_strategies.py   │   │
│  │                     │        │                             │   │
│  │ • Genera istanze    │        │ • Testa 3 strategie        │   │
│  │ • Iterative Deep.   │        │ • Genera CSV riassuntivo   │   │
│  │ • Calcola cicli     │        │ • Sostituisce placeholder  │   │
│  └──────────┬──────────┘        └──────────────┬──────────────┘   │
│             │                                   │                  │
│             └─────────────┬─────────────────────┘                  │
│                           ▼                                        │
├────────────────────────────────────────────────────────────────────┤
│                       LIVELLO MINIZINC                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────┐        ┌─────────────────────────────┐   │
│  │    sorting.mzn      │        │   sorting_template.mzn      │   │
│  │                     │        │                             │   │
│  │ • Modello completo  │        │ • {{SOLVE_STRATEGY}}       │   │
│  │ • Strategia fissa   │        │ • Per test strategie       │   │
│  └──────────┬──────────┘        └──────────────┬──────────────┘   │
│             │                                   │                  │
│             └─────────────┬─────────────────────┘                  │
│                           ▼                                        │
│                  ┌─────────────────┐                              │
│                  │  Gecode Solver  │                              │
│                  └─────────────────┘                              │
└────────────────────────────────────────────────────────────────────┘
```

### Meta-Solver: Iterative Deepening

```python
k = k_min  # Calcolato dalla decomposizione in cicli
while True:
    result = solve(k, timeout=300s)
    if result == SATISFIED:
        return k  # Trovato minimo!
    elif result == UNSATISFIED:
        k += 2  # Incrementa rispettando la parità
```

---

## Glossario

| Termine | Definizione |
|---------|-------------|
| **CP (Constraint Programming)** | Paradigma di programmazione dove si dichiara un problema tramite variabili e vincoli |
| **CSP** | Constraint Satisfaction Problem: trovare un assegnamento che soddisfa tutti i vincoli |
| **GAC (Generalized Arc Consistency)** | Livello massimo di propagazione per vincoli n-ari |
| **Channeling** | Tecnica che collega variabili ridondanti per aumentare la propagazione |
| **Symmetry Breaking** | Vincoli aggiuntivi che eliminano soluzioni equivalenti |
| **Frame Axiom** | Principio che specifica cosa NON cambia durante un'azione |
| **Inversione** | Coppia (i,j) con i < j ma v[i] > v[j] |
| **Ciclo (permutazione)** | Sottoinsieme di elementi che si mappano ciclicamente |
| **Luby Restart** | Strategia di restart con sequenza universale ottimale |
| **first_fail** | Euristica: scegli la variabile con dominio più piccolo |
| **dom_w_deg** | Euristica: domain / weighted degree, impara dai fallimenti |
| **Iterative Deepening** | Strategia che incrementa il bound finché trova soluzione |

---

## Riferimenti

1. **MiniZinc Handbook**: https://www.minizinc.org/doc-2.8.5/en/
2. **Gecode Reference**: https://www.gecode.org/doc-latest/reference/
3. **Corso CP 2025** - Slide su strategie di ricerca e restart
4. **Teoria delle Permutazioni** - Decomposizione in cicli e trasposizioni
