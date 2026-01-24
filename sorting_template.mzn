include "globals.mzn";

int: n;                      
array[1..n] of int: start_v; 
int: k;                      

array[0..k, 1..n] of var 1..n: v;
array[0..k, 1..n] of var 1..n: pos; % Dual model (Channeling)

array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;

array[1..2*k] of var 1..n: all_moves = [
    if i mod 2 == 1 then idx1[i div 2] else idx2[(i-1) div 2] endif | i in 1..2*k
];

% 1. Stato Iniziale e Finale
constraint forall(p in 1..n) (v[0, p] = start_v[p]);
constraint forall(p in 1..n-1) (v[k, p] <= v[k, p+1]);

% 2. Channeling & GAC (Propagazione Massima)
constraint forall(t in 0..k) (
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\
    alldifferent([v[t, p] | p in 1..n]) :: domain
);

% 3. Vincolo di Ottimalita (The Group Theory Swap)
% Ogni mossa DEVE mettere almeno un elemento nella sua posizione finale corretta.
constraint forall(t in 0..k-1) (
    idx1[t] < idx2[t] /\
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\
    
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);

% 4. Symmetry Breaking
constraint forall(t in 0..k-2) (
    let {
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\ 
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        disjoint -> (idx1[t] < idx1[t+1])
    )
);

{{SOLVE_STRATEGY}}