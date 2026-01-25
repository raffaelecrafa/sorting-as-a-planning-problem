% =============================================================================
% SORTING COME PROBLEMA DI PIANIFICAZIONE DISCRETA
% =============================================================================
% Progetto 5 - Constraint Programming
%
% PROBLEMA: Dato un vettore di N interi (permutazione di 1..N), trovare il
%           numero MINIMO di scambi (swap) per ordinarlo in modo crescente.
%
% APPROCCIO: Modellato come sistema di transizione di stati:
%            - Stato: configurazione del vettore ad ogni timestep
%            - Azione: scambio di due posizioni
%            - Goal: raggiungere lo stato ordinato in K passi
%
% NOTA: Questo è un problema di SODDISFACIMENTO (SAT), non ottimizzazione.
%       Il K minimo viene trovato tramite Iterative Deepening in Python.
% =============================================================================

include "globals.mzn";

% =============================================================================
% INPUT - Parametri forniti dall'istanza
% =============================================================================
int: n;                       % Dimensione del vettore
array[1..n] of int: start_v;  % Permutazione iniziale (es. [2, 3, 1, 5, 4])
int: k;                       % Lunghezza del piano (numero di swap da eseguire)

% =============================================================================
% VARIABILI DECISIONALI
% =============================================================================

% v[t, p] = valore nella posizione p al timestep t
% - Riga t=0: stato iniziale (fissato a start_v)
% - Riga t=k: stato finale (deve essere ordinato)
% - Ogni riga intermedia: stato dopo t swap
array[0..k, 1..n] of var 1..n: v;

% pos[t, i] = posizione del valore i al timestep t
% Questo è il MODELLO DUALE (ridondante) usato per il channeling.
% Permette di accedere efficientemente alla posizione di un valore.
% Esempio: se v[0,..] = [2,3,1,5,4], allora pos[0,..] = [3,1,2,5,4]
%          (il valore 1 è in posizione 3, il valore 2 è in posizione 1, ecc.)
array[0..k, 1..n] of var 1..n: pos;

% idx1[t], idx2[t] = indici delle posizioni da scambiare al passo t
% Invariante: idx1[t] < idx2[t] (symmetry breaking sugli indici)
array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;


% =============================================================================
% VINCOLO 1: CONDIZIONI AL CONTORNO (Boundary Conditions)
% =============================================================================
% Scopo: Fissare lo stato iniziale e imporre che lo stato finale sia ordinato.
%
% - v[0, p] = start_v[p]: la prima riga della matrice v corrisponde all'input
% - v[k, p] <= v[k, p+1]: l'ultima riga deve essere ordinata in modo crescente
% =============================================================================

constraint forall(p in 1..n) (
    v[0, p] = start_v[p]  % Stato iniziale fissato
);

constraint forall(p in 1..n) (
    v[k, p] = p  % Stato finale = permutazione identità (più forte di "ordinato")
);


% =============================================================================
% VINCOLO 2: PARITÀ DELLE INVERSIONI (Parity Constraint)
% =============================================================================
% Scopo: Tagliare il 50% dello spazio di ricerca sfruttando la teoria delle
%        permutazioni.
%
% TEORIA:
% - Un'INVERSIONE è una coppia (i,j) con i < j ma v[i] > v[j]
% - Ogni SWAP cambia il numero di inversioni di ±1 (inverte la parità)
% - Lo stato ordinato ha 0 inversioni (PARI)
% - Quindi: K deve avere la stessa parità del numero iniziale di inversioni
%
% ESEMPIO:
%   [2, 3, 1, 5, 4] ha 3 inversioni: (1,3), (2,3), (4,5) → DISPARI
%   Quindi K deve essere DISPARI (K = 1, 3, 5, ...)
%
% EFFETTO: Se initial_inv è dispari, tutti i K pari sono impossibili e vengono
%          scartati senza esplorazione.
% =============================================================================

int: initial_inv = sum(i, j in 1..n where i < j)(
    bool2int(start_v[i] > start_v[j])  % Conta le inversioni nella permutazione iniziale
);

