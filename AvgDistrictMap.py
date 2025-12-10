"""
average_district_map.py

Computes an "average" (consensus) district map from many 5×5 districting plans
ensuring exactly 5 districts with 5 cells each.
"""

import numpy as np
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


# ---------------------------------------------------------
# 1. Find most common district assignment for each cell
# ---------------------------------------------------------

def build_consensus_map_by_modal_neighbors(plans, height=5, width=5, cells_per_district=5):
    """
    Build a label-invariant consensus district map from multiple 2D plans.

    - plans: list of HxW numpy arrays with integer labels
    - height, width: grid size (default 5x5)
    - cells_per_district: how many cells each district must have (default 5)

    Enforces contiguity: each district is grown by only adding cells that are
    4-neighbors (N/S/E/W) of at least one cell already in the district.
    """
    plans = [np.array(p) for p in plans]
    H, W = height, width
    n_cells = H * W
    n_plans = len(plans)

    # Helper: convert between (row, col) and flat index
    def rc_to_idx(r, c):
        return r * W + c

    def idx_to_rc(idx):
        return divmod(idx, W)  # (row, col)

    # Helper: 4-neighbors (N,S,E,W) of a flat index
    def get_neighbors(idx):
        r, c = idx_to_rc(idx)
        nbrs = []
        if r > 0:      nbrs.append(rc_to_idx(r - 1, c))
        if r < H - 1:  nbrs.append(rc_to_idx(r + 1, c))
        if c > 0:      nbrs.append(rc_to_idx(r, c - 1))
        if c < W - 1:  nbrs.append(rc_to_idx(r, c + 1))
        return nbrs

    # ----- 1. Build co-occurrence matrix (label-invariant similarity) -----
    co_occurrence = np.zeros((n_cells, n_cells), dtype=float)

    for p in plans:
        flat = p.flatten()
        for i in range(n_cells):
            for j in range(n_cells):
                if flat[i] == flat[j]:
                    co_occurrence[i, j] += 1.0

    co_occurrence /= n_plans  # convert to fraction of plans

    # ----- 2. Greedy clustering with contiguity constraint -----
    assigned = np.zeros(n_cells, dtype=bool)
    district_labels = np.full(n_cells, -1, dtype=int)
    current_label = 0

    for start_idx in range(n_cells):
        if assigned[start_idx]:
            continue

        # Start a new district with this cell
        district = [start_idx]
        assigned[start_idx] = True
        district_labels[start_idx] = current_label

        # Grow district until we hit the required size
        while len(district) < cells_per_district:
            candidates = np.where(~assigned)[0]

            if len(candidates) == 0:
                break  # nothing left to assign (shouldn't happen in 5x5 case)

            # ---- contiguity filter: only candidates that touch the district ----
            district_set = set(district)
            contiguous_candidates = []
            for cand in candidates:
                nbrs = get_neighbors(cand)
                if any(n in district_set for n in nbrs):
                    contiguous_candidates.append(cand)

            # If no candidate is adjacent (very unlikely), fall back to all candidates
            if len(contiguous_candidates) == 0:
                contiguous_candidates = candidates

            # Pick candidate with highest average co-occurrence with current district
            best_cand = None
            best_score = -1.0
            for cand in contiguous_candidates:
                score = co_occurrence[cand, district].mean()
                if score > best_score:
                    best_score = score
                    best_cand = cand

            # Assign that cell to the district
            assigned[best_cand] = True
            district_labels[best_cand] = current_label
            district.append(best_cand)

        current_label += 1

    # ----- 3. Reshape back to HxW grid -----
    consensus_map = district_labels.reshape(H, W)
    return consensus_map



# ---------------------------------------------------------
# 2. Visualization
# ---------------------------------------------------------

