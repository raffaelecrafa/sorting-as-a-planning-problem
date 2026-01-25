% =============================================================================
% SORTING AS A DISCRETE PLANNING PROBLEM
% =============================================================================
% Project 5 - Constraint Programming
%
% PROBLEM: Given a vector of N integers (permutation of 1..N), find the
%          MINIMUM number of swaps to sort it in ascending order.
%
% APPROACH: Modeled as a state-transition system:
%           - State: vector configuration at each timestep
%           - Action: swap of two positions
%           - Goal: reach the sorted state in K steps
%
% NOTE: This is a SATISFACTION (SAT) problem, not optimization.
%       The minimum K is found via Iterative Deepening in Python.
% =============================================================================

include "globals.mzn";

% =============================================================================
% INPUT - Parameters provided by the instance
% =============================================================================
int: n;                       % Vector size
array[1..n] of int: start_v;  % Initial permutation (e.g., [2, 3, 1, 5, 4])
int: k;                       % Plan length (number of swaps to perform)

% =============================================================================
% DECISION VARIABLES
% =============================================================================

% v[t, p] = value at position p at timestep t
% - Row t=0: initial state (fixed to start_v)
% - Row t=k: final state (must be sorted)
% - Intermediate rows: state after t swaps
array[0..k, 1..n] of var 1..n: v;

% pos[t, i] = position of value i at timestep t
% This is the DUAL MODEL (redundant) used for channeling.
% Allows efficient access to the position of a value.
% Example: if v[0,..] = [2,3,1,5,4], then pos[0,..] = [3,1,2,5,4]
%          (value 1 is at position 3, value 2 is at position 1, etc.)
array[0..k, 1..n] of var 1..n: pos;

% idx1[t], idx2[t] = indices of positions to swap at step t
% Invariant: idx1[t] < idx2[t] (symmetry breaking on indices)
array[0..k-1] of var 1..n: idx1;
array[0..k-1] of var 1..n: idx2;


% =============================================================================
% CONSTRAINT 1: BOUNDARY CONDITIONS
% =============================================================================
% Purpose: Fix the initial state and require the final state to be sorted.
%
% - v[0, p] = start_v[p]: the first row of matrix v corresponds to the input
% - v[k, p] <= v[k, p+1]: the last row must be sorted in ascending order
% =============================================================================

constraint forall(p in 1..n) (
    v[0, p] = start_v[p]  % Initial state fixed
);

constraint forall(p in 1..n) (
    v[k, p] = p  % Final state = identity permutation (stronger than "sorted")
);


% =============================================================================
% CONSTRAINT 2: INVERSION PARITY (Parity Constraint)
% =============================================================================
% Purpose: Cut 50% of the search space by exploiting permutation theory.
%
% THEORY:
% - An INVERSION is a pair (i,j) with i < j but v[i] > v[j]
% - Each SWAP changes the inversion count by +/-1 (inverts the parity)
% - The sorted state has 0 inversions (EVEN)
% - Therefore: K must have the same parity as the initial inversion count
%
% EXAMPLE:
%   [2, 3, 1, 5, 4] has 3 inversions: (1,3), (2,3), (4,5) -> ODD
%   Therefore K must be ODD (K = 1, 3, 5, ...)
%
% EFFECT: If initial_inv is odd, all even K values are impossible and
%         are discarded without exploration.
% =============================================================================

int: initial_inv = sum(i, j in 1..n where i < j)(
    bool2int(start_v[i] > start_v[j])  % Count inversions in initial permutation
);

constraint (k mod 2) == (initial_inv mod 2);  % K and inversions must have same parity


% =============================================================================
% CONSTRAINT 3: CHANNELING & GAC (Dual Model with Maximum Propagation)
% =============================================================================
% Purpose: Create a dual value<->position representation to maximize
%          constraint propagation.
%
% INVERSE CONSTRAINT:
% - inverse(A, B) enforces that A[i] = j <=> B[j] = i
% - Here: v[t, p] = i <=> pos[t, i] = p
% - Every domain reduction in v propagates immediately to pos (and vice versa)
%
% ALLDIFFERENT :: DOMAIN:
% - Guarantees that all values in each row are distinct
% - The ":: domain" annotation activates Regin's algorithm for GAC
% - GAC (Generalized Arc Consistency) = maximum possible propagation
%
% WHY IS IT USEFUL:
% - If we discover that v[t, 3] != 5, automatically pos[t, 5] != 3
% - Drastically reduces the branching factor
% =============================================================================

constraint forall(t in 0..k) (
    % Channeling: links v and pos via the inverse relation
    inverse([v[t, p] | p in 1..n], [pos[t, i] | i in 1..n]) /\

    % GAC on alldifferent for maximum propagation
    alldifferent([v[t, p] | p in 1..n]) :: domain
);


% =============================================================================
% CONSTRAINT 4: OPTIMAL SWAP LOGIC (Optimal Swap Property)
% =============================================================================
% Purpose: Model swap mechanics and enforce that each swap is "useful".
%
% COMPONENTS:
%
% a) idx1[t] < idx2[t]
%    - SYMMETRY BREAKING: avoids counting (3,5) and (5,3) as different swaps
%
% b) (v[t, idx2[t]] = idx1[t]) \/ (v[t, idx1[t]] = idx2[t])
%    - OPTIMALITY PROPERTY (from group theory):
%      In a MINIMUM length plan, each swap must fix at least one
%      element in its final correct position.
%    - If we swap positions idx1 and idx2:
%      * v[t, idx2[t]] = idx1[t] means: "the value at idx2 is exactly idx1,
%        so after the swap it will go to the correct position"
%      * Similarly for the other condition
%    - EFFECT: Reduces branching from O(N^2) possible swaps to O(N)
%
% c) v[t+1, idx1[t]] = v[t, idx2[t]] and v[t+1, idx2[t]] = v[t, idx1[t]]
%    - SWAP MECHANICS: the values at the two positions are exchanged
%
% d) forall(p != idx1[t], idx2[t]): v[t+1, p] = v[t, p]
%    - FRAME AXIOM: everything not involved in the swap remains unchanged
%    - Fundamental in planning: specifies what does NOT change
% =============================================================================

