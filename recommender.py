"""
recommender.py - Core Recommendation Pipeline
===============================================
Implements the deterministic 3-stage Context-Aware pipeline:
  Stage 1: Pre-filtering  (thermal + social)
  Stage 2: Post-filtering (Clo Ratio + Structural Integrity)
  Stage 3: Feature extraction for ML ranking

All pure functions are fully documented and decoupled.
No ML libraries used inside this file.
"""

from __future__ import annotations
import json
import math
import itertools
from dataclasses import dataclass, field
from typing import Optional
import config


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClothingItem:
    """Represents one garment loaded from the database."""
    id:               int
    name:             str
    category:         str          # "Top" | "Bottom"
    layer_type:       str          # "Inner" | "Outer" | "Single"
    garment_type:     str
    style_tag:        str
    clo:              float
    thickness:        float        # t_j
    density:          float        # d_j
    alpha_type:       float        # structural cut weight (from config lookup via DB)
    beta_style:       float        # style intent baseline (from config lookup via DB)
    min_temp:         float
    max_temp:         float
    allowed_occasions: list[str]

    @classmethod
    def from_db_row(cls, row: dict) -> "ClothingItem":
        occasions = row.get("allowed_occasions", "[]")
        if isinstance(occasions, str):
            occasions = json.loads(occasions)
        return cls(
            id=row["id"], name=row["name"],
            category=row["category"], layer_type=row["layer_type"],
            garment_type=row["garment_type"], style_tag=row["style_tag"],
            clo=row["clo"], thickness=row["thickness"], density=row["density"],
            alpha_type=row["alpha_type"], beta_style=row["beta_style"],
            min_temp=row["min_temp"], max_temp=row["max_temp"],
            allowed_occasions=occasions,
        )


@dataclass
class UserContext:
    """Encapsulates all user + environmental context inputs."""
    bmi:        float
    t_weather:  float    # Ambient temperature (°C)
    humidity:   float    # Relative humidity % (0-100)
    wind_speed: float    # Wind speed km/h (0-40)
    occasion:   str


@dataclass
class OutfitCandidate:
    """A validated multi-layered outfit ensemble."""
    items:           list[ClothingItem]
    omega_structure: float
    omega_ratio:     int             # 1 | 0
    total_clo:       float
    clo_top:         float
    clo_bottom:      float
    w_outfit:        float
    h_outfit:        float
    f_outfit:        float
    item_traces:     list[dict] = field(default_factory=list)   # per-item math details
    ml_score:        float = 0.0
    affinity_score:  float = 0.0

    @property
    def signature(self) -> str:
        return ",".join(str(i.id) for i in sorted(self.items, key=lambda x: x.id))


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 & 2 – TEMPERATURE & CLO
# ─────────────────────────────────────────────────────────────────────────────

def calculate_t_adj(t_weather: float, bmi: float, k: float = config.K_COEFF) -> float:
    """
    Step 1 – Adjusted personal temperature.
    T_adj = T_weather + (BMI - 21.7) * K
    """
    return t_weather + (bmi - config.IDEAL_BMI) * k


def determine_ideal_clo(t_adj: float) -> float:
    """
    Step 2 – Ideal insulation demand (may be negative for hot weather).
    Ideal_Clo = ((24.1 - T_adj) / 8) + 0.5
    """
    return ((config.NEUTRAL_T - t_adj) / config.CLO_DIVISOR) + config.CLO_BASE


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – RULE-BASED POST-FILTERING CONSTRAINTS
# ─────────────────────────────────────────────────────────────────────────────

def omega_structure(items: list[ClothingItem], ideal_clo: float) -> float:
    """
    Adaptive structural integrity score Ω_structure(S).

    Returns:
      1.0   – perfectly complete outfit (1 Bottom + adequate top layering)
      0.95  – minor deficiency (cold weather but only single top layer)
      0.0   – invalid (no bottom, multiple bottoms, or no top)
    """
    tops    = [i for i in items if i.category == "Top"]
    bottoms = [i for i in items if i.category == "Bottom"]

    # Hard invalid cases
    if len(bottoms) != 1 or len(tops) == 0:
        return 0.0

    # Cold weather: expect layered top (inner + outer)
    if ideal_clo >= 0.80:
        has_inner = any(t.layer_type == "Inner" for t in tops)
        has_outer = any(t.layer_type == "Outer" for t in tops)
        if has_inner and has_outer:
            return 1.0
        return 0.95   # Only one top layer – minor deficiency but wearable

    # Warm weather: single top layer is adequate
    return 1.0


