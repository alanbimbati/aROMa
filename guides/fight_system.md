# ⚔️ Sistema di Combattimento

Benvenuto nel sistema di combattimento di aROMa RPG! Qui troverai tutto ciò che devi sapere per affrontare i nemici e sopravvivere.

## 📊 Statistiche Base

Ogni personaggio ha 3 statistiche principali:

1.  **❤️ Salute (HP)**: La tua vita. Se scende a 0, sei esausto e non puoi combattere finché non recuperi.
2.  **💙 Mana (MP)**: Energia magica usata per gli Attacchi Speciali.
3.  **⚔️ Danno Base**: Il danno fisico che infliggi con un attacco normale.

### Statistiche Avanzate (Allocabili)
4.  **🛡️ Resistenza**: Riduce i danni subiti (1% per punto allocato, MAX 75%)
5.  **💥 Critico**: Probabilità di infliggere danno critico (1% per punto allocato)
6.  **⚡ Velocità**: Determina l'ordine di attacco e la frequenza

## 🥊 Come Combattere

Quando appare un nemico (Mob o Boss), hai due opzioni:

1.  **Attacco Normale**: Infligge danni basati sul tuo Danno Base + un valore casuale (10-30). Non costa nulla.
2.  **Attacco Speciale**: Infligge molti più danni ma consuma Mana. Il danno e il costo dipendono dal personaggio selezionato (Grado).

### Formule di Danno

#### Attacco Normale
```
Danno Finale = (Danno Base + Random(10, 30)) × Moltiplicatore Critico
```

#### Attacco Speciale
```
Danno Finale = (Danno Base + Danno Skill Personaggio) × Moltiplicatore Critico
```

#### Critico
*   **Probabilità Base**: 5% + (Punti Critico × 1%)
*   **Moltiplicatore**: 1.5x (o superiore per alcuni personaggi)

#### Resistenza
```
Danno Subito = Danno Nemico × (1 - Resistenza%)
```

Esempio: Con 20% resistenza, un attacco da 100 danni diventa 80.

## 🛡️ Nemici

I nemici hanno diverse caratteristiche:
*   **Livello**: Determina la loro forza.
*   **Salute**: I punti vita che devi azzerare.
*   **Velocità**: Determina chi attacca per primo (in futuro).
*   **Resistenza**: Riduce il danno subito (in percentuale).

## 💀 Morte e Recupero

Se la tua salute scende a 0:
*   Non puoi più attaccare.
*   Devi aspettare il recupero automatico giornaliero (20% HP) o usare una **Pozione di Cura**.
*   Puoi acquistare pozioni nel Negozio (`/shop`).

## 💡 Consigli
*   Usa gli Attacchi Speciali contro i Boss o nemici forti.
*   Tieni d'occhio il Mana! Usa le **Pozioni Mana** se finisci l'energia.
*   Aumenta le tue statistiche salendo di livello e assegnando i Punti Statistica (`/stats`).
