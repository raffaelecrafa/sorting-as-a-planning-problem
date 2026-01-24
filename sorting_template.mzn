% =============================================================================
% SORTING TEMPLATE - Versione per Test delle Strategie di Ricerca
% =============================================================================
% Questo file è una versione TEMPLATE del modello di sorting.
% Il placeholder {{SOLVE_STRATEGY}} viene sostituito dinamicamente dallo script
% benchmark_strategies.py con diverse strategie di ricerca.
%
% DIFFERENZE rispetto a sorting.mzn:
% - Aggiunge la variabile ausiliaria all_moves per facilitare la ricerca
% - Non include il vincolo di parità (gestito dal meta-solver Python)
% - Il blocco solve è un placeholder
%
% STRATEGIE SUPPORTATE:
% 1. Default Restart: euristica default di Gecode con Luby restart
% 2. Moves FirstFail: focus sulle mosse, variabile più vincolata prima
% 3. Moves DomWdeg: domain/weighted-degree, impara dai fallimenti
% =============================================================================

include "globals.mzn";

% =============================================================================
% INPUT
% =============================================================================
int: n;                       % Dimensione del vettore
array[1..n] of int: start_v;  % Permutazione iniziale
int: k;                       % Lunghezza del piano (swap da eseguire)

% =============================================================================
% VARIABILI DECISIONALI
% =============================================================================

% Matrice degli stati: v[t, p] = valore in posizione p al tempo t
array[0..k, 1..n] of var 1..n: v;

% Modello duale per channeling: pos[t, i] = posizione del valore i al tempo t
array[0..k, 1..n] of var 1..n: pos;

% Indici dello swap al passo t
array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;

% =============================================================================
% VARIABILE AUSILIARIA PER LA RICERCA
% =============================================================================
% all_moves: array "piatto" che contiene tutte le mosse in sequenza
%
% Struttura: [idx1[0], idx2[0], idx1[1], idx2[1], ..., idx1[k-1], idx2[k-1]]
%
% Questa variabile permette di specificare strategie di ricerca che operano
% su TUTTE le mosse contemporaneamente, invece che sulla matrice v.
%
% PERCHÉ È UTILE:
% - Le variabili idx1 e idx2 sono quelle che determinano effettivamente la
%   struttura del piano (v è derivata dalle mosse)
% - Concentrare la ricerca sulle mosse è spesso più efficiente
% - Permette euristiche come first_fail e dom_w_deg di operare sulle
%   variabili più "importanti"
% =============================================================================

array[1..2*k] of var 1..n: all_moves = [
    if i mod 2 == 1
    then idx1[i div 2]      % Posizioni dispari: idx1[0], idx1[1], ...
    else idx2[(i-1) div 2]  % Posizioni pari: idx2[0], idx2[1], ...
    endif
    | i in 1..2*k
];


% =============================================================================
% VINCOLO 1: CONDIZIONI AL CONTORNO
% =============================================================================
% Stato iniziale = permutazione di input
% Stato finale = vettore ordinato
% =============================================================================

constraint forall(p in 1..n) (v[0, p] = start_v[p]);
constraint forall(p in 1..n-1) (v[k, p] <= v[k, p+1]);


% =============================================================================
% VINCOLO 2: CHANNELING & GAC
% =============================================================================
% Collega v (valore→posizione) con pos (posizione→valore) tramite inverse.
% Usa alldifferent con GAC per massima propagazione.
% =============================================================================

constraint forall(t in 0..k) (
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\
    alldifferent([v[t, p] | p in 1..n]) :: domain
);


% =============================================================================
% VINCOLO 3: SWAP OTTIMALE (Group Theory Lower Bound)
% =============================================================================
% Ogni mossa DEVE fissare almeno un elemento nella sua posizione corretta.
% Questo deriva dalla teoria dei gruppi sulle permutazioni e garantisce che
% il piano sia di lunghezza minima.
% =============================================================================

constraint forall(t in 0..k-1) (
    % Symmetry breaking: primo indice sempre minore del secondo
    idx1[t] < idx2[t] /\

    % Proprietà di ottimalità: lo swap sistema almeno un elemento
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\

    % Meccanica dello swap
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\

    % Frame Axiom: posizioni non coinvolte rimangono invariate
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);


% =============================================================================
% VINCOLO 4: SYMMETRY BREAKING (Swap Disgiunti)
% =============================================================================
% Ordina lessicograficamente gli swap che non condividono posizioni.
% Due swap disgiunti possono essere eseguiti in qualsiasi ordine, quindi
% imponiamo un ordine canonico per eliminare soluzioni simmetriche.
% =============================================================================

constraint forall(t in 0..k-2) (
    let {
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        disjoint -> (idx1[t] < idx1[t+1])
    )
);


% =============================================================================
% STRATEGIA DI RICERCA (PLACEHOLDER)
% =============================================================================
% Questo placeholder viene sostituito dinamicamente da benchmark_strategies.py
% con una delle seguenti strategie:
%
% 1. DEFAULT RESTART:
%    solve :: restart_luby(250) satisfy;
%    → Usa l'euristica di default di Gecode
%
% 2. MOVES FIRSTFAIL:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, first_fail, indomain_random, complete)
%          satisfy;
%    → first_fail: sceglie la variabile con dominio più piccolo
%    → indomain_random: sceglie un valore casuale dal dominio
%    → Focus sulle variabili delle mosse (idx1, idx2)
%
% 3. MOVES DOMWDEG:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, dom_w_deg, indomain_random, complete)
%          satisfy;
%    → dom_w_deg: domain / weighted degree (euristica adattiva)
%    → Impara dai fallimenti: penalizza variabili "problematiche"
%    → Generalmente la più efficace per problemi difficili
%
% LUBY RESTART (comune a tutte):
%    Sequenza: 1,1,2,1,1,2,4,1,1,2,1,1,2,4,8,...
%    Scala: 250 (riavvia dopo 250×L fallimenti)
%    Scopo: sfuggire a zone "morte" dello spazio di ricerca
% =============================================================================

{{SOLVE_STRATEGY}}