def show_consensus_map(labels, title="Consensus District Map", fig_num=None):
    """
    Plot each district in a different color.
    """
    H, W = labels.shape
    districts = np.unique(labels)
    num_districts = len(districts)

    cmap = plt.get_cmap("tab10")
    colors = [cmap(i % 10) for i in range(num_districts)]
    custom_cmap = ListedColormap(colors)

    plt.figure(num=fig_num, figsize=(5, 5))
    plt.imshow(labels, cmap=custom_cmap, vmin=0, vmax=num_districts - 1)

    # Draw clear grid lines
    plt.xticks(np.arange(-0.5, W, 1), [])
    plt.yticks(np.arange(-0.5, H, 1), [])
    plt.grid(color="black", linewidth=1)

    plt.title(title)
    plt.tight_layout()
   
    # Print district sizes
    unique, counts = np.unique(labels, return_counts=True)
    print(f"  District sizes: {dict(zip(unique, counts))}")




# --------------------------------------------------------
# Compactness Calculation
# --------------------------------------------------------
# Color names matching matplotlib's tab10 colormap indices
TAB10_COLOR_NAMES = {
    0: "Blue",
    1: "Orange",
    2: "Green",
    3: "Red",
    4: "Purple",
    5: "Brown",
    6: "Pink",
    7: "Gray",
    8: "Yellow-Green",
    9: "Cyan"
}


def compute_compactness_metrics(label_map):
    """
    Compute two compactness metrics for a labeled grid:
      - cut_edges: number of edges where neighboring cells have different labels
      - polsby_popper: dict[label] -> Polsby–Popper score for that district

    label_map: 2D numpy array of district labels
    """
    label_map = np.array(label_map)
    H, W = label_map.shape
    labels = np.unique(label_map)

    # Area and perimeter for each district
    area = {int(l): 0 for l in labels}
    perimeter = {int(l): 0 for l in labels}

    cut_edges = 0

    for r in range(H):
        for c in range(W):
            lab = int(label_map[r, c])
            area[lab] += 1

            # --- perimeter contributions (4-neighborhood) ---
            # Up
            if r == 0 or label_map[r - 1, c] != lab:
                perimeter[lab] += 1
            # Down
            if r == H - 1 or label_map[r + 1, c] != lab:
                perimeter[lab] += 1
            # Left
            if c == 0 or label_map[r, c - 1] != lab:
                perimeter[lab] += 1
            # Right
            if c == W - 1 or label_map[r, c + 1] != lab:
                perimeter[lab] += 1

            # --- cut edges (only count each interior edge once) ---
            if c + 1 < W and label_map[r, c] != label_map[r, c + 1]:
                cut_edges += 1
            if r + 1 < H and label_map[r, c] != label_map[r + 1, c]:
                cut_edges += 1

    # Polsby–Popper for each district
    polsby_popper = {}
    for lab in labels:
        lab = int(lab)
        A = area[lab]
        P = perimeter[lab]
        if P > 0:
            polsby_popper[lab] = 4.0 * np.pi * A / (P ** 2)
        else:
            polsby_popper[lab] = 0.0

    # Also return an overall average PP
    avg_pp = float(np.mean(list(polsby_popper.values())))

    return cut_edges, polsby_popper, avg_pp


def print_compactness_report(name, label_map):
    """
    Pretty-print compactness metrics for a given labeled map.
    Includes color names corresponding to tab10 colormap indices.
    """
    cut_edges, pp_scores, avg_pp = compute_compactness_metrics(label_map)
    print(f"\nCompactness metrics for {name}:")
    print(f"  Cut edges: {cut_edges}")
    print(f"  Polsby–Popper per district:")
    for lab in sorted(pp_scores.keys()):
        color = TAB10_COLOR_NAMES.get(int(lab), "Unknown Color")
        print(f"    District {lab} ({color}): {pp_scores[lab]:.3f}")
    print(f"  Average Polsby–Popper: {avg_pp:.3f}")