constraint forall(t in 0..k-1) (
    % a) Symmetry breaking: idx1 always less than idx2
    idx1[t] < idx2[t] /\

    % b) Optimality property: the swap must fix at least one element
    %    in its correct position (derived from group theory)
    (v[t, idx2[t]] = idx1[t] \/ v[t, idx1[t]] = idx2[t]) /\

    % c) Swap mechanics: exchange values at the two positions
    v[t+1, idx1[t]] = v[t, idx2[t]] /\
    v[t+1, idx2[t]] = v[t, idx1[t]] /\

    % d) Frame Axiom: other positions remain unchanged
    forall(p in 1..n where p != idx1[t] /\ p != idx2[t]) (
        v[t+1, p] = v[t, p]
    )
);


% =============================================================================
% CONSTRAINT 5: SYMMETRY BREAKING (Symmetry Breaking on Swap Sequences)
% =============================================================================
% Purpose: Eliminate equivalent solutions that represent the same plan
%          in different order.
%
% PART A: (idx1[t] != idx1[t+1]) \/ (idx2[t] != idx2[t+1])
%    - Forbids IDENTICAL consecutive swaps
%    - Two identical swaps in a row cancel each other: Swap(2,3) + Swap(2,3) = nothing
%    - Impossible in an optimal plan
%
% PART B: Lexicographic ordering of DISJOINT swaps
%    - Two swaps are DISJOINT if they share no position
%    - Disjoint swaps commute: the order doesn't affect the result
%    - Example: Swap(1,2) and Swap(4,5) can be executed in any order
%    - To eliminate this symmetry, we impose a canonical order:
%      If swaps at t and t+1 are disjoint, then idx1[t] < idx1[t+1]
%
% EXAMPLE:
%    Plan A: Swap(1,3), Swap(4,5)  <- accepted (1 < 4)
%    Plan B: Swap(4,5), Swap(1,3)  <- rejected (4 > 1, violates constraint)
%    Both produce the same result, but only A is allowed.
% =============================================================================

constraint forall(t in 0..k-2) (
    % Part A: No identical consecutive swaps
    (idx1[t] != idx1[t+1] \/ idx2[t] != idx2[t+1]) /\

    % Part B: Lexicographic ordering for disjoint swaps
    let {
        % Check if the two swaps are completely disjoint
        % (no position in common)
        var bool: disjoint = (idx1[t] != idx1[t+1] /\ idx1[t] != idx2[t+1] /\
                              idx2[t] != idx1[t+1] /\ idx2[t] != idx2[t+1])
    } in (
        % If disjoint, force lexicographic order
        disjoint -> (idx1[t] < idx1[t+1])
    )
);


% =============================================================================
% CONSTRAINT 6: FIXED POINT PROPAGATION
% =============================================================================
% Purpose: If an element is already in its correct position (v[t, p] = p),
%          that position must NOT be involved in future swaps.
%
% RATIONALE:
% - A "fixed" element (v[t, p] = p) is already in the right place
% - Involving it in a swap would displace it unnecessarily
% - In an optimal plan, no move "undoes" progress already made
%
% EFFECT: Reduces branching by eliminating useless moves
% =============================================================================

constraint forall(t in 0..k-1, p in 1..n) (
    v[t, p] = p -> (idx1[t] != p /\ idx2[t] != p)
);


% =============================================================================
% CONSTRAINT 7: NO REPEATED SWAPS (Global Uniqueness)
% =============================================================================
% Purpose: Each pair (i, j) can appear AT MOST ONCE in the plan.
%
% RATIONALE:
% - If (i,j) appears twice consecutively -> they cancel (already forbidden by constraint 5A)
% - If (i,j) appears twice non-consecutively -> a shorter plan exists
%   (intermediate swaps could be reorganized)
%
% PROOF (sketch):
%   If Swap(i,j) appears at times t1 and t2 (t1 < t2), the elements at i and j
%   return to their original positions after t2. Therefore the swaps between t1 and t2
%   could have acted directly -> plan is not optimal.
%
% EFFECT: Eliminates global redundancies in the plan
% =============================================================================

constraint forall(t1 in 0..k-2, t2 in t1+1..k-1) (
    idx1[t1] != idx1[t2] \/ idx2[t1] != idx2[t2]
);


% =============================================================================
% SEARCH STRATEGY
% =============================================================================
% We use Gecode with Luby Restart as suggested in CP 2025 slides.
%
% LUBY RESTART:
% - Universal sequence: 1, 1, 2, 1, 1, 2, 4, 1, 1, 2, 1, 1, 2, 4, 8, ...
% - After 250 * L failures (where L is the current sequence element),
%   the solver restarts from the root
% - Advantages: escapes "dead" zones of the search space, avoids heavy-tail
%
% NOTE: Gecode's default strategy automatically chooses variables
%       and values. For custom strategies, see sorting_template.mzn
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