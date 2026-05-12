"""
search_navigation.py
--------------------
The Search & Navigation Module for SmartFlow AI.
Implements BFS (unweighted), UCS (weighted), and A* (heuristic)
on the predefined city road graph. Returns the best route and
total cost for the given start and goal locations.
"""

import heapq
from collections import deque

# ------------------------------------------------------------------
# CITY WEIGHTED GRAPH
# Encoded from the "City Weighted Graph" diagram in the project PDF.
# Keys are node names, values are dicts of {neighbor: edge_cost}.
# All edges are bidirectional.
# ------------------------------------------------------------------

WEIGHTED_GRAPH = {
    "Police_HQ": {
        "Traffic_Control_Center": 2,
        "River_Bridge":           2,
    },
    "Traffic_Control_Center": {
        "Police_HQ":    2,
        "Airport_Road": 2,
        "North_Station": 4,
    },
    "River_Bridge": {
        "Police_HQ":     2,
        "North_Station": 4,
    },
    "North_Station": {
        "Traffic_Control_Center": 4,
        "River_Bridge":           4,
        "Central_Junction":       3,
        "South_Residential":      3,
    },
    "Central_Junction": {
        "North_Station":  3,
        "West_Terminal":  4,
        "East_Market":    3,
    },
    "East_Market": {
        "Central_Junction": 3,
        "Stadium":          2,
        "City_Hospital":    3,
        "South_Residential": 2,
    },
    "Stadium": {
        "East_Market":  2,
        "Airport_Road": 5,
        "City_Hospital": 3,
    },
    "Airport_Road": {
        "Traffic_Control_Center": 2,
        "Stadium":               5,
        "South_Residential":     2,
    },
    "City_Hospital": {
        "East_Market": 3,
        "Stadium":     3,
    },
    "South_Residential": {
        "North_Station":  3,
        "East_Market":    2,
        "Airport_Road":   2,
    },
    "West_Terminal": {
        "Central_Junction": 4,
        "Fire_Station":     2,
        "Industrial_Zone":  4,
    },
    "Fire_Station": {
        "West_Terminal": 2,
    },
    "Industrial_Zone": {
        "West_Terminal": 4,
    },
}

# ------------------------------------------------------------------
# UNWEIGHTED GRAPH (all edge costs = 1 for BFS)
# Encoded from "City Unweighted Graph" in the project PDF.
# ------------------------------------------------------------------

UNWEIGHTED_GRAPH = {
    node: {neighbor: 1 for neighbor in neighbors}
    for node, neighbors in WEIGHTED_GRAPH.items()
}

# ------------------------------------------------------------------
# HEURISTIC TABLE for A*
# Since we have no real coordinates, we use manually estimated
# distances to City_Hospital (the most common emergency destination).
# Values represent approximate hops/cost to reach the goal.
# For other destinations, we use a default fallback of 1.
# ------------------------------------------------------------------

HEURISTIC_TO_HOSPITAL = {
    "Central_Junction":      6,
    "North_Station":         7,
    "East_Market":           3,
    "Stadium":               3,
    "City_Hospital":         0,
    "South_Residential":     5,
    "West_Terminal":         8,
    "River_Bridge":          9,
    "Police_HQ":             10,
    "Traffic_Control_Center": 9,
    "Airport_Road":          8,
    "Fire_Station":          10,
    "Industrial_Zone":       12,
}


def _heuristic(node, goal):
    """
    Returns an estimated cost from 'node' to 'goal'.
    Uses precomputed table for City_Hospital.
    Falls back to 1 (admissible underestimate) for other goals.
    """
    if goal == "City_Hospital":
        return HEURISTIC_TO_HOSPITAL.get(node, 1)
    return 1   # admissible default — never overestimates


def _reconstruct_path(came_from, start, goal):
    """
    Traces back through the came_from dictionary (parent pointers)
    to build the route from start to goal as an ordered list.
    """
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = came_from.get(current)
    path.reverse()   # came_from builds path backwards — flip it

    # Sanity check: path must start at the start node
    if path and path[0] == start:
        return path
    return []   # no valid path could be reconstructed


# ------------------------------------------------------------------
# BFS — Breadth-First Search (unweighted shortest path)
# ------------------------------------------------------------------

def bfs(start, goal):
    """
    Breadth-First Search on the unweighted city graph.
    Guarantees the route with the fewest road segments (hops).
    Returns (path_list, total_hops) or ([], -1) if no path.
    """
    if start not in UNWEIGHTED_GRAPH:
        return [], -1
    if start == goal:
        return [start], 0

    # Queue holds nodes to explore — FIFO order
    queue    = deque([start])
    visited  = {start}
    came_from = {start: None}   # tracks parent of each visited node

    while queue:
        current_node = queue.popleft()

        # Check if we reached the goal
        if current_node == goal:
            path = _reconstruct_path(came_from, start, goal)
            return path, len(path) - 1   # hops = edges = nodes - 1

        # Explore all neighbors
        for neighbor in UNWEIGHTED_GRAPH.get(current_node, {}):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current_node
                queue.append(neighbor)

    return [], -1   # goal not reachable


