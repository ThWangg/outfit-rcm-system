import json
import math
import os
import requests
from flask import (Flask, render_template, request, redirect, url_for, session, jsonify, flash)
import config
import db
import init_db
import ml_ranker
from recommender import OutfitRecommender, UserContext

# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Global ML model (loaded/trained at startup)
_MODEL = None
_RECOMMENDER = OutfitRecommender()


def startup():
    """Initialise DB and load (or train) the ML model."""
    global _MODEL
    conn = db.get_db_connection()

    # Ensure tables + seed data exist
    db.create_tables(conn)
    init_db.run()

    # Load or train the ML model
    _MODEL = ml_ranker.load_model()
    if _MODEL is None:
        print("[app] No pickled model found – training from interaction data...")
        interactions = db.get_all_interactions(conn)
        _MODEL = ml_ranker.train_model(interactions)
        if _MODEL is None:
            print("[app] WARNING: ML model unavailable. Using cosine fallback.")
    else:
        print("[app] ML model loaded from disk.")

    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def current_user():
    return session.get("user")


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = db.get_db_connection()
        user = db.login_user(conn, username, password)
        conn.close()
        if user:
            session["user"] = {
                "id":       user["id"],
                "username": user["username"],
                "bmi":      user["bmi"],
                "height":   user["height_cm"],
                "weight":   user["weight_kg"],
            }
            return redirect(url_for("dashboard"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        try:
            height = float(request.form.get("height_cm", 170))
            weight = float(request.form.get("weight_kg", 65))
        except ValueError:
            error = "Height and weight must be numbers."
            return render_template("register.html", error=error)

        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif height <= 0 or weight <= 0:
            error = "Height and weight must be positive."
        else:
            conn = db.get_db_connection()
            uid = db.register_user(conn, username, password, height, weight)
            conn.close()
            if uid:
                flash("Registration successful! Please log in.")
                return redirect(url_for("login"))
            error = "Username already taken."

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
# WARDROBE ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/wardrobe")
@login_required
def wardrobe():
    user  = current_user()
    conn  = db.get_db_connection()
    my_items    = db.get_wardrobe(conn, user["id"])
    my_ids      = {i["id"] for i in my_items}
    all_items   = db.get_all_items(conn)
    catalog     = [i for i in all_items if i["id"] not in my_ids]
    conn.close()
    return render_template("wardrobe.html",
                           user=user,
                           my_items=my_items,
                           catalog=catalog)


@app.route("/wardrobe/add", methods=["POST"])
@login_required
def wardrobe_add():
    user    = current_user()
    item_id = request.form.get("item_id", type=int)
    if item_id:
        conn = db.get_db_connection()
        db.add_to_wardrobe(conn, user["id"], item_id)
        conn.close()
    return redirect(url_for("wardrobe"))


@app.route("/wardrobe/remove", methods=["POST"])
@login_required
def wardrobe_remove():
    user    = current_user()
    item_id = request.form.get("item_id", type=int)
    if item_id:
        conn = db.get_db_connection()
        db.remove_from_wardrobe(conn, user["id"], item_id)
        conn.close()
    return redirect(url_for("wardrobe"))


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    occasions = list(config.OCCASION_FORMALITY.keys())
    importances = ml_ranker.get_feature_importances(_MODEL)
    return render_template("dashboard.html",
                           user=user,
                           occasions=occasions,
                           importances=importances)


# ─────────────────────────────────────────────────────────────────────────────
# API – WEATHER
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/weather")
@login_required
def api_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "city parameter required"}), 400
    try:
        # Step 1: geocode
        geo_resp = requests.get(config.GEOCODING_URL, params={
            "name": city, "count": 1, "language": "en", "format": "json"
        }, timeout=5)
        geo_data = geo_resp.json()
        if not geo_data.get("results"):
            return jsonify({"error": f"City '{city}' not found."}), 404

        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        city_name = loc.get("name", city)

        # Step 2: current weather
        wx_resp = requests.get(config.WEATHER_URL, params={
            "latitude":  lat,
            "longitude": lon,
            "current":   "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "wind_speed_unit": "kmh",
        }, timeout=5)
        wx_data = wx_resp.json()
        cur = wx_data.get("current", {})

        return jsonify({
            "city":        city_name,
            "temperature": cur.get("temperature_2m"),
            "humidity":    cur.get("relative_humidity_2m"),
            "wind_speed":  cur.get("wind_speed_10m"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# API – RECOMMEND
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/recommend", methods=["POST"])
@login_required
def api_recommend():
    user_session = current_user()
    data = request.json or {}

    try:
        t_weather  = float(data.get("temperature", 25))
        humidity   = float(data.get("humidity", 60))
        wind_speed = float(data.get("wind_speed", 10))
        occasion   = data.get("occasion", "Casual")
        bmi        = float(user_session.get("bmi", 22.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input parameters."}), 400

    user_ctx = UserContext(
        bmi=bmi,
        t_weather=t_weather,
        humidity=humidity,
        wind_speed=wind_speed,
        occasion=occasion,
    )

    conn = db.get_db_connection()
    wardrobe = db.get_wardrobe(conn, user_session["id"])

    if not wardrobe:
        conn.close()
        return jsonify({
            "error": "Your wardrobe is empty. Please add items first.",
            "results": [],
        })

    liked_styles = db.get_liked_styles(conn, user_session["id"])
    conn.close()

    # ── Pipeline ─────────────────────────────────────────────────────────────
    candidates, math_trace = _RECOMMENDER.build_candidates(wardrobe, user_ctx)

    if not candidates:
        return jsonify({
            "math_trace": math_trace,
            "results": [],
            "message": "No valid outfit combinations found for the given context.",
        })

    mode = data.get("mode", "ml")
    active_model = _MODEL if mode == "ml" else None

    ranked = ml_ranker.rank_candidates(
        active_model, candidates, user_ctx, math_trace, liked_styles
    )

    top_n = ranked[:10]
    feature_importances = ml_ranker.get_feature_importances(active_model)

    results = []
    for outfit in top_n:
        results.append({
            "signature":       outfit.signature,
            "ml_score":        outfit.ml_score,
            "affinity_score":  outfit.affinity_score,
            "total_clo":       outfit.total_clo,
            "clo_top":         outfit.clo_top,
            "clo_bottom":      outfit.clo_bottom,
            "omega_structure": outfit.omega_structure,
            "omega_ratio":     outfit.omega_ratio,
            "w_outfit":        outfit.w_outfit,
            "h_outfit":        outfit.h_outfit,
            "f_outfit":        outfit.f_outfit,
            "items": [
                {
                    "id":         item.id,
                    "name":       item.name,
                    "category":   item.category,
                    "layer_type": item.layer_type,
                    "style_tag":  item.style_tag,
                    "clo":        item.clo,
                }
                for item in outfit.items
            ],
            "item_traces": outfit.item_traces,
        })

    return jsonify({
        "math_trace":          math_trace,
        "feature_importances": feature_importances,
        "results":             results,
        "mode":                mode
    })


# ─────────────────────────────────────────────────────────────────────────────
# API – LOG INTERACTION
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/interact", methods=["POST"])
@login_required
def api_interact():
    """Log a click/like event to user_interactions for ongoing ML learning."""
    user_session = current_user()
    data = request.json or {}
    sig   = data.get("signature", "")
    label = int(data.get("label", 1))
    feat  = data.get("features", {})

    conn = db.get_db_connection()
    db.log_interaction(conn, user_session["id"], sig, label, feat)
    conn.close()
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    startup()
    app.run(debug=config.DEBUG, port=5000)
