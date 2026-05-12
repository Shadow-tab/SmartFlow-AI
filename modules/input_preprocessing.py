"""
input_preprocessing.py
-----------------------
Entry point for all traffic requests in SmartFlow AI.
Validates fields, normalizes values, rejects bad input,
and builds the numeric feature vector for the ANN module.
"""

# ------------------------------------------------------------------
# CONSTANTS — all valid options the system accepts
# ------------------------------------------------------------------

VALID_VEHICLE_TYPES = ["Civilian", "Ambulance", "FireTruck", "Police"]

VALID_REQUEST_CATEGORIES = [
    "Route_Request",
    "Policy_Check",
    "Control_Allocation_Request",
    "Emergency_Response_Request",
    "Integrated_City_Service_Request",
]

VALID_LOCATIONS = [
    "Police_HQ",
    "Traffic_Control_Center",
    "River_Bridge",
    "North_Station",
    "Central_Junction",
    "East_Market",
    "Stadium",
    "Airport_Road",
    "City_Hospital",
    "South_Residential",
    "West_Terminal",
    "Fire_Station",
    "Industrial_Zone",
]

VALID_SEVERITIES    = ["Low", "Medium", "High"]
VALID_DENSITIES     = ["Light", "Moderate", "Dense"]
VALID_SENSITIVITIES = ["Yes", "No"]
VALID_CLAIMS        = ["Normal", "Emergency"]

# ------------------------------------------------------------------
# NORMALIZATION MAPS
# These let users type common variations and still get accepted.
# e.g. "ambulance" → "Ambulance", "fire truck" → "FireTruck"
# ------------------------------------------------------------------

VEHICLE_ALIASES = {
    "civilian":   "Civilian",
    "car":        "Civilian",
    "normal car": "Civilian",
    "ambulance":  "Ambulance",
    "firetruck":  "FireTruck",
    "fire truck": "FireTruck",
    "fire":       "FireTruck",
    "police":     "Police",
    "police car": "Police",
}

SEVERITY_ALIASES = {
    "low":    "Low",
    "medium": "Medium",
    "med":    "Medium",
    "high":   "High",
}

DENSITY_ALIASES = {
    "light":    "Light",
    "low":      "Light",
    "moderate": "Moderate",
    "medium":   "Moderate",
    "dense":    "Dense",
    "heavy":    "Dense",
    "high":     "Dense",
}

SENSITIVITY_ALIASES = {
    "yes": "Yes",
    "y":   "Yes",
    "no":  "No",
    "n":   "No",
}

CLAIM_ALIASES = {
    "normal":    "Normal",
    "emergency": "Emergency",
    "urgent":    "Emergency",
}

# ------------------------------------------------------------------
# ENCODING MAPS
# Convert normalized text values to numbers for the ANN.
# ------------------------------------------------------------------

VEHICLE_ENCODING = {
    "Civilian":  0,
    "Ambulance": 1,
    "FireTruck": 1,
    "Police":    1,
}

SEVERITY_ENCODING    = {"Low": 0, "Medium": 1, "High": 2}
SENSITIVITY_ENCODING = {"No": 0,  "Yes": 1}
DENSITY_ENCODING     = {"Light": 0, "Moderate": 1, "Dense": 2}
CLAIM_ENCODING       = {"Normal": 0, "Emergency": 1}


# ------------------------------------------------------------------
# HELPER: normalize a single field using an alias map
# ------------------------------------------------------------------

def normalize_field(raw_value, alias_map, field_name):
    """
    Strips whitespace, lowercases the input, and looks it up
    in the alias map. Returns the clean standard value, or
    raises a ValueError with a descriptive message if not found.
    """
    # Strip surrounding spaces and convert to lowercase for comparison
    cleaned = str(raw_value).strip().lower()

    # Look up in the alias map
    if cleaned in alias_map:
        return alias_map[cleaned]

    # Not found — build an error message showing what was received
    raise ValueError(
        f"Invalid value for '{field_name}': '{raw_value}'. "
        f"Accepted: {list(alias_map.keys())}"
    )


# ------------------------------------------------------------------
# HELPER: check that a location string is in our city graph
# ------------------------------------------------------------------

