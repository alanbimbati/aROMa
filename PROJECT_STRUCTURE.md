# Aroma RPG Bot - Project Structure

## 📁 Directory Structure

```
aroma/
├── main.py                 # Main bot entry point
├── database.py            # Database configuration
├── settings.py            # Bot configuration
├── requirements.txt       # Python dependencies
│
├── models/               # Database models
│   ├── user.py          # User and admin models
│   ├── system.py        # Character, transformation models
│   ├── game.py          # Game-related models
│   └── pve.py           # PvE (mob, raid) models
│
├── services/            # Business logic
│   ├── user_service.py
│   ├── character_service.py
│   ├── transformation_service.py
│   ├── pve_service.py
│   ├── item_service.py
│   ├── game_service.py
│   ├── shop_service.py
│   ├── wish_service.py
│   └── stats_service.py
│
├── data/                # CSV data files
│   ├── characters.csv
│   ├── transformations.csv
│   ├── potions.csv
│   └── mobs.csv
│
├── images/              # Character images
│   └── characters/
│
├── scripts/             # Utility scripts
│   ├── setup/          # Initial setup scripts
│   │   ├── populate_characters.py
│   │   ├── populate_transformations.py
│   │   └── update_characters_from_csv.py
│   │
│   ├── migrations/     # Database migrations
│   │   ├── migrate_combat_system.py
│   │   ├── migrate_user_characters.py
│   │   └── ...
│   │
│   └── maintenance/    # Maintenance scripts
│       ├── backup.py
│       ├── verify_images.py
│       └── ...
│
├── docs/               # Documentation
│   ├── README.md
│   └── guides/
│       ├── CHARACTER_IMAGES_GUIDE.md
│       ├── IMAGE_GENERATION_PROMPTS.md
│       ├── IMAGE_PRIORITY_LIST.md
│       └── INTEGRATION_GUIDE.md
│
└── auto_generate_images.py  # 🎨 IMAGE GENERATOR (keep in root)
```

## 🎨 Image Generation Script

### **`auto_generate_images.py`** - Automatic Image Generator

**Location**: Root directory (for easy access)

**What it does**:
1. ✅ Creates placeholder images for ALL 254 characters
2. 🎨 Attempts to generate real images using AI
3. ⏰ Automatically waits when quota is exhausted
4. 🔄 Resumes generation after quota reset
5. 📊 Shows progress and statistics

**How to use**:
```bash
# Run in background (recommended)
python3 auto_generate_images.py &

# Or run in foreground to see progress
python3 auto_generate_images.py
```

**Features**:
- Creates nice placeholder images with character names
- Generates images in priority order (early game first)
- Handles API quota limits gracefully
- Auto-retry logic with exponential backoff
- Progress tracking and logging

**Output**:
- Placeholder images: `images/characters/{character_name}.png`
- Real images replace placeholders when generated
- Log file: Shows generation progress

## 🚀 Quick Start Scripts

### Setup (First Time)
```bash
# 1. Update database with new characters
python3 scripts/setup/update_characters_from_csv.py

# 2. Populate transformations
python3 scripts/setup/populate_transformations.py

# 3. Generate character images
python3 auto_generate_images.py &
```

### Daily Operations
```bash
# Start the bot
python3 main.py

# Check image generation status
ps aux | grep auto_generate_images

# Verify database
python3 scripts/maintenance/verify_images.py
```

## 📝 Key Files

| File | Purpose |
|------|---------|
| `main.py` | Bot entry point, command handlers |
| `auto_generate_images.py` | **IMAGE GENERATOR** - Creates all character images |
| `database.py` | Database connection and setup |
| `settings.py` | Bot token, configuration |
| `scripts/setup/update_characters_from_csv.py` | Update DB from CSV |
| `scripts/setup/populate_transformations.py` | Load transformations |

## 🎯 Current Status

- ✅ 254 characters in database
- ✅ 248 placeholder images created
- 🔄 Real image generation in progress
- ✅ Transformation system ready
- ✅ Sunday reset removed
