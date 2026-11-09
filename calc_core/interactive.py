"""
Interactive terminal workflow for the Calorie Calculator CLI:
- Profile Setup Wizard
- Daily Food Logger with dynamic search
- Water Intake Tracker
- Daily Progress & Macro Visualizer
- Weight Tracking
- Interactive Navigation Menu
"""

import sys
from datetime import date, datetime
from typing import Optional

from calc_core.calculator import (
    ACTIVITY_MULTIPLIERS,
    GOALS,
    MACRO_SPLITS,
    compute_full_profile,
    lbs_to_kg,
    feet_inches_to_cm,
    cm_to_feet_inches,
    kg_to_lbs,
)
from calc_core.database import Database
from calc_core.terminal_ui import (
    Colors,
    bold,
    cyan,
    green,
    yellow,
    red,
    magenta,
    dim,
    header,
    print_alert,
    progress_bar,
    macro_bar,
    render_table,
    colorize,
)


def prompt_choice(prompt_text: str, options: list, default: int = 1) -> int:
    """Prompt user to select from a list of options."""
    print(f"\n{bold(prompt_text)}")
    for i, opt in enumerate(options, 1):
        def_tag = dim(" (default)") if i == default else ""
        print(f"  [{cyan(str(i))}] {opt}{def_tag}")

    while True:
        try:
            choice = input(colorize(f"Select option [1-{len(options)}] (default: {default}): ", Colors.CYAN)).strip()
            if not choice:
                return default
            val = int(choice)
            if 1 <= val <= len(options):
                return val
            print(red(f"Please enter a number between 1 and {len(options)}."))
        except ValueError:
            print(red("Invalid input. Please enter a valid number."))
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return default


def prompt_float(prompt_text: str, default: Optional[float] = None, min_val: float = 0.0) -> float:
    """Prompt user for a positive float number."""
    suffix = f" (default: {default})" if default is not None else ""
    while True:
        try:
            raw = input(colorize(f"{prompt_text}{suffix}: ", Colors.CYAN)).strip()
            if not raw and default is not None:
                return default
            val = float(raw)
            if val < min_val:
                print(red(f"Value must be at least {min_val}."))
                continue
            return val
        except ValueError:
            print(red("Invalid number, please enter a valid decimal number."))
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)


def prompt_int(prompt_text: str, default: Optional[int] = None, min_val: int = 1, max_val: int = 150) -> int:
    """Prompt user for an integer number within bounds."""
    suffix = f" (default: {default})" if default is not None else ""
    while True:
        try:
            raw = input(colorize(f"{prompt_text}{suffix}: ", Colors.CYAN)).strip()
            if not raw and default is not None:
                return default
            val = int(raw)
            if val < min_val or val > max_val:
                print(red(f"Please enter an integer between {min_val} and {max_val}."))
                continue
            return val
        except ValueError:
            print(red("Invalid integer."))
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)


