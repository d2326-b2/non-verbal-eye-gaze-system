"""
Stats Chart — light theme, embedded in its own clean window.
"""

import tkinter as tk
from datetime import datetime

WHITE      = "#ffffff"
BG         = "#f0f4f8"
ACCENT     = "#3b82f6"
ACCENT_DARK= "#1d4ed8"
TEXT_PRI   = "#111827"
TEXT_SEC   = "#374151"
TEXT_MUTED = "#6b7280"
BORDER     = "#d1d5db"
DANGER     = "#dc2626"
SUCCESS    = "#16a34a"

BAR_COLORS = ["#3b82f6","#8b5cf6","#10b981","#f59e0b",
               "#ef4444","#06b6d4","#f97316","#84cc16","#ec4899"]

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    _MPL = True
except ImportError:
    _MPL = False


def show_stats_window(parent, counts: dict):
    """Display task usage statistics in separate window with bar chart."""
    win = tk.Toplevel(parent)
    win.title("Task Usage Statistics")
    win.configure(bg=WHITE)
    win.geometry("620x480")
    win.resizable(True, True)

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = tk.Frame(win, bg=ACCENT, pady=12)
    hdr.pack(fill="x")
    tk.Label(hdr, text="📊  Task Usage Statistics",
             font=("Segoe UI Emoji", 13, "bold"),
             bg=ACCENT, fg=WHITE, padx=16).pack(side="left")

    total = sum(counts.values())
    tk.Label(hdr, text=f"Total requests: {total}",
             font=("Segoe UI", 11),
             bg=ACCENT, fg="#bfdbfe", padx=16).pack(side="right")

    if not _MPL:
        # Show error if matplotlib not installed
        tk.Label(win,
                 text="matplotlib not installed.\nRun:  pip install matplotlib",
                 font=("Segoe UI", 12), bg=WHITE, fg=DANGER,
                 pady=40).pack()
        return

    # Extract task names and counts
    labels = list(counts.keys())
    values = [counts.get(l, 0) for l in labels]
    max_v  = max(values) if values else 1

    # Create bar chart with matplotlib
    fig = Figure(figsize=(6, 3.2), dpi=100, facecolor=WHITE)
    ax  = fig.add_subplot(111)
    ax.set_facecolor("#f8fafc")

    # Draw colored bars for each task
    colors = [BAR_COLORS[i % len(BAR_COLORS)] for i in range(len(labels))]
    bars   = ax.bar(labels, values, color=colors,
                    edgecolor="white", linewidth=1.5,
                    width=0.6)

    # Add count labels on top of bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    str(val),
                    ha="center", va="bottom",
                    color=TEXT_PRI, fontsize=10, fontweight="bold")

    # Configure chart axes and styling
    ax.set_xlabel("Task", color=TEXT_SEC, fontsize=10, labelpad=6)
    ax.set_ylabel("Times selected", color=TEXT_SEC, fontsize=10, labelpad=6)
    ax.set_ylim(0, max(values + [1]) + 2)
    ax.tick_params(colors=TEXT_SEC, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color="#e5e7eb", linewidth=0.8)

    # Rotate x-axis labels for readability
    for lbl in ax.get_xticklabels():
        lbl.set_rotation(25)
        lbl.set_ha("right")
        lbl.set_color(TEXT_SEC)

    fig.tight_layout(pad=1.8)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=8)

    # ── Summary cards ─────────────────────────────────────────────────────────
    summary = tk.Frame(win, bg=WHITE)
    summary.pack(fill="x", padx=12, pady=(0, 4))

    if total > 0:
        top_task = max(counts, key=counts.get)
        top_count = counts[top_task]

        for label, value, color in [
            ("Total requests",   str(total),        ACCENT),
            ("Most used task",   f"{top_task} ({top_count}×)", SUCCESS),
            ("Tasks available",  str(len(labels)),  "#7c3aed"),
        ]:
            card = tk.Frame(summary, bg="#f0f9ff",
                            highlightthickness=1,
                            highlightbackground="#bae6fd")
            card.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(card, text=label,
                     font=("Segoe UI", 8),
                     bg="#f0f9ff", fg=TEXT_MUTED,
                     pady=4).pack()
            tk.Label(card, text=value,
                     font=("Segoe UI", 12, "bold"),
                     bg="#f0f9ff", fg=color,
                     pady=2).pack()

    # ── Bottom buttons ────────────────────────────────────────────────────────
    btn_row = tk.Frame(win, bg=WHITE, pady=8)
    btn_row.pack()

    tk.Button(btn_row, text="🗑  Reset All Counts",
              command=lambda: _reset(counts, win, parent),
              font=("Segoe UI", 10), bg=DANGER, fg=WHITE,
              relief="flat", padx=14, pady=6,
              cursor="hand2", bd=0).pack(side="left", padx=6)

    tk.Button(btn_row, text="✕  Close",
              command=win.destroy,
              font=("Segoe UI", 10), bg=BG, fg=TEXT_SEC,
              relief="flat", padx=14, pady=6,
              cursor="hand2", bd=0).pack(side="left", padx=6)


def _reset(counts, win, parent):
    for k in counts:
        counts[k] = 0
    win.destroy()
    show_stats_window(parent, counts)