constraint (k mod 2) == (initial_inv mod 2);  % K e inversioni devono avere stessa parità


% =============================================================================
% VINCOLO 3: CHANNELING & GAC (Dual Model with Maximum Propagation)
% =============================================================================
% Scopo: Creare una rappresentazione duale valore↔posizione per massimizzare
%        la propagazione dei vincoli.
%
% VINCOLO INVERSE:
% - inverse(A, B) impone che A[i] = j ⟺ B[j] = i
% - Qui: v[t, p] = i ⟺ pos[t, i] = p
% - Ogni riduzione di dominio in v si propaga immediatamente a pos (e viceversa)
%
% ALLDIFFERENT :: DOMAIN:
% - Garantisce che tutti i valori in ogni riga siano distinti
% - L'annotazione ":: domain" attiva l'algoritmo di Régin per GAC
% - GAC (Generalized Arc Consistency) = massima propagazione possibile
%
% PERCHÉ È UTILE:
% - Se scopriamo che v[t, 3] ≠ 5, automaticamente pos[t, 5] ≠ 3
% - Riduce drasticamente il branching factor
% =============================================================================

constraint forall(t in 0..k) (
    % Channeling: collega v e pos tramite la relazione inversa
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\

    % GAC su alldifferent per propagazione massima
    alldifferent([v[t, p] | p in 1..n]) :: domain
);


% =============================================================================
% VINCOLO 4: LOGICA DELLO SWAP OTTIMALE (Optimal Swap Property)
% =============================================================================
% Scopo: Modellare la meccanica dello swap e imporre che ogni swap sia "utile".
%
% COMPONENTI:
%
% a) idx1[t] < idx2[t]
%    - SYMMETRY BREAKING: evita di contare (3,5) e (5,3) come swap diversi
%
% b) (v[t, idx2[t]] = idx1[t]) ∨ (v[t, idx1[t]] = idx2[t])
%    - PROPRIETÀ DI OTTIMALITÀ (dalla teoria dei gruppi):
%      In un piano di lunghezza MINIMA, ogni swap deve fissare almeno un
%      elemento nella sua posizione finale corretta.
%    - Se scambiamo posizioni idx1 e idx2:
%      * v[t, idx2[t]] = idx1[t] significa: "il valore in idx2 è proprio idx1,
%        quindi dopo lo swap andrà nella posizione giusta"
%      * Analogamente per l'altra condizione
%    - EFFETTO: Riduce il branching da O(N²) scambi possibili a O(N)
%
% c) v[t+1, idx1[t]] = v[t, idx2[t]] e v[t+1, idx2[t]] = v[t, idx1[t]]
%    - MECCANICA DELLO SWAP: i valori nelle due posizioni si scambiano
%
% d) forall(p ≠ idx1[t], idx2[t]): v[t+1, p] = v[t, p]
%    - FRAME AXIOM: tutto ciò che non è coinvolto nello swap rimane invariato
%    - Fondamentale nella pianificazione: specifica cosa NON cambia
% =============================================================================

constraint forall(t in 0..k-1) (
    % a) Symmetry breaking: idx1 sempre minore di idx2
    idx1[t] < idx2[t] /\

    % b) Proprietà di ottimalità: lo swap deve fissare almeno un elemento
    %    nella sua posizione corretta (derivato dalla teoria dei gruppi)
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\

    % c) Meccanica dello swap: scambia i valori nelle due posizioni
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\

    % d) Frame Axiom: le altre posizioni rimangono invariate
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);


