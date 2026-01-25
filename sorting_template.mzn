include "globals.mzn";

% =============================================================================
% INPUT
% =============================================================================
int: n;                       % Vector size
array[1..n] of int: start_v;  % Initial permutation
int: k;                       % Plan length (number of swaps to perform)

% =============================================================================
% DECISION VARIABLES
% =============================================================================

% State matrix: v[t, p] = value at position p at time t
array[0..k, 1..n] of var 1..n: v;

% Dual model for channeling: pos[t, i] = position of value i at time t
array[0..k, 1..n] of var 1..n: pos;

% Swap indices at step t
array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;

% =============================================================================
% AUXILIARY VARIABLE FOR SEARCH
% =============================================================================
% all_moves: flat array containing all moves in sequence
%
% Structure: [idx1[0], idx2[0], idx1[1], idx2[1], ..., idx1[k-1], idx2[k-1]]
%
% This variable allows specifying search strategies that operate on
% ALL moves simultaneously, rather than on the state matrix v.
%
% WHY IS IT USEFUL:
% - The variables idx1 and idx2 are the ones that actually determine
%   the plan structure (v is derived from the moves)
% - Focusing the search on moves is often more efficient
% - Allows heuristics like first_fail and dom_w_deg to operate on
%   the most "important" variables
% =============================================================================

array[1..2*k] of var 1..n: all_moves = [
    if i mod 2 == 1
    then idx1[i div 2]      % Odd positions: idx1[0], idx1[1], ...
    else idx2[(i-1) div 2]  % Even positions: idx2[0], idx2[1], ...
    endif
    | i in 1..2*k
];


% =============================================================================
% CONSTRAINT 1: BOUNDARY CONDITIONS
% =============================================================================
% Initial state = input permutation
% Final state = identity permutation (v[k, p] = p for all p)
%
% NOTE: The constraint v[k, p] = p is stronger than v[k, p] <= v[k, p+1]
%       and improves backward propagation. It is repeated in constraint 6
%       for clarity, but the solver optimizes it automatically.
% =============================================================================

constraint forall(p in 1..n) (v[0, p] = start_v[p]);


% =============================================================================
% CONSTRAINT 2: CHANNELING & GAC
% =============================================================================
% Links v (value->position) with pos (position->value) via inverse.
% Uses alldifferent with GAC for maximum propagation.
% =============================================================================

constraint forall(t in 0..k) (
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\
    alldifferent([v[t, p] | p in 1..n]) :: domain
);


% =============================================================================
% CONSTRAINT 3: OPTIMAL SWAP (Group Theory Lower Bound)
% =============================================================================
% Each move MUST fix at least one element in its correct position.
% This derives from group theory on permutations and guarantees that
% the plan is of minimum length.
% =============================================================================

constraint forall(t in 0..k-1) (
    % Symmetry breaking: first index always less than the second
    idx1[t] < idx2[t] /\

    % Optimality property: the swap fixes at least one element
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\

    % Swap mechanics
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\

    % Frame Axiom: positions not involved remain unchanged
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);


% =============================================================================
% CONSTRAINT 4: SYMMETRY BREAKING (Disjoint Swaps)
% =============================================================================
% Lexicographically orders swaps that do not share positions.
% Two disjoint swaps can be executed in any order, so we impose
% a canonical order to eliminate symmetric solutions.
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
% CONSTRAINT 5: FIXED POINT PROPAGATION
% =============================================================================
% If an element is in its correct position (v[t, p] = p), that position
% must NEVER be involved in future swaps.
% Rationale: a swap on a fixed point would displace it unnecessarily.
% =============================================================================

constraint forall(t in 0..k-1, p in 1..n) (
    v[t, p] = p -> (idx1[t] != p /\ idx2[t] != p)
);


% =============================================================================
% CONSTRAINT 6: EXPLICIT FINAL STATE (IDENTITY)
% =============================================================================
% The final state must be exactly the identity permutation.
% Although implicit from the ordering constraint, making it explicit
% can improve backward propagation.
% =============================================================================

constraint forall(p in 1..n) (v[k, p] = p);


% =============================================================================
% CONSTRAINT 7: NO REPEATED SWAPS (GLOBAL)
% =============================================================================
% Each pair (i, j) can appear AT MOST ONCE in the plan.
% In an optimal solution, repeating a swap is always useless:
% - If (i,j) appears twice consecutively: they cancel out
% - If (i,j) appears non-consecutively: a shorter plan exists
% =============================================================================

constraint forall(t1 in 0..k-2, t2 in t1+1..k-1) (
    idx1[t1] != idx1[t2] \/ idx2[t1] != idx2[t2]
);


% =============================================================================
% SEARCH STRATEGY (PLACEHOLDER)
% =============================================================================
% This placeholder is dynamically replaced by benchmark_strategies.py
% with one of the following strategies:
%
% BASE STRATEGIES:
% ----------------
% 1. DEFAULT:
%    solve :: restart_luby(250) satisfy;
%    -> Uses Gecode's default heuristic
%
% 2. FIRSTFAIL:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, first_fail, indomain_random, complete) satisfy;
%    -> first_fail: chooses variable with smallest domain
%
% 3. DOMWDEG:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;
%    -> dom_w_deg: domain / weighted degree (adaptive heuristic)
%    -> Learns from failures: penalizes "problematic" variables
%
% ADVANCED VARIABLE SELECTION STRATEGIES:
% ---------------------------------------
% 4. SMALLEST:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, smallest, indomain_min, complete) satisfy;
%    -> smallest: chooses variable with minimum value in domain
%
% 5. MOSTCONSTRAINED:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, most_constrained, indomain_random, complete) satisfy;
%    -> most_constrained: first_fail + constraint count (more aggressive)
%
% 6. MAXREGRET:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, max_regret, indomain_random, complete) satisfy;
%    -> max_regret: maximizes difference between best and second-best value
%
% 7. ANTIFIRSTFAIL:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, anti_first_fail, indomain_random, complete) satisfy;
%    -> anti_first_fail: chooses variable with LARGEST domain
%
% BISECTION STRATEGIES:
% ---------------------
% 8. DOMWDEG_SPLIT:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, dom_w_deg, indomain_split, complete) satisfy;
%    -> indomain_split: splits domain in half instead of enumerating
%
% 9. FIRSTFAIL_SPLIT:
%    solve :: restart_luby(250)
%          :: int_search(all_moves, first_fail, indomain_split, complete) satisfy;
%    -> Combines first_fail with bisection
%
% ALTERNATIVE RESTART STRATEGIES:
% -------------------------------
% 10. GEOMETRIC:
%     solve :: restart_geometric(1.5, 100)
%           :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;
%     -> Geometric restart: scales x1.5 each time (100, 150, 225, ...)
%
% 11. LINEAR:
%     solve :: restart_linear(250)
%           :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;
%     -> Linear restart: fixed increment (250, 500, 750, ...)
%
% 12. NORESTART:
%     solve :: int_search(all_moves, dom_w_deg, indomain_random, complete) satisfy;
%     -> NO restart - baseline for comparison
%
% LUBY RESTART (used by strategies 1-9):
%    Sequence: 1,1,2,1,1,2,4,1,1,2,1,1,2,4,8,...
%    Scale: 250 (restarts after 250*L failures)
%    Purpose: escape "dead" zones of the search space
% =============================================================================

{{SOLVE_STRATEGY}}