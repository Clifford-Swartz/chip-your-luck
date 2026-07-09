"""Board geometry and tile placement.

The board is the perimeter of a 6-wide x 5-tall grid: 30 cells, minus the
inner 4x3 block reserved for the centre display, leaves exactly 18 tiles.
Positions are ordered clockwise from the top-left so the travelling light
walks a sensible ring.
"""
import random

from .config import Config, Tile, SHORT_CIRCUIT

COLS, ROWS = 6, 5
INNER_COLS = range(1, COLS - 1)
INNER_ROWS = range(1, ROWS - 1)


def ring_cells() -> list[tuple[int, int]]:
    """18 (col, row) pairs, clockwise from top-left."""
    top = [(c, 0) for c in range(COLS)]
    right = [(COLS - 1, r) for r in range(1, ROWS)]
    bottom = [(c, ROWS - 1) for c in range(COLS - 2, -1, -1)]
    left = [(0, r) for r in range(ROWS - 2, 0, -1)]
    cells = top + right + bottom + left
    assert len(cells) == 18, f"expected 18 ring cells, got {len(cells)}"
    return cells


RING = ring_cells()
NUM_POSITIONS = len(RING)

SHORT_CIRCUIT_LABELS = [
    "SHORT CIRCUIT!",
    "MAGIC SMOKE!",
    "BROWNOUT!",
]


def short_circuit_tile(i: int = 0) -> Tile:
    return Tile(
        label=SHORT_CIRCUIT_LABELS[i % len(SHORT_CIRCUIT_LABELS)],
        value=0,
        type=SHORT_CIRCUIT,
        qty=0,
        image="",
        unlimited=True,
    )


class Board:
    """Owns the 18 face-up tiles and the inventory behind them."""

    def __init__(self, cfg: Config, rng: random.Random | None = None) -> None:
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.faces: list[Tile] = []
        self.reshuffle()

    # ---- inventory ---------------------------------------------------
    def _prize_pool(self) -> list[Tile]:
        return [t for t in self.cfg.tiles if t.available and not t.is_short_circuit]

    def consume(self, tile: Tile) -> None:
        """Decrement a limited prize. No-op for unlimited tiles."""
        if not tile.unlimited:
            tile.qty = max(0, tile.qty - 1)

    # ---- placement ---------------------------------------------------
    def reshuffle(self) -> None:
        """Rebuild the 18 visible faces from the prize pool + short circuits."""
        n_sc = min(self.cfg.short_circuit_count, NUM_POSITIONS)
        n_prize = NUM_POSITIONS - n_sc

        pool = self._prize_pool()
        if not pool:
            # Everything sold out: fall back to a token prize so the board
            # is still playable rather than all-short-circuit.
            pool = [Tile(label="THANKS!", value=0)]

        faces: list[Tile] = []
        while len(faces) < n_prize:
            chunk = pool[:]
            self.rng.shuffle(chunk)
            faces.extend(chunk[: n_prize - len(faces)])

        faces.extend(short_circuit_tile(i) for i in range(n_sc))
        self.rng.shuffle(faces)
        self.faces = faces

    def tile_at(self, pos: int) -> Tile:
        return self.faces[pos % NUM_POSITIONS]

    def random_position(self, exclude: int | None = None) -> int:
        choices = [p for p in range(NUM_POSITIONS) if p != exclude]
        return self.rng.choice(choices)
