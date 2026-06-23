import sqlite3
import hashlib
import json
from typing import Optional
import config


#connectiom
def get_db_connection():
    """Return a database connection based on config.DB_MODE."""
    if config.DB_MODE == "mysql":
        try:
            import pymysql
            conn = pymysql.connect(
                host=config.MYSQL_HOST,
                port=config.MYSQL_PORT,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
            )
            cur = conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.select_db(config.MYSQL_DATABASE)
            return conn
        except ImportError:
            raise RuntimeError("pymysql not installed. Run: pip install pymysql")
    else:
        conn = sqlite3.connect(config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def placeholder(n: int = 1) -> str:
    """Return the correct parameterized query placeholder for the active DB."""
    if config.DB_MODE == "mysql":
        return ",".join(["%s"] * n) if n > 1 else "%s"
    return ",".join(["?"] * n) if n > 1 else "?"


def ph(n: int = 1) -> str:
    return placeholder(n)


# ── Table Creation ────────────────────────────────────────────────────────────

def create_tables(conn) -> None:
    """Create all tables if they do not exist."""
    cur = conn.cursor()
    
    if config.DB_MODE == "mysql":
        # Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                username      VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                height_cm     DOUBLE       NOT NULL DEFAULT 170,
                weight_kg     DOUBLE       NOT NULL DEFAULT 65,
                bmi           DOUBLE       NOT NULL DEFAULT 22.0
            )
        """)
        # Global clothing catalog
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clothing_items (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                name             VARCHAR(255) NOT NULL,
                category         VARCHAR(255) NOT NULL,
                layer_type       VARCHAR(255) NOT NULL,
                garment_type     VARCHAR(255) NOT NULL,
                style_tag        VARCHAR(255) NOT NULL,
                clo              DOUBLE       NOT NULL,
                thickness        DOUBLE       NOT NULL,
                density          DOUBLE       NOT NULL,
                alpha_type       DOUBLE       NOT NULL,
                beta_style       DOUBLE       NOT NULL,
                min_temp         DOUBLE       NOT NULL,
                max_temp         DOUBLE       NOT NULL,
                allowed_occasions TEXT         NOT NULL
            )
        """)
        # User private wardrobe (items from global catalog)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_wardrobe (
                id      INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                item_id INT NOT NULL,
                UNIQUE(user_id, item_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES clothing_items(id) ON DELETE CASCADE
            )
        """)
        # Interaction history for ML training
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                user_id          INT NOT NULL,
                outfit_signature VARCHAR(255) NOT NULL,
                label_clicked    INT NOT NULL,
                bmi              DOUBLE,
                t_adj            DOUBLE,
                humidity         DOUBLE,
                wind_speed       DOUBLE,
                f_target         DOUBLE,
                w_outfit         DOUBLE,
                h_outfit         DOUBLE,
                f_outfit         DOUBLE,
                total_clo        DOUBLE,
                omega_structure  DOUBLE,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
    else:
        # Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                height_cm     REAL    NOT NULL DEFAULT 170,
                weight_kg     REAL    NOT NULL DEFAULT 65,
                bmi           REAL    NOT NULL DEFAULT 22.0
            )
        """)
        # Global clothing catalog
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clothing_items (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT    NOT NULL,
                category         TEXT    NOT NULL,   -- Top | Bottom
                layer_type       TEXT    NOT NULL,   -- Inner | Outer | Single
                garment_type     TEXT    NOT NULL,   -- T-Shirt, Jeans, etc.
                style_tag        TEXT    NOT NULL,   -- casual | formal | sporty | ...
                clo              REAL    NOT NULL,
                thickness        REAL    NOT NULL,
                density          REAL    NOT NULL,
                alpha_type       REAL    NOT NULL,   -- cut weight (from config lookup)
                beta_style       REAL    NOT NULL,   -- style intent (from config lookup)
                min_temp         REAL    NOT NULL,
                max_temp         REAL    NOT NULL,
                allowed_occasions TEXT   NOT NULL    -- JSON list of strings
            )
        """)
        # User private wardrobe (items from global catalog)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_wardrobe (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                item_id INTEGER NOT NULL REFERENCES clothing_items(id) ON DELETE CASCADE,
                UNIQUE(user_id, item_id)
            )
        """)
        # Interaction history for ML training
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                outfit_signature TEXT    NOT NULL,   -- comma-joined sorted item IDs
                label_clicked    INTEGER NOT NULL,   -- 1 = liked, 0 = dismissed
                bmi              REAL,
                t_adj            REAL,
                humidity         REAL,
                wind_speed       REAL,
                f_target         REAL,
                w_outfit         REAL,
                h_outfit         REAL,
                f_outfit         REAL,
                total_clo        REAL,
                omega_structure  REAL,
                created_at       TEXT DEFAULT (datetime('now'))
            )
        """)
    conn.commit()


# ── Users ─────────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(conn, username: str, password: str,
                  height_cm: float, weight_kg: float) -> Optional[int]:
    """Register a new user. Returns user id or None if username taken."""
    bmi = weight_kg / ((height_cm / 100) ** 2)
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO users (username, password_hash, height_cm, weight_kg, bmi) "
            f"VALUES ({ph()},{ph()},{ph()},{ph()},{ph()})",
            (username, _hash(password), height_cm, weight_kg, round(bmi, 2))
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        return None


def login_user(conn, username: str, password: str) -> Optional[dict]:
    """Validate credentials. Returns user dict or None."""
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE username = {ph()}", (username,))
    row = cur.fetchone()
    if row and row["password_hash"] == _hash(password):
        return dict(row)
    return None


def get_user_by_id(conn, user_id: int) -> Optional[dict]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {ph()}", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def update_user_profile(conn, user_id: int, height_cm: float, weight_kg: float) -> None:
    bmi = weight_kg / ((height_cm / 100) ** 2)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE users SET height_cm={ph()}, weight_kg={ph()}, bmi={ph()} WHERE id={ph()}",
        (height_cm, weight_kg, round(bmi, 2), user_id)
    )
    conn.commit()


# ── Clothing Items ────────────────────────────────────────────────────────────

def get_all_items(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM clothing_items ORDER BY category, name")
    return [dict(r) for r in cur.fetchall()]


def get_item_by_id(conn, item_id: int) -> Optional[dict]:
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM clothing_items WHERE id = {ph()}", (item_id,))
    row = cur.fetchone()
    return dict(row) if row else None


# ── Wardrobe ─────────────────────────────────────────────────────────────────

def get_wardrobe(conn, user_id: int) -> list[dict]:
    """Return all clothing items in a user's wardrobe."""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT ci.* FROM clothing_items ci
        JOIN user_wardrobe uw ON uw.item_id = ci.id
        WHERE uw.user_id = {ph()}
        ORDER BY ci.category, ci.name
    """, (user_id,))
    return [dict(r) for r in cur.fetchall()]


def get_wardrobe_item_ids(conn, user_id: int) -> set[int]:
    cur = conn.cursor()
    cur.execute(f"SELECT item_id FROM user_wardrobe WHERE user_id = {ph()}", (user_id,))
    return {row["item_id"] for row in cur.fetchall()}


def add_to_wardrobe(conn, user_id: int, item_id: int) -> bool:
    try:
        cur = conn.cursor()
        cmd = "INSERT IGNORE" if config.DB_MODE == "mysql" else "INSERT OR IGNORE"
        cur.execute(
            f"{cmd} INTO user_wardrobe (user_id, item_id) VALUES ({ph()},{ph()})",
            (user_id, item_id)
        )
        conn.commit()
        return True
    except Exception:
        return False


def remove_from_wardrobe(conn, user_id: int, item_id: int) -> None:
    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM user_wardrobe WHERE user_id={ph()} AND item_id={ph()}",
        (user_id, item_id)
    )
    conn.commit()


# ── Interactions ──────────────────────────────────────────────────────────────

def log_interaction(conn, user_id: int, outfit_signature: str,
                    label: int, features: dict) -> None:
    """Store a user interaction event for ML training."""
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO user_interactions
          (user_id, outfit_signature, label_clicked,
           bmi, t_adj, humidity, wind_speed, f_target,
           w_outfit, h_outfit, f_outfit, total_clo, omega_structure)
        VALUES ({ph(13)})
    """, (
        user_id, outfit_signature, label,
        features.get("bmi"), features.get("t_adj"),
        features.get("humidity"), features.get("wind_speed"),
        features.get("f_target"), features.get("w_outfit"),
        features.get("h_outfit"), features.get("f_outfit"),
        features.get("total_clo"), features.get("omega_structure"),
    ))
    conn.commit()


