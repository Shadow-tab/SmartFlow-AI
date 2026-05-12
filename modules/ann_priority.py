"""
ann_priority.py
---------------
The ANN Priority Prediction Module for SmartFlow AI.
Uses scikit-learn MLPClassifier trained on manually created
traffic request data to predict priority level:
Low | Normal | High | Critical

The model trains once on import and is reused for all predictions.
"""

import os
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing  import StandardScaler, LabelEncoder

# ------------------------------------------------------------------
# MODULE-LEVEL GLOBALS
# Stored once after training so prediction is instant afterwards.
# ------------------------------------------------------------------
_model         = None   # the trained MLPClassifier
_scaler        = None   # the fitted StandardScaler
_label_encoder = None   # maps string labels ↔ integer indices
_trained       = False  # flag so we only train once
_train_log     = []     # human-readable training summary for the GUI


def _load_training_data():
    """
    Loads training_data.csv from the data/ directory relative
    to the project root. Separates features (X) and labels (y).
    Returns (X, y) as numpy arrays, or raises FileNotFoundError.
    """
    # Build path relative to this file's location
    base_dir   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path   = os.path.join(base_dir, "data", "training_data.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Training data not found at: {csv_path}\n"
            "Make sure data/training_data.csv exists."
        )

    df = pd.read_csv(csv_path)

    # First 6 columns are features, last column is the label
    feature_columns = [
        "vehicle_type",
        "severity",
        "time_sensitivity",
        "traffic_density",
        "distance",
        "priority_claim",
    ]
    label_column = "priority_label"

    X = df[feature_columns].values.astype(float)
    y = df[label_column].values

    return X, y


def train_model():
    """
    Trains the MLPClassifier on the CSV data.
    Fits a StandardScaler to normalize input features so that
    no single feature dominates due to its numeric scale.
    Stores the trained model, scaler, and label encoder globally.
    Called automatically the first time predict_priority() is used.
    """
    global _model, _scaler, _label_encoder, _trained, _train_log

    _train_log = []
    _train_log.append("Loading training data from data/training_data.csv ...")

    try:
        X, y = _load_training_data()
    except FileNotFoundError as e:
        _train_log.append(f"ERROR: {e}")
        return False

    _train_log.append(f"Loaded {len(X)} training samples with {X.shape[1]} features.")
    _train_log.append(f"Classes found: {list(set(y))}")

    # --- Encode string labels to integers for the classifier ---
    # e.g. Critical→0, High→1, Low→2, Normal→3 (alphabetical)
    _label_encoder = LabelEncoder()
    y_encoded = _label_encoder.fit_transform(y)

    # --- Scale features: mean=0, std=1 for each column ---
    # This prevents distance (range 1-10) from dominating
    # severity (range 0-2) during weight updates.
    _scaler = StandardScaler()
    X_scaled = _scaler.fit_transform(X)

    # --- Build MLP: 2 hidden layers (16 → 8 neurons) ---
    # Architecture matches the MLP diagram in the project spec.
    # relu activation, lbfgs solver works well for small datasets.
    _model = MLPClassifier(
        hidden_layer_sizes=(16, 8),
        activation="relu",
        solver="lbfgs",           # good for small data (< 1000 samples)
        max_iter=1000,
        random_state=42,          # fixed seed for reproducibility
    )

    _model.fit(X_scaled, y_encoded)
    _trained = True

    # --- Compute training accuracy for the log ---
    y_predicted  = _model.predict(X_scaled)
    correct      = int(np.sum(y_predicted == y_encoded))
    accuracy_pct = round((correct / len(y_encoded)) * 100, 1)

    _train_log.append(f"Training complete. Accuracy on training set: {accuracy_pct}%")
    _train_log.append("Model ready for predictions.")

    return True


def predict_priority(feature_vector):
    """
    Accepts a feature vector (list of 6 numbers) prepared by
    input_preprocessing and returns the predicted priority level
    along with class probabilities.

    feature_vector order:
      [vehicle_type, severity, time_sensitivity,
       traffic_density, distance, priority_claim]

    Returns a dict with:
      - predicted_priority: str  (Low / Normal / High / Critical)
      - confidence: float        (probability of predicted class)
      - all_probabilities: dict  (probability per class)
      - train_log: list          (training messages for GUI display)
    """
    global _trained

    # Train on first call if not already done
    if not _trained:
        success = train_model()
        if not success:
            return {
                "predicted_priority": "Unknown",
                "confidence":         0.0,
                "all_probabilities":  {},
                "train_log":          _train_log,
                "error":              "ANN training failed — check training data.",
            }

    # --- Validate input ---
    if not isinstance(feature_vector, (list, tuple)) or len(feature_vector) != 6:
        return {
            "predicted_priority": "Unknown",
            "confidence":         0.0,
            "all_probabilities":  {},
            "train_log":          _train_log,
            "error":              "feature_vector must be a list of exactly 6 numbers.",
        }

    try:
        # Reshape to 2D array as required by sklearn: [[v1, v2, ...]]
        X_input = np.array(feature_vector, dtype=float).reshape(1, -1)

        # Apply the same scaler used during training
        X_scaled = _scaler.transform(X_input)

        # Predict the class index and convert back to string label
        predicted_index = _model.predict(X_scaled)[0]
        predicted_label = _label_encoder.inverse_transform([predicted_index])[0]

        # Get probabilities for all 4 classes
        prob_array   = _model.predict_proba(X_scaled)[0]
        class_labels = _label_encoder.classes_   # ['Critical','High','Low','Normal']

        all_probabilities = {
            label: round(float(prob), 3)
            for label, prob in zip(class_labels, prob_array)
        }

        confidence = round(float(prob_array[predicted_index]), 3)

        return {
            "predicted_priority": predicted_label,
            "confidence":         confidence,
            "all_probabilities":  all_probabilities,
            "train_log":          _train_log,
        }

    except Exception as prediction_error:
        return {
            "predicted_priority": "Unknown",
            "confidence":         0.0,
            "all_probabilities":  {},
            "train_log":          _train_log,
            "error":              f"Prediction failed: {str(prediction_error)}",
        }


def get_train_log():
    """
    Returns the list of training log messages.
    Used by the GUI to display training status on startup.
    """
    return _train_log