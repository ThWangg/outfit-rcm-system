import os

#database
DB_MODE = "mysql"
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "outfit_rs.db")

MYSQL_HOST     = "localhost"
MYSQL_PORT     = 3306
MYSQL_USER     = "root"
MYSQL_PASSWORD = ""
MYSQL_DATABASE = "weather_rs"

#ML Model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml_model.pkl")

#Weather API
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL   = "https://api.open-meteo.com/v1/forecast"

#Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG      = True

#constants
IDEAL_BMI  = 21.7
K_COEFF    = 0.42
NEUTRAL_T  = 24.1
CLO_DIVISOR = 8.0
CLO_BASE   = 0.5

#occasion -> Formality score (F_target)
OCCASION_FORMALITY: dict[str, float] = {
    "Home":        0.10,
    "Beach":       0.30,
    "Gym":         0.25,
    "Casual":      0.40,
    "Party":       0.55,
    "Date":        0.65,
    "Office":      0.80,
    "Formal":      0.95,
}

# alpha_type lookup (structural design cut weight by garment type)
ALPHA_TYPE: dict[str, float] = {
    "T-Shirt":       0.30,
    "Tank Top":      0.20,
    "Polo Shirt":    0.50,
    "Button Shirt":  0.65,
    "Sweater":       0.55,
    "Hoodie":        0.45,
    "Jacket":        0.80,
    "Blazer":        0.95,
    "Coat":          0.90,
    "Vest":          0.60,
    "Jeans":         0.55,
    "Trousers":      0.80,
    "Chinos":        0.75,
    "Shorts":        0.30,
    "Skirt":         0.50,
    "Dress Pants":   0.90,
    "Leggings":      0.25,
    "Joggers":       0.30,
    "Cargo Pants":   0.45,
}

# beta_style lookup (style intent weight by style tag)
BETA_STYLE: dict[str, float] = {
    "casual":   0.40,
    "sporty":   0.30,
    "smart":    0.70,
    "formal":   0.95,
    "beach":    0.25,
    "home":     0.15,
    "outdoor":  0.35,
}
