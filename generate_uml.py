"""Generate uml_final.png from the Mermaid class diagram using matplotlib."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(14, 9))
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("#FBF8F3")

ACCENT   = "#E07B39"
DARK     = "#1C1C1C"
BORDER   = "#D4C5B0"
BG_HEAD  = "#E07B39"
BG_BODY  = "#FFFFFF"
TEXT_W   = "#FFFFFF"
TEXT_D   = "#1C1C1C"
TEXT_M   = "#555555"

def draw_class(ax, x, y, w, h, title, attrs, methods):
    row_h = 0.38
    head_h = 0.55
    # shadow
    shadow = FancyBboxPatch((x+0.07, y-0.07), w, h,
                             boxstyle="round,pad=0.05", linewidth=0,
                             facecolor="#D4C5B0", zorder=1)
    ax.add_patch(shadow)
    # body
    body = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.05", linewidth=1.5,
                           edgecolor=BORDER, facecolor=BG_BODY, zorder=2)
    ax.add_patch(body)
    # header band
    head = FancyBboxPatch((x, y+h-head_h), w, head_h,
                           boxstyle="round,pad=0.05", linewidth=0,
                           facecolor=BG_HEAD, zorder=3)
    ax.add_patch(head)
    # title
    ax.text(x+w/2, y+h-head_h/2, f"«class»\n{title}",
            ha="center", va="center", fontsize=9.5, fontweight="bold",
            color=TEXT_W, zorder=4, linespacing=1.3)
    # divider
    ax.plot([x+0.1, x+w-0.1], [y+h-head_h, y+h-head_h],
            color=BORDER, lw=0.8, zorder=4)

    all_rows = [(a, "#3B82C4") for a in attrs] + [(m, ACCENT) for m in methods]
    for i, (label, col) in enumerate(all_rows):
        ty = y + h - head_h - (i+1)*row_h + row_h*0.35
        ax.text(x+0.18, ty, label, ha="left", va="center",
                fontsize=7.5, color=TEXT_D, zorder=4, family="monospace")
    # attr/method divider
    if attrs and methods:
        dy = y + h - head_h - len(attrs)*row_h
        ax.plot([x+0.1, x+w-0.1], [dy, dy], color=BORDER, lw=0.5,
                linestyle="--", zorder=4)

def arrow(ax, x1, y1, x2, y2, label="", style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=DARK,
                                lw=1.3, connectionstyle="arc3,rad=0.0"),
                zorder=5)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx, my+0.15, label, ha="center", va="bottom",
                fontsize=7.5, color="#555555", style="italic", zorder=6)

# ── Classes ────────────────────────────────────────────────────────────────
# Owner  (top-left)
draw_class(ax, 0.5, 5.2, 3.5, 3.1, "Owner",
    ["owner_id: str", "name: str", "pets: list[Pet]"],
    ["add_pet(pet)", "get_pets() → list", "get_all_tasks() → list"])

# Pet  (top-right)
draw_class(ax, 5.2, 5.2, 3.5, 3.3, "Pet",
    ["pet_id: str", "name: str", "species: str", "tasks: list[Task]"],
    ["add_task(task)", "get_tasks() → list", "remove_task(task_id)"])

# Task  (bottom-right)
draw_class(ax, 5.2, 0.6, 3.5, 3.9, "Task",
    ["task_id: str", "description: str", "time: str  # HH:MM",
     "frequency: str", "due_date: date", "completed: bool"],
    ["mark_complete() → Task | None"])

# Scheduler  (bottom-left)
draw_class(ax, 0.5, 0.6, 3.5, 3.9, "Scheduler",
    ["owner: Owner"],
    ["get_todays_schedule() → list",
     "sort_by_time(tasks) → list",
     "filter_by_pet(name) → list",
     "filter_by_status(done) → list",
     "detect_conflicts() → list",
     "handle_recurring(task, pet)"])

# ── Arrows ─────────────────────────────────────────────────────────────────
arrow(ax, 4.0, 6.6, 5.2, 6.6, "1 owns many")        # Owner → Pet
arrow(ax, 6.95, 5.2, 6.95, 4.5, "1 has many")       # Pet → Task
arrow(ax, 4.0, 2.5, 5.2, 2.5, "creates next")        # Scheduler ← Task (info)
arrow(ax, 2.25, 5.2, 2.25, 4.5, "1 manages 1")       # Scheduler → Owner

# ── Title ──────────────────────────────────────────────────────────────────
ax.text(7.0, 8.6, "PawPal+  UML Class Diagram",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color=DARK)
ax.text(7.0, 8.2, "System Architecture — Final Implementation",
        ha="center", va="center", fontsize=9, color="#666666")

plt.tight_layout(pad=0.3)
plt.savefig("uml_final.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("Saved uml_final.png")
