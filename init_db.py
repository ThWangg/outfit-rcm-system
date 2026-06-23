"""
init_db.py - Database Initialization & Seeding
================================================
Creates all tables and populates:
  - 300+ clothing items spanning diverse garment types, styles, and temperature ranges.
  - 500+ mock user interactions for ML model training.

Run once:
    python init_db.py
"""

import random
import json
import math
import db
import config


def build_catalog() -> list[dict]:
    """
    Returns a list of item definition dicts.
    All items are passed through db.insert_item which auto-resolves alpha/beta from config.
    """
    items = []

    # ── Template helper ────────────────────────────────────────────────────────
    def add(name, category, layer_type, garment_type, style_tag,
            clo, thickness, density, min_temp, max_temp, occasions):
        items.append(dict(
            name=name, category=category, layer_type=layer_type,
            garment_type=garment_type, style_tag=style_tag,
            clo=clo, thickness=thickness, density=density,
            min_temp=min_temp, max_temp=max_temp,
            allowed_occasions=occasions,
        ))

    ALL = ["Home", "Beach", "Gym", "Casual", "Party", "Date", "Office", "Formal"]
    SOCIAL = ["Casual", "Party", "Date", "Office", "Formal"]
    WORK   = ["Office", "Formal", "Date"]
    RELAX  = ["Home", "Casual", "Beach"]
    SPORT  = ["Gym", "Beach", "Casual"]

    # ═══════════════════════════  TOPS  ═══════════════════════════

    # -- T-Shirts (casual, single layer, warm weather) -------------------------
    colors  = ["White", "Black", "Navy", "Grey", "Olive", "Red", "Blue",
               "Coral", "Mint", "Beige", "Charcoal", "Teal", "Burgundy"]
    fabrics = ["Cotton", "Linen", "Bamboo", "Modal"]
    for col in colors:
        for fab in fabrics:
            clo = round(random.uniform(0.09, 0.18), 2)
            t   = round(random.uniform(0.10, 0.22), 2)
            d   = round(random.uniform(0.25, 0.45), 2)
            add(f"{col} {fab} T-Shirt", "Top", "Single", "T-Shirt", "casual",
                clo, t, d, 18, 40, RELAX + ["Party", "Date"])

    # -- Polo Shirts (smart-casual) -------------------------------------------
    polo_cols = ["White", "Navy", "Grey", "Black", "Sky Blue", "Burgundy",
                 "Forest Green", "Dusty Pink", "Royal Blue", "Teal"]
    polo_fabs = ["Pique Cotton", "Jersey Cotton", "Dry-Fit Poly"]
    for col in polo_cols:
        for fab in polo_fabs:
            clo = round(random.uniform(0.15, 0.22), 2)
            t   = round(random.uniform(0.18, 0.28), 2)
            d   = round(random.uniform(0.30, 0.50), 2)
            style = "sporty" if "Dry-Fit" in fab else "smart"
            add(f"{col} {fab} Polo", "Top", "Single", "Polo Shirt", style,
                clo, t, d, 15, 35, ["Casual", "Date", "Office", "Party", "Gym"])

    # -- Button Shirts ---------------------------------------------------------
    shirt_cols = ["White", "Light Blue", "Grey", "Pink", "Navy", "Striped White",
                  "Black", "Chambray Blue", "Checkered", "Olive"]
    shirt_fabs = ["Oxford Cotton", "Linen", "Flannel", "Poplin"]
    for col in shirt_cols:
        for fab in shirt_fabs:
            clo = round(random.uniform(0.20, 0.28), 2)
            t   = round(random.uniform(0.20, 0.30), 2)
            d   = round(random.uniform(0.35, 0.55), 2)
            style = "casual" if fab in ["Flannel", "Linen"] else "formal"
            add(f"{col} {fab} Shirt", "Top", "Single", "Button Shirt", style,
                clo, t, d, 14, 32, WORK + ["Party", "Casual"])

    # -- Tank Tops -------------------------------------------------------------
    tank_cols = ["White", "Black", "Grey", "Pastel Blue", "Coral", "Olive", "Pink", "Red"]
    tank_fabs = ["Ribbed Cotton", "Polyester Sport"]
    for col in tank_cols:
        for fab in tank_fabs:
            clo = round(random.uniform(0.05, 0.10), 2)
            t   = round(random.uniform(0.05, 0.12), 2)
            d   = round(random.uniform(0.20, 0.35), 2)
            style = "sporty" if "Sport" in fab else "beach"
            add(f"{col} {fab} Tank", "Top", "Inner", "Tank Top", style,
                clo, t, d, 22, 42, ["Beach", "Home", "Gym"])

    # -- Sweaters (mid-layer, smart-casual/formal) -----------------------------
    sw_cols = ["Cream", "Charcoal", "Forest Green", "Navy", "Burgundy",
               "Camel", "Heather Grey", "Slate Blue"]
    sw_fabs = ["Knit Wool", "Cashmere Blend"]
    for col in sw_cols:
        for fab in sw_fabs:
            clo = round(random.uniform(0.35, 0.55), 2)
            t   = round(random.uniform(0.40, 0.60), 2)
            d   = round(random.uniform(0.50, 0.70), 2)
            add(f"{col} {fab} Sweater", "Top", "Outer", "Sweater", "smart",
                clo, t, d, 5, 18, ["Office", "Casual", "Date", "Formal"])

    # -- Hoodies ---------------------------------------------------------------
    hoodie_cols = ["Grey", "Black", "Navy", "Olive", "Burgundy", "Off-White", "Red", "Charcoal"]
    hoodie_fabs = ["Fleece", "Cotton Terry"]
    for col in hoodie_cols:
        for fab in hoodie_fabs:
            clo = round(random.uniform(0.30, 0.50), 2)
            t   = round(random.uniform(0.35, 0.55), 2)
            d   = round(random.uniform(0.45, 0.65), 2)
            add(f"{col} {fab} Hoodie", "Top", "Outer", "Hoodie", "casual",
                clo, t, d, 5, 20, ["Home", "Casual", "Gym"])

    # -- Light Jackets (outer layer) -------------------------------------------
    jacket_variants = [
        ("Denim", "casual"), ("Bomber", "casual"), ("Windbreaker", "sporty"),
        ("Track", "sporty"), ("Chore", "casual"), ("Linen", "smart"),
    ]
    for (jtype, style) in jacket_variants:
        for col in ["Black", "Navy", "Grey", "Khaki", "Olive"]:
            clo = round(random.uniform(0.25, 0.45), 2)
            t   = round(random.uniform(0.30, 0.50), 2)
            d   = round(random.uniform(0.40, 0.65), 2)
            add(f"{col} {jtype} Jacket", "Top", "Outer", "Jacket", style,
                clo, t, d, 8, 22, ALL)

    # -- Blazers ---------------------------------------------------------------
    blazer_cols = ["Black", "Navy", "Charcoal", "Light Grey", "Beige", "Camel"]
    blazer_fabs = ["Classic Wool", "Relaxed Linen"]
    for col in blazer_cols:
        for fab in blazer_fabs:
            clo = round(random.uniform(0.35, 0.55), 2)
            t   = round(random.uniform(0.40, 0.60), 2)
            d   = round(random.uniform(0.55, 0.75), 2)
            style = "casual" if "Linen" in fab else "formal"
            add(f"{col} {fab} Blazer", "Top", "Outer", "Blazer", style,
                clo, t, d, 8, 24, WORK + ["Party"])

    # -- Winter Coats ----------------------------------------------------------
    coat_cols = ["Black", "Camel", "Navy", "Charcoal", "Olive"]
    coat_fabs = ["Heavy Wool", "Down Puffer"]
    for col in coat_cols:
        for fab in coat_fabs:
            clo = round(random.uniform(0.70, 1.20), 2)
            t   = round(random.uniform(0.70, 1.00), 2)
            d   = round(random.uniform(0.70, 0.90), 2)
            style = "casual" if "Down" in fab else "formal"
            add(f"{col} {fab} Coat", "Top", "Outer", "Coat", style,
                clo, t, d, -5, 12, ["Office", "Formal", "Date", "Casual"])

    # -- Vests -----------------------------------------------------------------
    vest_cols = ["Black", "Navy", "Grey", "Burgundy"]
    vest_fabs = ["Suit Vest", "Puffer Vest"]
    for col in vest_cols:
        for fab in vest_fabs:
            clo = round(random.uniform(0.20, 0.35), 2)
            t   = round(random.uniform(0.25, 0.40), 2)
            d   = round(random.uniform(0.45, 0.65), 2)
            style = "formal" if "Suit" in fab else "outdoor"
            add(f"{col} {fab}", "Top", "Outer", "Vest", style,
                clo, t, d, 10, 24, WORK if "Suit" in fab else RELAX)

    # ═══════════════════════════  BOTTOMS  ════════════════════════

    # -- Jeans -----------------------------------------------------------------
    jean_cuts = ["Slim", "Straight", "Relaxed", "Skinny", "Tapered"]
    jean_cols = ["Blue", "Dark Blue", "Black", "Grey", "Light Blue", "Indigo", "Charcoal"]
    for cut in jean_cuts:
        for col in jean_cols:
            clo = round(random.uniform(0.22, 0.34), 2)
            t   = round(random.uniform(0.28, 0.40), 2)
            d   = round(random.uniform(0.55, 0.75), 2)
            add(f"{col} {cut} Jeans", "Bottom", "Single", "Jeans", "casual",
                clo, t, d, 10, 28, ALL)

    # -- Trousers (formal) -----------------------------------------------------
    trouser_cols = ["Black", "Navy", "Charcoal", "Light Grey", "Beige", "Dark Brown", "Olive"]
    trouser_fabs = ["Wool Suit", "Cotton Blend"]
    for col in trouser_cols:
        for fab in trouser_fabs:
            clo = round(random.uniform(0.25, 0.38), 2)
            t   = round(random.uniform(0.30, 0.42), 2)
            d   = round(random.uniform(0.55, 0.75), 2)
            add(f"{col} {fab} Trousers", "Bottom", "Single", "Dress Pants", "formal",
                clo, t, d, 8, 28, WORK + ["Party", "Date"])

    # -- Chinos ----------------------------------------------------------------
    chino_cols = ["Khaki", "Olive", "Navy", "Beige", "Stone", "Burgundy", "White"]
    chino_fabs = ["Classic Twill", "Stretch Cotton"]
    for col in chino_cols:
        for fab in chino_fabs:
            clo = round(random.uniform(0.20, 0.32), 2)
            t   = round(random.uniform(0.25, 0.38), 2)
            d   = round(random.uniform(0.50, 0.68), 2)
            add(f"{col} {fab} Chinos", "Bottom", "Single", "Chinos", "smart",
                clo, t, d, 12, 30, ["Office", "Casual", "Date", "Party"])

    # -- Shorts ----------------------------------------------------------------
    shorts_cols = ["Khaki", "Navy", "Black", "Olive", "Light Grey", "White", "Blue"]
    shorts_fabs = ["Tailored Chino", "Fleece Sweat", "Swim Nylon"]
    for col in shorts_cols:
        for fab in shorts_fabs:
            clo = round(random.uniform(0.09, 0.15), 2)
            t   = round(random.uniform(0.12, 0.20), 2)
            d   = round(random.uniform(0.30, 0.50), 2)
            style = "sporty" if "Swim" in fab or "Sweat" in fab else "casual"
            add(f"{col} {fab} Shorts", "Bottom", "Single", "Shorts", style,
                clo, t, d, 20, 42, RELAX + ["Gym", "Party"])

    # -- Joggers / Sweatpants --------------------------------------------------
    jog_cols = ["Grey", "Black", "Navy", "Olive", "Burgundy"]
    jog_fabs = ["Heavy Fleece", "Tech Stretch"]
    for col in jog_cols:
        for fab in jog_fabs:
            clo = round(random.uniform(0.22, 0.35), 2)
            t   = round(random.uniform(0.28, 0.42), 2)
            d   = round(random.uniform(0.45, 0.65), 2)
            add(f"{col} {fab} Joggers", "Bottom", "Single", "Joggers", "sporty",
                clo, t, d, 5, 22, ["Home", "Gym", "Casual"])

    # -- Cargo Pants -----------------------------------------------------------
    cargo_cols = ["Olive", "Black", "Khaki", "Grey"]
    cargo_fabs = ["Ripstop Nylon", "Heavy Cotton"]
    for col in cargo_cols:
        for fab in cargo_fabs:
            clo = round(random.uniform(0.28, 0.42), 2)
            t   = round(random.uniform(0.32, 0.50), 2)
            d   = round(random.uniform(0.55, 0.75), 2)
            add(f"{col} {fab} Cargo Pants", "Bottom", "Single", "Cargo Pants", "outdoor",
                clo, t, d, 8, 25, ["Casual", "Gym", "Beach", "Home"])

    # -- Leggings --------------------------------------------------------------
    leg_cols = ["Black", "Navy", "Grey", "Olive"]
    leg_fabs = ["Athletic Compression", "Thermal Fleece"]
    for col in leg_cols:
        for fab in leg_fabs:
            clo = round(random.uniform(0.10, 0.20), 2)
            t   = round(random.uniform(0.12, 0.22), 2)
            d   = round(random.uniform(0.35, 0.55), 2)
            add(f"{col} {fab} Leggings", "Bottom", "Single", "Leggings", "sporty",
                clo, t, d, 8, 28, ["Gym", "Home", "Casual"])

    # -- Skirts ----------------------------------------------------------------
    skirt_cols = ["Black", "Navy", "Beige", "Burgundy", "Olive"]
    skirt_fabs = ["Pleated Midi", "Denim Mini"]
    for col in skirt_cols:
        for fab in skirt_fabs:
            clo = round(random.uniform(0.12, 0.20), 2)
            t   = round(random.uniform(0.14, 0.24), 2)
            d   = round(random.uniform(0.35, 0.55), 2)
            style = "casual" if "Denim" in fab else "smart"
            add(f"{col} {fab} Skirt", "Bottom", "Single", "Skirt", style,
                clo, t, d, 14, 32, ["Casual", "Date", "Office", "Party"])

    return items


