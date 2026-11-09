#!/usr/bin/env python3
"""
Calorie Calculator CLI - Complete Nutrition & Metabolism Management System.

Usage:
  python3 calorie_calc.py                         # Launch interactive UI
  python3 calorie_calc.py calc --help             # Calculate BMR/TDEE on the fly
  python3 calorie_calc.py log --help              # Log meals, water, or weight
  python3 calorie_calc.py summary [--date YYYY-MM-DD]
  python3 calorie_calc.py food search [query]
  python3 calorie_calc.py profile show
  python3 calorie_calc.py export [--format csv|json]
"""

import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional

# Ensure package directory is always in sys.path even when called via symlink or external PATH
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from calc_core.calculator import (
    ACTIVITY_MULTIPLIERS,
    GOALS,
    MACRO_SPLITS,
    compute_full_profile,
    feet_inches_to_cm,
    lbs_to_kg,
)
from calc_core.database import Database, get_default_db_path
from calc_core.interactive import (
    interactive_main,
    run_profile_wizard,
    show_daily_summary,
)
from calc_core.terminal_ui import (
    Colors,
    bold,
    cyan,
    green,
    yellow,
    red,
    dim,
    header,
    print_alert,
    render_table,
    colorize,
)


def get_db(args) -> Database:
    db_path = getattr(args, "db", None) or os.environ.get("CALORIE_DB_PATH", None)
    return Database(db_path)


def cmd_calc(args):
    """Handle standalone BMR/TDEE calculation from CLI arguments."""
    db = get_db(args)

    # Resolve weight
    if args.weight is None:
        profile = db.get_profile()
        if profile:
            weight_kg = profile["weight_kg"]
        else:
            print_alert("Weight is required (e.g. --weight 75 or --weight 165 --lbs)", "error")
            return 1
    else:
        weight_kg = lbs_to_kg(args.weight) if args.lbs else args.weight

    # Resolve height
    if args.feet is not None:
        height_cm = feet_inches_to_cm(args.feet, args.inches or 0.0)
    elif args.height is not None:
        height_cm = args.height * 2.54 if args.inches_only else args.height
    else:
        profile = db.get_profile()
        if profile:
            height_cm = profile["height_cm"]
        else:
            print_alert("Height is required (e.g. --height 175 or --feet 5 --inches 10)", "error")
            return 1

    # Resolve gender & age
    profile = db.get_profile()
    gender = args.gender or (profile["gender"] if profile else "male")
    age = args.age or (profile["age"] if profile else 25)
    activity = args.activity or (profile["activity_level"] if profile else "sedentary")
    goal = args.goal or (profile["goal"] if profile else "maintain")
    split = args.macro_split or (profile["macro_split"] if profile else "high_protein")
    body_fat = args.body_fat if args.body_fat is not None else (profile.get("body_fat_pct") if profile else None)

    calc = compute_full_profile(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity,
        goal=goal,
        formula="katch" if body_fat is not None else "mifflin",
        body_fat_pct=body_fat,
        macro_split=split,
    )

    header("Calorie & Macronutrient Assessment")

    rows = [
        ["Gender & Age", f"{gender.capitalize()}, {age} yrs"],
        ["Height & Weight", f"{height_cm:.1f} cm, {weight_kg:.1f} kg"],
        ["BMI & Classification", f"{calc.bmi} ({calc.bmi_category})"],
        ["Healthy Weight Range", f"{calc.healthy_weight_range[0]} kg - {calc.healthy_weight_range[1]} kg"],
        ["BMR (Mifflin-St Jeor)", f"{calc.bmr_mifflin:g} kcal/day"],
        ["BMR (Harris-Benedict)", f"{calc.bmr_harris_benedict:g} kcal/day"],
    ]
    if calc.bmr_katch_mcardle:
        rows.append(["BMR (Katch-McArdle)", f"{calc.bmr_katch_mcardle:g} kcal/day"])

    rows.extend([
        ["Activity Level", ACTIVITY_MULTIPLIERS.get(activity.lower(), (1.2, activity))[1]],
        ["TDEE (Maintenance)", f"{bold(str(int(calc.tdee)))} kcal/day"],
        ["Goal", GOALS.get(goal.lower(), (0, goal))[1]],
        ["Target Daily Calorie Intake", f"{bold(green(str(calc.target_calories)))} kcal/day"],
    ])

    render_table(["Metric", "Details"], rows)

    print()
    print(bold(f"Target Macronutrient Breakdown ({split.replace('_', ' ').title()}):"))
    print(f"  • {colorize('Protein:', Colors.CYAN)} {bold(str(calc.macros.protein_g))}g ({calc.macros.protein_pct}%)")
    print(f"  • {colorize('Carbohydrates:', Colors.YELLOW)} {bold(str(calc.macros.carbs_g))}g ({calc.macros.carbs_pct}%)")
    print(f"  • {colorize('Fat:', Colors.MAGENTA)} {bold(str(calc.macros.fat_g))}g ({calc.macros.fat_pct}%)")

    if calc.warning:
        print()
        print_alert(calc.warning, "warning")

    if getattr(args, "save", False):
        db.save_profile(
            name="User",
            gender=gender,
            age=age,
            height_cm=round(height_cm, 1),
            weight_kg=round(weight_kg, 1),
            body_fat_pct=round(body_fat, 1) if body_fat else None,
            activity_level=activity,
            goal=goal,
            target_calories=calc.target_calories,
            macro_split=split,
        )
        db.log_weight(weight_kg=weight_kg, notes="Profile update")
        print()
        print_alert(f"Profile saved! Target updated to {calc.target_calories} kcal/day.", "success")

    return 0


