"""Tkinter admin panel: edit tiles, upload prize images, tune the odds.

Opened from the game with F1. It runs its own mainloop and blocks the game
loop until closed, which is exactly what you want at a booth.
"""
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import Config, Tile, PRIZE, PRIZE_PLUS_SPIN
from .paths import PRIZES_DIR, ensure_dirs

TYPES = [PRIZE, PRIZE_PLUS_SPIN]
IMAGE_TYPES = [("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]


class AdminPanel:
    def __init__(self, cfg: Config) -> None:
        ensure_dirs()
        self.cfg = cfg
        self.saved = False
        self.tiles = [Tile(**vars(t)) for t in cfg.tiles]  # edit a copy

        self.root = tk.Tk()
        self.root.title("Chip Your Luck - Admin")
        self.root.geometry("900x640")
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self._cancel)

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self._build_prizes(nb)
        self._build_settings(nb)

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="Save & Close", command=self._save).pack(side="right")
        ttk.Button(bar, text="Cancel", command=self._cancel).pack(side="right", padx=6)

    # ---- prizes tab --------------------------------------------------
    def _build_prizes(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="Prizes")

        cols = ("label", "value", "type", "qty", "image")
        self.tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        widths = {"label": 240, "value": 80, "type": 130, "qty": 70, "image": 260}
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True, pady=(6, 6))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.Frame(tab)
        form.pack(fill="x")

        self.v_label = tk.StringVar()
        self.v_value = tk.StringVar()
        self.v_type = tk.StringVar(value=PRIZE)
        self.v_qty = tk.StringVar()
        self.v_image = tk.StringVar()

        def row(r, text, var, width=28, **kw):
            ttk.Label(form, text=text).grid(row=r, column=0, sticky="e", padx=4, pady=3)
            e = ttk.Entry(form, textvariable=var, width=width, **kw)
            e.grid(row=r, column=1, sticky="w", padx=4)
            return e

        row(0, "Label", self.v_label)
        row(1, "Value ($)", self.v_value, width=10)
        ttk.Label(form, text="Type").grid(row=2, column=0, sticky="e", padx=4)
        ttk.Combobox(form, textvariable=self.v_type, values=TYPES, width=25,
                     state="readonly").grid(row=2, column=1, sticky="w", padx=4)
        row(3, "Qty (0 = unlimited)", self.v_qty, width=10)

        ttk.Label(form, text="Image").grid(row=4, column=0, sticky="e", padx=4)
        ttk.Entry(form, textvariable=self.v_image, width=30,
                  state="readonly").grid(row=4, column=1, sticky="w", padx=4)
        ttk.Button(form, text="Upload...", command=self._pick_image).grid(
            row=4, column=2, sticky="w")
        ttk.Button(form, text="Clear", command=lambda: self.v_image.set("")).grid(
            row=4, column=3, sticky="w", padx=4)

        btns = ttk.Frame(tab)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Add", command=self._add).pack(side="left")
        ttk.Button(btns, text="Update Selected", command=self._update).pack(
            side="left", padx=6)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left")
        ttk.Label(
            btns,
            text="Short circuits are generated automatically - set how many "
                 "on the Settings tab.",
            foreground="#666",
        ).pack(side="right")

        self._refresh()

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, t in enumerate(self.tiles):
            qty = "unlimited" if t.unlimited else f"{t.qty} left"
            self.tree.insert("", "end", iid=str(i),
                             values=(t.label, t.value, t.type, qty, t.image or "-"))

    def _selected_index(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self, _evt=None) -> None:
        i = self._selected_index()
        if i is None:
            return
        t = self.tiles[i]
        self.v_label.set(t.label)
        self.v_value.set(str(t.value))
        self.v_type.set(t.type)
        self.v_qty.set(str(t.qty))
        self.v_image.set(t.image)

    def _read_form(self) -> Tile | None:
        label = self.v_label.get().strip()
        if not label:
            messagebox.showerror("Missing label", "Give the tile a label.", parent=self.root)
            return None
        try:
            value = int(self.v_value.get() or 0)
            qty = int(self.v_qty.get() or 0)
        except ValueError:
            messagebox.showerror("Bad number", "Value and Qty must be whole numbers.",
                                 parent=self.root)
            return None
        return Tile(label=label, value=value, type=self.v_type.get(),
                    qty=max(0, qty), image=self.v_image.get().strip(),
                    unlimited=qty <= 0)

    def _add(self) -> None:
        t = self._read_form()
        if t:
            self.tiles.append(t)
            self._refresh()

    def _update(self) -> None:
        i = self._selected_index()
        if i is None:
            messagebox.showinfo("Nothing selected", "Pick a row first.", parent=self.root)
            return
        t = self._read_form()
        if t:
            self.tiles[i] = t
            self._refresh()
            self.tree.selection_set(str(i))

    def _delete(self) -> None:
        i = self._selected_index()
        if i is None:
            return
        del self.tiles[i]
        self._refresh()

    def _pick_image(self) -> None:
        src = filedialog.askopenfilename(title="Choose a prize image",
                                         filetypes=IMAGE_TYPES, parent=self.root)
        if not src:
            return
        src_path = Path(src)
        dest = PRIZES_DIR / src_path.name
        if dest.resolve() != src_path.resolve():
            try:
                shutil.copy2(src_path, dest)
            except OSError as exc:
                messagebox.showerror("Copy failed", str(exc), parent=self.root)
                return
        self.v_image.set(dest.name)

    # ---- settings tab ------------------------------------------------
    def _build_settings(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb)
        nb.add(tab, text="Settings")

        self.s_title = tk.StringVar(value=self.cfg.title)
        self.s_subtitle = tk.StringVar(value=self.cfg.subtitle)
        self.s_spins = tk.StringVar(value=str(self.cfg.spins))
        self.s_sc = tk.StringVar(value=str(self.cfg.short_circuit_count))
        self.s_start = tk.StringVar(value=str(self.cfg.hop_ms_start))
        self.s_end = tk.StringVar(value=str(self.cfg.hop_ms_end))
        self.s_full = tk.BooleanVar(value=self.cfg.fullscreen)
        self.s_reshuffle = tk.BooleanVar(value=self.cfg.reshuffle_each_spin)

        self.s_flash = tk.StringVar(value=str(self.cfg.flash_ms))
        self.s_blink = tk.StringVar(value=str(self.cfg.blink_ms))
        self.s_resolve = tk.StringVar(value=str(self.cfg.resolve_hold_ms))
        self.s_schold = tk.StringVar(value=str(self.cfg.short_circuit_hold_ms))
        self.s_over = tk.StringVar(value=str(self.cfg.game_over_hold_ms))

        rows = [
            ("Title", self.s_title, 40),
            ("Subtitle", self.s_subtitle, 40),
            ("Spins per player", self.s_spins, 8),
            ("Short circuits on board (of 18)", self.s_sc, 8),
            ("Light speed at start (ms/tile)", self.s_start, 8),
            ("Light speed at end (ms/tile)", self.s_end, 8),
        ]
        for r, (text, var, w) in enumerate(rows):
            ttk.Label(tab, text=text).grid(row=r, column=0, sticky="e", padx=8, pady=5)
            ttk.Entry(tab, textvariable=var, width=w).grid(row=r, column=1, sticky="w")

        ttk.Checkbutton(tab, text="Fullscreen", variable=self.s_full).grid(
            row=6, column=1, sticky="w", pady=4)
        ttk.Checkbutton(tab, text="Reshuffle board between spins",
                        variable=self.s_reshuffle).grid(row=7, column=1, sticky="w")

        ttk.Separator(tab, orient="horizontal").grid(
            row=8, column=0, columnspan=3, sticky="ew", pady=12)
        ttk.Label(tab, text="Timing (milliseconds)", font=("", 9, "bold")).grid(
            row=9, column=0, columnspan=2, sticky="w", padx=8)

        timing = [
            ("Short Circuit flash rate", self.s_flash,
             "lower = faster strobe"),
            ("Blinking text rate", self.s_blink,
             "'PRESS TO PLAY' and the bank/press prompt"),
            ("Prize on screen", self.s_resolve,
             "how long a win is shown"),
            ("Short Circuit on screen", self.s_schold,
             "how long the red flash lasts"),
            ("Game over on screen", self.s_over,
             "before returning to attract"),
        ]
        for i, (text, var, hint) in enumerate(timing):
            r = 10 + i
            ttk.Label(tab, text=text).grid(row=r, column=0, sticky="e", padx=8, pady=3)
            ttk.Entry(tab, textvariable=var, width=8).grid(row=r, column=1, sticky="w")
            ttk.Label(tab, text=hint, foreground="#888").grid(
                row=r, column=2, sticky="w", padx=6)

        note = ("A higher short-circuit count makes the game meaner. 3 of 18 is "
                "about a 1-in-6 chance per spin.\nLower ms = faster light = harder. "
                "1000 ms = 1 second.")
        ttk.Label(tab, text=note, foreground="#666", justify="left").grid(
            row=16, column=0, columnspan=3, sticky="w", padx=8, pady=14)

    # ---- save / cancel -----------------------------------------------
    def _save(self) -> None:
        if not self.tiles:
            messagebox.showerror("No prizes", "Add at least one prize tile.",
                                 parent=self.root)
            return
        try:
            spins = int(self.s_spins.get())
            sc = int(self.s_sc.get())
            hop_start = int(self.s_start.get())
            hop_end = int(self.s_end.get())
            flash = int(self.s_flash.get())
            blink = int(self.s_blink.get())
            resolve = int(self.s_resolve.get())
            schold = int(self.s_schold.get())
            over = int(self.s_over.get())
        except ValueError:
            messagebox.showerror("Bad number", "Numeric settings must be whole numbers.",
                                 parent=self.root)
            return
        if not 0 <= sc < 18:
            messagebox.showerror("Bad count", "Short circuits must be 0-17.",
                                 parent=self.root)
            return
        if flash < 40 or blink < 60:
            messagebox.showerror(
                "Too fast",
                "Flash rate must be at least 40 ms and blink rate at least 60 ms.\n"
                "Anything faster strobes hard enough to be a seizure risk.",
                parent=self.root)
            return

        self.cfg.title = self.s_title.get()
        self.cfg.subtitle = self.s_subtitle.get()
        self.cfg.spins = max(1, spins)
        self.cfg.short_circuit_count = sc
        self.cfg.hop_ms_start = max(60, hop_start)
        self.cfg.hop_ms_end = max(40, hop_end)
        self.cfg.fullscreen = self.s_full.get()
        self.cfg.reshuffle_each_spin = self.s_reshuffle.get()
        self.cfg.flash_ms = flash
        self.cfg.blink_ms = blink
        self.cfg.resolve_hold_ms = max(200, resolve)
        self.cfg.short_circuit_hold_ms = max(200, schold)
        self.cfg.game_over_hold_ms = max(500, over)
        self.cfg.tiles = self.tiles

        try:
            self.cfg.save()
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.root)
            return
        self.saved = True
        self.root.destroy()

    def _cancel(self) -> None:
        self.saved = False
        self.root.destroy()

    def run(self) -> bool:
        self.root.mainloop()
        return self.saved


def open_admin(cfg: Config) -> bool:
    """Blocking. Returns True if the config was saved."""
    return AdminPanel(cfg).run()
