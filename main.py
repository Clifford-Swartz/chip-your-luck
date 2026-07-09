"""CHIP YOUR LUCK - entry point.

  python main.py              fullscreen (per config.json)
  python main.py --windowed   force a window, handy while developing
"""
import sys

import pygame

from game.admin import open_admin
from game.audio import Audio
from game.config import Config
from game.engine import Engine
from game.paths import ensure_dirs
from game.render import Renderer, VW, VH

WINDOWED_SIZE = (1280, 720)


def keymap(cfg: Config) -> dict[int, str]:
    """config key names -> action, resolved to pygame key codes."""
    out: dict[int, str] = {}
    for action, names in cfg.keys.items():
        for name in names:
            try:
                out[pygame.key.key_code(name)] = action
            except ValueError:
                print(f"[keys] unknown key name {name!r} for action {action!r}")
    return out


def make_screen(cfg: Config, force_windowed: bool) -> pygame.Surface:
    if cfg.fullscreen and not force_windowed:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)


def run_admin(cfg: Config, force_windowed: bool):
    """Drop the display, run tkinter, rebuild. Returns (screen, renderer, cfg)."""
    pygame.display.quit()
    saved = open_admin(cfg)
    if saved:
        cfg = Config.load()

    pygame.display.init()
    pygame.display.set_caption(cfg.title)
    screen = make_screen(cfg, force_windowed)
    return screen, Renderer(), cfg


def main() -> int:
    force_windowed = "--windowed" in sys.argv
    ensure_dirs()
    cfg = Config.load()

    pygame.init()
    pygame.display.set_caption(cfg.title)
    screen = make_screen(cfg, force_windowed)
    pygame.mouse.set_visible(False)

    renderer = Renderer()
    audio = Audio()
    eng = Engine(cfg)

    clock = pygame.time.Clock()
    keys = keymap(cfg)
    t = 0.0
    running = True

    while running:
        dt = clock.tick(60)
        t += dt

        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                running = False
            elif evt.type == pygame.KEYDOWN:
                action = keys.get(evt.key)
                if action == "quit":
                    running = False
                elif action == "admin":
                    screen, renderer, cfg = run_admin(cfg, force_windowed)
                    audio.reload()
                    eng = Engine(cfg)
                    keys = keymap(cfg)
                    pygame.mouse.set_visible(False)
                elif action in ("buzzer", "start"):
                    eng.press_buzzer()
                elif action == "bank":
                    eng.press_bank()

        eng.update(dt)
        for name in eng.drain_events():
            audio.play(name)

        renderer.draw(screen, eng, t)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
