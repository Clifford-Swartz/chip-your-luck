"""Pure game logic. No pygame import here, so it stays testable."""
import csv
import datetime as dt
import random
from dataclasses import dataclass, field
from enum import Enum, auto

from .board import Board, NUM_POSITIONS
from .config import Config, Tile
from .paths import APP_DIR


class State(Enum):
    ATTRACT = auto()
    READY = auto()
    SPINNING = auto()
    RESOLVE = auto()
    DECISION = auto()
    GAME_OVER = auto()


@dataclass
class Result:
    banked: int = 0
    spins_used: int = 0
    short_circuited: bool = False
    prizes: list[str] = field(default_factory=list)


class Engine:
    def __init__(self, cfg: Config, rng: random.Random | None = None) -> None:
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.board = Board(cfg, self.rng)
        self.state = State.ATTRACT
        self.events: list[str] = []

        self.light_pos = 0
        self.landed_pos: int | None = None
        self.landed_tile: Tile | None = None

        self.bank = 0
        self.spins_left = cfg.spins
        self.spins_used = 0
        self.result = Result()

        self._hop_accum = 0.0
        self._state_ms = 0.0
        self._idle_ms = 0.0

    # ---- helpers -----------------------------------------------------
    def emit(self, name: str) -> None:
        self.events.append(name)

    def drain_events(self) -> list[str]:
        out, self.events = self.events, []
        return out

    @property
    def hop_ms(self) -> float:
        """Board speeds up over the course of a game."""
        n = self.cfg.hop_accel_spins
        t = 1.0 if n == 0 else min(1.0, self.spins_used / n)
        return self.cfg.hop_ms_start + (self.cfg.hop_ms_end - self.cfg.hop_ms_start) * t

    def _goto(self, state: State) -> None:
        self.state = state
        self._state_ms = 0.0

    # ---- lifecycle ---------------------------------------------------
    def reset_game(self) -> None:
        self.bank = 0
        self.spins_left = self.cfg.spins
        self.spins_used = 0
        self.result = Result()
        self.landed_pos = None
        self.landed_tile = None
        self.board.reshuffle()
        self._goto(State.READY)
        self.emit("game_start")

    def start_spin(self) -> None:
        if self.cfg.reshuffle_each_spin and self.spins_used > 0:
            self.board.reshuffle()
        self.landed_pos = None
        self.landed_tile = None
        self._hop_accum = 0.0
        self._goto(State.SPINNING)
        self.emit("spin_start")

    def stop_board(self) -> None:
        """The buzzer press that lands the light."""
        self.landed_pos = self.light_pos
        tile = self.board.tile_at(self.light_pos)
        self.landed_tile = tile
        self.spins_used += 1
        self.spins_left -= 1

        if tile.is_short_circuit:
            self.bank = 0
            self.spins_left = 0
            self.result.short_circuited = True
            self.emit("short_circuit")
        else:
            self.bank += tile.value
            self.board.consume(tile)
            self.result.prizes.append(tile.label)
            if tile.grants_spin:
                self.spins_left += 1
                self.emit("bonus_spin")
            self.emit("prize")

        self._goto(State.RESOLVE)

    def bank_and_stop(self) -> None:
        self.result.banked = self.bank
        self.result.spins_used = self.spins_used
        self._log_result()
        self._goto(State.GAME_OVER)
        self.emit("bank")

    def _end_game(self) -> None:
        self.result.banked = self.bank
        self.result.spins_used = self.spins_used
        self._log_result()
        self._goto(State.GAME_OVER)
        self.emit("game_over")

    def _log_result(self) -> None:
        path = APP_DIR / self.cfg.log_csv
        new = not path.exists()
        try:
            with path.open("a", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                if new:
                    w.writerow(["timestamp", "banked", "spins_used",
                                "short_circuited", "prizes"])
                w.writerow([
                    dt.datetime.now().isoformat(timespec="seconds"),
                    self.result.banked,
                    self.result.spins_used,
                    int(self.result.short_circuited),
                    "; ".join(self.result.prizes),
                ])
        except OSError as exc:
            print(f"[log] could not append to {path}: {exc}")

    # ---- input -------------------------------------------------------
    def press_buzzer(self) -> None:
        self._idle_ms = 0.0
        if self.state is State.ATTRACT:
            self.reset_game()
        elif self.state is State.READY:
            self.start_spin()
        elif self.state is State.SPINNING:
            self.stop_board()
        elif self.state is State.DECISION:
            self.start_spin()
        elif self.state is State.GAME_OVER and self._state_ms > 1200:
            self._goto(State.ATTRACT)

    def press_bank(self) -> None:
        self._idle_ms = 0.0
        if self.state is State.DECISION:
            self.bank_and_stop()

    # ---- tick --------------------------------------------------------
    def update(self, dt_ms: float) -> None:
        self._state_ms += dt_ms
        self._idle_ms += dt_ms

        if self.state is State.SPINNING:
            self._hop_accum += dt_ms
            while self._hop_accum >= self.hop_ms:
                self._hop_accum -= self.hop_ms
                self.light_pos = self.board.random_position(exclude=self.light_pos)
                self.emit("hop")

        elif self.state is State.ATTRACT:
            # Idle demo light so the screen is never dead.
            self._hop_accum += dt_ms
            while self._hop_accum >= 520:
                self._hop_accum -= 520
                self.light_pos = (self.light_pos + 1) % NUM_POSITIONS

        elif self.state is State.RESOLVE:
            hold = (self.cfg.short_circuit_hold_ms if self.result.short_circuited
                    else self.cfg.resolve_hold_ms)
            if self._state_ms >= hold:
                if self.spins_left <= 0:
                    self._end_game()
                else:
                    self._goto(State.DECISION)

        elif self.state is State.GAME_OVER:
            if self._state_ms >= self.cfg.game_over_hold_ms:
                self._goto(State.ATTRACT)

        elif self.state is State.READY:
            idle = self.cfg.attract_idle_seconds
            if idle and self._idle_ms >= idle * 1000:
                self._goto(State.ATTRACT)
