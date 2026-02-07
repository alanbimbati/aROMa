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

1. **Esperienza (Exp)**: Necessaria per salire di livello.
2. **Punti (Wumpa)**: Moneta di gioco per comprare pozioni, personaggi e item.
3. **Risorse Grezze**: Frammenti di metallo, cristalli e altri materiali necessari per la Raffineria.
   • **Mob Comuni**: Possibilità di drop basata sul livello e fortuna.
   • **Boss**: Garantiscono sempre il drop di risorse rare ed epiche.