def cmd_profile(args):
    db = get_db(args)
    action = args.profile_action or "show"

    if action == "wizard":
        run_profile_wizard(db)
        return 0
    elif action == "set-target":
        if args.target is None:
            print_alert("Please specify a target, e.g.: calorie_calc.py profile set-target 2200", "error")
            return 1
        db.update_target_calories(args.target)
        print_alert(f"Target calories updated to {args.target} kcal/day.", "success")
        return 0

    # Show profile
    profile = db.get_profile()
    if not profile:
        print_alert("No profile configured yet. Run 'calorie_calc.py profile wizard' to set one up!", "info")
        return 0

    header(f"Profile: {profile.get('name', 'User')}")
    rows = [
        ["Gender", profile["gender"].capitalize()],
        ["Age", f"{profile['age']} years"],
        ["Height", f"{profile['height_cm']} cm"],
        ["Weight", f"{profile['weight_kg']} kg"],
        ["Body Fat", f"{profile['body_fat_pct']}%" if profile.get("body_fat_pct") else "Not set"],
        ["Activity Level", ACTIVITY_MULTIPLIERS.get(profile["activity_level"], (0, profile["activity_level"]))[1]],
        ["Goal", GOALS.get(profile["goal"], (0, profile["goal"]))[1]],
        ["Target Calories", f"{bold(green(str(profile['target_calories'])))} kcal/day"],
        ["Macro Split", profile.get("macro_split", "high_protein").replace("_", " ").title()],
        ["Last Updated", profile["updated_at"][:19]],
    ]
    render_table(["Profile Field", "Setting"], rows)
    return 0


