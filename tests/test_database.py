"""
Unit tests for the SQLite Database layer.
"""

import os
import tempfile
import unittest
from calc_core.database import Database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_calories.db")
        self.db = Database(self.db_path)

    def tearDown(self):
        self.db.conn.close()
        self.temp_dir.cleanup()

    def test_seeding_foods(self):
        foods = self.db.search_foods()
        self.assertGreater(len(foods), 15)
        # Check specific items
        chicken = self.db.get_food_by_name("Chicken Breast")
        self.assertIsNotNone(chicken)
        self.assertEqual(chicken["calories_per_100g"], 165.0)

    def test_profile_lifecycle(self):
        # Empty profile
        self.assertIsNone(self.db.get_profile())

        # Save profile
        self.db.save_profile(
            name="Alex",
            gender="male",
            age=28,
            height_cm=180.0,
            weight_kg=82.0,
            activity_level="moderate",
            goal="lose_mild",
            target_calories=2300,
            macro_split="high_protein"
        )
        p = self.db.get_profile()
        self.assertIsNotNone(p)
        self.assertEqual(p["name"], "Alex")
        self.assertEqual(p["target_calories"], 2300)

        # Update target calories
        self.db.update_target_calories(2150)
        p2 = self.db.get_profile()
        self.assertEqual(p2["target_calories"], 2150)

    def test_custom_food_lifecycle(self):
        self.db.add_custom_food(
            name="My Protein Bar",
            category="Snack",
            calories_per_100g=380.0,
            protein_per_100g=30.0,
            carbs_per_100g=35.0,
            fat_per_100g=10.0,
            default_unit="bar",
            serving_size_g=60.0
        )
        food = self.db.get_food_by_name("My Protein Bar")
        self.assertIsNotNone(food)
        self.assertEqual(food["is_custom"], 1)

        # Delete custom food
        deleted = self.db.delete_custom_food(food["id"])
        self.assertTrue(deleted)
        self.assertIsNone(self.db.get_food_by_name("My Protein Bar"))

    def test_food_logging_and_summary(self):
        self.db.save_profile(
            gender="female",
            age=30,
            height_cm=165.0,
            weight_kg=60.0,
            activity_level="sedentary",
            goal="maintain",
            target_calories=1800
        )

        # Log breakfast
        log1_id = self.db.log_food(
            food_name="Egg (Large, whole)",
            amount=2.0,
            unit="egg",
            calories=143.0,
            protein=12.6,
            carbs=0.7,
            fat=9.5,
            meal_type="breakfast",
            log_date="2026-11-10"
        )
        self.assertGreater(log1_id, 0)

        # Log lunch
        log2_id = self.db.log_food(
            food_name="Chicken Breast",
            amount=200.0,
            unit="g",
            calories=330.0,
            protein=62.0,
            carbs=0.0,
            fat=7.2,
            meal_type="lunch",
            log_date="2026-11-10"
        )
        self.assertGreater(log2_id, 0)

        # Check logs
        entries = self.db.get_food_logs_for_date("2026-11-10")
        self.assertEqual(len(entries), 2)

        # Daily summary
        summary = self.db.get_daily_summary("2026-11-10")
        self.assertEqual(summary["total_calories"], 473.0)
        self.assertEqual(summary["remaining_calories"], 1800 - 473.0)
        self.assertEqual(summary["total_protein_g"], 74.6)
        self.assertEqual(summary["entry_count"], 2)

        # Delete one log entry
        self.assertTrue(self.db.delete_food_log(log1_id))
        updated_summary = self.db.get_daily_summary("2026-11-10")
        self.assertEqual(updated_summary["entry_count"], 1)
        self.assertEqual(updated_summary["total_calories"], 330.0)

    def test_water_and_weight_logging(self):
        # Water
        self.db.log_water(250.0, "2026-11-10")
        self.db.log_water(500.0, "2026-11-10")
        self.assertEqual(self.db.get_water_for_date("2026-11-10"), 750.0)

        # Weight
        self.db.log_weight(72.5, "2026-11-10", "Morning fasted")
        history = self.db.get_weight_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["weight_kg"], 72.5)
        self.assertEqual(history[0]["notes"], "Morning fasted")


if __name__ == "__main__":
    unittest.main()