def run_profile_wizard(db: Database) -> bool:
    """Interactive wizard to configure user profile and compute TDEE/macros."""
    header("User Profile & Metabolism Setup", "Calculate your BMR, TDEE, and custom calorie targets")

    existing = db.get_profile()
    if existing:
        print(f"Current profile detected for {bold(existing.get('name', 'User'))} (Target: {existing['target_calories']} kcal/day).")
        overwrite = input(colorize("Do you want to reconfigure your profile? (y/n, default: y): ", Colors.YELLOW)).strip().lower()
        if overwrite in ("n", "no"):
            return False

    name = input(colorize("Enter your name (default: User): ", Colors.CYAN)).strip() or "User"

    # Unit system choice
    unit_choice = prompt_choice("Choose measurement system:", ["Metric (kg, cm)", "Imperial (lbs, ft/in)"], default=1)
    is_metric = (unit_choice == 1)

    # Gender
    gender_choice = prompt_choice("Gender:", ["Male", "Female"], default=1)
    gender = "Male" if gender_choice == 1 else "Female"

    # Age
    age = prompt_int("Age (years)", default=25, min_val=10, max_val=110)

    # Weight
    if is_metric:
        weight_kg = prompt_float("Current Weight in kg", default=75.0, min_val=25.0)
    else:
        weight_lbs = prompt_float("Current Weight in lbs", default=165.0, min_val=50.0)
        weight_kg = lbs_to_kg(weight_lbs)

    # Height
    if is_metric:
        height_cm = prompt_float("Height in cm", default=175.0, min_val=90.0)
    else:
        print(dim("Enter height in feet and inches:"))
        feet = prompt_float("Feet", default=5.0, min_val=3.0)
        inches = prompt_float("Inches", default=9.0, min_val=0.0)
        height_cm = feet_inches_to_cm(feet, inches)

    # Body fat (optional)
    bf_input = input(colorize("Body Fat percentage if known (or press Enter to skip): ", Colors.CYAN)).strip()
    body_fat_pct = float(bf_input) if bf_input else None

    # Activity level
    activity_keys = list(ACTIVITY_MULTIPLIERS.keys())
    activity_labels = [ACTIVITY_MULTIPLIERS[k][1] for k in activity_keys]
    act_idx = prompt_choice("Select your typical weekly activity level:", activity_labels, default=2)
    selected_activity = activity_keys[act_idx - 1]

    # Goal
    goal_keys = list(GOALS.keys())
    goal_labels = [GOALS[k][1] for k in goal_keys]
    goal_idx = prompt_choice("Select your primary fitness & weight goal:", goal_labels, default=4)
    selected_goal = goal_keys[goal_idx - 1]

    # Macro split
    split_keys = list(MACRO_SPLITS.keys())
    split_labels = [MACRO_SPLITS[k][3] for k in split_keys]
    split_idx = prompt_choice("Select preferred macronutrient distribution:", split_labels, default=2)
    selected_split = split_keys[split_idx - 1]

    # Run calculation
    formula = "katch" if body_fat_pct is not None else "mifflin"
    calc = compute_full_profile(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=selected_activity,
        goal=selected_goal,
        formula=formula,
        body_fat_pct=body_fat_pct,
        macro_split=selected_split
    )

    # Display results
    print()
    header("Metabolic Analysis Results")
    summary_data = [
        ["BMI", f"{calc.bmi} ({calc.bmi_category})"],
        ["Healthy Weight Range", f"{calc.healthy_weight_range[0]} kg - {calc.healthy_weight_range[1]} kg"],
        ["BMR (Mifflin-St Jeor)", f"{calc.bmr_mifflin:g} kcal/day"],
        ["BMR (Harris-Benedict)", f"{calc.bmr_harris_benedict:g} kcal/day"],
    ]
    if calc.bmr_katch_mcardle:
        summary_data.append(["BMR (Katch-McArdle)", f"{calc.bmr_katch_mcardle:g} kcal/day"])
    summary_data.extend([
        ["TDEE (Maintenance)", f"{bold(str(int(calc.tdee)))} kcal/day"],
        ["Goal Target Calories", f"{bold(colorize(str(calc.target_calories), Colors.GREEN))} kcal/day"],
    ])

    render_table(["Metric", "Calculated Value"], summary_data)

    print()
    print(bold("Recommended Daily Macronutrient Targets:"))
    print(f"  • {colorize('Protein:', Colors.CYAN)} {bold(str(calc.macros.protein_g))}g ({calc.macros.protein_pct}%)")
    print(f"  • {colorize('Carbohydrates:', Colors.YELLOW)} {bold(str(calc.macros.carbs_g))}g ({calc.macros.carbs_pct}%)")
    print(f"  • {colorize('Fat:', Colors.MAGENTA)} {bold(str(calc.macros.fat_g))}g ({calc.macros.fat_pct}%)")

    if calc.warning:
        print()
        print_alert(calc.warning, "warning")

    # Save to DB
    db.save_profile(
        name=name,
        gender=gender,
        age=age,
        height_cm=round(height_cm, 1),
        weight_kg=round(weight_kg, 1),
        body_fat_pct=round(body_fat_pct, 1) if body_fat_pct else None,
        activity_level=selected_activity,
        goal=selected_goal,
        target_calories=calc.target_calories,
        macro_split=selected_split
    )
    # Log initial weight
    db.log_weight(weight_kg=weight_kg, notes="Profile setup baseline")

    print()
    print_alert(f"Profile saved! Target set to {calc.target_calories} kcal/day.", "success")
    return True


