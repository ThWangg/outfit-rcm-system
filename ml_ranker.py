import os
import pickle
import math
from typing import Optional
import config
from recommender import (
    OutfitCandidate, UserContext, FEATURE_NAMES,
    extract_features, compute_style_affinity,
    calculate_t_adj, map_contexts,
)


#training

def train_model(interactions: list[dict]):
    """
    Train a RandomForestClassifier on past user interactions.

    Parameters
    ----------
    interactions : list of dicts returned by db.get_all_interactions()

    Returns
    -------
    Trained sklearn model, saved to config.MODEL_PATH.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    if not interactions:
        print("[ml_ranker] No interaction data – using fallback cosine scorer.")
        return None

    X, y = [], []
    for row in interactions:
        try:
            feature_vec = [
                float(row.get("bmi") or 22.0),
                float(row.get("f_target") or 0.5),
                float(row.get("t_adj") or 22.0),
                float(row.get("humidity") or 50.0),
                float(row.get("wind_speed") or 10.0),
                float(row.get("w_outfit") or 0.3),
                float(row.get("h_outfit") or 0.7),
                float(row.get("f_outfit") or 0.4),
                float(row.get("total_clo") or 0.5),
                float(row.get("omega_structure") or 1.0),
                0.0,   # affinity_score not stored in interactions; default 0
            ]
            X.append(feature_vec)
            y.append(int(row["label_clicked"]))
        except (ValueError, TypeError):
            continue

    if len(X) < 10:
        print("[ml_ranker] Insufficient data – using fallback cosine scorer.")
        return None

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", RandomForestClassifier(
            n_estimators=150,
            max_depth=8,
            random_state=42,
            n_jobs=-1,
        )),
    ])
    model.fit(X, y)

    with open(config.MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    acc = model.score(X, y)
    print(f"[ml_ranker] Model trained on {len(X)} samples. Training accuracy: {acc:.2%}")
    return model


# ─────────────────────────────────────────────────────────────────────────────
# LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_model():
    """Load pickled model from disk, or return None if not found."""
    if os.path.exists(config.MODEL_PATH):
        with open(config.MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION
# ─────────────────────────────────────────────────────────────────────────────

def predict_score(model, feature_vec: list[float]) -> float:
    """
    Return a match probability in [0, 100] using the trained ML model.
    Falls back to 0.0 if model is None.
    """
    if model is None:
        return 0.0
    prob = model.predict_proba([feature_vec])[0]
    # prob[1] = P(label=1 | X) = probability the user likes this outfit
    return round(float(prob[1]) * 100, 2)


# ─────────────────────────────────────────────────────────────────────────────
# COSINE FALLBACK SCORER (used when no ML model is available)
# ─────────────────────────────────────────────────────────────────────────────

def cosine_fallback_score(ideal_clo: float,
                          h_target: float, w_target: float, f_target: float,
                          outfit: OutfitCandidate) -> float:
    """
    6-Dimensional Cosine Similarity as a fallback when no ML model exists.

    V_u = [Ideal_Top, Ideal_Bottom, 1.0, H_target, W_target, F_target]
    V_s = [Clo_top,   Clo_bottom,   Omega_struct, H_outfit, W_outfit, F_outfit]
    r_uS = dot(V_u, V_s) / (|V_u| * |V_s|) * 100
    """
    ideal_top    = ideal_clo * 0.6
    ideal_bottom = ideal_clo * 0.4

    v_u = [ideal_top, ideal_bottom, 1.0, h_target, w_target, f_target]
    v_s = [
        outfit.clo_top, outfit.clo_bottom,
        outfit.omega_structure,
        outfit.h_outfit, outfit.w_outfit, outfit.f_outfit,
    ]

    dot = sum(a * b for a, b in zip(v_u, v_s))
    mag_u = math.sqrt(sum(a ** 2 for a in v_u))
    mag_s = math.sqrt(sum(b ** 2 for b in v_s))

    if mag_u == 0 or mag_s == 0:
        return 0.0

    similarity = (dot / (mag_u * mag_s)) * 100
    return round(similarity, 2)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE IMPORTANCES  (XAI)
# ─────────────────────────────────────────────────────────────────────────────

def get_feature_importances(model) -> list[dict]:
    """
    Returns a ranked list of feature importance dicts for the XAI panel.
    Each dict has: {name, importance (0-100%), group}
    """
    if model is None:
        # Default importances for cosine fallback display
        return [
            {"name": "total_clo",       "importance": 30.0, "group": "Thermal"},
            {"name": "f_outfit",        "importance": 20.0, "group": "Social"},
            {"name": "omega_structure", "importance": 15.0, "group": "Structure"},
            {"name": "t_adj",           "importance": 12.0, "group": "Thermal"},
            {"name": "h_outfit",        "importance": 8.0,  "group": "Environment"},
            {"name": "w_outfit",        "importance": 8.0,  "group": "Environment"},
            {"name": "bmi",             "importance": 5.0,  "group": "User"},
            {"name": "affinity_score",  "importance": 2.0,  "group": "User"},
        ]

    try:
        rf = model.named_steps["clf"]
        raw = rf.feature_importances_
        total = sum(raw)
        if total == 0:
            return []

        # Group mapping for readable display
        groups = {
            "bmi": "User", "f_target": "Social",
            "t_adj": "Thermal", "humidity": "Environment",
            "wind_speed": "Environment", "w_outfit": "Environment",
            "h_outfit": "Environment", "f_outfit": "Social",
            "total_clo": "Thermal", "omega_structure": "Structure",
            "affinity_score": "User",
        }

        items = []
        for name, imp in zip(FEATURE_NAMES, raw):
            items.append({
                "name":       name,
                "importance": round(float(imp / total) * 100, 2),
                "group":      groups.get(name, "Other"),
            })
        items.sort(key=lambda x: x["importance"], reverse=True)
        return items
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RANKING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def rank_candidates(model,
                    candidates: list[OutfitCandidate],
                    user: UserContext,
                    math_trace: dict,
                    liked_styles: dict[str, int]) -> list[OutfitCandidate]:
    """
    Rank outfit candidates using the ML model (or cosine fallback).
    Mutates each candidate's ml_score in place and returns sorted list.
    """
    t_adj    = math_trace["t_adj"]
    h_target = math_trace["h_target"]
    w_target = math_trace["w_target"]
    f_target = math_trace["f_target"]
    ideal_clo = math_trace["ideal_clo"]

    for outfit in candidates:
        affinity = compute_style_affinity(outfit, liked_styles)
        outfit.affinity_score = affinity

        feat_vec = extract_features(user, t_adj, outfit, f_target, affinity)

        if model is not None:
            score = predict_score(model, feat_vec)
        else:
            score = cosine_fallback_score(ideal_clo, h_target, w_target, f_target, outfit)

        outfit.ml_score = score

    candidates.sort(key=lambda c: c.ml_score, reverse=True)
    return candidates
