include "globals.mzn";

% --- INPUT ---
int: n;                      
array[1..n] of int: start_v; 
int: k;                      

% --- VARIABILI ---
array[0..k, 1..n] of var 1..n: v;
array[0..k, 1..n] of var 1..n: pos; % Modello ridondante (Channeling)

array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;

% --- VINCOLI BASATI SULLA LETTERATURA TECNICA ---

% 1. Condizioni al contorno
constraint forall(p in 1..n) (v[0, p] = start_v[p]);
constraint forall(p in 1..n-1) (v[k, p] <= v[k, p+1]);

% 2. VINCOLO DI PARITÀ (Da teoria delle permutazioni)
% Ogni scambio inverte la parità. Questo taglia il 50% dei k impossibili.
int: initial_inv = sum(i, j in 1..n where i < j)(bool2int(start_v[i] > start_v[j]));
constraint (k mod 2) == (initial_inv mod 2);

% 3. CHANNELING & GAC (Propagazione massima)
constraint forall(t in 0..k) (
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\
    alldifferent([v[t, p] | p in 1..n]) :: domain
);

% 4. LOGICA DELLO SWAP OTTIMALE (Group Theory Lower Bound)
constraint forall(t in 0..k-1) (
    idx1[t] < idx2[t] /\
    
    % In un piano ottimo, ogni scambio sistema almeno un elemento
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\
    
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);

% 5. ROTTURA DELLE SIMMETRIE (Symmetry Breaking)
constraint forall(t in 0..k-2) (
    (idx1[t] != idx1[t+1] \/ idx2[t] != idx2[t+1]) /\
    let {
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\ 
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        disjoint -> (idx1[t] < idx1[t+1])
    )
);

% --- RICERCA ---
% Utilizziamo Gecode con restarts come suggerito nelle slide CP 2025
solve :: restart_luby(250) satisfy;

output [
    "Plan found (k=\(k)):\n"
] ++
[
    "Step \(t): Swap(\(idx1[t]), \(idx2[t])) -> \(v[t+1, ..])\n" 
    | t in 0..k-1
];