def show_daily_summary(db: Database, log_date: Optional[str] = None):
    """Render comprehensive daily intake, progress bar, meal breakdown, and macros."""
    if not log_date:
        log_date = date.today().isoformat()

    summary = db.get_daily_summary(log_date)
    logs = db.get_food_logs_for_date(log_date)

    header(f"Daily Calorie Summary: {log_date}")

    total_c = summary["total_calories"]
    target_c = summary["target_calories"]
    remaining = summary["remaining_calories"]

    print(bold("Calorie Intake vs Daily Goal:"))
    print(f"  {progress_bar(total_c, target_c, length=30, unit='kcal')}")

    if remaining >= 0:
        print(f"  {green('✓ Remaining:')} {bold(str(remaining))} kcal")
    else:
        print(f"  {red('! Over Budget by:')} {bold(str(abs(remaining)))} kcal")

    print()
    print(bold("Macronutrient Distribution:"))
    print(f"  {macro_bar(summary['total_carbs_g'], summary['total_protein_g'], summary['total_fat_g'])}")

    print()
    print(f"  {colorize('💧 Water Intake:', Colors.CYAN)} {bold(str(summary['water_ml']))} ml ({round(summary['water_ml']/1000, 2)} L)")
    print()

    # Table of logged items
    print(bold("Logged Meals & Foods:"))
    if not logs:
        print(dim("  No food items logged for this date yet. Select 'Log Food' to add an item!"))
    else:
        rows = []
        for item in logs:
            meal_badge = item['meal_type'].capitalize()
            qty_str = f"{item['amount']:g} {item['unit']}"
            rows.append([
                str(item['id']),
                meal_badge,
                item['food_name'],
                qty_str,
                f"{item['calories']:g}",
                f"{item['protein']:g}g",
                f"{item['carbs']:g}g",
                f"{item['fat']:g}g",
            ])
        render_table(
            headers=["ID", "Meal", "Food Item", "Amount", "Calories", "Protein", "Carbs", "Fat"],
            rows=rows,
            alignments=["R", "L", "L", "R", "R", "R", "R", "R"]
        )


def log_food_flow(db: Database):
    """Interactive food logging flow with search and quantity scaling."""
    header("Log Food Entry")

    # Meal type
    meal_types = ["Breakfast", "Lunch", "Dinner", "Snack"]
    meal_idx = prompt_choice("Select meal type:", meal_types, default=2)
    meal = meal_types[meal_idx - 1].lower()

    # Food search
    query = input(colorize("Search food item (e.g., 'chicken', 'rice', 'egg', or enter to list common): ", Colors.CYAN)).strip()
    results = db.search_foods(query)

    if not results:
        print_alert(f"No foods found matching '{query}'. Would you like to enter it manually?", "warning")
        create_custom = input(colorize("Enter manually? (y/n, default: y): ", Colors.YELLOW)).strip().lower()
        if create_custom not in ("n", "no"):
            add_custom_food_flow(db)
        return

    # Display matches
    display_list = []
    for f in results[:10]:
        display_list.append(f"{f['name']} ({f['calories_per_100g']} kcal/100g) - [{f['category']}]")
    display_list.append("[+] Enter a custom unlisted food")

    pick = prompt_choice("Select food:", display_list, default=1)

    if pick == len(display_list):
        # Custom entry
        add_custom_food_flow(db)
        return

    selected = results[pick - 1]

    # Amount & unit selection
    default_unit = selected.get("default_unit", "g")
    serving_size_g = selected.get("serving_size_g", 100.0)

    print(f"\nSelected: {bold(selected['name'])}")
    print(f"Default unit: {bold(default_unit)} (standard serving: {serving_size_g}g)")

    amount = prompt_float(f"Enter quantity in {default_unit}", default=1.0 if default_unit != "g" else 100.0)

    # Compute nutritional scaling
    if default_unit == "g":
        factor = amount / 100.0
    else:
        total_grams = amount * serving_size_g
        factor = total_grams / 100.0

    calories = selected["calories_per_100g"] * factor
    protein = selected["protein_per_100g"] * factor
    carbs = selected["carbs_per_100g"] * factor
    fat = selected["fat_per_100g"] * factor

    print(f"\nCalculated Nutrients for {amount:g} {default_unit}:")
    print(f"  Calories: {bold(f'{calories:.1f}')} kcal | Protein: {bold(f'{protein:.1f}')}g | Carbs: {bold(f'{carbs:.1f}')}g | Fat: {bold(f'{fat:.1f}')}g")

    confirm = input(colorize("Save log entry? (y/n, default: y): ", Colors.GREEN)).strip().lower()
    if confirm in ("n", "no"):
        print_alert("Log cancelled.", "info")
        return

    db.log_food(
        food_name=selected["name"],
        amount=amount,
        unit=default_unit,
        calories=calories,
        protein=protein,
        carbs=carbs,
        fat=fat,
        meal_type=meal
    )
    print_alert(f"Logged {amount:g} {default_unit} of {selected['name']} to {meal.capitalize()}!", "success")


