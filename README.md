# 🥗 Calorie Calculator CLI

A feature-packed, zero-dependency command-line application written in Python for calculating metabolic energy expenditure (BMR, TDEE), setting personalized fitness targets, tracking daily calories, macronutrients, water intake, and body weight.

---

## ✨ Features

- **Scientific Metabolic Engine**:
  - **BMR (Basal Metabolic Rate)**: Mifflin-St Jeor, Revised Harris-Benedict, and Katch-McArdle (with body fat %).
  - **TDEE (Total Daily Energy Expenditure)**: 5 activity multipliers (Sedentary, Lightly Active, Moderately Active, Very Active, Extra Active).
  - **Goals & Adjustments**: Maintain, mild/standard/rapid weight loss, lean/standard bulk.
  - **Safety Threshold Checks**: Automatic alerts if target calories fall below healthy minimums (1500 kcal for men, 1200 kcal for women).
  - **Macronutrient Distributions**: Balanced, High Protein, Low Carb, and Ketogenic presets.
  - **Metric & Imperial Support**: Kilograms/centimeters or pounds/feet/inches.
- **Interactive Terminal UI**:
  - Guided step-by-step profile setup wizard.
  - Colored ANSI progress bars tracking calories consumed vs. daily target.
  - Macronutrient breakdown bars (Carbs / Protein / Fat).
  - Food catalog search and custom item creation.
- **Daily Tracking & History**:
  - Log meals by category (Breakfast, Lunch, Dinner, Snack).
  - Track hydration (water in ml/L) with quick presets.
  - Log body weight history and monitor trends.
  - Export logs directly to **CSV** or **JSON**.
- **Zero External Dependencies**:
  - Built purely with the Python standard library (`sqlite3`, `argparse`, `dataclasses`, `datetime`).

---

## 🚀 Quick Start & Single-Command Setup

### Run with a Single Command from Anywhere (`calorie` or `calorie-calc`)

On Fedora (and other Linux distros), `~/.local/bin` is already in your `$PATH`. Run the one-step setup script:

```bash
./install.sh
```

Now you can start the application from **any terminal directory** simply by running:
```bash
calorie
```
*(or `calorie-calc`)*

---

### Manual / Direct Execution

You can also run it directly using Python:

```bash
# Launch interactive mode directly:
python3 calorie_calc.py

Or make it executable:

```bash
chmod +x calorie_calc.py
./calorie_calc.py
```

---

## 📖 CLI Command Reference

In addition to interactive mode, `calorie_calc.py` provides rich subcommands for quick logging and scripting.

### 1. Calculate BMR, TDEE & Macros (`calc`)

Perform on-the-fly calculations without configuring a profile, or save the result with `--save`:

```bash
# Metric calculation
python3 calorie_calc.py calc \
  --weight 78 \
  --height 180 \
  --age 28 \
  --gender male \
  --activity moderate \
  --goal lose_moderate \
  --macro-split high_protein \
  --save

# Imperial calculation (lbs and feet/inches)
python3 calorie_calc.py calc \
  --weight 170 --lbs \
  --feet 5 --inches 10 \
  --age 30 \
  --gender female \
  --activity light \
  --goal maintain
```

### 2. View and Manage User Profile (`profile`)

```bash
# View active profile and daily target
python3 calorie_calc.py profile show

# Launch interactive setup wizard
python3 calorie_calc.py profile wizard

# Manually update daily target calories
python3 calorie_calc.py profile set-target 2150
```

### 3. Log Meals, Water, and Weight (`log`)

```bash
# Log a food item from the pre-seeded database
python3 calorie_calc.py log food --name "Chicken Breast" --amount 200 --unit g --meal lunch
python3 calorie_calc.py log food --name "White Rice (Cooked)" --amount 1 --unit cup --meal lunch

# Quick log any custom food/snack directly
python3 calorie_calc.py log quick --name "Protein Bar" --cals 220 --protein 20 --carbs 22 --fat 6 --meal snack

# Log water intake (in ml)
python3 calorie_calc.py log water --amount 500

# Log body weight
python3 calorie_calc.py log weight 77.8 --note "Morning weigh-in"

# Delete a log entry by ID
python3 calorie_calc.py log delete 1
```

### 4. Daily Summary & Progress (`summary`)

View daily calorie consumption, remaining allowance, progress bar, and macro breakdown:

```bash
# View today's summary
python3 calorie_calc.py summary

# View summary for a specific date
python3 calorie_calc.py summary --date 2026-11-10
```

### 5. Historical Trends (`history`)

```bash
# View intake over the last 7 days (default)
python3 calorie_calc.py history

# View last 14 days
python3 calorie_calc.py history --days 14
```

### 6. Food Database Search & Addition (`food`)

```bash
# Search food catalog
python3 calorie_calc.py food search egg
python3 calorie_calc.py food search salmon

# Add a custom food item to your local catalog
python3 calorie_calc.py food add \
  --name "Almond Butter" \
  --category "Fats" \
  --cals 614 \
  --protein 21 \
  --carbs 19 \
  --fat 56 \
  --unit tbsp \
  --serving 16
```

### 7. Export Records (`export`)

Export all logged entries to CSV or JSON for spreadsheets, backups, or external analysis:

```bash
# Export to CSV
python3 calorie_calc.py export --format csv --output nutrition_logs.csv

# Export to JSON
python3 calorie_calc.py export --format json --output nutrition_logs.json
```

---

## 🧮 Mathematical Formulas

### 1. BMR Formulas
- **Mifflin-St Jeor (Standard)**:
  $$\text{Men: } 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age} + 5$$
  $$\text{Women: } 10 \times \text{weight (kg)} + 6.25 \times \text{height (cm)} - 5 \times \text{age} - 161$$
- **Revised Harris-Benedict**:
  $$\text{Men: } 88.362 + (13.397 \times W) + (4.799 \times H) - (5.677 \times A)$$
  $$\text{Women: } 447.593 + (9.247 \times W) + (3.098 \times H) - (4.330 \times A)$$
- **Katch-McArdle (Body Fat %)**:
  $$\text{BMR} = 370 + 21.6 \times \text{Lean Body Mass (kg)}$$

### 2. TDEE Multipliers
- **Sedentary**: $\text{BMR} \times 1.2$
- **Lightly Active**: $\text{BMR} \times 1.375$
- **Moderately Active**: $\text{BMR} \times 1.55$
- **Very Active**: $\text{BMR} \times 1.725$
- **Extra Active**: $\text{BMR} \times 1.9$

---

## 🧪 Running Tests

The test suite covers unit conversions, metabolic formulas, BMI classifications, safety checks, and SQLite database operations:

```bash
python3 -m unittest discover tests
```

---

## 📁 Project Architecture

```
Calorie Calculator/
├── calorie_calc.py        # CLI entry point & argument parser
├── calc_core/
│   ├── __init__.py
│   ├── calculator.py      # BMR, TDEE, BMI, and macro algorithms
│   ├── database.py        # SQLite persistence layer & queries
│   ├── interactive.py     # Interactive terminal menus & wizards
│   ├── seed_data.py       # Nutritional catalog of common foods
│   └── terminal_ui.py     # ANSI styling, tables, & progress bars
├── tests/
│   ├── test_calculator.py # Math & formula unit tests
│   └── test_database.py   # Database CRUD & aggregation tests
├── .gitignore
└── README.md
```
