# 📊 Allocazione Statistiche

Salendo di livello, il tuo personaggio diventa più forte. Oltre all'aumento automatico delle statistiche base, ottieni Punti Statistica da assegnare manualmente.

## 📈 Punti per Livello

Ogni volta che sali di livello, ricevi 2 Punti Statistica da assegnare come preferisci.
• Formula Totale: `Livello × 2`. Al livello 50 avrai quindi 100 punti totali da distribuire.

## 🛡️ Calcolo delle Statistiche

Il tuo potere cresce in due modi: automaticamente salendo di livello e manualmente assegnando punti.

1. **Progressione Automatica (Base Sistema)**
Mentre scali i livelli, il tuo corpo si adatta alla fatica. Ogni livello garantisce:
• ❤️ Salute (HP): +2 HP per ogni livello.
• 💙 Mana (MP): +1 MP per ogni livello.
• ⚔️ Danno: +0.5 Danno per ogni livello (1 punto ogni 2 livelli).

2. **Formula Finale Trasparente**
Il calcolo totale che vedi nel profilo è dato da:
`Stat Totale = [Basi + (Livello-1) × Crescita] + Bonus Personaggio + Allocazioni + Bonus Equipaggiamento`

• **Basi Iniziali**: 20 HP, 20 MP, 5 Dmg.
• **Bonus Personaggio**: I valori fissi del personaggio scelto (es. Goten, Goku).
• **Allocazioni**: I punti che assegni tu (1pt = 10 HP, 5 Mana, 2 Danno, ecc.).
• **Equipaggiamento**: Bonus di armi e armature (Gear).

> [!NOTE]
> La progressione automatica serve a bilanciare la difficoltà crescente dei mostri nei Dungeon e nel mondo di gioco. I punti che allochi tu sono il surplus che definisce la tua specializzazione (Tank, DPS, ecc.).

## 🛠️ Come Assegnare i Punti

Usa il comando /stats per aprire il menu di allocazione. Puoi spendere i tuoi punti in:

### Statistiche Base
1. ❤️ **Salute Max (+10 HP)**: Aumenta la tua vita massima. Utile per sopravvivere più a lungo.
2. 💙 **Mana Max (+5 MP)**: Aumenta il tuo mana massimo. Utile per usare più Attacchi Speciali.
3. ⚔️ **Danno Base (+2 Danno)**: Aumenta il danno dei tuoi attacchi fisici e speciali.

### Statistiche Avanzate
4. 🛡️ **Resistenza (+1%)**: Riduce il danno subito. Ogni punto = 1% riduzione danni. MAX: 75%
5. 💥 **Critico (+1%)**: Aumenta la probabilità di colpo critico. Ogni punto = 1% probabilità.
6. ⚡ **Velocità (+5%)**: Riduce il tempo di ricarica degli attacchi. Ogni punto riduce il cooldown del 5%.
   Formula: `Tempo = 60 / (1 + Punti x 0.05)`
   Esempio: 20 punti dimezzano il tempo di attesa!

## 🔄 Reset Statistiche

Hai sbagliato ad assegnare i punti? Nessun problema!
• Puoi resettare le tue statistiche dal menu /stats.
• Tutti i punti spesi ti verranno restituiti e potrai riassegnarli da capo.

## 💡 Build Consigliate

### 🗡️ Ladro (Rogue)
Focus: **Danno + Velocità**
• Colpisci velocemente e forte
• Ideale per: Burst damage, primo attacco

### 🛡️ Tank
Focus: **Salute + Resistenza**
• Massima sopravvivenza
• Ideale per: Boss fight lunghe, tanking

### 🔮 Stregone (Sorcerer)
Focus: **Mana + Danno**
• Massimo danno magico
• Ideale per: Attacchi speciali devastanti

### ⚡ Mago (Mage)
Focus: **Mana + Velocità**
• Cast frequenti e veloci
• Ideale per: DPS sostenuto, controllo

### ⚖️ Bilanciato
Focus: **Mix equilibrato**
• Versatilità in ogni situazione
• Ideale per: Giocatori che vogliono provare tutto