def add_custom_food_flow(db: Database):
    """Interactive wizard to add custom food item to local database."""
    header("Add Custom Food to Database")
    name = input(colorize("Food name: ", Colors.CYAN)).strip()
    if not name:
        print_alert("Food name cannot be empty.", "error")
        return

    category = input(colorize("Category (Protein, Grains, Fruits, Vegetables, Dairy, Fats, Snacks, etc.): ", Colors.CYAN)).strip() or "General"
    cal_100 = prompt_float("Calories per 100g", min_val=0.0)
    prot_100 = prompt_float("Protein per 100g (in grams)", min_val=0.0)
    carb_100 = prompt_float("Carbohydrates per 100g (in grams)", min_val=0.0)
    fat_100 = prompt_float("Fat per 100g (in grams)", min_val=0.0)
    unit = input(colorize("Default serving unit (e.g. g, slice, cup, piece) [default: g]: ", Colors.CYAN)).strip() or "g"
    serving_g = prompt_float(f"Grams per 1 {unit}", default=100.0, min_val=0.1)

    db.add_custom_food(
        name=name,
        category=category,
        calories_per_100g=cal_100,
        protein_per_100g=prot_100,
        carbs_per_100g=carb_100,
        fat_per_100g=fat_100,
        default_unit=unit,
        serving_size_g=serving_g
    )
    print_alert(f"Successfully added '{name}' to your food database!", "success")


def log_water_flow(db: Database):
    """Interactive flow to log water intake."""
    header("Log Water Intake")
    presets = [
        "Small Glass (200 ml)",
        "Standard Glass / Mug (250 ml)",
        "Water Bottle (500 ml)",
        "Large Bottle (750 ml)",
        "1 Liter Bottle (1000 ml)",
        "Custom amount"
    ]
    choice = prompt_choice("Select water portion:", presets, default=3)
    amounts = [200.0, 250.0, 500.0, 750.0, 1000.0]

    if choice <= 5:
        amount_ml = amounts[choice - 1]
    else:
        amount_ml = prompt_float("Enter water volume in ml", min_val=10.0)

    db.log_water(amount_ml)
    today_total = db.get_water_for_date()
    print_alert(f"Added {amount_ml:g} ml! Today's water total: {today_total:g} ml ({round(today_total/1000, 2)} L)", "success")


def log_weight_flow(db: Database):
    """Log current weight and view recent trend."""
    header("Weight Tracking")
    profile = db.get_profile()
    def_weight = profile["weight_kg"] if profile else 70.0

    print(f"Last recorded weight: {bold(str(def_weight))} kg")
    new_weight = prompt_float("Enter new weight in kg", default=def_weight, min_val=20.0)
    note = input(colorize("Optional note (e.g. morning, post-workout): ", Colors.CYAN)).strip()

    db.log_weight(weight_kg=new_weight, notes=note)
    print_alert(f"Logged weight: {new_weight:g} kg.", "success")

    # Show weight history
    history = db.get_weight_history(limit=7)
    if history:
        rows = []
        for r in history:
            rows.append([r["log_date"], f"{r['weight_kg']:g} kg", r["notes"] or "—"])
        print()
        print(bold("Recent Weight Entries:"))
        render_table(["Date", "Weight", "Note"], rows, alignments=["L", "R", "L"])


