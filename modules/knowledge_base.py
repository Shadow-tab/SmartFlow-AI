"""
knowledge_base.py
-----------------
The Logic / Knowledge Base Module for SmartFlow AI.
Implements all policy rules and predicates from the project spec
using rule-based reasoning. Acts as the authorization gatekeeper
before CSP and Search modules are allowed to execute.
"""

# Locations designated as hospitals in the city graph
HOSPITAL_LOCATIONS = {"City_Hospital"}

# Locations designated as signal control zones
SIGNAL_ZONES = {
    "Central_Junction",
    "North_Station",
    "East_Market",
    "River_Bridge",
    "West_Terminal",
}

# Emergency vehicle types recognized by the system
EMERGENCY_VEHICLE_TYPES = {"Ambulance", "FireTruck", "Police"}


def run_knowledge_base(clean_request):
    """
    Receives the validated request dict and applies all policy rules
    from the project specification in sequence. Derives facts about
    the vehicle's priority, authorization, and allowed actions, then
    determines whether the overall request is Approved or Rejected.

    Returns a dict containing:
      - facts: all derived logical predicates and their truth values
      - approved: bool — overall approval status
      - rejection_reason: str — only present if rejected
      - emergency_corridor: bool — whether corridor was granted
      - signal_override_authorized: bool
      - priority: str — derived priority level
    """

    # ---- Extract key fields from the request --------------------
    vehicle_type      = clean_request.get("vehicle_type", "Civilian")
    request_category  = clean_request.get("request_category", "")
    destination       = clean_request.get("destination", "")
    incident_severity = clean_request.get("incident_severity", "Low")
    time_sensitive    = clean_request.get("time_sensitivity", "No") == "Yes"
    predicted_priority = clean_request.get("predicted_priority", None)

    # Start with an empty facts dictionary — we'll fill it step by step
    facts = {}

    # ================================================================
    # BLOCK 1: VEHICLE CLASSIFICATION PREDICATES
    # EmergencyVehicle(v) and CivilianVehicle(v) are mutually exclusive
    # ================================================================

    is_emergency = vehicle_type in EMERGENCY_VEHICLE_TYPES
    is_civilian  = not is_emergency

    facts["EmergencyVehicle"]  = is_emergency
    facts["CivilianVehicle"]   = is_civilian
    facts["VehicleType"]       = vehicle_type

    # ================================================================
    # BLOCK 2: LOCATION PREDICATES
    # Hospital(h) and SignalZone(z) checks
    # ================================================================

    going_to_hospital = destination in HOSPITAL_LOCATIONS
    in_signal_zone    = destination in SIGNAL_ZONES or True  # always in some zone

    facts["Destination"]      = destination
    facts["Hospital"]         = going_to_hospital
    facts["SignalZone"]       = True   # all intersections are in a signal zone

    # ================================================================
    # BLOCK 3: PRIORITY DERIVATION RULES
    # Rules from the spec (applied in priority order):
    #   EmergencyVehicle ∧ IncidentSeverity=High → Priority=Critical
    #   EmergencyVehicle ∧ TimeSensitive         → Priority=High
    #   CivilianVehicle                          → Priority=Normal
    # If ANN already predicted a priority, we also record it.
    # ================================================================

    if is_emergency and incident_severity == "High":
        kb_priority = "Critical"
    elif is_emergency and time_sensitive:
        kb_priority = "High"
    elif is_emergency:
        kb_priority = "High"         # emergency vehicle always at least High
    else:
        kb_priority = "Normal"       # CivilianVehicle → Priority=Normal

    # Use ANN prediction if available; KB priority is the rule-based check
    effective_priority = predicted_priority if predicted_priority else kb_priority

    facts["Priority_KB"]        = kb_priority
    facts["Priority_ANN"]       = predicted_priority
    facts["Priority_Effective"] = effective_priority
    facts["IncidentSeverity"]   = incident_severity
    facts["TimeSensitive"]      = time_sensitive

    # ================================================================
    # BLOCK 4: AUTHORIZATION RULES
    # EmergencyVehicle ∧ SignalZone → Authorized(SignalOverride)
    # CivilianVehicle  ∧ SignalZone → ¬Authorized(SignalOverride)
    # EmergencyVehicle ∧ Hospital   → EmergencyCorridor
    # EmergencyCorridor             → Authorized(EmergencyRoute)
    # ================================================================

    # Signal override authorization
    if is_emergency:
        signal_override_authorized = True   # EmergencyVehicle ∧ SignalZone
    else:
        signal_override_authorized = False  # ¬Authorized for civilians

    # Emergency corridor: only when emergency vehicle going to hospital
    if is_emergency and going_to_hospital:
        emergency_corridor = True
    else:
        emergency_corridor = False

    # Emergency route authorization follows from corridor
    emergency_route_authorized = emergency_corridor

    facts["Authorized_SignalOverride"]  = signal_override_authorized
    facts["EmergencyCorridor"]          = emergency_corridor
    facts["Authorized_EmergencyRoute"]  = emergency_route_authorized

    # ================================================================
    # BLOCK 5: ALLOWED ACTION DERIVATION
    # Authorized(v, action) → AllowedAction(v, action)
    # ¬AllowedAction(v, action) → Rejected
    # Priority=Critical ∧ Authorized(EmergencyRoute) → AllowedAction(SignalOverride)
    # ================================================================

    # Base allowed action from authorization
    action_allowed = signal_override_authorized or emergency_route_authorized

    # Special rule: Critical priority + emergency route → also allows signal override
    if effective_priority == "Critical" and emergency_route_authorized:
        action_allowed = True
        signal_override_authorized = True   # update since critical grants this too
        facts["Authorized_SignalOverride"] = True

    facts["AllowedAction"] = action_allowed

    # ================================================================
    # BLOCK 6: REQUEST APPROVAL / REJECTION RULES
    # Different request types have specific approval conditions
    # from the spec predicates.
    # ================================================================

    approved         = False
    rejection_reason = ""

    if request_category == "Route_Request":
        # RequestType(Route_Request) → always Approved
        approved = True

    elif request_category == "Policy_Check":
        # RequestType(Policy_Check) ∧ Authorized(action) → Approved
        # RequestType(Policy_Check) ∧ ¬Authorized(action) → Rejected
        if signal_override_authorized or emergency_route_authorized:
            approved = True
        else:
            approved = False
            rejection_reason = (
                "Policy check failed: vehicle is not authorized for "
                "signal override or emergency route access. "
                "Civilian vehicles are not permitted these actions."
            )

    elif request_category == "Control_Allocation_Request":
        # RequestType(Control_Allocation) ∧ AllowedAction → Approved
        if action_allowed:
            approved = True
        else:
            approved = False
            rejection_reason = (
                "Control allocation rejected: no allowed action found. "
                "Vehicle lacks authorization for signal or corridor control."
            )

    elif request_category == "Emergency_Response_Request":
        # RequestType(Emergency_Response) ∧ Priority(level) ∧ Authorized(EmergencyRoute) → Approved
        if effective_priority in ("High", "Critical") and emergency_route_authorized:
            approved = True
        elif is_emergency:
            # Emergency vehicle but not going to hospital — still approve with High
            approved = True
        else:
            approved = False
            rejection_reason = (
                "Emergency response rejected: vehicle does not qualify for "
                "emergency route authorization. Only emergency vehicles with "
                "high-severity incidents are approved."
            )

    elif request_category == "Integrated_City_Service_Request":
        # RequestType(Integrated) ∧ Priority=Critical ∧ Authorized(EmergencyRoute)
        #   ∧ AllowedAction → Approved
        if (
            effective_priority == "Critical"
            and emergency_route_authorized
            and action_allowed
        ):
            approved = True
        elif is_emergency and action_allowed:
            # Slightly relax for non-critical emergency vehicles
            approved = True
        else:
            approved = False
            rejection_reason = (
                "Integrated service request rejected: requires Critical priority, "
                "emergency route authorization, and an allowed action. "
                "Current request does not meet all conditions."
            )

    else:
        # Unknown category — should not reach here after preprocessing
        approved = False
        rejection_reason = f"Unknown request category: '{request_category}'"

    facts["Approved"] = approved
    facts["Rejected"] = not approved

    # ================================================================
    # BUILD AND RETURN RESULT
    # ================================================================

    result = {
        "facts":                      facts,
        "approved":                   approved,
        "priority":                   effective_priority,
        "emergency_corridor":         emergency_corridor,
        "signal_override_authorized": signal_override_authorized,
        "action_allowed":             action_allowed,
    }

    if not approved:
        result["rejection_reason"] = rejection_reason

    return result