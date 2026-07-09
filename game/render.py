"""All drawing. Everything is composed at 1920x1080 then scaled to the
real display with letterboxing, so the game looks identical on any monitor.
"""
import math

import pygame

from .board import COLS, ROWS, RING
from .config import Tile
from .engine import Engine, State
from .paths import PRIZES_DIR

VW, VH = 1920, 1080

BG = (10, 12, 20)
PANEL = (18, 22, 36)
TILE = (28, 34, 58)
TILE_EDGE = (52, 62, 96)
LIGHT = (255, 226, 90)
LIGHT_EDGE = (255, 255, 255)
SC_TILE = (86, 14, 20)
SC_EDGE = (220, 40, 50)
TEXT = (232, 236, 248)
DIM = (140, 150, 180)
GOLD = (255, 200, 60)
GREEN = (80, 220, 140)
RED = (240, 70, 80)

MARGIN_X, TOP = 70, 150
BOARD_W, BOARD_H = VW - MARGIN_X * 2, 880
CELL_W, CELL_H = BOARD_W / COLS, BOARD_H / ROWS
GAP = 9


def cell_rect(col: int, row: int) -> pygame.Rect:
    return pygame.Rect(
        int(MARGIN_X + col * CELL_W + GAP),
        int(TOP + row * CELL_H + GAP),
        int(CELL_W - GAP * 2),
        int(CELL_H - GAP * 2),
    )


CENTER_RECT = pygame.Rect(
    int(MARGIN_X + CELL_W + GAP),
    int(TOP + CELL_H + GAP),
    int(CELL_W * (COLS - 2) - GAP * 2),
    int(CELL_H * (ROWS - 2) - GAP * 2),
)