def get_all_interactions(conn) -> list[dict]:
    """Fetch all interactions for ML model training."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_interactions WHERE bmi IS NOT NULL")
    return [dict(r) for r in cur.fetchall()]


def get_liked_styles(conn, user_id: int) -> dict[str, int]:
    """
    Return a dict of {style_tag: count} representing the user's
    historically liked style preferences.
    """
    cur = conn.cursor()
    cur.execute(f"""
        SELECT ci.style_tag
        FROM user_interactions ui
        JOIN user_wardrobe uw ON uw.user_id = ui.user_id
        JOIN clothing_items ci ON ci.id = uw.item_id
        WHERE ui.user_id = {ph()} AND ui.label_clicked = 1
    """, (user_id,))
    counts: dict[str, int] = {}
    for row in cur.fetchall():
        tag = row["style_tag"]
        counts[tag] = counts.get(tag, 0) + 1
    return counts


# ── Seed Helper ───────────────────────────────────────────────────────────────

def insert_item(conn, name: str, category: str, layer_type: str,
                garment_type: str, style_tag: str, clo: float,
                thickness: float, density: float,
                min_temp: float, max_temp: float,
                allowed_occasions: list[str]) -> int:
    """Insert a clothing item and auto-compute alpha_type, beta_style from config."""
    alpha = config.ALPHA_TYPE.get(garment_type, 0.5)
    beta  = config.BETA_STYLE.get(style_tag, 0.5)
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO clothing_items
          (name, category, layer_type, garment_type, style_tag,
           clo, thickness, density, alpha_type, beta_style,
           min_temp, max_temp, allowed_occasions)
        VALUES ({ph(13)})
    """, (
        name, category, layer_type, garment_type, style_tag,
        clo, thickness, density, alpha, beta,
        min_temp, max_temp, json.dumps(allowed_occasions)
    ))
    conn.commit()
    return cur.lastrowid
