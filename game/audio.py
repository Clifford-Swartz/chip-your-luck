"""Optional sound. Any file that isn't there is simply silent — the game
never fails to start because a .wav is missing.

Drop files named after the engine events into assets/sounds/:
  hop, prize, bonus_spin, short_circuit, bank, game_start, game_over
"""
import pygame

from .paths import SOUNDS_DIR

EVENTS = ("hop", "prize", "bonus_spin", "short_circuit",
          "bank", "game_start", "game_over")
EXTS = (".ogg", ".wav", ".mp3")


class Audio:
    def __init__(self) -> None:
        self.enabled = True
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
        except pygame.error as exc:
            print(f"[audio] disabled: {exc}")
            self.enabled = False
            return
        self.reload()

    def reload(self) -> None:
        if not self.enabled:
            return
        self.sounds.clear()
        for name in EVENTS:
            for ext in EXTS:
                path = SOUNDS_DIR / f"{name}{ext}"
                if path.exists():
                    try:
                        self.sounds[name] = pygame.mixer.Sound(str(path))
                    except pygame.error as exc:
                        print(f"[audio] could not load {path}: {exc}")
                    break

    def play(self, name: str) -> None:
        snd = self.sounds.get(name)
        if snd is not None:
            snd.play()
