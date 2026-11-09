"""
Terminal UI Utilities:
- ANSI colors and text styles
- Clean Unicode table rendering
- Progress bars and macro ratio visualizers
- Card banners and alerts
"""

import sys
import shutil
from typing import List, Sequence, Optional, Any


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Standard colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Backgrounds
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"


# Disable colors if stdout is not a TTY or NO_COLOR is set
def _supports_color() -> bool:
    import os
    if "NO_COLOR" in os.environ:
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOR = _supports_color()


def colorize(text: str, *styles: str) -> str:
    """Apply ANSI style sequences to text."""
    if not USE_COLOR or not styles:
        return text
    prefix = "".join(styles)
    return f"{prefix}{text}{Colors.RESET}"


def bold(text: str) -> str:
    return colorize(text, Colors.BOLD)


def cyan(text: str) -> str:
    return colorize(text, Colors.CYAN)


def green(text: str) -> str:
    return colorize(text, Colors.GREEN)


def yellow(text: str) -> str:
    return colorize(text, Colors.YELLOW)


def red(text: str) -> str:
    return colorize(text, Colors.RED)


def magenta(text: str) -> str:
    return colorize(text, Colors.MAGENTA)


def dim(text: str) -> str:
    return colorize(text, Colors.DIM)


def header(title: str, subtitle: Optional[str] = None):
    """Print an eye-catching header box."""
    term_width = min(shutil.get_terminal_size((80, 24)).columns, 80)
    border = "═" * (term_width - 2)
    print()
    print(colorize(f"╔{border}╗", Colors.CYAN, Colors.BOLD))
    centered_title = f"  {title}  ".center(term_width - 2)
    print(colorize(f"║{centered_title}║", Colors.CYAN, Colors.BOLD))
    if subtitle:
        centered_sub = f"  {subtitle}  ".center(term_width - 2)
        print(colorize(f"║{centered_sub}║", Colors.DIM))
    print(colorize(f"╚{border}╝", Colors.CYAN, Colors.BOLD))
    print()


def print_alert(message: str, level: str = "info"):
    """Print standard styled alert box."""
    if level == "error":
        icon = "[✕]"
        styled_tag = colorize("ERROR", Colors.RED, Colors.BOLD)
        msg_color = Colors.RED
    elif level == "warning":
        icon = "[!]"
        styled_tag = colorize("WARNING", Colors.YELLOW, Colors.BOLD)
        msg_color = Colors.YELLOW
    elif level == "success":
        icon = "[✓]"
        styled_tag = colorize("SUCCESS", Colors.GREEN, Colors.BOLD)
        msg_color = Colors.GREEN
    else:
        icon = "[i]"
        styled_tag = colorize("INFO", Colors.CYAN, Colors.BOLD)
        msg_color = Colors.CYAN

    print(f" {icon} {styled_tag}: {colorize(message, msg_color)}")


def progress_bar(current: float, target: float, length: int = 24, unit: str = "kcal") -> str:
    """Generate a colored progress bar with completion percentage."""
    if target <= 0:
        ratio = 0.0
    else:
        ratio = current / target

    pct = ratio * 100
    filled_len = int(round(length * min(ratio, 1.0)))
    empty_len = length - filled_len

    # Choose color based on goal status
    if pct > 105:
        bar_color = Colors.RED
    elif pct >= 85:
        bar_color = Colors.GREEN
    elif pct >= 50:
        bar_color = Colors.YELLOW
    else:
        bar_color = Colors.CYAN

    bar_blocks = "█" * filled_len + "░" * empty_len
    colored_bar = colorize(bar_blocks, bar_color)
    status_str = f"[{colored_bar}] {bold(f'{pct:.1f}%')} ({current:g}/{target:g} {unit})"
    return status_str