def build_mock_interactions(conn, user_ids: list[int],
                             item_ids: list[int], n: int = 600) -> None:
    """
    Generate synthetic interaction records for ML training.
    Outfits that match thermal and formality needs are labelled 1, others 0.
    """
    rng = random.Random(42)
    all_items = db.get_all_items(conn)
    tops    = [i for i in all_items if i["category"] == "Top"]
    bottoms = [i for i in all_items if i["category"] == "Bottom"]

    for _ in range(n):
        user_id   = rng.choice(user_ids)
        bmi_val   = rng.uniform(17.0, 38.0)
        t_weather = rng.uniform(5.0, 38.0)
        humidity  = rng.uniform(20.0, 95.0)
        wind_speed = rng.uniform(0.0, 40.0)
        occasion  = rng.choice(list(config.OCCASION_FORMALITY.keys()))
        f_target  = config.OCCASION_FORMALITY[occasion]
        t_adj     = t_weather + (bmi_val - config.IDEAL_BMI) * config.K_COEFF

        if not tops or not bottoms:
            continue
        top    = rng.choice(tops)
        bottom = rng.choice(bottoms)

        total_clo     = top["clo"] + bottom["clo"]
        clo_ratio     = bottom["clo"] / total_clo if total_clo > 0 else 0
        omega_struct  = 1.0 if clo_ratio >= 0.20 else 0.0

        ideal_clo = ((config.NEUTRAL_T - t_adj) / config.CLO_DIVISOR) + config.CLO_BASE

        # Compute outfit attributes
        w_vals = []
        h_vals = []
        f_vals = []
        for item in [top, bottom]:
            td = item["thickness"] * item["density"]
            w_vals.append(min(1.0, math.sqrt(td)))
            h_vals.append(max(0.0, 1.0 - td))
            f_vals.append(item["alpha_type"] * item["beta_style"])

        w_outfit = max(w_vals)
        h_outfit = min(h_vals)
        f_outfit = min(f_vals)

        # Label: 1 if clo is reasonably close to ideal AND style+ratio OK
        clo_diff  = abs(total_clo - ideal_clo)
        form_diff = abs(f_outfit - f_target)
        is_good   = (clo_diff < 0.4 and form_diff < 0.30
                     and clo_ratio >= 0.20 and omega_struct >= 0.9)
        label = 1 if is_good else 0

        sig = f"{sorted([top['id'], bottom['id']])}"
        features = dict(
            bmi=bmi_val, t_adj=round(t_adj, 3), humidity=humidity,
            wind_speed=wind_speed, f_target=f_target,
            w_outfit=round(w_outfit, 4), h_outfit=round(h_outfit, 4),
            f_outfit=round(f_outfit, 4), total_clo=round(total_clo, 3),
            omega_structure=omega_struct,
        )
        db.log_interaction(conn, user_id, sig, label, features)

    print(f"  Inserted {n} mock interactions.")


