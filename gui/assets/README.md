# Sabacc GUI Assets

This directory contains graphical assets for the Sabacc GUI.

## Directory Structure

- **cards/** - Card face images (78 cards + 1 back)
  - Naming convention: `{rank}_{suit}.png` (e.g., `5_W.png`, `12_T.png`)
  - Card back: `card_back.png`
  - Recommended size: 71x96 pixels (matches current CardWidget dimensions)
  - Format: PNG with transparency

- **chips/** - Poker chip images for pot display
  - Naming convention: `chip_{value}.png` (e.g., `chip_1.png`, `chip_100.png`)
  - Required denominations: 1, 5, 10, 25, 100
  - Recommended size: 30x30 pixels (circular)
  - Format: PNG with transparency
  - Colors (programmatic fallback):
    - 1 credit: White (#FFFFFF)
    - 5 credits: Red (#FF0000)
    - 10 credits: Blue (#0000FF)
    - 25 credits: Green (#00AA00)
    - 100 credits: Black (#000000)

- **avatars/** - Character avatar images (8-bit style planned for v2.0)
  - Naming convention: `{character_name}.png` (e.g., `han_solo.png`)
  - Recommended size: 64x64 or 128x128 pixels
  - Format: PNG with transparency

- **backgrounds/** - Table/background textures
  - `table_felt.png` - Green felt texture for main play area
  - Format: PNG or JPG

## Current Implementation

The GUI uses a **hybrid approach with automatic fallback**:
- **If images exist** in `cards/`: Uses PNG images
- **If images don't exist**: Falls back to programmatic drawing with Unicode symbols
- Images are cached after first load for performance
- No external dependencies required!

**Current fallback rendering:**
- Card faces: Unicode symbols for suits, text for ranks
- Card backs: Solid color (#8B0000) with Unicode symbol
- Background: Solid green (#008000)

## How to Add Graphics

**The system is already implemented!** Just add PNG files and they'll be used automatically:

1. **Create or obtain card images** (71x96 pixels, PNG format)
2. **Name them correctly**: `{rank}_{suit}.png`
   - Examples: `5_W.png`, `K_C.png`, `0_T.png`, `card_back.png`
3. **Place in `gui/assets/cards/` directory**
4. **Run the game** - images will load automatically!

### All 78 Card Filenames Needed:

**Trionfi (22 cards):**
`0_T.png` through `21_T.png`

**Numbered cards (40 cards):**
`1_W.png` through `10_W.png` (Wands)
`1_C.png` through `10_C.png` (Cups)
`1_S.png` through `10_S.png` (Swords)
`1_D.png` through `10_D.png` (Disks)

**Face cards (16 cards):**
`P_W.png`, `N_W.png`, `Q_W.png`, `K_W.png` (Wands: Page, Knight, Queen, King)
`P_C.png`, `N_C.png`, `Q_C.png`, `K_C.png` (Cups)
`P_S.png`, `N_S.png`, `Q_S.png`, `K_S.png` (Swords)
`P_D.png`, `N_D.png`, `Q_D.png`, `K_D.png` (Disks)

**Card back:**
`card_back.png`

### Tips for Creating Card Graphics

- Use transparent PNG backgrounds for best results
- Keep aspect ratio at 71:96 (standard card proportion)
- Value badges will overlay automatically if enabled
- Test with a few cards first before creating all 78!
- You can mix programmatic and image cards - missing images will use fallback
