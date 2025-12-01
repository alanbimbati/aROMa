# Migration Guide: Aroma Bot v2.0

This guide documents the steps required to migrate the production environment to the new version of the Aroma Bot.

## 1. New Dependencies
No mandatory new dependencies.
- Optional: `google-generativeai` (for Gemini image generation)
  ```bash
  pip install google-generativeai
  ```

## 2. File Structure Changes

### New Directories
- `legacy/` (contains deprecated files)
- `scripts/setup/`
- `scripts/maintenance/`
- `services/` (expanded)

### New Files to Copy
Ensure these files are copied to the production server:

**Core:**
- `main.py` (Updated)
- `services/potion_service.py` (New)
- `services/drop_service.py` (New)
- `services/character_service.py` (Updated)
- `services/item_service.py` (Updated)
- `services/shop_service.py` (Updated)

**Data:**
- `data/potions.csv` (Updated with mana potions)
- `data/characters.csv` (Updated list)
- `data/transformations.csv` (New)

**Scripts:**
- `scripts/setup/track_image_sources.py`
- `scripts/maintenance/replace_placeholders.py`
- `populate_transformations.py`

### Files to Remove/Archive
Move these to `legacy/` or delete:
- `Steam.py`
- `Points.py`
- `model.py` (Old model definition, replaced by `models/` package)

## 3. Database Updates
No raw SQL migration is required for the schema, but you need to populate new tables.

1. **Transformations**:
   Run the population script to load transformations into the DB.
   ```bash
   python3 populate_transformations.py
   ```

2. **Characters**:
   If you have new characters in CSV, run the update script.
   ```bash
   python3 update_characters_from_csv.py
   ```

## 4. Image System Migration

1. **Track existing images**:
   Run this once to index current images.
   ```bash
   python3 scripts/setup/track_image_sources.py
   ```

2. **Upgrade Images (Optional)**:
   If you have a Gemini API key, set it and run the replacement script. Otherwise, it will use Pollinations Flux.
   ```bash
   export GEMINI_API_KEY="your_key_here"
   python3 scripts/maintenance/replace_placeholders.py
   ```

## 5. Configuration Check
- Ensure `BOT_TOKEN` is set.
- Ensure `admin_ids` in `main.py` (or config) includes your ID for admin features.

## 6. Verification Steps
1. **Start Bot**: `python3 main.py`
2. **Check Shop**: Verify "Negozio Pozioni" shows Mana potions.
3. **Check Characters**: Verify navigation has +5/-5 buttons.
4. **Check Drops**: Write in a group chat to verify random drops (TNT/Nitro/Cassa).