def omega_ratio(items: list[ClothingItem]) -> int:
    """
    Clo ratio constraint Ω_ratio(S).
    Returns 1 if Clo_bottom / sum(Clo_all) >= 0.20, else 0.
    """
    clo_total  = sum(i.clo for i in items)
    clo_bottom = sum(i.clo for i in items if i.category == "Bottom")
    if clo_total == 0:
        return 0
    return 1 if (clo_bottom / clo_total) >= 0.20 else 0


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 – ENVIRONMENTAL CONTEXT MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def map_contexts(humidity: float, wind_speed: float,
                 occasion: str) -> tuple[float, float, float]:
    """
    Step 4 – Normalize environmental variables to [0, 1].
    H_target = clamp((H_API - 20) / 80, 0, 1)
    W_target = clamp(W_API / 40, 0, 1)
    F_target = mapped from OCCASION_FORMALITY dict
    """
    h_target = max(0.0, min(1.0, (humidity - 20.0) / 80.0))
    w_target = max(0.0, min(1.0, wind_speed / 40.0))
    f_target = config.OCCASION_FORMALITY.get(occasion, 0.5)
    return h_target, w_target, f_target


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – INDIVIDUAL & AGGREGATE OUTFIT ATTRIBUTES
# ─────────────────────────────────────────────────────────────────────────────

def compute_item_attributes(item: ClothingItem) -> dict:
    """
    Per-item indices.
    W_j = min(1.0, sqrt(t_j * d_j))   – windbreak capacity
    H_j = max(0.0, 1.0 - (t_j * d_j)) – breathability (inverse of W)
    F_j = alpha_type * beta_style       – formality score (fetched from DB columns)
    """
    td  = item.thickness * item.density
    w_j = min(1.0, math.sqrt(td))
    h_j = max(0.0, 1.0 - td)
    f_j = item.alpha_type * item.beta_style
    return {"W_j": round(w_j, 4), "H_j": round(h_j, 4), "F_j": round(f_j, 4)}


def compute_ensemble_attributes(items: list[ClothingItem]) -> tuple[float, float, float]:
    """
    Aggregate attributes for an outfit ensemble S.
    W_outfit = max(W_j for j in S)
    H_outfit = min(H_j for j in S)
    F_outfit = min(F_j for j in S)
    """
    attrs    = [compute_item_attributes(i) for i in items]
    w_outfit = max(a["W_j"] for a in attrs)
    h_outfit = min(a["H_j"] for a in attrs)
    f_outfit = min(a["F_j"] for a in attrs)
    return round(w_outfit, 4), round(h_outfit, 4), round(f_outfit, 4)


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE EXTRACTION FOR ML STAGE
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "bmi", "f_target",                              # user features
    "t_adj", "humidity", "wind_speed",              # context features
    "w_outfit", "h_outfit", "f_outfit",             # outfit textile features
    "total_clo", "omega_structure",                 # outfit structure features
    "affinity_score",                               # style affinity
]


def extract_features(user: UserContext, t_adj: float,
                     outfit: OutfitCandidate,
                     f_target: float,
                     affinity_score: float = 0.0) -> list[float]:
    """
    Build the feature vector X for the ML model.
    Feature order must match FEATURE_NAMES.
    """
    return [
        user.bmi,
        f_target,
        t_adj,
        user.humidity,
        user.wind_speed,
        outfit.w_outfit,
        outfit.h_outfit,
        outfit.f_outfit,
        outfit.total_clo,
        outfit.omega_structure,
        affinity_score,
    ]


def compute_style_affinity(outfit: OutfitCandidate,
                            liked_styles: dict[str, int]) -> float:
    """
    Numerical affinity score: fraction of outfit style tags that appear
    in the user's liked style history, weighted by like count.
    Returns a value in [0, 1].
    """
    if not liked_styles:
        return 0.0
    total_likes  = sum(liked_styles.values())
    outfit_styles = {i.style_tag for i in outfit.items}
    matched      = sum(liked_styles.get(s, 0) for s in outfit_styles)
    return round(min(1.0, matched / total_likes), 4)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

