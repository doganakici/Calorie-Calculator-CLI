"""
Unit tests for the metabolic and nutritional calculator engine.
"""

import unittest
from calc_core.calculator import (
    bmr_mifflin_st_jeor,
    bmr_harris_benedict,
    bmr_katch_mcardle,
    calculate_bmi,
    calculate_healthy_weight_range,
    calculate_tdee,
    calculate_target_calories,
    calculate_macros,
    compute_full_profile,
    lbs_to_kg,
    kg_to_lbs,
    feet_inches_to_cm,
    cm_to_feet_inches,
)


class TestMetabolicCalculator(unittest.TestCase):

    def test_unit_conversions(self):
        # 150 lbs to kg
        kg = lbs_to_kg(150.0)
        self.assertAlmostEqual(kg, 68.0388555, places=2)
        # Back to lbs
        self.assertAlmostEqual(kg_to_lbs(kg), 150.0, places=2)

        # 5 feet 10 inches to cm
        cm = feet_inches_to_cm(5, 10)
        self.assertAlmostEqual(cm, 177.8, places=1)
        feet, inches = cm_to_feet_inches(cm)
        self.assertEqual(feet, 5)
        self.assertAlmostEqual(inches, 10.0, places=1)

    def test_bmr_mifflin_st_jeor(self):
        # Male: 80kg, 180cm, 30 years -> 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
        male_bmr = bmr_mifflin_st_jeor(weight_kg=80.0, height_cm=180.0, age=30, gender="male")
        self.assertEqual(male_bmr, 1780.0)

        # Female: 60kg, 165cm, 28 years -> 10*60 + 6.25*165 - 5*28 - 161 = 600 + 1031.25 - 140 - 161 = 1330.25
        female_bmr = bmr_mifflin_st_jeor(weight_kg=60.0, height_cm=165.0, age=28, gender="female")
        self.assertEqual(female_bmr, 1330.25)

    def test_bmr_harris_benedict(self):
        # Male formula
        male_bmr = bmr_harris_benedict(weight_kg=80.0, height_cm=180.0, age=30, gender="male")
        # 88.362 + (13.397*80) + (4.799*180) - (5.677*30) = 88.362 + 1071.76 + 863.82 - 170.31 = 1853.632
        self.assertAlmostEqual(male_bmr, 1853.632, places=2)

    def test_bmr_katch_mcardle(self):
        # 80kg, 15% body fat -> LBM = 80 * 0.85 = 68kg
        # BMR = 370 + (21.6 * 68) = 370 + 1468.8 = 1838.8
        bmr = bmr_katch_mcardle(weight_kg=80.0, body_fat_pct=15.0)
        self.assertAlmostEqual(bmr, 1838.8, places=1)

    def test_calculate_bmi_and_classification(self):
        # 70 kg, 175 cm -> 70 / (1.75^2) = 22.86 -> Normal
        bmi, cat = calculate_bmi(70.0, 175.0)
        self.assertEqual(bmi, 22.9)
        self.assertEqual(cat, "Normal weight")

        # 95 kg, 175 cm -> 95 / 3.0625 = 31.02 -> Obese Class I
        bmi, cat = calculate_bmi(95.0, 175.0)
        self.assertEqual(bmi, 31.0)
        self.assertEqual(cat, "Obese Class I (Moderate)")

        # Underweight
        bmi, cat = calculate_bmi(45.0, 170.0)
        self.assertEqual(cat, "Underweight")

    def test_healthy_weight_range(self):
        min_w, max_w = calculate_healthy_weight_range(180.0)
        # 18.5 * (1.8^2) = 59.94, 24.9 * (1.8^2) = 80.676
        self.assertAlmostEqual(min_w, 59.9, places=1)
        self.assertAlmostEqual(max_w, 80.7, places=1)

    def test_calculate_tdee(self):
        bmr = 1800.0
        # Sedentary (1.2) -> 2160.0
        self.assertAlmostEqual(calculate_tdee(bmr, "sedentary"), 2160.0)
        # Moderately active (1.55) -> 2790.0
        self.assertAlmostEqual(calculate_tdee(bmr, "moderate"), 2790.0)

    def test_calculate_target_calories_and_warning(self):
        tdee = 2500.0
        # Mild deficit (-250)
        target, warning = calculate_target_calories(tdee, "lose_mild", "male")
        self.assertEqual(target, 2250)
        self.assertIsNone(warning)

        # Dangerously low intake check
        low_tdee = 1400.0
        target, warning = calculate_target_calories(low_tdee, "lose_fast", "male")
        # 1400 - 1000 = 400, but min male floor is 1500
        self.assertIsNotNone(warning)
        self.assertIn("Caution", warning)

    def test_macro_targets(self):
        # 2000 kcal, High Protein (40% Carbs, 35% Protein, 25% Fat)
        # Carbs: 800 kcal / 4 = 200g
        # Protein: 700 kcal / 4 = 175g
        # Fat: 500 kcal / 9 = 55.55g
        macros = calculate_macros(2000, "high_protein")
        self.assertEqual(macros.carbs_g, 200.0)
        self.assertEqual(macros.protein_g, 175.0)
        self.assertEqual(macros.fat_g, 55.6)
        self.assertEqual(macros.protein_pct, 35.0)
        self.assertEqual(macros.carbs_pct, 40.0)
        self.assertEqual(macros.fat_pct, 25.0)

    def test_compute_full_profile(self):
        res = compute_full_profile(
            weight_kg=75.0,
            height_cm=175.0,
            age=25,
            gender="male",
            activity_level="moderate",
            goal="lose_moderate",
            macro_split="high_protein"
        )
        self.assertGreater(res.tdee, res.target_calories)
        self.assertEqual(res.target_calories, int(round(res.tdee - 500)))
        self.assertEqual(res.bmi, 24.5)
        self.assertEqual(res.bmi_category, "Normal weight")


if __name__ == "__main__":
    unittest.main()
