"""
Nutritional and metabolic calculations:
- BMR (Mifflin-St Jeor, Harris-Benedict, Katch-McArdle)
- TDEE (Total Daily Energy Expenditure)
- BMI (Body Mass Index) & healthy weight ranges
- Calorie target based on fitness goals
- Macronutrient distributions (Balanced, High Protein, Low Carb, Keto, Custom)
- Metric <-> Imperial conversion utilities
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Activity level multipliers
ACTIVITY_MULTIPLIERS: Dict[str, Tuple[float, str]] = {
    "sedentary": (1.2, "Sedentary (desk job, little to no exercise)"),
    "light": (1.375, "Lightly Active (light exercise 1-3 days/week)"),
    "moderate": (1.55, "Moderately Active (moderate exercise 3-5 days/week)"),
    "very": (1.725, "Very Active (hard exercise 6-7 days/week)"),
    "extra": (1.9, "Extra Active (physical job & hard exercise / athlete)"),
}

# Goal calorie adjustments (kcal delta per day)
GOALS: Dict[str, Tuple[int, str]] = {
    "lose_fast": (-1000, "Rapid Weight Loss (~1 kg / 2.2 lbs per week)"),
    "lose_moderate": (-500, "Standard Weight Loss (~0.5 kg / 1.1 lbs per week)"),
    "lose_mild": (-250, "Mild Weight Loss (~0.25 kg / 0.55 lbs per week)"),
    "maintain": (0, "Maintain Current Weight"),
    "gain_mild": (250, "Lean Bulk / Mild Gain (~0.25 kg / 0.55 lbs per week)"),
    "gain_moderate": (500, "Standard Weight Gain (~0.5 kg / 1.1 lbs per week)"),
}

# Macronutrient ratio splits (Carbs %, Protein %, Fat %)
# Note: 1g Protein = 4 kcal, 1g Carb = 4 kcal, 1g Fat = 9 kcal
MACRO_SPLITS: Dict[str, Tuple[float, float, float, str]] = {
    "balanced": (0.50, 0.20, 0.30, "Balanced (50% Carbs, 20% Protein, 30% Fat)"),
    "high_protein": (0.40, 0.35, 0.25, "High Protein / Fitness (40% Carbs, 35% Protein, 25% Fat)"),
    "low_carb": (0.25, 0.40, 0.35, "Low Carb (25% Carbs, 40% Protein, 35% Fat)"),
    "keto": (0.05, 0.25, 0.70, "Ketogenic (5% Carbs, 25% Protein, 70% Fat)"),
}


@dataclass
class MacroTarget:
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    protein_pct: float
    carbs_pct: float
    fat_pct: float


@dataclass
class CalculationResult:
    bmr_mifflin: float
    bmr_harris_benedict: float
    bmr_katch_mcardle: Optional[float]
    selected_bmr: float
    tdee: float
    target_calories: int
    bmi: float
    bmi_category: str
    healthy_weight_range: Tuple[float, float]
    macros: MacroTarget
    warning: Optional[str] = None


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms."""
    return lbs * 0.45359237


def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds."""
    return kg / 0.45359237


def feet_inches_to_cm(feet: float, inches: float = 0.0) -> float:
    """Convert feet and inches to centimeters."""
    total_inches = (feet * 12.0) + inches
    return total_inches * 2.54


def cm_to_feet_inches(cm: float) -> Tuple[int, float]:
    """Convert centimeters to (feet, inches)."""
    total_inches = cm / 2.54
    feet = int(total_inches // 12)
    inches = total_inches % 12
    return feet, round(inches, 1)


def calculate_bmi(weight_kg: float, height_cm: float) -> Tuple[float, str]:
    """Calculate BMI and return value with WHO classification."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        return 0.0, "Invalid height"
    bmi = weight_kg / (height_m * height_m)
    bmi_rounded = round(bmi, 1)

    if bmi_rounded < 18.5:
        category = "Underweight"
    elif bmi_rounded < 25.0:
        category = "Normal weight"
    elif bmi_rounded < 30.0:
        category = "Overweight"
    elif bmi_rounded < 35.0:
        category = "Obese Class I (Moderate)"
    elif bmi_rounded < 40.0:
        category = "Obese Class II (Severe)"
    else:
        category = "Obese Class III (Very severe)"

    return bmi_rounded, category


def calculate_healthy_weight_range(height_cm: float) -> Tuple[float, float]:
    """Calculate healthy weight range (BMI 18.5 to 24.9) in kg."""
    height_m = height_cm / 100.0
    min_weight = round(18.5 * (height_m ** 2), 1)
    max_weight = round(24.9 * (height_m ** 2), 1)
    return min_weight, max_weight


