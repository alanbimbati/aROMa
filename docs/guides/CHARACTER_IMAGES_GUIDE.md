# Guida Immagini Personaggi

## Immagini Generate

Ho creato la cartella `images/characters/` e generato le seguenti immagini:
- ✅ `goku.png` - Goku (Dragon Ball)
- ✅ `naruto.png` - Naruto Uzumaki

## Come Aggiungere Altre Immagini

### 1. Formato Raccomandato
- **Dimensioni**: 512x512 px o superiore (quadrato)
- **Formato**: PNG con sfondo trasparente (preferito) o JPG
- **Stile**: Portrait del personaggio, stile artwork professionale

### 2. Naming Convention
Salva le immagini in `images/characters/` con il nome esatto del personaggio in minuscolo:
```
images/characters/sonic.png
images/characters/mario.png
images/characters/link.png
images/characters/crash_bandicoot.png
images/characters/spyro.png
```

### 3. Mapping nel Codice

Le immagini vengono caricate automaticamente nel `handle_choose_character` tramite il character_service.

Per aggiungere manualmente mappings personalizzati, modifica in `main.py` la funzione `handle_info`:

```python
image_map = {
    "Crash Bandicoot": "images/characters/crash_bandicoot.png",
    "Spyro": "images/characters/spyro.png",
    "Sonic": "images/characters/sonic.png",
    "Mario": "images/characters/mario.png",
    "Link": "images/characters/link.png",
    "Goku": "images/characters/goku.png",
    "Naruto": "images/characters/naruto.png",
    "Cloud Strife": "images/characters/cloud.png",
    "Samus Aran": "images/characters/samus.png",
    "Mega Man": "images/characters/megaman.png",
    "Pikachu": "images/characters/pikachu.png",
    "Ryu": "images/characters/ryu.png",
    "Kratos": "images/characters/kratos.png",
    # ... aggiungi altri
}
```

### 4. Personaggi Prioritari

Questi sono i personaggi più usati, crea immagini per loro per primi:
1. Crash Bandicoot (ID 1)
2. Spyro (ID 2)
3. Sonic (ID 3)
4. Mario (ID 4)
5. Link (ID 5)
6. Goku (ID 6) - ✅ FATTO
7. Naruto (ID 7) - ✅ FATTO
8. Pikachu (ID 11)
9. Kratos (ID 13)
10. Master Chief (ID 16)

### 5. Trovare Immagini

**Opzioni:**
1. **Fan Art**: Cerca su DeviantArt, ArtStation (con licenza appropriata)
2. **AI Generation**: Usa DALL-E, Midjourney, Stable Diffusion
3. **Official Art**: Artwork ufficiale dei giochi (verifica licenze)
4. **Wikipedia/Wikia**: Spesso hanno immagini utilizzabili

**Prompt per AI Generation:**
```
Portrait of [CHARACTER NAME], [key visual features], vibrant [style] art, professional character artwork, dynamic pose
```

### 6. Automatizzazione

Una volta che hai le immagini nella cartella, il bot:
1. Tenta di mostrarle quando viene equipaggiato il personaggio
2. Salva il `telegram_file_id` dopo il primo invio
3. Riutilizza il `file_id` per invii futuri (più veloce)

### 7. Testing

Dopo aver aggiunto un'immagine:
```bash
# Verifica che esista
ls -lh images/characters/goku.png

# Testa nel bot
# Equipaggia il personaggio e usa /profile o "info"
```

## Note
- Il sistema è già configurato per cercare automaticamente le immagini
- Il primo invio dell'immagine la carica su Telegram e salva il file_id
- I successivi invii usano il file_id salvato (istantaneo)
- Se un'immagine non esiste, il bot funziona comunque (solo testo)