def macro_bar(carbs_g: float, protein_g: float, fat_g: float, length: int = 30) -> str:
    """
    Generate a colored tri-split bar representing macro distribution:
    - Carbs (Yellow/Orange)
    - Protein (Blue/Cyan)
    - Fat (Magenta/Red)
    """
    c_cal = carbs_g * 4.0
    p_cal = protein_g * 4.0
    f_cal = fat_g * 9.0
    total_cal = c_cal + p_cal + f_cal

    if total_cal <= 0:
        return dim("[ No macronutrient data ]")

    c_len = max(0, int(round((c_cal / total_cal) * length)))
    p_len = max(0, int(round((p_cal / total_cal) * length)))
    f_len = max(0, length - c_len - p_len)

    bar = (
        colorize("■" * p_len, Colors.CYAN) +
        colorize("■" * c_len, Colors.YELLOW) +
        colorize("■" * f_len, Colors.MAGENTA)
    )

    p_pct = (p_cal / total_cal) * 100
    c_pct = (c_cal / total_cal) * 100
    f_pct = (f_cal / total_cal) * 100

    legend = (
        f" {colorize('■ Protein', Colors.CYAN)}: {protein_g:.1f}g ({p_pct:.0f}%) | "
        f"{colorize('■ Carbs', Colors.YELLOW)}: {carbs_g:.1f}g ({c_pct:.0f}%) | "
        f"{colorize('■ Fat', Colors.MAGENTA)}: {fat_g:.1f}g ({f_pct:.0f}%)"
    )
    return f"[{bar}]\n{legend}"


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    alignments: Optional[Sequence[str]] = None
):
    """
    Render clean Unicode bordered table:
    ┌──────┬──────┐
    │ Col1 │ Col2 │
    ├──────┼──────┤
    │ Val1 │ Val2 │
    └──────┴──────┘
    alignments: 'L' (left) or 'R' (right) for each column.
    """
    if not headers and not rows:
        print(dim("  (No records found)"))
        return

    col_count = len(headers)
    if not alignments:
        alignments = ["L"] * col_count

    # Determine column widths
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            if idx < col_count:
                widths[idx] = max(widths[idx], len(str(val)))

    # Add 2 char padding
    widths = [w + 2 for w in widths]

    # Box-drawing characters
    tl, tm, tr = "┌", "┬", "┐"
    ml, mm, mr = "├", "┼", "┤"
    bl, bm, br = "└", "┴", "┘"
    vl, hl = "│", "─"

    top_border = tl + tm.join(hl * w for w in widths) + tr
    mid_border = ml + mm.join(hl * w for w in widths) + mr
    bot_border = bl + bm.join(hl * w for w in widths) + br

    print(colorize(top_border, Colors.DIM))

    # Header Row
    header_cells = []
    for h, w, a in zip(headers, widths, alignments):
        cell = f" {h} "
        if a == "R":
            cell = cell.rjust(w)
        else:
            cell = cell.ljust(w)
        header_cells.append(bold(cell))
    print(colorize(vl, Colors.DIM) + colorize(vl, Colors.DIM).join(header_cells) + colorize(vl, Colors.DIM))

    print(colorize(mid_border, Colors.DIM))

    # Data Rows
    if not rows:
        empty_msg = "  No data entries  ".center(sum(widths) + col_count - 1)
        print(colorize(vl, Colors.DIM) + dim(empty_msg) + colorize(vl, Colors.DIM))
    else:
        for row in rows:
            cells = []
            for idx in range(col_count):
                val = str(row[idx]) if idx < len(row) else ""
                w = widths[idx]
                a = alignments[idx] if idx < len(alignments) else "L"
                cell = f" {val} "
                if a == "R":
                    cell = cell.rjust(w)
                else:
                    cell = cell.ljust(w)
                cells.append(cell)
            print(colorize(vl, Colors.DIM) + colorize(vl, Colors.DIM).join(cells) + colorize(vl, Colors.DIM))

    print(colorize(bot_border, Colors.DIM))
