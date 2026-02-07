# ⚔️ Sistema di Combattimento

Benvenuto nel sistema di combattimento di aROMa RPG! Qui troverai tutto ciò che devi sapere per affrontare i nemici e sopravvivere.

## 📊 Statistiche Base

Ogni personaggio parte con dei valori minimi di sistema:

1. **❤️ Salute (HP)**: Base sistema: **100 HP**
2. **💙 Mana (MP)**: Base sistema: **50 MP**
3. **⚔️ Danno Base**: Base sistema: **10**

**SUGGERIMENTO**: Puoi aumentare queste statistiche equipaggiando personaggi più forti, assegnando i punti guadagnati livellando o indossando equipaggiamento potente.

**Statistiche Avanzate (Allocabili)**
4. **🛡️ Resistenza**: Riduce i danni subiti (1% per punto allocato, MAX 75%).
5. **💥 Critico**: Probabilità di infliggere danno critico (1% per punto allocato).
6. **⚡ Velocità**: Riduce il tempo di ricarica (Cooldown) tra un attacco e l'altro.
   • **Base**: 0 punti velocità = 60 secondi di cooldown.
   • **Scaling**: Ogni punto di velocità riduce il cooldown del **5%**.
   • **Formula**: 60 / (1 + Velocità x 0.05) secondi.
   • **Esempio**: Con 20 punti velocità, il cooldown si dimezza a **30 secondi**.

## 🥊 Come Combattere

Quando appare un nemico (Mob o Boss), hai tre opzioni:

1. **Attacco Normale**: Infligge danni basati sul tuo Danno Base + un valore casuale (10-30). Non costa nulla.

2. **Attacco Speciale**: Infligge molti più danni ma consuma Mana. Il danno e il costo dipendono dal personaggio selezionato.

3. **Attacco AoE (Area of Effect)**: Colpisce **tutti** i nemici attivi nel gruppo contemporaneamente.
   • **Danno**: 70% al bersaglio principale, 50% agli altri (fino a 5 nemici totali).
   • **Costo**: 0 Mana (Gratis).
   • **Cooldown**: Il tempo di ricarica è raddoppiato rispetto a un attacco normale.
   • **Utilità**: Ideale quando ci sono molti nemici deboli. Disponibile solo con almeno 2 nemici.

**Formule di Danno**

**Attacco Normale**
Danno Finale = (Danno Base + Random(10, 30)) × Moltiplicatore Critico

**Attacco Speciale**
Danno Finale = (Danno Base + Danno Skill Personaggio) × Moltiplicatore Critico

**Attacco AoE**
Danno Finale = (Danno Base × 0.7) × Moltiplicatore Critico (su ogni bersaglio)

**Critico**
• **Probabilità Base**: 5% + (Punti Critico × 1%)
• **Moltiplicatore**: 1.5x (o superiore per alcuni personaggi)

**Resistenza**
Danno Subito = Danno Nemico × (1 - Resistenza%)
Esempio: Con 20% resistenza, un attacco da 100 danni diventa 80.

## 🛡️ Nemici

I nemici hanno diverse caratteristiche:
• **Livello**: Determina la loro forza.
• **Salute**: I punti vita che devi azzerare.
• **Velocità**: Determina chi attacca per primo.
• **Resistenza**: Riduce il danno subito (in percentuale).

## 💀 Morte e Recupero

Se la tua salute scende a 0:
• Non puoi più attaccare.
• Devi aspettare il recupero automatico giornaliero (20% HP) o usare una **Pozione di Cura**.
• Puoi acquistare pozioni nel Negozio con il comando /shop.

## 💰 Ricompense e Drop

Ogni vittoria in combattimento ti garantisce diverse ricompense:

### 🌟 Esperienza (EXP)

L'esperienza è calcolata in base a diversi fattori:

**Formula Base:**
```
EXP = (Livello Nemico × 5) × (Tier Difficoltà ^ 1.8) × Contributo
```

**Tier Difficoltà:**
- **Tier 1**: Mob deboli e comuni (×1 EXP)
- **Tier 2**: Mob standard (×3.5 EXP)
- **Tier 3**: Mob forti (×6.7 EXP)
- **Tier 4**: Mob elite (×10.6 EXP)
- **Tier 5-6**: Mini-boss (×18-25 EXP)
- **Tier 7-8**: Boss principali (×35-50 EXP)

**Contributo:** L'EXP totale del nemico viene distribuita in base al danno inflitto.
- Se infliggi il 50% del danno totale, ricevi il 50% dell'EXP
- Chi dà il colpo finale non riceve bonus extra
- Variazione casuale: ±10% sull'EXP finale

**Esempi:**
- Cell Junior (Lv 9, Tier 4): ~475 EXP circa
- Boss Lv 20 (Tier 7): ~2,400 EXP circa
- Mob comune Lv 5 (Tier 1): ~25 EXP circa

**NOTA**: L'EXP necessaria per salire di livello aumenta progressivamente. A livelli alti (50+), servono decine di mob per leveluppare.

### 💎 Punti (Wumpa)

I Frutti Wumpa 🍑 sono la moneta di gioco:
- **Formula**: Danno inflitto × 0.05 × Tier Difficoltà
- **Uso**: Comprare pozioni, personaggi e item dal negozio (/shop)

### 🔩 Risorse Grezze

Frammenti di metallo, cristalli e altri materiali:
- **Mob Comuni**: Drop basato su livello e fortuna
- **Boss**: Garantiscono sempre drop di risorse rare ed epiche
- **Utilizzo**: Necessarie per la Raffineria e Crafting

### ✨ Cristalli aROMa (Premium)

I **Cristalli aROMa** sono una valuta premium esclusiva utilizzata per:
- **Skin personalizzate** per personaggi
- **Effetti visivi** speciali
- **Oggetti cosmetici** unici

**Come ottenerli:**
- Supportando il progetto tramite **donazioni**
- Eventi speciali e ricompense stagionali
- Premi esclusivi per la community

**NOTA**: I Cristalli aROMa NON danno vantaggi di gioco - sono puramente estetici!