def delete_food_entry_flow(db: Database):
    """Interactive prompt to delete a food entry by ID."""
    logs = db.get_food_logs_for_date()
    if not logs:
        print_alert("No food entries logged today to delete.", "info")
        return

    show_daily_summary(db)
    log_id = prompt_int("Enter the ID of the entry to delete", min_val=1, max_val=9999999)
    if db.delete_food_log(log_id):
        print_alert(f"Deleted food entry #{log_id}.", "success")
    else:
        print_alert(f"No entry found with ID #{log_id}.", "error")


def view_history_flow(db: Database):
    """Display past 7-14 days summary."""
    header("Intake History (Recent Days)")
    history = db.get_recent_history(days=14)
    if not history:
        print_alert("No history recorded yet.", "info")
        return

    profile = db.get_profile()
    target = profile["target_calories"] if profile else 2000

    rows = []
    for day in history:
        cals = day["total_calories"]
        delta = target - cals
        delta_str = f"+{abs(delta):g} remaining" if delta >= 0 else f"{delta:g} over"
        rows.append([
            day["log_date"],
            f"{cals:g} kcal",
            f"{target:g} kcal",
            delta_str,
            f"{day['total_protein']:g}g",
            f"{day['total_carbs']:g}g",
            f"{day['total_fat']:g}g",
            str(day["entries"]),
        ])

    render_table(
        ["Date", "Calories", "Target", "Balance", "Protein", "Carbs", "Fat", "Items"],
        rows,
        alignments=["L", "R", "R", "R", "R", "R", "R", "R"]
    )


def interactive_main(db: Database):
    """Main interactive loop."""
    while True:
        profile = db.get_profile()
        target_str = f"Target: {profile['target_calories']} kcal/day" if profile else "Profile: Not configured"

        header("Calorie Calculator CLI", f"Your personal nutrition & metabolism tracker • {target_str}")

        menu_items = [
            "View Today's Summary & Progress",
            "Log Food / Meal",
            "Delete a Food Log Entry",
            "Log Water Intake",
            "Log Weight & View Trend",
            "View Intake History",
            "Search Food Catalog / Add Custom Food",
            "Setup / Update User Profile (BMR & TDEE Wizard)",
            "Exit"
        ]

        choice = prompt_choice("Main Menu:", menu_items, default=1)

        try:
            if choice == 1:
                show_daily_summary(db)
            elif choice == 2:
                log_food_flow(db)
            elif choice == 3:
                delete_food_entry_flow(db)
            elif choice == 4:
                log_water_flow(db)
            elif choice == 5:
                log_weight_flow(db)
            elif choice == 6:
                view_history_flow(db)
            elif choice == 7:
                sub_pick = prompt_choice("Catalog options:", ["Search food database", "Add custom food item"], default=1)
                if sub_pick == 1:
                    q = input(colorize("Search query: ", Colors.CYAN)).strip()
                    res = db.search_foods(q)
                    rows = [[r["name"], r["category"], f"{r['calories_per_100g']:g}", f"{r['protein_per_100g']:g}g", f"{r['carbs_per_100g']:g}g", f"{r['fat_per_100g']:g}g", f"1 {r['default_unit']} ({r['serving_size_g']:g}g)"] for r in res]
                    render_table(["Food Name", "Category", "Kcal/100g", "Protein", "Carbs", "Fat", "Serving Unit"], rows)
                else:
                    add_custom_food_flow(db)
            elif choice == 8:
                run_profile_wizard(db)
            elif choice == 9:
                print(green("\nThank you for using Calorie Calculator CLI. Stay healthy and energized!\n"))
                break

            input(dim("\nPress Enter to return to main menu..."))
        except (KeyboardInterrupt, EOFError):
            print("\nReturning to menu...\n")