def run(force=False):
    conn = db.get_db_connection()
    db.create_tables(conn)

    # Check if already seeded
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM clothing_items")
    row = cur.fetchone()
    count = row["cnt"] if isinstance(row, dict) else row[0]
    
    if count > 0 and not force:
        print(f"Database already seeded with {count} items. Skipping.")
        conn.close()
        return

    if force:
        print("Force seeding: clearing all tables...")
        if config.DB_MODE == "mysql":
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cur.execute("TRUNCATE TABLE user_wardrobe;")
            cur.execute("TRUNCATE TABLE user_interactions;")
            cur.execute("TRUNCATE TABLE clothing_items;")
            cur.execute("TRUNCATE TABLE users;")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        else:
            cur.execute("PRAGMA foreign_keys = OFF;")
            cur.execute("DELETE FROM user_wardrobe;")
            cur.execute("DELETE FROM user_interactions;")
            cur.execute("DELETE FROM clothing_items;")
            cur.execute("DELETE FROM users;")
            cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

    print("Seeding clothing catalog...")
    catalog = build_catalog()
    for item in catalog:
        db.insert_item(
            conn,
            name=item["name"],
            category=item["category"],
            layer_type=item["layer_type"],
            garment_type=item["garment_type"],
            style_tag=item["style_tag"],
            clo=item["clo"],
            thickness=item["thickness"],
            density=item["density"],
            min_temp=item["min_temp"],
            max_temp=item["max_temp"],
            allowed_occasions=item["allowed_occasions"],
        )
    print(f"  Inserted {len(catalog)} clothing items.")

    # Create seed users for interaction generation
    seed_users = [
        ("seed_alice", "pass", 162.0, 58.0),
        ("seed_bob",   "pass", 178.0, 90.0),
        ("seed_carol", "pass", 155.0, 45.0),
        ("seed_dave",  "pass", 185.0, 105.0),
    ]
    user_ids = []
    for uname, pwd, h, w in seed_users:
        uid = db.register_user(conn, uname, pwd, h, w)
        if uid:
            user_ids.append(uid)
    print(f"  Created {len(user_ids)} seed users for interaction generation.")

    all_items = db.get_all_items(conn)
    item_ids  = [i["id"] for i in all_items]

    print("Generating mock interaction history...")
    build_mock_interactions(conn, user_ids, item_ids, n=600)

    conn.close()
    print("Database initialization complete.")


if __name__ == "__main__":
    run(force=True)