# --------------------------------------------------------
# Ranking original plans by compactness
# --------------------------------------------------------
def rank_and_print_plans_by_compactness(plans, name_prefix="Plan"):
    """
    For a list of labeled grids (plans), compute compactness metrics and
    print a ranking based on:
      - primary: average Polsby–Popper (higher is better)
      - tie-breaker: cut edges (fewer is better)
    """
    results = []

    for idx, p in enumerate(plans):
        cut_edges, pp_scores, avg_pp = compute_compactness_metrics(p)
        plan_name = f"{name_prefix} {idx + 1}"
        results.append({
            "index": idx,
            "name": plan_name,
            "cut_edges": cut_edges,
            "avg_pp": avg_pp
        })

    # Sort by avg PP (descending) and then cut edges (ascending)
    results_sorted = sorted(
        results,
        key=lambda d: (-d["avg_pp"], d["cut_edges"])
    )

    print(f"\nRanking of {name_prefix}s by compactness "
          f"(higher avg Polsby–Popper, fewer cut edges = better):")

    for rank, r in enumerate(results_sorted, start=1):
        print(
            f"{rank}. {r['name']}: "
            f"avg PP = {r['avg_pp']:.3f}, "
            f"cut edges = {r['cut_edges']}"
        )

    return results_sorted





# ---------------------------------------------------------
# 3. Main - Generate 3 consensus maps
# ---------------------------------------------------------

if __name__ == "__main__":
    # Load plans from separate file
    from Plans import all_plans, neutral_plans, hearts_representative_plans
   
    # Generate consensus map for all plans
    print("=" * 60)
    print("CONSENSUS MAP: ALL PLANS")
    print("=" * 60)
    consensus_all = build_consensus_map_by_modal_neighbors(all_plans)
    print("Consensus district labels:")
    print(consensus_all)
    print("Number of districts:", len(np.unique(consensus_all)))
    show_consensus_map(consensus_all, title="Consensus Map - All Plans (n=20)", fig_num=1)
    print()
   
    # Generate consensus map for neutral plans
    print("=" * 60)
    print("CONSENSUS MAP: NEUTRAL PLANS")
    print("=" * 60)
    consensus_neutral = build_consensus_map_by_modal_neighbors(neutral_plans)
    print("Consensus district labels:")
    print(consensus_neutral)
    print("Number of districts:", len(np.unique(consensus_neutral)))
    show_consensus_map(consensus_neutral, title="Consensus Map - Neutral Plans (n=10)", fig_num=2)
    print()
   
    # Generate consensus map for hearts representative plans
    print("=" * 60)
    print("CONSENSUS MAP: HEARTS REPRESENTATIVE PLANS")
    print("=" * 60)
    consensus_hearts = build_consensus_map_by_modal_neighbors(hearts_representative_plans)
    print("Consensus district labels:")
    print(consensus_hearts)
    print("Number of districts:", len(np.unique(consensus_hearts)))
    show_consensus_map(consensus_hearts, title="Consensus Map - Hearts Representative Plans (n=10)", fig_num=3)
    print()

    # After computing the three consensus maps...
    print_compactness_report("ALL PLANS consensus", consensus_all)
    print_compactness_report("NEUTRAL PLANS consensus", consensus_neutral)
    print_compactness_report("HEARTS REPRESENTATIVE PLANS consensus", consensus_hearts)

    # --- Rank original survey plans by compactness ---
    rank_and_print_plans_by_compactness(all_plans, name_prefix="Survey Plan")

    # (Optional) you can also separately rank subsets if you want:
    # rank_and_print_plans_by_compactness(neutral_plans, name_prefix="Neutral Plan")
    # rank_and_print_plans_by_compactness(hearts_representative_plans, name_prefix="Hearts Rep Plan")

    plt.show()

   
    # Show all plots at once
    print("=" * 60)
    print("Displaying all 3 consensus maps...")
    print("=" * 60)
    plt.show()