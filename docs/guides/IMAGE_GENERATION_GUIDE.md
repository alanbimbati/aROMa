# 🎨 Image Generation Guide

## Problema Attuale

Lo script `auto_generate_images.py` crea **placeholder** (immagini con testo) perché:
- Non ha accesso diretto all'API `generate_image` di Gemini
- L'API `generate_image` è disponibile solo tramite l'interfaccia Antigravity, non da Python standalone

## Soluzioni Disponibili

### ✅ Soluzione 1: Comando Telegram `/generate_images`

**File**: `image_generation_command.py`

**Come funziona**:
1. Aggiungi il comando al bot
2. Manda `/generate_images` da Telegram
3. Il bot genera 10 immagini alla volta
4. Ripeti il comando per continuare

**Setup**:
```python
# In main.py, aggiungi:
from image_generation_command import register_image_generation_command

# Dopo aver inizializzato il bot:
register_image_generation_command(bot, admin_ids=[TUO_TELEGRAM_ID])
```

**Uso**:
```
/generate_images
```

### ✅ Soluzione 2: Script SSH/Termux

**File**: `auto_generate_images.py`

**Come funziona**:
1. Connettiti via SSH al server
2. Esegui: `python3 auto_generate_images.py`
3. Lo script crea placeholder per tutti
4. (Opzionale) Integra con API esterna

**Attualmente**:
- ✅ Crea 251 placeholder
- ❌ Non genera immagini AI (serve integrazione API)

### 🔧 Soluzione 3: Integrazione API Esterna

Per generare immagini AI vere, puoi integrare:

**Opzione A - DALL-E (OpenAI)**:
```python
import openai

def generate_with_dalle(prompt, output_path):
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response['data'][0]['url']
    # Download and save
```

**Opzione B - Stable Diffusion (Stability AI)**:
```python
import stability_sdk

def generate_with_sd(prompt, output_path):
    # Use Stability AI API
```

**Opzione C - Midjourney (via Discord Bot)**:
- Più complesso, richiede bot Discord

## 📊 Stato Attuale

- ✅ 251 placeholder creati
- ✅ Struttura file pronta
- ✅ Script funzionante
- ⏳ Serve integrazione API per immagini AI

## 🎯 Raccomandazione

**Per ora**: Usa i placeholder! Funzionano perfettamente nel bot.

**Futuro**: 
1. Integra DALL-E o Stable Diffusion
2. Oppure genera immagini manualmente e caricale
3. Oppure usa il comando `/generate_images` quando disponibile

## 💡 Quick Fix

Se vuoi immagini vere subito:
1. Trova immagini online dei personaggi
2. Rinominale correttamente (es. `goku.png`)
3. Mettile in `images/characters/`
4. Il bot le userà automaticamente!

## 📝 Nome File Corretto

Il nome file deve essere:
- Tutto minuscolo
- Spazi sostituiti con `_`
- Apostrofi rimossi
- Estensione `.png`

Esempi:
- "Goku SSJ" → `goku_ssj.png`
- "Mario" → `mario.png`
- "The One Above All" → `the_one_above_all.png`
