"""
final_response.py
-----------------
The Final Response Layer for SmartFlow AI.
Aggregates outputs from only the modules that were actually used
for the current request and formats them into a clean,
structured, human-readable response for the GUI output console.
"""

# Divider lines for visual separation in the console output
DIVIDER_THIN  = "─" * 52
DIVIDER_THICK = "═" * 52


def _format_signal_plan(signal_plan):
    """
    Converts the CSP signal plan dict into a compact display string.
    Example: {Central_Junction: GREEN, East_Market: RED} →
             "Central_Junction: GREEN  |  East_Market: RED"
    """
    if not signal_plan:
        return "No signal plan generated."

    parts = []
    for intersection, phase in signal_plan.items():
        # Shorten intersection names for display brevity
        short_name = intersection.replace("_", " ")
        parts.append(f"{short_name}: {phase}")

    return "  |  ".join(parts)


def _format_probabilities(prob_dict):
    """
    Formats the ANN class probability dict as a readable line.
    Example: Critical: 0.87, High: 0.10, Normal: 0.02, Low: 0.01
    """
    if not prob_dict:
        return ""

    # Sort by probability descending
    sorted_probs = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
    parts = [f"{label}: {prob:.2f}" for label, prob in sorted_probs]
    return "  |  ".join(parts)


def build_final_response(results):
    """
    Main function that receives the results dict from the router
    (containing outputs from all modules that ran) and builds:
      1. A list of labeled output lines for the GUI console
      2. A structured summary dict for GUI status fields

    Returns a dict with:
      - lines     : list of (tag, text) tuples for color-coded display
      - summary   : dict of key status fields for the GUI header
      - approved  : bool — overall approval (for GUI badge)
      - priority  : str  — final priority level (for GUI badge)
    """

    lines   = []   # each entry: (tag_label, display_text)
    summary = {}

    request_id = results.get("request_id", "N/A")
    category   = results.get("request_category", "N/A")

    # ---- Header ------------------------------------------------
    lines.append(("HEADER", DIVIDER_THICK))
    lines.append(("HEADER", f"  SMARTFLOW AI — {category.replace('_', ' ').upper()}"))
    lines.append(("HEADER", f"  Request ID: {request_id}"))
    lines.append(("HEADER", DIVIDER_THICK))

    # ---- ANN Section (if ANN was used) -------------------------
    if "ann" in results:
        ann = results["ann"]
        priority = ann.get("predicted_priority", "Unknown")
        confidence = ann.get("confidence", 0.0)
        probs = ann.get("all_probabilities", {})

        lines.append(("ANN", f"Priority predicted      →  {priority}"))
        lines.append(("ANN", f"Confidence              →  {confidence * 100:.1f}%"))
        if probs:
            lines.append(("ANN", f"Class probabilities     →  {_format_probabilities(probs)}"))

        summary["priority"] = priority

    # ---- Knowledge Base Section (if KB was used) ---------------
    if "knowledge_base" in results:
        kb = results["knowledge_base"]

        approved   = kb.get("approved", False)
        kb_priority = kb.get("priority", "N/A")
        corridor   = kb.get("emergency_corridor", False)
        override   = kb.get("signal_override_authorized", False)
        action_ok  = kb.get("action_allowed", False)

        lines.append((DIVIDER_THIN, DIVIDER_THIN))

        status_text = "APPROVED" if approved else "REJECTED"
        lines.append(("KB",  f"Policy status           →  {status_text}"))
        lines.append(("KB",  f"KB priority level       →  {kb_priority}"))
        lines.append(("KB",  f"Emergency corridor      →  {'GRANTED' if corridor else 'NOT GRANTED'}"))
        lines.append(("KB",  f"Signal override auth    →  {'YES' if override else 'NO'}"))
        lines.append(("KB",  f"Action allowed          →  {'YES' if action_ok else 'NO'}"))

        if not approved:
            reason = kb.get("rejection_reason", "No reason provided.")
            lines.append(("KB_REJECT", f"Rejection reason        →  {reason}"))

        summary["approved"]           = approved
        summary["emergency_corridor"] = corridor
        if "priority" not in summary:
            summary["priority"] = kb_priority

    # ---- CSP Section (if CSP was used) -------------------------
    if "csp" in results:
        csp = results["csp"]
        status = csp.get("status", "unknown")

        lines.append((DIVIDER_THIN, DIVIDER_THIN))

        if status == "solved":
            plan_str  = _format_signal_plan(csp.get("signal_plan", {}))
            forced    = csp.get("forced_green", [])
            em_mode   = csp.get("emergency_mode", False)

            lines.append(("CSP", f"Signal plan status      →  SOLVED"))
            lines.append(("CSP", f"Emergency corridor mode →  {'YES' if em_mode else 'NO'}"))
            lines.append(("CSP", f"Signal assignments      →  {plan_str}"))
            if forced:
                lines.append(("CSP", f"Forced GREEN            →  {', '.join(forced)}"))
            lines.append(("CSP", csp.get("explanation", "")))

        elif status == "skipped":
            lines.append(("CSP", f"CSP scheduler           →  SKIPPED"))
            lines.append(("CSP", csp.get("reason", "")))

        else:
            lines.append(("CSP", f"Signal plan status      →  NO SOLUTION FOUND"))
            lines.append(("CSP", csp.get("explanation", "")))

    # ---- Search Section (if Search was used) -------------------
    if "search" in results:
        search = results["search"]

        lines.append((DIVIDER_THIN, DIVIDER_THIN))

        algorithm   = search.get("algorithm", "Unknown")
        path_string = search.get("path_string", "No route.")
        cost        = search.get("cost", -1)
        reachable   = search.get("reachable", False)

        lines.append(("SEARCH", f"Search algorithm        →  {algorithm}"))

        if reachable:
            lines.append(("SEARCH", f"Route found             →  {path_string}"))
            lines.append(("SEARCH", f"Total route cost        →  {cost} units"))
        else:
            lines.append(("SEARCH", f"Route status            →  NO ROUTE FOUND"))
            lines.append(("SEARCH", path_string))

        summary["route"]      = path_string
        summary["route_cost"] = cost

    # ---- Final Status Line -------------------------------------
    lines.append((DIVIDER_THIN, DIVIDER_THIN))

    approved_final = summary.get("approved", True)   # Route_Request always approved

    if approved_final:
        lines.append(("DONE", f"✓  Request {request_id} fully processed and dispatched."))
    else:
        lines.append(("FAIL", f"✗  Request {request_id} was REJECTED. See reason above."))

    lines.append(("HEADER", DIVIDER_THICK))

    # Ensure summary has all keys the GUI needs
    summary.setdefault("approved",  True)
    summary.setdefault("priority",  "N/A")
    summary.setdefault("route",     "N/A")
    summary.setdefault("route_cost", "N/A")

    return {
        "lines":    lines,
        "summary":  summary,
        "approved": approved_final,
        "priority": summary.get("priority", "N/A"),
    }