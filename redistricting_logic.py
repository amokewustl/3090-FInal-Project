"""
redistricting_logic.py - District validation and consensus generation
Includes full AvgDistrictMap.py functionality
"""
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import io
import base64

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

def validate_districts(districts):
    """
    Validate a district plan
    Returns: (is_valid, errors_list)
    """
    districts = np.array(districts)
    errors = []
    
    # Check 1: Must have exactly 5 districts (0-4)
    unique_districts = np.unique(districts)
    if len(unique_districts) != 5:
        errors.append(f"Must have exactly 5 districts. Found {len(unique_districts)}.")
        return False, errors
    
    # Check 2: Each district must have exactly 5 cells
    for d in range(5):
        count = np.sum(districts == d)
        if count != 5:
            errors.append(f"District {d +1} has {count} cells. Each district must have exactly 5 cells.")
    
    if errors:
        return False, errors
    
    # Check 3: Each district must be contiguous (4-connected)
    for d in range(5):
        if not is_contiguous(districts, d):
            errors.append(f"District {d +1} is not contiguous. All cells must connect by sides (not corners).")
    
    if errors:
        return False, errors
    
    return True, []

def is_contiguous(districts, district_num):
    """Check if a district is contiguous using flood fill"""
    H, W = districts.shape
    district_cells = np.argwhere(districts == district_num)
    
    if len(district_cells) == 0:
        return False
    
    # Start from first cell and flood fill
    visited = set()
    stack = [tuple(district_cells[0])]
    
    while stack:
        r, c = stack.pop()
        if (r, c) in visited:
            continue
        visited.add((r, c))
        
        # Check 4 neighbors (N, S, E, W)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W:
                if districts[nr, nc] == district_num and (nr, nc) not in visited:
                    stack.append((nr, nc))
    
    return len(visited) == len(district_cells)

def calculate_district_winners(districts, vote_grid):
    """
    Calculate which party wins each district
    Returns: dict {district_num: 'Hearts' or 'Clubs'}
    """
    districts = np.array(districts)
    vote_grid = np.array(vote_grid)
    winners = {}
    
    for d in range(5):
        district_mask = districts == d
        hearts = np.sum(vote_grid[district_mask] == 1)
        clubs = np.sum(vote_grid[district_mask] == 0)
        winners[d] = 'Hearts' if hearts > clubs else 'Clubs'
    
    return winners

def generate_consensus_maps(plans):
    """Generate consensus map from multiple plans (simplified version)"""
    if not plans:
        return None
    
    plans = [np.array(p) for p in plans]
    H, W = 5, 5
    n_plans = len(plans)
    
    # Build co-occurrence matrix
    co_occurrence = np.zeros((25, 25), dtype=float)
    
    for p in plans:
        flat = p.flatten()
        for i in range(25):
            for j in range(25):
                if flat[i] == flat[j]:
                    co_occurrence[i, j] += 1.0
    
    co_occurrence /= n_plans
    
    # Greedy clustering with contiguity
    def rc_to_idx(r, c):
        return r * W + c
    
    def idx_to_rc(idx):
        return divmod(idx, W)
    
    def get_neighbors(idx):
        r, c = idx_to_rc(idx)
        nbrs = []
        if r > 0: nbrs.append(rc_to_idx(r-1, c))
        if r < H-1: nbrs.append(rc_to_idx(r+1, c))
        if c > 0: nbrs.append(rc_to_idx(r, c-1))
        if c < W-1: nbrs.append(rc_to_idx(r, c+1))
        return nbrs
    
    assigned = np.zeros(25, dtype=bool)
    district_labels = np.full(25, -1, dtype=int)
    current_label = 0
    
    for start_idx in range(25):
        if assigned[start_idx]:
            continue
        
        district = [start_idx]
        assigned[start_idx] = True
        district_labels[start_idx] = current_label
        
        while len(district) < 5:
            candidates = np.where(~assigned)[0]
            if len(candidates) == 0:
                break
            
            district_set = set(district)
            contiguous = [c for c in candidates if any(n in district_set for n in get_neighbors(c))]
            
            if not contiguous:
                contiguous = candidates
            
            best_cand = max(contiguous, key=lambda c: co_occurrence[c, district].mean())
            
            assigned[best_cand] = True
            district_labels[best_cand] = current_label
            district.append(best_cand)
        
        current_label += 1
    
    return district_labels.reshape(H, W)

def generate_consensus_figure(consensus_map, title):
    """Generate matplotlib figure as base64 image"""
    if consensus_map is None:
        return None
    
    cmap = plt.get_cmap("tab10")
    colors = [cmap(i % 10) for i in range(5)]
    custom_cmap = ListedColormap(colors)
    
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(consensus_map, cmap=custom_cmap, vmin=0, vmax=4)
    
    # Grid lines
    ax.set_xticks(np.arange(-0.5, 5, 1))
    ax.set_yticks(np.arange(-0.5, 5, 1))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(color="black", linewidth=2)
    ax.set_title(title, fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


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


def get_compactness_report(label_map):
    """
    Get compactness metrics as a dictionary for JSON response
    """
    cut_edges, pp_scores, avg_pp = compute_compactness_metrics(label_map)
    
    districts_info = []
    for lab in sorted(pp_scores.keys()):
        color = TAB10_COLOR_NAMES.get(int(lab), "Unknown Color")
        districts_info.append({
            'district': int(lab),
            'color': color,
            'polsby_popper': round(pp_scores[lab], 3)
        })
    
    return {
        'cut_edges': cut_edges,
        'districts': districts_info,
        'avg_polsby_popper': round(avg_pp, 3)
    }


def rank_plans_by_compactness(plans):
    """
    Rank plans by compactness metrics
    Returns list of dicts with rankings
    """
    results = []
    
    for idx, plan in enumerate(plans):
        plan_array = np.array(plan['districts'])
        cut_edges, pp_scores, avg_pp = compute_compactness_metrics(plan_array)
        
        results.append({
            'id': plan['id'],
            'name': plan.get('user_name', f"Plan {idx+1}"),
            'type': plan['type'],
            'is_base': plan.get('is_base', False),
            'cut_edges': cut_edges,
            'avg_pp': round(avg_pp, 3)
        })
    
    # Sort by avg PP (descending) and then cut edges (ascending)
    results_sorted = sorted(
        results,
        key=lambda d: (-d["avg_pp"], d["cut_edges"])
    )
    
    return results_sorted