def bmr_mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Mifflin-St Jeor formula:
    Men: 10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5
    Women: 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 161
    """
    base = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age)
    if gender.strip().lower() in ("m", "male"):
        return base + 5.0
    return base - 161.0


def bmr_harris_benedict(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Revised Harris-Benedict formula (Roza and Shizgal, 1984):
    Men: 88.362 + (13.397 * kg) + (4.799 * cm) - (5.677 * age)
    Women: 447.593 + (9.247 * kg) + (3.098 * cm) - (4.330 * age)
    """
    if gender.strip().lower() in ("m", "male"):
        return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)


def bmr_katch_mcardle(weight_kg: float, body_fat_pct: float) -> float:
    """
    Katch-McArdle formula:
    BMR = 370 + (21.6 * Lean Body Mass in kg)
    """
    lbm = weight_kg * (1.0 - (body_fat_pct / 100.0))
    return 370.0 + (21.6 * lbm)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Calculate Total Daily Energy Expenditure (TDEE) based on activity level."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level.lower(), (1.2, ""))[0]
    return bmr * multiplier


def calculate_target_calories(tdee: float, goal: str, gender: str) -> Tuple[int, Optional[str]]:
    """
    Calculate daily calorie target based on goal with safety floor check:
    Minimum safe threshold: ~1500 kcal/day for men, ~1200 kcal/day for women.
    """
    delta = GOALS.get(goal.lower(), (0, ""))[0]
    target = int(round(tdee + delta))

    min_safe = 1500 if gender.strip().lower() in ("m", "male") else 1200
    warning = None

    if target < min_safe:
        warning = (
            f"Caution: The calculated target ({target} kcal) is below the recommended "
            f"minimum safe intake of {min_safe} kcal/day for your gender. Consider a slower weight loss rate."
        )

    return max(target, 800), warning


def calculate_macros(
    target_calories: int,
    split_name: str = "high_protein",
    custom_ratios: Optional[Tuple[float, float, float]] = None
) -> MacroTarget:
    """
    Calculate macronutrients (grams and percentages) for a calorie goal.
    1g Carb = 4 kcal, 1g Protein = 4 kcal, 1g Fat = 9 kcal.
    """
    if custom_ratios:
        c_pct, p_pct, f_pct = custom_ratios
    else:
        preset = MACRO_SPLITS.get(split_name.lower(), MACRO_SPLITS["high_protein"])
        c_pct, p_pct, f_pct = preset[0], preset[1], preset[2]

    total_pct = c_pct + p_pct + f_pct
    if total_pct > 0 and abs(total_pct - 1.0) > 0.001:
        # Normalize
        c_pct /= total_pct
        p_pct /= total_pct
        f_pct /= total_pct

    carbs_cal = target_calories * c_pct
    protein_cal = target_calories * p_pct
    fat_cal = target_calories * f_pct

    carbs_g = round(carbs_cal / 4.0, 1)
    protein_g = round(protein_cal / 4.0, 1)
    fat_g = round(fat_cal / 9.0, 1)

    return MacroTarget(
        calories=target_calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        protein_pct=round(p_pct * 100, 1),
        carbs_pct=round(c_pct * 100, 1),
        fat_pct=round(f_pct * 100, 1)
    )


def compute_full_profile(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str = "sedentary",
    goal: str = "maintain",
    formula: str = "mifflin",
    body_fat_pct: Optional[float] = None,
    macro_split: str = "high_protein"
) -> CalculationResult:
    """Generate comprehensive metabolic assessment and recommendations."""
    bmr_m = bmr_mifflin_st_jeor(weight_kg, height_cm, age, gender)
    bmr_hb = bmr_harris_benedict(weight_kg, height_cm, age, gender)
    bmr_km = bmr_katch_mcardle(weight_kg, body_fat_pct) if body_fat_pct is not None else None

    # Determine selected BMR
    if formula.lower() == "katch" and bmr_km is not None:
        selected_bmr = bmr_km
    elif formula.lower() in ("harris", "harris_benedict"):
        selected_bmr = bmr_hb
    else:
        selected_bmr = bmr_m

    tdee = calculate_tdee(selected_bmr, activity_level)
    target_cals, warning = calculate_target_calories(tdee, goal, gender)
    bmi, bmi_cat = calculate_bmi(weight_kg, height_cm)
    healthy_range = calculate_healthy_weight_range(height_cm)
    macros = calculate_macros(target_cals, macro_split)

    return CalculationResult(
        bmr_mifflin=round(bmr_m, 1),
        bmr_harris_benedict=round(bmr_hb, 1),
        bmr_katch_mcardle=round(bmr_km, 1) if bmr_km is not None else None,
        selected_bmr=round(selected_bmr, 1),
        tdee=round(tdee, 1),
        target_calories=target_cals,
        bmi=bmi,
        bmi_category=bmi_cat,
        healthy_weight_range=healthy_range,
        macros=macros,
        warning=warning
    )
