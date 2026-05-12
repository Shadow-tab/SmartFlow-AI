"""
csp_scheduler.py
----------------
The CSP Scheduler / Control Allocation Module for SmartFlow AI.
Assigns GREEN or RED signal phases to intersections using a
backtracking CSP solver. Ensures no two conflicting (adjacent)
intersections are both GREEN simultaneously.
When emergency corridor is active, the route intersections
are forced GREEN to clear the path for the emergency vehicle.
"""

# ------------------------------------------------------------------
# INTERSECTION DEFINITIONS
# Based on the CSP graph in the project specification PDF.
# Variables = intersections, Domain = {GREEN, RED}
# ------------------------------------------------------------------

# The 5 signal-controlled intersections in our city
INTERSECTIONS = [
    "Central_Junction",    # S1
    "North_Station",       # S2
    "East_Market",         # S3
    "River_Bridge",        # S4
    "City_Hospital",       # S5
]

# Conflict pairs — these two intersections cannot both be GREEN
# (they share a road segment or create a collision risk)
# Based on the "in conflict" edges from the CSP graph in the PDF
CONFLICT_PAIRS = [
    ("Central_Junction", "North_Station"),   # S1 ↔ S2 conflict
    ("Central_Junction", "East_Market"),     # S1 ↔ S3 conflict
    ("North_Station",    "East_Market"),     # S2 ↔ S3 (via coordination)
    ("River_Bridge",     "North_Station"),   # S4 ↔ S2 coordination
]

# Domain options for each intersection
SIGNAL_DOMAIN = ["GREEN", "RED"]


def _is_consistent(intersection, assigned_value, current_assignment):
    """
    Constraint check function used during backtracking.
    Returns True if assigning 'assigned_value' to 'intersection'
    does not violate any conflict pair with already-assigned intersections.
    Two intersections conflict if both are assigned GREEN.
    """
    for (node_a, node_b) in CONFLICT_PAIRS:
        # Check if this intersection is part of a conflict pair
        if node_a == intersection and node_b in current_assignment:
            if assigned_value == "GREEN" and current_assignment[node_b] == "GREEN":
                return False   # Conflict: both would be GREEN
        if node_b == intersection and node_a in current_assignment:
            if assigned_value == "GREEN" and current_assignment[node_a] == "GREEN":
                return False   # Conflict: both would be GREEN
    return True   # No conflicts found — assignment is safe


def _backtrack(remaining_intersections, current_assignment, forced_green):
    """
    Recursive backtracking solver.
    Tries to assign GREEN or RED to each unassigned intersection.
    Forced-green intersections (emergency corridor) skip the domain
    loop and are assigned GREEN directly.

    Returns a complete assignment dict if solution found,
    or None if no valid assignment exists.
    """

    # Base case — all intersections assigned
    if not remaining_intersections:
        return current_assignment

    # Pick the next unassigned intersection (first in list)
    current_node = remaining_intersections[0]
    rest         = remaining_intersections[1:]

    # If this intersection is forced GREEN (emergency corridor), skip RED option
    domain_to_try = ["GREEN"] if current_node in forced_green else SIGNAL_DOMAIN

    for signal_value in domain_to_try:
        if _is_consistent(current_node, signal_value, current_assignment):
            # Tentatively assign this value
            current_assignment[current_node] = signal_value

            # Recurse into the remaining intersections
            result = _backtrack(rest, current_assignment, forced_green)

            if result is not None:
                return result   # Solution found — propagate it up

            # Backtrack — remove this assignment and try next value
            del current_assignment[current_node]

    return None   # No valid assignment found from this branch


def run_csp_scheduler(clean_request, emergency=False):
    """
    Main CSP entry point. Determines which intersections need
    signal control based on the request, forces emergency corridor
    intersections to GREEN when applicable, and runs the backtracking
    solver to find a valid signal assignment plan.

    Parameters:
      clean_request : dict — the validated request from preprocessing
      emergency     : bool — True when emergency corridor was granted by KB

    Returns a dict containing:
      - signal_plan    : dict mapping intersection → GREEN/RED
      - status         : "solved" or "no_solution"
      - emergency_mode : bool
      - forced_green   : list of intersections forced to GREEN
      - explanation    : human-readable description
    """

    # Determine which intersections are on the route
    # For simplicity, we use all 5 predefined intersections in the CSP
    # (in a real system these would come from the search result)
    active_intersections = INTERSECTIONS.copy()

    # Decide which intersections to force GREEN
    # When emergency corridor is active, the primary route nodes get cleared
    forced_green = set()

    if emergency:
        # Force the start and destination signal zones to GREEN
        start       = clean_request.get("current_location", "")
        destination = clean_request.get("destination", "")

        if start in active_intersections:
            forced_green.add(start)
        if destination in active_intersections:
            forced_green.add(destination)

        # Also force East_Market GREEN (common corridor midpoint to hospital)
        if "East_Market" in active_intersections:
            forced_green.add("East_Market")

    # Run the backtracking CSP solver
    solution = _backtrack(
        remaining_intersections=active_intersections,
        current_assignment={},
        forced_green=forced_green,
    )

    if solution is None:
        return {
            "signal_plan":    {},
            "status":         "no_solution",
            "emergency_mode": emergency,
            "forced_green":   list(forced_green),
            "explanation":    "CSP solver could not find a valid signal assignment. "
                              "All constraint combinations were exhausted.",
        }

    # Build a human-readable explanation of the plan
    green_nodes = [n for n, v in solution.items() if v == "GREEN"]
    red_nodes   = [n for n, v in solution.items() if v == "RED"]

    if emergency:
        explanation = (
            f"Emergency corridor active. "
            f"Intersections cleared (GREEN): {', '.join(green_nodes)}. "
            f"Intersections held (RED): {', '.join(red_nodes)}."
        )
    else:
        explanation = (
            f"Standard signal plan assigned. "
            f"GREEN: {', '.join(green_nodes) if green_nodes else 'none'}. "
            f"RED: {', '.join(red_nodes) if red_nodes else 'none'}."
        )

    return {
        "signal_plan":    solution,
        "status":         "solved",
        "emergency_mode": emergency,
        "forced_green":   list(forced_green),
        "explanation":    explanation,
    }