def validate_location(location_value, field_name):
    """
    Checks that the given location exists in the predefined city
    graph node list. Returns the clean location string or raises
    a ValueError if unknown.
    """
    cleaned = str(location_value).strip()

    # Direct match — exact name like "City_Hospital"
    if cleaned in VALID_LOCATIONS:
        return cleaned

    # Try case-insensitive match for convenience
    for valid_loc in VALID_LOCATIONS:
        if valid_loc.lower() == cleaned.lower():
            return valid_loc

    raise ValueError(
        f"Unknown location for '{field_name}': '{location_value}'. "
        f"Valid locations: {VALID_LOCATIONS}"
    )


# ------------------------------------------------------------------
# MAIN FUNCTION: validate_and_preprocess
# ------------------------------------------------------------------

def validate_and_preprocess(raw_request):
    """
    Receives a raw request dictionary from the GUI or demo cases.
    Validates every required field, normalizes values, and returns
    a clean standardized request dict. Also builds the ANN feature
    vector (a list of 6 numbers) for priority prediction.

    Returns a dict with either:
      - All cleaned fields + 'feature_vector' key  (success)
      - An 'error' key with a descriptive message   (failure)
    """

    # ---- Step 1: Check that required fields are all present ------
    required_fields = [
        "request_id",
        "vehicle_type",
        "request_category",
        "current_location",
        "destination",
        "incident_severity",
        "time_sensitivity",
        "traffic_density",
        "priority_claim",
    ]

    for field in required_fields:
        # Check if the key exists and is not empty/None
        if field not in raw_request or str(raw_request[field]).strip() == "":
            return {"error": f"Missing required field: '{field}'"}

    # ---- Step 2: Normalize each field using alias maps -----------
    try:
        vehicle_type = normalize_field(
            raw_request["vehicle_type"], VEHICLE_ALIASES, "vehicle_type"
        )

        request_category = str(raw_request["request_category"]).strip()
        if request_category not in VALID_REQUEST_CATEGORIES:
            return {
                "error": (
                    f"Invalid request_category: '{request_category}'. "
                    f"Valid options: {VALID_REQUEST_CATEGORIES}"
                )
            }

        current_location = validate_location(
            raw_request["current_location"], "current_location"
        )

        destination = validate_location(
            raw_request["destination"], "destination"
        )

        # Source and destination must not be the same node
        if current_location == destination:
            return {
                "error": "current_location and destination cannot be the same."
            }

        incident_severity = normalize_field(
            raw_request["incident_severity"], SEVERITY_ALIASES, "incident_severity"
        )

        time_sensitivity = normalize_field(
            raw_request["time_sensitivity"], SENSITIVITY_ALIASES, "time_sensitivity"
        )

        traffic_density = normalize_field(
            raw_request["traffic_density"], DENSITY_ALIASES, "traffic_density"
        )

        priority_claim = normalize_field(
            raw_request["priority_claim"], CLAIM_ALIASES, "priority_claim"
        )

        # Optional field — distance estimate (default 5 if not provided)
        try:
            distance = float(raw_request.get("distance", 5))
            if distance <= 0:
                distance = 5.0
        except (ValueError, TypeError):
            distance = 5.0

        # Optional field — free text note (just clean it)
        description_note = str(raw_request.get("description_note", "")).strip()

    except ValueError as validation_error:
        # Any normalize_field failure lands here
        return {"error": str(validation_error)}

    # ---- Step 3: Build ANN feature vector ------------------------
    # Order must match training_data.csv column order:
    # [vehicle_type, severity, time_sensitivity, traffic_density, distance, priority_claim]
    feature_vector = [
        VEHICLE_ENCODING[vehicle_type],
        SEVERITY_ENCODING[incident_severity],
        SENSITIVITY_ENCODING[time_sensitivity],
        DENSITY_ENCODING[traffic_density],
        min(distance, 10.0),          # cap at 10 to match training range
        CLAIM_ENCODING[priority_claim],
    ]

    # ---- Step 4: Return the clean, standardized request ----------
    return {
        "request_id":       str(raw_request["request_id"]).strip(),
        "vehicle_type":     vehicle_type,
        "request_category": request_category,
        "current_location": current_location,
        "destination":      destination,
        "incident_severity": incident_severity,
        "time_sensitivity": time_sensitivity,
        "traffic_density":  traffic_density,
        "priority_claim":   priority_claim,
        "distance":         distance,
        "description_note": description_note,
        "feature_vector":   feature_vector,   # ready for ANN
        "is_emergency_vehicle": vehicle_type != "Civilian",
        "going_to_hospital":    destination == "City_Hospital",
    }