% =============================================================================
% VINCOLO 5: ROTTURA DELLE SIMMETRIE (Symmetry Breaking on Swap Sequences)
% =============================================================================
% Scopo: Eliminare soluzioni equivalenti che rappresentano lo stesso piano
%        in ordine diverso.
%
% PARTE A: (idx1[t] ≠ idx1[t+1]) ∨ (idx2[t] ≠ idx2[t+1])
%    - Vieta swap IDENTICI consecutivi
%    - Due swap uguali di fila si annullano: Swap(2,3) + Swap(2,3) = nulla
%    - Impossibile in un piano ottimo
%
% PARTE B: Ordinamento lessicografico degli swap DISGIUNTI
%    - Due swap sono DISGIUNTI se non condividono alcuna posizione
%    - Swap disgiunti commutano: l'ordine non influenza il risultato
%    - Esempio: Swap(1,2) e Swap(4,5) possono essere eseguiti in qualsiasi ordine
%    - Per eliminare questa simmetria, imponiamo un ordine canonico:
%      Se gli swap t e t+1 sono disgiunti, allora idx1[t] < idx1[t+1]
%
% ESEMPIO:
%    Piano A: Swap(1,3), Swap(4,5)  ← accettato (1 < 4)
%    Piano B: Swap(4,5), Swap(1,3)  ← rifiutato (4 > 1, viola il vincolo)
%    Entrambi producono lo stesso risultato, ma solo A è ammesso.
% =============================================================================

constraint forall(t in 0..k-2) (
    % Parte A: No swap identici consecutivi
    (idx1[t] != idx1[t+1] \/ idx2[t] != idx2[t+1]) /\

    % Parte B: Ordinamento lessicografico per swap disgiunti
    let {
        % Verifica se i due swap sono completamente disgiunti
        % (nessuna posizione in comune)
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        % Se disgiunti, forza ordine lessicografico
        disjoint -> (idx1[t] < idx1[t+1])
    )
);


% =============================================================================
% VINCOLO 6: FIXED POINT PROPAGATION
% =============================================================================
% Scopo: Se un elemento è già nella sua posizione corretta (v[t, p] = p),
%        quella posizione NON deve essere coinvolta in swap futuri.
%
% RAZIONALE:
% - Un elemento "fissato" (v[t, p] = p) è già al posto giusto
% - Coinvolgerlo in uno swap lo sposterebbe inutilmente
% - In un piano ottimo, nessuna mossa "disfa" progresso già fatto
%
% EFFETTO: Riduce il branching eliminando mosse inutili
% =============================================================================

constraint forall(t in 0..k-1, p in 1..n) (
    v[t, p] = p -> (idx1[t] != p /\ idx2[t] != p)
);


% =============================================================================
% VINCOLO 7: NO SWAP RIPETUTI (Global Uniqueness)
% =============================================================================
% Scopo: Ogni coppia (i, j) può apparire AL MASSIMO UNA VOLTA nel piano.
%
% RAZIONALE:
% - Se (i,j) appare due volte consecutive → si annullano (già vietato dal vincolo 5A)
% - Se (i,j) appare due volte non consecutive → esiste un piano più corto
%   (gli swap intermedi potrebbero essere riorganizzati)
%
% DIMOSTRAZIONE (sketch):
%   Se Swap(i,j) appare ai tempi t1 e t2 (t1 < t2), gli elementi in i e j
%   tornano alle posizioni originali dopo t2. Quindi gli swap tra t1 e t2
%   avrebbero potuto agire direttamente → piano non ottimo.
%
% EFFETTO: Elimina ridondanze globali nel piano
% =============================================================================

constraint forall(t1 in 0..k-2, t2 in t1+1..k-1) (
    idx1[t1] != idx1[t2] \/ idx2[t1] != idx2[t2]
);


% =============================================================================
% STRATEGIA DI RICERCA
% =============================================================================
% Utilizziamo Gecode con Luby Restart come suggerito nelle slide CP 2025.
%
% LUBY RESTART:
% - Sequenza universale: 1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8, ...
% - Dopo 250 × L fallimenti (dove L è l'elemento corrente della sequenza),
%   il solver riparte dalla radice
% - Vantaggi: sfugge a zone "morte" dello spazio di ricerca, evita heavy-tail
%
% NOTA: La strategia di default di Gecode sceglie automaticamente le variabili
%       e i valori. Per strategie personalizzate, vedere sorting_template.mzn
% =============================================================================

solve :: restart_luby(250) satisfy;


% =============================================================================
% OUTPUT
% =============================================================================

output [
    "Plan found (k=\(k)):\n"
] ++
[
    "Step \(t): Swap(\(idx1[t]), \(idx2[t])) -> \(v[t+1, ..])\n"
    | t in 0..k-1
];