def cmd_log(args):
    db = get_db(args)
    sub = args.log_subcommand

    if sub == "food":
        food_item = db.get_food_by_name(args.name)
        if not food_item:
            print_alert(f"Food '{args.name}' not found in database. Use 'log quick' or add to catalog first.", "error")
            return 1

        amount = args.amount
        unit = args.unit or food_item["default_unit"]
        serving_g = food_item.get("serving_size_g", 100.0)

        if unit == "g":
            factor = amount / 100.0
        else:
            factor = (amount * serving_g) / 100.0

        calories = food_item["calories_per_100g"] * factor
        protein = food_item["protein_per_100g"] * factor
        carbs = food_item["carbs_per_100g"] * factor
        fat = food_item["fat_per_100g"] * factor

        db.log_food(
            food_name=food_item["name"],
            amount=amount,
            unit=unit,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            meal_type=args.meal or "lunch",
            log_date=args.date
        )
        print_alert(
            f"Logged {amount:g} {unit} of '{food_item['name']}' ({calories:.1f} kcal, {protein:.1f}g P, {carbs:.1f}g C, {fat:.1f}g F).",
            "success"
        )
        return 0

    elif sub == "quick":
        if not args.name or args.cals is None:
            print_alert("Please provide --name and --cals for quick food logging.", "error")
            return 1
        db.log_food(
            food_name=args.name,
            amount=args.amount or 1.0,
            unit=args.unit or "serving",
            calories=args.cals,
            protein=args.protein or 0.0,
            carbs=args.carbs or 0.0,
            fat=args.fat or 0.0,
            meal_type=args.meal or "snack",
            log_date=args.date
        )
        print_alert(f"Logged quick entry: '{args.name}' ({args.cals:g} kcal).", "success")
        return 0

    elif sub == "water":
        if args.amount is None:
            print_alert("Please provide water amount in ml, e.g. --amount 500", "error")
            return 1
        db.log_water(args.amount, log_date=args.date)
        total = db.get_water_for_date(args.date)
        print_alert(f"Logged {args.amount:g} ml water. Today's total: {total:g} ml ({round(total/1000, 2)} L).", "success")
        return 0

    elif sub == "weight":
        if args.weight is None:
            print_alert("Please provide weight value, e.g.: calorie_calc.py log weight 74.2", "error")
            return 1
        weight_kg = lbs_to_kg(args.weight) if args.lbs else args.weight
        db.log_weight(weight_kg, log_date=args.date, notes=args.note or "")
        print_alert(f"Logged weight: {weight_kg:g} kg.", "success")
        return 0

    elif sub == "delete":
        if args.id is None:
            print_alert("Specify log ID to delete: calorie_calc.py log delete <id>", "error")
            return 1
        if db.delete_food_log(args.id):
            print_alert(f"Deleted food log #{args.id}.", "success")
        else:
            print_alert(f"Log entry #{args.id} not found.", "error")
            return 1
        return 0

    else:
        print_alert("Available log subcommands: food, quick, water, weight, delete. Run with --help for details.", "warning")
        return 1


def cmd_summary(args):
    db = get_db(args)
    show_daily_summary(db, log_date=args.date)
    return 0


