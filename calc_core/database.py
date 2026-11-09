"""
SQLite Database Layer for Calorie Calculator CLI:
- User profile & goals
- Food catalog (pre-seeded + custom items)
- Daily food consumption logs
- Weight tracking history
- Water intake logs
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from calc_core.seed_data import FOOD_DATABASE

def get_default_db_path() -> Path:
    """Resolve database path with fallback if home directory is read-only."""
    import os
    if "CALORIE_DB_PATH" in os.environ:
        return Path(os.environ["CALORIE_DB_PATH"])

    home_target = Path.home() / ".calorie_calc" / "calories.db"
    try:
        home_target.parent.mkdir(parents=True, exist_ok=True)
        test_file = home_target.parent / ".perm_check"
        test_file.touch()
        test_file.unlink()
        return home_target
    except (OSError, PermissionError):
        pass

    # Fallback to local directory
    local_dir = Path.cwd() / "data"
    local_dir.mkdir(parents=True, exist_ok=True)
    return local_dir / "calories.db"


class Database:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = get_default_db_path()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._seed_default_foods()

    def _init_tables(self):
        with self.conn:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT DEFAULT 'User',
                    gender TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    height_cm REAL NOT NULL,
                    weight_kg REAL NOT NULL,
                    body_fat_pct REAL,
                    activity_level TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    target_calories INTEGER NOT NULL,
                    macro_split TEXT NOT NULL DEFAULT 'high_protein',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS foods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    calories_per_100g REAL NOT NULL,
                    protein_per_100g REAL NOT NULL,
                    carbs_per_100g REAL NOT NULL,
                    fat_per_100g REAL NOT NULL,
                    default_unit TEXT DEFAULT 'g',
                    serving_size_g REAL DEFAULT 100.0,
                    is_custom INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS food_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    food_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    unit TEXT NOT NULL,
                    calories REAL NOT NULL,
                    protein REAL NOT NULL,
                    carbs REAL NOT NULL,
                    fat REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS weight_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS water_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TEXT NOT NULL,
                    amount_ml REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_food_logs_date ON food_logs(log_date);
                CREATE INDEX IF NOT EXISTS idx_weight_logs_date ON weight_logs(log_date);
                CREATE INDEX IF NOT EXISTS idx_water_logs_date ON water_logs(log_date);
            """)

    def _seed_default_foods(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM foods")
        count = cursor.fetchone()[0]
        if count == 0:
            with self.conn:
                for item in FOOD_DATABASE:
                    self.conn.execute("""
                        INSERT OR IGNORE INTO foods (
                            name, category, calories_per_100g, protein_per_100g,
                            carbs_per_100g, fat_per_100g, default_unit, serving_size_g, is_custom
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        item["name"], item["category"], item["calories"],
                        item["protein"], item["carbs"], item["fat"],
                        item["default_unit"], item["serving_size_g"]
                    ))

    # --- Profile Operations ---
    def get_profile(self) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE id = 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_profile(
        self,
        gender: str,
        age: int,
        height_cm: float,
        weight_kg: float,
        activity_level: str,
        goal: str,
        target_calories: int,
        macro_split: str = "high_protein",
        body_fat_pct: Optional[float] = None,
        name: str = "User"
    ):
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO user_profile (
                    id, name, gender, age, height_cm, weight_kg,
                    body_fat_pct, activity_level, goal, target_calories,
                    macro_split, updated_at
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    gender = excluded.gender,
                    age = excluded.age,
                    height_cm = excluded.height_cm,
                    weight_kg = excluded.weight_kg,
                    body_fat_pct = excluded.body_fat_pct,
                    activity_level = excluded.activity_level,
                    goal = excluded.goal,
                    target_calories = excluded.target_calories,
                    macro_split = excluded.macro_split,
                    updated_at = excluded.updated_at
            """, (
                name, gender, age, height_cm, weight_kg,
                body_fat_pct, activity_level, goal, target_calories,
                macro_split, now
            ))

    def update_target_calories(self, target_calories: int):
        with self.conn:
            self.conn.execute(
                "UPDATE user_profile SET target_calories = ?, updated_at = ? WHERE id = 1",
                (target_calories, datetime.now().isoformat())
            )

    # --- Food Catalog Operations ---
    def search_foods(self, query: str = "") -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        if not query.strip():
            cursor.execute("SELECT * FROM foods ORDER BY category, name LIMIT 50")
        else:
            q = f"%{query.strip()}%"
            cursor.execute("""
                SELECT * FROM foods
                WHERE name LIKE ? OR category LIKE ?
                ORDER BY
                    CASE WHEN name LIKE ? THEN 0 ELSE 1 END,
                    name
                LIMIT 50
            """, (q, q, f"{query.strip()}%"))
        return [dict(r) for r in cursor.fetchall()]

    def get_food_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM foods WHERE LOWER(name) = LOWER(?)", (name.strip(),))
        row = cursor.fetchone()
        if not row:
            # Fuzzy like
            cursor.execute("SELECT * FROM foods WHERE LOWER(name) LIKE LOWER(?) ORDER BY LENGTH(name) LIMIT 1", (f"%{name.strip()}%",))
            row = cursor.fetchone()
        return dict(row) if row else None

    def add_custom_food(
        self,
        name: str,
        category: str,
        calories_per_100g: float,
        protein_per_100g: float,
        carbs_per_100g: float,
        fat_per_100g: float,
        default_unit: str = "g",
        serving_size_g: float = 100.0
    ):
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO foods (
                    name, category, calories_per_100g, protein_per_100g,
                    carbs_per_100g, fat_per_100g, default_unit, serving_size_g, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                name.strip(), category.strip(), calories_per_100g,
                protein_per_100g, carbs_per_100g, fat_per_100g,
                default_unit.strip(), serving_size_g
            ))

    def delete_custom_food(self, food_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM foods WHERE id = ? AND is_custom = 1", (food_id,))
            return cursor.rowcount > 0

    # --- Food Logging Operations ---
    def log_food(
        self,
        food_name: str,
        amount: float,
        unit: str,
        calories: float,
        protein: float,
        carbs: float,
        fat: float,
        meal_type: str = "lunch",
        log_date: Optional[str] = None
    ) -> int:
        if not log_date:
            log_date = date.today().isoformat()
        now = datetime.now().isoformat()
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO food_logs (
                    log_date, meal_type, food_name, amount, unit,
                    calories, protein, carbs, fat, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_date, meal_type.lower(), food_name, amount, unit,
                round(calories, 1), round(protein, 1), round(carbs, 1), round(fat, 1), now
            ))
            return cursor.lastrowid

    def delete_food_log(self, log_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
            return cursor.rowcount > 0

    def get_food_logs_for_date(self, log_date: Optional[str] = None) -> List[Dict[str, Any]]:
        if not log_date:
            log_date = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM food_logs
            WHERE log_date = ?
            ORDER BY
                CASE meal_type
                    WHEN 'breakfast' THEN 1
                    WHEN 'lunch' THEN 2
                    WHEN 'dinner' THEN 3
                    WHEN 'snack' THEN 4
                    ELSE 5
                END, id ASC
        """, (log_date,))
        return [dict(r) for r in cursor.fetchall()]

    def get_daily_summary(self, log_date: Optional[str] = None) -> Dict[str, Any]:
        if not log_date:
            log_date = date.today().isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE(SUM(calories), 0) as total_cals,
                COALESCE(SUM(protein), 0) as total_protein,
                COALESCE(SUM(carbs), 0) as total_carbs,
                COALESCE(SUM(fat), 0) as total_fat,
                COUNT(*) as entry_count
            FROM food_logs
            WHERE log_date = ?
        """, (log_date,))
        summary_row = cursor.fetchone()

        cursor.execute("SELECT COALESCE(SUM(amount_ml), 0) FROM water_logs WHERE log_date = ?", (log_date,))
        water_ml = cursor.fetchone()[0]

        profile = self.get_profile()
        target_cals = profile["target_calories"] if profile else 2000

        total_cals = round(summary_row["total_cals"], 1)
        remaining_cals = round(target_cals - total_cals, 1)

        return {
            "date": log_date,
            "total_calories": total_cals,
            "target_calories": target_cals,
            "remaining_calories": remaining_cals,
            "total_protein_g": round(summary_row["total_protein"], 1),
            "total_carbs_g": round(summary_row["total_carbs"], 1),
            "total_fat_g": round(summary_row["total_fat"], 1),
            "water_ml": round(water_ml, 1),
            "entry_count": summary_row["entry_count"]
        }

    def get_recent_history(self, days: int = 7) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                log_date,
                COALESCE(SUM(calories), 0) as total_calories,
                COALESCE(SUM(protein), 0) as total_protein,
                COALESCE(SUM(carbs), 0) as total_carbs,
                COALESCE(SUM(fat), 0) as total_fat,
                COUNT(id) as entries
            FROM food_logs
            GROUP BY log_date
            ORDER BY log_date DESC
            LIMIT ?
        """, (days,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

    # --- Weight Logging ---
    def log_weight(self, weight_kg: float, log_date: Optional[str] = None, notes: str = ""):
        if not log_date:
            log_date = date.today().isoformat()
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO weight_logs (log_date, weight_kg, notes, created_at)
                VALUES (?, ?, ?, ?)
            """, (log_date, round(weight_kg, 2), notes, now))

            # Also update profile current weight
            self.conn.execute("""
                UPDATE user_profile SET weight_kg = ?, updated_at = ? WHERE id = 1
            """, (round(weight_kg, 2), now))

    def get_weight_history(self, limit: int = 14) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM weight_logs
            ORDER BY log_date DESC, id DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cursor.fetchall()]

    # --- Water Intake Logging ---
    def log_water(self, amount_ml: float, log_date: Optional[str] = None):
        if not log_date:
            log_date = date.today().isoformat()
        now = datetime.now().isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO water_logs (log_date, amount_ml, created_at)
                VALUES (?, ?, ?)
            """, (log_date, round(amount_ml, 1), now))

    def get_water_for_date(self, log_date: Optional[str] = None) -> float:
        if not log_date:
            log_date = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(amount_ml), 0) FROM water_logs WHERE log_date = ?", (log_date,))
        return float(cursor.fetchone()[0])
