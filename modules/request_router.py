"""
request_router.py
-----------------
The control-flow manager of SmartFlow AI.
Reads the request_category and routes each request through
the correct sequence of AI modules. Each category activates
only the modules it actually needs — nothing more.
"""

# Import all AI modules
from modules.ann_priority      import predict_priority
from modules.knowledge_base    import run_knowledge_base
from modules.csp_scheduler     import run_csp_scheduler
from modules.search_navigation import run_search


def route_request(clean_request):
    """
    Main routing function. Receives the validated, normalized
    request dict from input_preprocessing and dispatches it
    through the correct module pipeline based on request_category.

    Returns a results dict containing outputs from every module
    that was actually used for this request.
    """

    category = clean_request["request_category"]

    # Start with base info that every response includes
    results = {
        "request_id":       clean_request["request_id"],
        "request_category": category,
        "vehicle_type":     clean_request["vehicle_type"],
        "current_location": clean_request["current_location"],
        "destination":      clean_request["destination"],
        "modules_used":     [],   # track which modules ran
    }

    # ----------------------------------------------------------
    # PIPELINE 1: Route_Request
    # Simple navigation — only Search is needed.
    # No priority prediction, no policy check, no CSP.
    # ----------------------------------------------------------
    if category == "Route_Request":
        results["modules_used"].append("Search")

        search_result = run_search(
            start=clean_request["current_location"],
            goal=clean_request["destination"],
            mode="bfs",           # unweighted = BFS per spec
        )
        results["search"] = search_result
        return results

    # ----------------------------------------------------------
    # PIPELINE 2: Policy_Check
    # Only the Knowledge Base runs — checks authorization rules.
    # No routing or signal control needed.
    # ----------------------------------------------------------
    if category == "Policy_Check":
        results["modules_used"].append("KnowledgeBase")

        kb_result = run_knowledge_base(clean_request)
        results["knowledge_base"] = kb_result
        return results

    # ----------------------------------------------------------
    # PIPELINE 3: Control_Allocation_Request
    # Knowledge Base validates authorization first.
    # If approved, CSP assigns the signal plan.
    # ----------------------------------------------------------
    if category == "Control_Allocation_Request":
        results["modules_used"].extend(["KnowledgeBase", "CSP"])

        # Step 1 — Policy check
        kb_result = run_knowledge_base(clean_request)
        results["knowledge_base"] = kb_result

        # Step 2 — Only run CSP if policy approved
        if kb_result.get("approved"):
            csp_result = run_csp_scheduler(clean_request)
            results["csp"] = csp_result
        else:
            results["csp"] = {
                "status": "skipped",
                "reason": "Policy check failed — CSP not executed.",
            }

        return results

    # ----------------------------------------------------------
    # PIPELINE 4: Emergency_Response_Request
    # Full emergency pipeline: ANN → KB → CSP → Search
    # Each step feeds information into the next.
    # ----------------------------------------------------------
    if category == "Emergency_Response_Request":
        results["modules_used"].extend(["ANN", "KnowledgeBase", "CSP", "Search"])

        # Step 1 — ANN predicts priority from feature vector
        ann_result = predict_priority(clean_request["feature_vector"])
        results["ann"] = ann_result

        # Inject predicted priority back into request so KB can use it
        clean_request["predicted_priority"] = ann_result["predicted_priority"]

        # Step 2 — Knowledge Base validates based on predicted priority
        kb_result = run_knowledge_base(clean_request)
        results["knowledge_base"] = kb_result

        # Step 3 — CSP assigns signal plan (runs regardless, but
        #           result notes if emergency corridor was granted)
        csp_result = run_csp_scheduler(clean_request, emergency=kb_result.get("emergency_corridor", False))
        results["csp"] = csp_result

        # Step 4 — A* search for fastest weighted route
        search_result = run_search(
            start=clean_request["current_location"],
            goal=clean_request["destination"],
            mode="astar",
        )
        results["search"] = search_result

        return results

    # ----------------------------------------------------------
    # PIPELINE 5: Integrated_City_Service_Request
    # Same as Emergency but with richer final response messaging.
    # ANN → KB → CSP → Search → Full integrated output.
    # ----------------------------------------------------------
    if category == "Integrated_City_Service_Request":
        results["modules_used"].extend(["ANN", "KnowledgeBase", "CSP", "Search"])

        # Step 1 — ANN priority prediction
        ann_result = predict_priority(clean_request["feature_vector"])
        results["ann"] = ann_result

        clean_request["predicted_priority"] = ann_result["predicted_priority"]

        # Step 2 — Knowledge Base policy validation
        kb_result = run_knowledge_base(clean_request)
        results["knowledge_base"] = kb_result

        # Step 3 — CSP signal control allocation
        csp_result = run_csp_scheduler(
            clean_request,
            emergency=kb_result.get("emergency_corridor", False)
        )
        results["csp"] = csp_result

        # Step 4 — A* search (weighted, heuristic-guided)
        search_result = run_search(
            start=clean_request["current_location"],
            goal=clean_request["destination"],
            mode="astar",
        )
        results["search"] = search_result

        # Mark as integrated so final_response knows to show full output
        results["integrated"] = True

        return results

    # ----------------------------------------------------------
    # FALLBACK: unknown category slipped through preprocessing
    # ----------------------------------------------------------
    results["error"] = f"Unknown request_category: '{category}'"
    return results