class Renderer:
    def __init__(self) -> None:
        self.canvas = pygame.Surface((VW, VH)).convert()
        self._fonts: dict[int, pygame.font.Font] = {}
        self._images: dict[str, pygame.Surface | None] = {}

    # ---- resources ---------------------------------------------------
    def font(self, size: int) -> pygame.font.Font:
        if size not in self._fonts:
            # Arial Black before Impact: Impact's narrow N reads as an H
            # from across a trade-show aisle.
            self._fonts[size] = pygame.font.SysFont(
                "arialblack,dejavusans,impact", size, bold=True
            )
        return self._fonts[size]

    def image(self, name: str) -> pygame.Surface | None:
        if not name:
            return None
        if name not in self._images:
            path = PRIZES_DIR / name
            try:
                self._images[name] = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error, FileNotFoundError):
                print(f"[render] missing prize image: {path}")
                self._images[name] = None
        return self._images[name]

    def forget_images(self) -> None:
        """Called after the admin panel edits prizes."""
        self._images.clear()

    # ---- text --------------------------------------------------------
    def text(self, surf, s, cx, cy, size, color=TEXT, max_w=None):
        f = self.font(size)
        while max_w and f.size(s)[0] > max_w and size > 10:
            size -= 2
            f = self.font(size)
        img = f.render(s, True, color)
        surf.blit(img, img.get_rect(center=(cx, cy)))
        return img.get_rect(center=(cx, cy))

    def wrapped(self, surf, s, rect, size, color=TEXT):
        """Centre `s` in `rect`, breaking on spaces and shrinking to fit.

        Shrinks on width as well as height: a single unbreakable word wider
        than the tile (BROWNOUT!) has nowhere to wrap and must scale down.
        """
        avail_w = rect.w - 12
        while True:
            f = self.font(size)
            words, lines, cur = s.split(), [], ""
            for w in words:
                trial = f"{cur} {w}".strip()
                if f.size(trial)[0] <= avail_w or not cur:
                    cur = trial
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)

            lh = f.get_linesize()
            too_tall = lh * len(lines) > rect.h
            too_wide = any(f.size(ln)[0] > avail_w for ln in lines)
            if (too_tall or too_wide) and size > 12:
                size -= 3
                continue
            break

        y = rect.centery - lh * len(lines) / 2 + lh / 2
        for line in lines:
            img = f.render(line, True, color)
            surf.blit(img, img.get_rect(center=(rect.centerx, int(y))))
            y += lh

    # ---- board -------------------------------------------------------
    def draw_tile(self, surf, rect: pygame.Rect, tile: Tile, lit: bool, t: float):
        sc = tile.is_short_circuit
        body = SC_TILE if sc else TILE
        edge = SC_EDGE if sc else TILE_EDGE

        if lit:
            pulse = 0.5 + 0.5 * math.sin(t * 0.02)
            body = tuple(int(a + (b - a) * (0.55 + 0.45 * pulse))
                         for a, b in zip(body, LIGHT))
            edge = LIGHT_EDGE

        pygame.draw.rect(surf, body, rect, border_radius=10)
        pygame.draw.rect(surf, edge, rect, width=4 if lit else 2, border_radius=10)

        img = self.image(tile.image)
        if img:
            box = rect.inflate(-16, -46)
            scale = min(box.w / img.get_width(), box.h / img.get_height())
            w, h = int(img.get_width() * scale), int(img.get_height() * scale)
            pic = pygame.transform.smoothscale(img, (w, h))
            surf.blit(pic, pic.get_rect(center=(rect.centerx, rect.centery - 14)))
            label = pygame.Rect(rect.x, rect.bottom - 40, rect.w, 34)
            self.wrapped(surf, tile.label, label, 26,
                         (10, 10, 10) if lit else TEXT)
        else:
            color = (10, 10, 10) if lit else (RED if sc else TEXT)
            self.wrapped(surf, tile.label, rect.inflate(-10, -10), 40, color)

    # ---- centre panel ------------------------------------------------
    def draw_center(self, surf, eng: Engine, t: float):
        r = CENTER_RECT
        pygame.draw.rect(surf, PANEL, r, border_radius=14)
        pygame.draw.rect(surf, TILE_EDGE, r, width=2, border_radius=14)

        st = eng.state
        top = pygame.Rect(r.x, r.y + 20, r.w, 120)
        mid = pygame.Rect(r.x, r.y + 150, r.w, 200)
        bot = pygame.Rect(r.x, r.bottom - 130, r.w, 100)

        blink = eng.cfg.blink_ms

        if st is State.ATTRACT:
            # The title already sits in the header on every screen; repeating
            # it here just made the board say it twice.
            self.wrapped(surf, eng.cfg.subtitle, top, 56, TEXT)
            if int(t / blink) % 2 == 0:
                self.wrapped(surf, "PRESS THE BUTTON TO PLAY", mid, 68, GREEN)
            self.wrapped(surf, f"{eng.cfg.spins} SPINS. BANK IT, OR PRESS ON.",
                         bot, 34, DIM)
            return

        if st is State.RESOLVE and eng.result.short_circuited:
            flash = RED if int(t / eng.cfg.flash_ms) % 2 == 0 else (120, 10, 20)
            pygame.draw.rect(surf, flash, r, border_radius=14)
            self.wrapped(surf, eng.landed_tile.label, mid, 110, (255, 255, 255))
            self.wrapped(surf, "YOU LOSE IT ALL", bot, 52, (255, 220, 220))
            return

        # bank
        self.wrapped(surf, "YOUR BANK", top, 40, DIM)
        self.wrapped(surf, f"${eng.bank:,}", mid, 130, GOLD)

        if st is State.READY:
            self.wrapped(surf, f"{eng.spins_left} SPINS - PRESS TO START", bot, 40, GREEN)
        elif st is State.SPINNING:
            self.wrapped(surf, "PRESS TO STOP!", bot, 48, GREEN)
        elif st is State.RESOLVE:
            got = eng.landed_tile.label if eng.landed_tile else ""
            self.wrapped(surf, got, bot, 46, TEXT)
        elif st is State.DECISION:
            msg = f"{eng.spins_left} SPINS LEFT   |   [B] BANK IT    [BUTTON] PRESS ON"
            self.wrapped(surf, msg, bot, 34, GREEN if int(t / blink) % 2 == 0 else TEXT)
        elif st is State.GAME_OVER:
            if eng.result.short_circuited:
                self.wrapped(surf, "SHORT CIRCUITED!", bot, 48, RED)
            else:
                self.wrapped(surf, f"BANKED ${eng.result.banked:,}!", bot, 48, GREEN)

    # ---- frame -------------------------------------------------------
    def draw(self, screen: pygame.Surface, eng: Engine, t: float) -> None:
        c = self.canvas
        c.fill(BG)

        self.text(c, eng.cfg.title, VW // 2, 68, 74, GOLD)

        show_light = eng.state in (State.SPINNING, State.ATTRACT)
        lit_pos = eng.light_pos
        if eng.state in (State.RESOLVE, State.DECISION, State.GAME_OVER):
            lit_pos = eng.landed_pos if eng.landed_pos is not None else -1
            show_light = eng.landed_pos is not None

        for i, (col, row) in enumerate(RING):
            self.draw_tile(c, cell_rect(col, row), eng.board.tile_at(i),
                           show_light and i == lit_pos, t)

        self.draw_center(c, eng, t)

        self.text(c, "F1 admin    ESC quit", VW // 2, VH - 26, 24, DIM)

        _blit_scaled(screen, c)


def _blit_scaled(screen: pygame.Surface, canvas: pygame.Surface) -> None:
    sw, sh = screen.get_size()
    scale = min(sw / VW, sh / VH)
    w, h = int(VW * scale), int(VH * scale)
    screen.fill((0, 0, 0))
    screen.blit(pygame.transform.smoothscale(canvas, (w, h)),
                ((sw - w) // 2, (sh - h) // 2))