# ------------------------------------------------------------------
# UCS — Uniform Cost Search (weighted, no heuristic)
# ------------------------------------------------------------------

def ucs(start, goal):
    """
    Uniform Cost Search on the weighted city graph.
    Always finds the minimum-cost path. Uses a min-heap
    (priority queue) ordered by cumulative path cost.
    Returns (path_list, total_cost) or ([], -1) if no path.
    """
    if start not in WEIGHTED_GRAPH:
        return [], -1
    if start == goal:
        return [start], 0

    # Heap entries: (cumulative_cost, node_name)
    heap      = [(0, start)]
    visited   = set()
    came_from = {start: None}
    cost_so_far = {start: 0}

    while heap:
        current_cost, current_node = heapq.heappop(heap)

        if current_node in visited:
            continue   # skip if already settled with lower cost
        visited.add(current_node)

        if current_node == goal:
            path = _reconstruct_path(came_from, start, goal)
            return path, current_cost

        for neighbor, edge_cost in WEIGHTED_GRAPH.get(current_node, {}).items():
            new_cost = current_cost + edge_cost

            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                came_from[neighbor]   = current_node
                heapq.heappush(heap, (new_cost, neighbor))

    return [], -1   # goal not reachable


# ------------------------------------------------------------------
# A* — A-Star Search (weighted + heuristic)
# ------------------------------------------------------------------

def astar(start, goal):
    """
    A* Search on the weighted city graph using a precomputed heuristic.
    Faster than UCS for emergency routing because it biases exploration
    toward the goal rather than exploring all directions equally.
    Returns (path_list, total_cost) or ([], -1) if no path.
    """
    if start not in WEIGHTED_GRAPH:
        return [], -1
    if start == goal:
        return [start], 0

    # Heap entries: (f_score, g_score, node)
    # f = g + h, g = cost so far, h = heuristic estimate to goal
    start_h = _heuristic(start, goal)
    heap    = [(start_h, 0, start)]

    visited     = set()
    came_from   = {start: None}
    g_score     = {start: 0}

    while heap:
        f, g, current_node = heapq.heappop(heap)

        if current_node in visited:
            continue
        visited.add(current_node)

        if current_node == goal:
            path = _reconstruct_path(came_from, start, goal)
            return path, g

        for neighbor, edge_cost in WEIGHTED_GRAPH.get(current_node, {}).items():
            tentative_g = g + edge_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor]   = tentative_g
                came_from[neighbor] = current_node
                f_score = tentative_g + _heuristic(neighbor, goal)
                heapq.heappush(heap, (f_score, tentative_g, neighbor))

    return [], -1   # goal not reachable


# ------------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------------

def run_search(start, goal, mode="astar"):
    """
    Public interface for the Search module.
    Selects the algorithm based on the 'mode' parameter
    and returns a structured result dict.

    Parameters:
      start : str  — starting node name (from city graph)
      goal  : str  — destination node name
      mode  : str  — 'bfs', 'ucs', or 'astar'

    Returns a dict with:
      - algorithm   : str   — which algorithm was used
      - path        : list  — ordered list of node names
      - cost        : int/float — total path cost (-1 if unreachable)
      - path_string : str   — human-readable route  "A → B → C"
      - reachable   : bool
    """

    # Validate that start and goal exist in the graph
    if start not in WEIGHTED_GRAPH:
        return {
            "algorithm": mode, "path": [], "cost": -1,
            "path_string": "Invalid start location.",
            "reachable": False,
        }
    if goal not in WEIGHTED_GRAPH:
        return {
            "algorithm": mode, "path": [], "cost": -1,
            "path_string": "Invalid destination.",
            "reachable": False,
        }

    # Select and run the appropriate algorithm
    if mode == "bfs":
        path, cost = bfs(start, goal)
        algorithm_name = "BFS (Breadth-First Search)"
    elif mode == "ucs":
        path, cost = ucs(start, goal)
        algorithm_name = "UCS (Uniform Cost Search)"
    else:   # default to astar
        path, cost = astar(start, goal)
        algorithm_name = "A* (A-Star Search)"

    # Build human-readable path string
    if path:
        path_string = " → ".join(path)
        reachable   = True
    else:
        path_string = f"No route found from {start} to {goal}."
        reachable   = False

    return {
        "algorithm":   algorithm_name,
        "path":        path,
        "cost":        cost,
        "path_string": path_string,
        "reachable":   reachable,
    }