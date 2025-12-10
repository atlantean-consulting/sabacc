# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sabacc con i Tarocchi - A Python card game combining poker-style betting, rummy-style draws, and blackjack-style scoring using a 78-card Tarot deck. Target hand value is 23 (absolute value).

## Commands

```bash
# Run CLI version
python3 sabacc_main.py

# Run GUI version (Tkinter) - two options:
python3 sabacc_gui_launcher.py
# OR from gui directory:
python3 gui/sabacc_gui.py

# Run tests
python3 test_sabacc.py
```

No external dependencies - uses only Python standard library (including tkinter).

## Architecture

### File Structure

**Core Game Engine:**
- **sabacc_game.py** - Core game engine: `Deck`, `Player`, `GameState` classes, hand scoring, name loading
- **sabacc_main.py** - CLI/text-based interface and main game loop
- **sabacc_ai.py** - AI player decision logic (`get_simple_ai_action()`)
- **sabacc_trionfi.py** - Special Trionfi card effects system (`TrionfiEffect` class)
- **test_sabacc.py** - Test suite (`run_tests()`)

**GUI Package (`gui/`):**
- **gui/sabacc_gui.py** - Tkinter GUI with `SabaccGUI` and `CardWidget` classes
- **gui/__init__.py** - Package initialization
- **sabacc_gui_launcher.py** - Convenience launcher script at root level

**Data Files:**
- **player_names.md** - Star Wars character names for AI opponents (94+ names)

### Key Concepts

**Card System:**
- 22 Trionfi (trump cards, 0-21) + 56 regular cards (4 suits x 14 ranks)
- Suits: Wands (W), Cups (C), Swords (S), Disks (D)
- Card tuple format: `(rank, suit)` e.g., `('5', 'W')`, `('12', 'T')` for Trionfi

**Hand Scoring (`calculate_hand_value()`):**
- Goal: Get absolute value closest to 23 without exceeding
- Aces: 1 or 11 (optimized), Face cards: P=11, N=12, Q=13, K=14
- Most Trionfi: 0 points; some have negative values
- Busted if |value| > 23

**Game Flow (`GameState.play_hand()`):**
1. Collect blinds
2. Deal 2 cards per player + 3 community (flop)
3. Three betting rounds (flop/turn/river) with draw options
4. Showdown - closest to 23 wins

**Player Actions (dict format):**
```python
{'bet_action': 'call'|'fold'|'raise', 'draw_action': 'draw_pile'|'discard_pile'|'community'|None, 'discard_index': int|None}
```

### Type Aliases (from sabacc_game.py)

```python
Card = Tuple[str, str]  # (rank, suit)
Hand = List[Card]
```

### Card Piles in GameState

- `draw_pile` - Face-down draw pile
- `discard_pile` - Face-up discards
- `community_cards` - Shared cards (flop/turn/river)
- `removed_pile` - Cards permanently out of play