def cmd_history(args):
    db = get_db(args)
    days = args.days or 7
    history = db.get_recent_history(days=days)
    if not history:
        print_alert(f"No log history in the past {days} days.", "info")
        return 0

    profile = db.get_profile()
    target = profile["target_calories"] if profile else 2000

    header(f"Calorie History (Last {len(history)} Active Days)")
    rows = []
    for day in history:
        cals = day["total_calories"]
        delta = target - cals
        delta_str = f"+{abs(delta):g} left" if delta >= 0 else f"-{abs(delta):g} over"
        rows.append([
            day["log_date"],
            f"{cals:g}",
            f"{target:g}",
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
    return 0


def cmd_food(args):
    db = get_db(args)
    action = args.food_action or "search"

    if action == "search":
        q = args.query or ""
        items = db.search_foods(q)
        if not items:
            print_alert(f"No food items found matching '{q}'.", "info")
            return 0
        rows = [
            [
                str(f["id"]),
                f["name"],
                f["category"],
                f"{f['calories_per_100g']:g}",
                f"{f['protein_per_100g']:g}g",
                f"{f['carbs_per_100g']:g}g",
                f"{f['fat_per_100g']:g}g",
                f"1 {f['default_unit']} ({f['serving_size_g']:g}g)",
            ]
            for f in items
        ]
        header(f"Food Catalog Search: '{q or 'All'}'")
        render_table(
            ["ID", "Name", "Category", "Kcal/100g", "Protein", "Carbs", "Fat", "Serving Unit"],
            rows,
            alignments=["R", "L", "L", "R", "R", "R", "R", "L"]
        )
        return 0

    elif action == "add":
        if not args.name or args.cals is None:
            print_alert("Must provide --name and --cals (calories per 100g).", "error")
            return 1
        db.add_custom_food(
            name=args.name,
            category=args.category or "Custom",
            calories_per_100g=args.cals,
            protein_per_100g=args.protein or 0.0,
            carbs_per_100g=args.carbs or 0.0,
            fat_per_100g=args.fat or 0.0,
            default_unit=args.unit or "g",
            serving_size_g=args.serving or 100.0,
        )
        print_alert(f"Added custom food '{args.name}' to database.", "success")
        return 0

    return 0


def cmd_export(args):
    db = get_db(args)
    logs = db.conn.execute("SELECT * FROM food_logs ORDER BY log_date ASC, id ASC").fetchall()
    if not logs:
        print_alert("No food logs available to export.", "info")
        return 0

    fmt = (args.format or "csv").lower()
    out_file = args.output or f"calorie_logs_{date.today().isoformat()}.{fmt}"

    if fmt == "json":
        data = [dict(r) for r in logs]
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    else:
        keys = logs[0].keys()
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            for r in logs:
                writer.writerow([r[k] for k in keys])

    print_alert(f"Exported {len(logs)} log records to '{out_file}'.", "success")
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=str, help="Custom SQLite database file path")

    parser = argparse.ArgumentParser(
        prog="calorie_calc",
        description="Calorie Calculator & Nutrition Tracker CLI App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common]
    )

    subparsers = parser.add_subparsers(dest="command")

    # Interactive
    subparsers.add_parser("interactive", parents=[common], help="Start full interactive terminal UI")

    # Calc
    p_calc = subparsers.add_parser("calc", parents=[common], help="Calculate BMR, TDEE, and macros")
    p_calc.add_argument("--weight", type=float, help="Body weight")
    p_calc.add_argument("--lbs", action="store_true", help="Weight is in pounds (lbs)")
    p_calc.add_argument("--height", type=float, help="Height in cm (or inches with --inches-only)")
    p_calc.add_argument("--feet", type=float, help="Height feet component")
    p_calc.add_argument("--inches", type=float, help="Height inches component")
    p_calc.add_argument("--inches-only", action="store_true", help="Height is in total inches")
    p_calc.add_argument("--age", type=int, help="Age in years")
    p_calc.add_argument("--gender", choices=["male", "female", "m", "f"], help="Gender")
    p_calc.add_argument(
        "--activity",
        choices=["sedentary", "light", "moderate", "very", "extra"],
        help="Physical activity level"
    )
    p_calc.add_argument(
        "--goal",
        choices=["maintain", "lose_mild", "lose_moderate", "lose_fast", "gain_mild", "gain_moderate"],
        help="Target fitness goal"
    )
    p_calc.add_argument(
        "--macro-split",
        choices=["balanced", "high_protein", "low_carb", "keto"],
        help="Macronutrient distribution"
    )
    p_calc.add_argument("--body-fat", type=float, help="Body fat percentage for Katch-McArdle formula")
    p_calc.add_argument("--save", action="store_true", help="Save these calculated values to your user profile")
    p_calc.set_defaults(func=cmd_calc)

    # Profile
    p_prof = subparsers.add_parser("profile", parents=[common], help="Manage user profile and daily targets")
    p_prof_subs = p_prof.add_subparsers(dest="profile_action")
    p_prof_show = p_prof_subs.add_parser("show", parents=[common], help="View current profile")
    p_prof_show.set_defaults(func=cmd_profile)
    p_prof_wiz = p_prof_subs.add_parser("wizard", parents=[common], help="Interactive profile setup wizard")
    p_prof_wiz.set_defaults(func=cmd_profile)
    p_prof_set = p_prof_subs.add_parser("set-target", parents=[common], help="Directly set daily target calories")
    p_prof_set.add_argument("target", type=int, help="Target calories (e.g. 2100)")
    p_prof_set.set_defaults(func=cmd_profile)
    p_prof.set_defaults(func=cmd_profile, profile_action="show")

    # Log
    p_log = subparsers.add_parser("log", parents=[common], help="Log food, water, or weight")
    p_log_subs = p_log.add_subparsers(dest="log_subcommand")

    # Log food from db
    p_lf = p_log_subs.add_parser("food", parents=[common], help="Log food item from database")
    p_lf.add_argument("--name", required=True, help="Food name (e.g. 'Chicken Breast')")
    p_lf.add_argument("--amount", type=float, required=True, help="Portion amount")
    p_lf.add_argument("--unit", type=str, help="Unit of measurement (e.g. g, cup, slice)")
    p_lf.add_argument("--meal", choices=["breakfast", "lunch", "dinner", "snack"], default="lunch")
    p_lf.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")
    p_lf.set_defaults(func=cmd_log)

    # Log quick
    p_lq = p_log_subs.add_parser("quick", parents=[common], help="Log custom meal/food directly with nutritional values")
    p_lq.add_argument("--name", required=True, help="Meal/item description")
    p_lq.add_argument("--cals", type=float, required=True, help="Total calories")
    p_lq.add_argument("--protein", type=float, default=0.0, help="Protein in grams")
    p_lq.add_argument("--carbs", type=float, default=0.0, help="Carbohydrates in grams")
    p_lq.add_argument("--fat", type=float, default=0.0, help="Fat in grams")
    p_lq.add_argument("--amount", type=float, default=1.0, help="Portion amount")
    p_lq.add_argument("--unit", type=str, default="serving", help="Portion unit")
    p_lq.add_argument("--meal", choices=["breakfast", "lunch", "dinner", "snack"], default="snack")
    p_lq.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")
    p_lq.set_defaults(func=cmd_log)

    # Log water
    p_lw = p_log_subs.add_parser("water", parents=[common], help="Log water intake")
    p_lw.add_argument("--amount", type=float, required=True, help="Amount of water in ml (e.g. 500)")
    p_lw.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")
    p_lw.set_defaults(func=cmd_log)

    # Log weight
    p_lwt = p_log_subs.add_parser("weight", parents=[common], help="Log current body weight")
    p_lwt.add_argument("weight", type=float, help="Body weight")
    p_lwt.add_argument("--lbs", action="store_true", help="Weight is in pounds")
    p_lwt.add_argument("--note", type=str, default="", help="Optional note")
    p_lwt.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")
    p_lwt.set_defaults(func=cmd_log)

    # Delete log
    p_ld = p_log_subs.add_parser("delete", parents=[common], help="Delete a food log entry by ID")
    p_ld.add_argument("id", type=int, help="Log Entry ID")
    p_ld.set_defaults(func=cmd_log)

    # Summary
    p_sum = subparsers.add_parser("summary", parents=[common], help="Show daily nutrition summary and progress")
    p_sum.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")
    p_sum.set_defaults(func=cmd_summary)

    # History
    p_hist = subparsers.add_parser("history", parents=[common], help="Show past intake history")
    p_hist.add_argument("--days", type=int, default=7, help="Number of past days (default: 7)")
    p_hist.set_defaults(func=cmd_history)

    # Food
    p_food = subparsers.add_parser("food", parents=[common], help="Search or add items to food catalog")
    p_food_subs = p_food.add_subparsers(dest="food_action")

    p_fs = p_food_subs.add_parser("search", parents=[common], help="Search foods in catalog")
    p_fs.add_argument("query", nargs="?", default="", help="Food keyword to search")
    p_fs.set_defaults(func=cmd_food)

    p_fa = p_food_subs.add_parser("add", parents=[common], help="Add custom food to database")
    p_fa.add_argument("--name", required=True, help="Food name")
    p_fa.add_argument("--category", default="Custom", help="Category")
    p_fa.add_argument("--cals", type=float, required=True, help="Calories per 100g")
    p_fa.add_argument("--protein", type=float, default=0.0, help="Protein per 100g")
    p_fa.add_argument("--carbs", type=float, default=0.0, help="Carbs per 100g")
    p_fa.add_argument("--fat", type=float, default=0.0, help="Fat per 100g")
    p_fa.add_argument("--unit", default="g", help="Serving unit")
    p_fa.add_argument("--serving", type=float, default=100.0, help="Grams per serving unit")
    p_fa.set_defaults(func=cmd_food)

    # Export
    p_exp = subparsers.add_parser("export", parents=[common], help="Export logs to CSV or JSON")
    p_exp.add_argument("--format", choices=["csv", "json"], default="csv", help="Export file format")
    p_exp.add_argument("--output", type=str, help="Output destination file")
    p_exp.set_defaults(func=cmd_export)

    return parser


def main():
    parser = build_parser()

    # If no arguments provided or 'interactive', launch interactive UI
    if len(sys.argv) == 1:
        db = Database()
        interactive_main(db)
        return 0

    args = parser.parse_args()

    if args.command == "interactive":
        db = get_db(args)
        interactive_main(db)
        return 0

    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
