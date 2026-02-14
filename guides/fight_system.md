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

## 🥊 Formule di Combattimento

Per i giocatori più tecnici, ecco come il sistema calcola i risultati delle tue azioni:

### ⚔️ Danno Finale
Il danno non è mai fisso, ma oscilla per rendere ogni turno unico:
- **Attacco Base**: `(Danno Base + Random(10, 30)) × Moltiplicatore Critico`
- **Attacco Speciale**: `(Danno Base + Potenza Skill) × Moltiplicatore Critico`
- **Attacco AoE**: `(Danno Base × 0.70) × Moltiplicatore Critico` (70% al main, 50% agli altri)

### ⚡ Cooldown (Tempo di Ricarica)
La velocità riduce il tempo che devi aspettare tra un attacco e l'altro:
- **Formula**: `60 / (1 + Velocità × 0.05)` secondi.
- **Esempio**: Con 20 punti velocità, il tempo scende da 60 a 30 secondi.

### 🔥 Aggro & Taunt (Minaccia)
I nemici decidono chi attaccare in base alla "Minaccia" generata:
- **Attacco**: Genera minaccia pari al danno inflitto (`1:1`).
- **Difesa (Tank)**: Attivare la difesa moltiplica la tua minaccia attuale per **15x** e imposta un "Taunt" diretto sul mostro per 2 minuti.

---

## 🛡️ Sistema Anti-Farming & Affaticamento

Per mantenere l'equilibrio del mondo di Aura, esistono meccanismi che impediscono lo sfruttamento di nemici troppo deboli.

### 🚫 Penalità di Livello (Anti-Farming)
Affrontare nemici molto più deboli di te riduce drasticamente i guadagni:
- **Condizione**: Se il tuo livello supera quello del mostro di oltre **10 livelli**.
- **Effetto**: 
    - **EXP**: Ridotta del **50%**.
    - **Wumpa**: Ridotti del **75%**.

### 🥱 Affaticamento (Fatigue)
L'uso intensivo delle proprie energie porta a un calo dell'efficienza giornaliera:
- **Soglia**: Dopo aver guadagnato **300 Wumpa** in un singolo giorno.
- **Effetto**: Tutte le ricompense (EXP e Wumpa) subiscono una riduzione del **10%**.
- **Reset**: Il contatore si azzera ogni giorno a mezzanotte.

---

## 🌟 Crescita e Scaling

L'ascesa verso il potere diventa più ardua man mano che ci si avvicina alle vette del mondo:

- **EXP Necessaria**: La quantità di esperienza richiesta per salire segue una curva quadratica (`100 × Livello^2`). 
- **Scaling Alto Livello**: Oltre il livello 50, la curva diventa più ripida per riflettere la rarità dei guerrieri leggendari.
- **Consiglio**: Per livellare in modo efficiente, cerca sempre di affrontare nemici vicini al tuo livello (entro il range di +/- 5 livelli) per massimizzare il bonus di Tier e contributo.

---

## 💰 Ricompense e Drop

Ogni vittoria garantisce ricompense calcolate con precisione:

### 🌟 Esperienza (EXP)
**Formula Base:**
```
EXP = (Livello Nemico × 5) × (Tier Difficoltà ^ 1.8) × Contributo
```
- **Fattore Tier**: I Boss (Tier 7-8) forniscono un moltiplicatore massiccio (fino a 50x) rispetto ai mob comuni.
- **Contributo**: L'EXP totale viene divisa proporzionalmente al danno che hai inflitto al nemico.

### 💎 Punti (Wumpa)
I Frutti Wumpa 🍑 sono calcolati in base all'efficacia del tuo combattimento:
- **Formula**: `Danno inflitto × 0.05 × Tier Difficoltà`.
- **Esempio**: Fare 100 danni a un Boss Tier 8 ti darà molti più Wumpa che farli a un mob Tier 1.