class OutfitRecommender:
    """
    Orchestrates the 3-stage hybrid recommendation pipeline.
      Stage 1: Pre-filtering  – thermal & social
      Stage 2: Post-filtering – Clo Ratio + Structural Integrity
      Stage 3: Feature extraction + ML scoring (done externally via ml_ranker)
    """

    # ── Stage 1 ──────────────────────────────────────────────────────────────

    def pre_filter(self, catalog: list[ClothingItem],
                   user: UserContext) -> list[ClothingItem]:
        """
        Eliminate items that:
        1. Are out of temperature season (thermal filter).
        2. Completely violate the occasion (social filter).
        """
        filtered = []
        for item in catalog:
            # Thermal filter
            if not (item.min_temp <= user.t_weather <= item.max_temp):
                continue
            # Social filter
            if user.occasion not in item.allowed_occasions:
                continue
            filtered.append(item)
        return filtered

    # ── Combination Synthesis ─────────────────────────────────────────────────

    def generate_ensembles(self, filtered: list[ClothingItem],
                           max_combos: int = 500
                           ) -> list[list[ClothingItem]]:
        """
        Synthesize valid multi-layered outfit combinations.
        Each ensemble must contain:
          - Exactly 1 Bottom
          - 1 or 2 Tops that share a cohesive style tag.
        Style Integrity Rule: All items in S must share a compatible style tag.
        """
        tops    = [i for i in filtered if i.category == "Top"]
        bottoms = [i for i in filtered if i.category == "Bottom"]

        ensembles: list[list[ClothingItem]] = []

        for bottom in bottoms:
            b_style = bottom.style_tag

            # Compatible tops: same style tag as the bottom
            compat_tops = [t for t in tops if t.style_tag == b_style
                           or self._styles_compatible(t.style_tag, b_style)]

            # Single-top ensembles
            for top in compat_tops:
                ensembles.append([top, bottom])
                if len(ensembles) >= max_combos:
                    return ensembles

            # Two-top ensembles (inner + outer)
            inners = [t for t in compat_tops if t.layer_type == "Inner"]
            outers = [t for t in compat_tops if t.layer_type == "Outer"]
            for inner, outer in itertools.product(inners, outers):
                ensembles.append([inner, outer, bottom])
                if len(ensembles) >= max_combos:
                    return ensembles

        return ensembles

    @staticmethod
    def _styles_compatible(s1: str, s2: str) -> bool:
        """
        Define which style pairs are considered cohesive.
        Prevents obvious clashes (e.g., formal + sporty).
        """
        compat_map: dict[str, set[str]] = {
            "casual":  {"casual", "smart", "outdoor", "home"},
            "smart":   {"smart", "casual", "formal"},
            "formal":  {"formal", "smart"},
            "sporty":  {"sporty", "casual", "outdoor", "beach"},
            "beach":   {"beach", "sporty", "casual"},
            "home":    {"home", "casual", "sporty"},
            "outdoor": {"outdoor", "casual", "sporty"},
        }
        return s2 in compat_map.get(s1, {s1})

    # ── Stage 2 ──────────────────────────────────────────────────────────────

    def post_filter(self, ensembles: list[list[ClothingItem]],
                    ideal_clo: float) -> list[OutfitCandidate]:
        """
        Apply rule-based constraints and build OutfitCandidate objects.
        Keep ONLY outfits where:
          - Omega_structure(S) >= 0.90
          - Omega_ratio(S) == 1
        """
        candidates: list[OutfitCandidate] = []

        for items in ensembles:
            o_struct = omega_structure(items, ideal_clo)
            o_ratio  = omega_ratio(items)

            # ─ Hard filters ─────────────────────────────────────────────────
            if o_struct < 0.90:
                continue
            if o_ratio != 1:
                continue

            # ─ Build candidate ───────────────────────────────────────────────
            clo_top    = sum(i.clo for i in items if i.category == "Top")
            clo_bottom = sum(i.clo for i in items if i.category == "Bottom")
            total_clo  = clo_top + clo_bottom
            w_out, h_out, f_out = compute_ensemble_attributes(items)

            item_traces = []
            for item in items:
                attrs = compute_item_attributes(item)
                item_traces.append({
                    "id":          item.id,
                    "name":        item.name,
                    "category":    item.category,
                    "clo":         item.clo,
                    "alpha_type":  item.alpha_type,
                    "beta_style":  item.beta_style,
                    **attrs,
                })

            candidates.append(OutfitCandidate(
                items=items,
                omega_structure=o_struct,
                omega_ratio=o_ratio,
                total_clo=round(total_clo, 3),
                clo_top=round(clo_top, 3),
                clo_bottom=round(clo_bottom, 3),
                w_outfit=w_out,
                h_outfit=h_out,
                f_outfit=f_out,
                item_traces=item_traces,
            ))

        return candidates

    # ── Full pipeline (no ML score – that is applied externally) ─────────────

    def build_candidates(self, wardrobe: list[dict],
                         user: UserContext) -> tuple[list[OutfitCandidate], dict]:
        """
        Runs Stages 1 & 2 and returns (candidates, math_trace).
        math_trace contains all intermediate values for UI visualization.
        """
        catalog = [ClothingItem.from_db_row(r) for r in wardrobe]

        t_adj     = calculate_t_adj(user.t_weather, user.bmi)
        ideal_clo = determine_ideal_clo(t_adj)
        h_target, w_target, f_target = map_contexts(
            user.humidity, user.wind_speed, user.occasion
        )

        math_trace = {
            "t_weather":  user.t_weather,
            "bmi":        user.bmi,
            "k_coeff":    config.K_COEFF,
            "t_adj":      round(t_adj, 3),
            "ideal_clo":  round(ideal_clo, 3),
            "h_target":   round(h_target, 4),
            "w_target":   round(w_target, 4),
            "f_target":   f_target,
            "occasion":   user.occasion,
        }

        # Stage 1
        filtered = self.pre_filter(catalog, user)

        if not filtered:
            return [], math_trace

        # Synthesis
        ensembles = self.generate_ensembles(filtered, max_combos=800)

        # Stage 2 (rule-based post-filter)
        candidates = self.post_filter(ensembles, ideal_clo)

        return candidates, math_trace
