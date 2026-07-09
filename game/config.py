"""Config load/save. Tolerates a missing or partial config.json."""
import json
from dataclasses import dataclass, field, asdict
from typing import Any

from .paths import CONFIG_PATH

BOARD_TILES = 18

DEFAULTS: dict[str, Any] = {
    "title": "CHIP YOUR LUCK",
    "subtitle": "BIG BUCKS, NO SHORT CIRCUITS!",
    "fullscreen": True,
    "spins": 3,
    "short_circuit_count": 3,
    "hop_ms_start": 460,
    "hop_ms_end": 240,
    "hop_accel_spins": 2,
    "reshuffle_each_spin": True,
    "attract_idle_seconds": 45,
    # Timing, all milliseconds.
    "flash_ms": 140,          # Short Circuit strobe, half-period
    "blink_ms": 500,          # blinking prompt text, half-period
    "resolve_hold_ms": 2600,  # how long a won prize stays up
    "short_circuit_hold_ms": 3400,
    "game_over_hold_ms": 6000,
    "log_csv": "results.csv",
    "keys": {
        "buzzer": ["space", "return"],
        "bank": ["b"],
        "start": ["space", "return"],
        "admin": ["f1"],
        "quit": ["escape"],
    },
    "tiles": [],
}

# type -> behaviour
PRIZE = "prize"
PRIZE_PLUS_SPIN = "prize_plus_spin"
SHORT_CIRCUIT = "short_circuit"


@dataclass
class Tile:
    label: str = "$100"
    value: int = 100
    type: str = PRIZE
    qty: int = 0  # remaining stock; meaningless when `unlimited`
    image: str = ""
    # Stored explicitly rather than inferred from `qty == 0`: a limited prize
    # that sells out also reaches 0, and must NOT become unlimited again.
    unlimited: bool = True

    @property
    def available(self) -> bool:
        return self.unlimited or self.qty > 0

    @property
    def is_short_circuit(self) -> bool:
        return self.type == SHORT_CIRCUIT

    @property
    def grants_spin(self) -> bool:
        return self.type == PRIZE_PLUS_SPIN


@dataclass
class Config:
    title: str = DEFAULTS["title"]
    subtitle: str = DEFAULTS["subtitle"]
    fullscreen: bool = True
    spins: int = 3
    short_circuit_count: int = 3
    hop_ms_start: int = 460
    hop_ms_end: int = 240
    hop_accel_spins: int = 2
    reshuffle_each_spin: bool = True
    attract_idle_seconds: int = 45
    flash_ms: int = 140
    blink_ms: int = 500
    resolve_hold_ms: int = 2600
    short_circuit_hold_ms: int = 3400
    game_over_hold_ms: int = 6000
    log_csv: str = "results.csv"
    keys: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULTS["keys"]))
    tiles: list[Tile] = field(default_factory=list)

    # ---- persistence -------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        raw = dict(DEFAULTS)
        if CONFIG_PATH.exists():
            try:
                raw.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError) as exc:
                print(f"[config] could not read {CONFIG_PATH}: {exc}; using defaults")

        keys = dict(DEFAULTS["keys"])
        keys.update(raw.get("keys") or {})

        tiles = [_tile_from(t) for t in raw.get("tiles") or []]
        if not tiles:
            tiles = _fallback_tiles()

        return cls(
            title=str(raw["title"]),
            subtitle=str(raw["subtitle"]),
            fullscreen=bool(raw["fullscreen"]),
            spins=max(1, int(raw["spins"])),
            short_circuit_count=max(0, int(raw["short_circuit_count"])),
            hop_ms_start=max(60, int(raw["hop_ms_start"])),
            hop_ms_end=max(40, int(raw["hop_ms_end"])),
            hop_accel_spins=max(0, int(raw["hop_accel_spins"])),
            reshuffle_each_spin=bool(raw["reshuffle_each_spin"]),
            attract_idle_seconds=max(0, int(raw["attract_idle_seconds"])),
            # Floors keep a typo like `0` from dividing by zero or pinning
            # the strobe at seizure speed.
            flash_ms=max(40, int(raw["flash_ms"])),
            blink_ms=max(60, int(raw["blink_ms"])),
            resolve_hold_ms=max(200, int(raw["resolve_hold_ms"])),
            short_circuit_hold_ms=max(200, int(raw["short_circuit_hold_ms"])),
            game_over_hold_ms=max(500, int(raw["game_over_hold_ms"])),
            log_csv=str(raw["log_csv"]),
            keys=keys,
            tiles=tiles,
        )

    def save(self) -> None:
        payload = asdict(self)
        payload["tiles"] = [asdict(t) for t in self.tiles]
        tmp = CONFIG_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_PATH)


def _tile_from(d: dict[str, Any]) -> Tile:
    qty = int(d.get("qty", 0) or 0)
    return Tile(
        label=str(d.get("label", "$100")),
        value=int(d.get("value", 0) or 0),
        type=str(d.get("type", PRIZE)),
        qty=max(0, qty),
        image=str(d.get("image", "") or ""),
        # Hand-written configs just say `qty: 0` to mean unlimited.
        unlimited=bool(d.get("unlimited", qty <= 0)),
    )


def _fallback_tiles() -> list[Tile]:
    vals = [100, 250, 400, 500, 600, 750, 800, 1000, 1500, 2000]
    return [Tile(label=f"${v}", value=v) for v in vals]
