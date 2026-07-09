# CHIP YOUR LUCK

A trade-show prize board. A light races around 18 tiles, you press a button to
stop it, and then you decide: bank what you've won, or press on and risk a
**Short Circuit** that wipes your bank to zero.

Original board art, original names, no theme music. The bank-or-press mechanic
is a mechanic, not a copyrightable thing.

## Download

Grab the latest `ChipYourLuck-windows.zip` from
[Releases](../../releases/latest), unzip it anywhere, and run
`ChipYourLuck.exe`. No install, no Python needed.

The exe isn't code-signed, so Windows SmartScreen will show a blue
"Windows protected your PC" box the first time. Click **More info** →
**Run anyway**.

## Running from source

```
pip install -r requirements.txt
python main.py              # fullscreen, per config.json
python main.py --windowed   # 1280x720 window, for development
```

## Building the executable

```
python build.py
```

Produces `dist/ChipYourLuck/`. Zip that whole folder — the `.exe` needs the
`_internal/` folder next to it. `config.json` and `assets/` sit beside the exe
on purpose, so a booth operator can swap prize images and retune the odds
without a rebuild.

## Controls

| Key | Does |
| --- | --- |
| `Space` / `Enter` | Start, stop the board, press on |
| `B` | Bank your winnings and end the game |
| `F1` | Admin panel |
| `Esc` | Quit |

All bindings live under `keys` in `config.json`. USB arcade buttons enumerate as
keyboards, so wiring one up is a config edit, not a code change.

## Admin panel (F1)

The game drops out of fullscreen, the panel opens, and the game resumes when you
close it.

**Prizes tab** — add, edit, and delete tiles. *Upload...* copies an image into
`assets/prizes/` for you. Set **Qty** to `0` for unlimited; any other number is
real stock that counts down as it's won, and the prize disappears from the board
once it hits zero.

**Settings tab** — title, spins per player, how many of the 18 tiles are Short
Circuits, and how fast the light moves. Faster light = harder game.

## Tile types

- `prize` — adds its value to your bank.
- `prize_plus_spin` — adds its value *and* grants an extra spin.
- `short_circuit` — bank to zero, game over. You don't create these by hand;
  set how many you want on the Settings tab and they're placed randomly.

## Results

Every completed game appends a row to `results.csv` next to the exe: timestamp,
amount banked, spins used, whether they short-circuited, and which prizes they
hit. Open it in Excel at the end of the day.

## Notes for the booth

- Inventory counts are held in memory for the session. If you restart the exe,
  quantities reset to whatever `config.json` says. Save from the admin panel to
  persist the current counts.
- With 3 Short Circuits on an 18-tile board, each spin is about a 1-in-6 loss.
  Three of those in a row is roughly a 58% chance of surviving a full game — a
  good feel. Raise the count to make it meaner.
- `attract_idle_seconds` sends an abandoned game back to the attract screen so
  the board is never sitting dead in front of a line.
