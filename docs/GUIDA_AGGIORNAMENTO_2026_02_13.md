# Guida all'Aggiornamento: Giardino & Combattimento

Questa guida descrive le nuove funzionalità introdotte per il Giardino e il sistema di Combattimento (Aggro/Parata), incluse le istruzioni per applicare le modifiche sul server DietPi.

## 1. Novità Giardino (Umidità e Marcimento)

Il sistema di coltivazione è ora più dinamico e richiede attenzione costante.

### Meccaniche core:
- **Umidità (💧)**: Ogni pianta ha una percentuale di umidità che cala del **2% ogni 10 minuti**.
- **Irrigazione**: È possibile innaffiare le piante tramite il pulsante **"💦 Irriga"** nel menu del giardino. L'irrigazione riporta l'umidità al 100%.
- **Blocco Crescita**: Se l'umidità scende a **0%**, la pianta smette di crescere finché non viene innaffiata.
- **Raccolto Succoso (Bonus)**: Se mantieni l'umidità sopra il **50%** per tutta la durata della crescita, otterrai un **bonus del 20%** sulla quantità raccolta (es. 6 erbe invece di 5).
- **Marcimento**: Una volta pronta, la pianta ha una "finestra di freschezza". Se non viene raccolta entro un tempo limite (pari al suo tempo di crescita), inizierà a marcire.
    - **In marciume**: Resi ridotti del 50%.
    - **Marcita**: Raccolto andato perduto.

## 2. Raffinatezze Combattimento (Aggro & Scouter)

### Cambiamenti Aggro (Taunt):
- **Difesa Strategica**: Quando un giocatore preme **"🛡️ Difesa"**, il suo valore di **Aggro** (minaccia) viene moltiplicato per **15x**.
- **Taunt Diretto**: Oltre al moltiplicatore, l'azione di difesa applica un "Taunt" che imposta il giocatore come bersaglio prioritario del mostro per i successivi 2 minuti.
- **Ruolo del Tank**: Questi cambiamenti rendono finalmente possibile il ruolo del "Tank" nei combattimenti di gruppo, permettendo a chi ha molta vita/difesa di proteggere i compagni più fragili.

### Visualizzazione Mostri:
- **Velocità Nascosta**: La velocità dei mostri non è più visibile nel menu base per rendere i combattimenti meno prevedibili.
- **Uso dello Scouter**: La velocità (e altre stats precise) diventano visibili solo se il giocatore ha attivato uno **Scouter**.

## 3. Istruzioni per il Deployment (DietPi / Produzione)

Poiché queste modifiche includono cambiamenti alla struttura del database (schema), è fondamentale seguire questi passi sul server DietPi:

### Passo 1: Aggiornare il codice
Eseguire il pull delle modifiche o copiare i file aggiornati.

### Passo 2: Aggiornare il Database
Il file `db_setup.py` è stato aggiornato per gestire automaticamente l'aggiunta delle nuove colonne. Per applicare le modifiche, esegui:
```bash
python3 db_setup.py
```
Questo comando:
1. Aggiungerà le colonne `moisture`, `last_watered_at` e `rot_time` alla tabella `garden_slots`.
2. Sincronizzerà le nuove risorse (Erba Verde, Blu, Gialla e relativi semi) nella tabella `resources`.
3. Verificherà l'integrità di tutte le altre tabelle.

### Troubleshooting
Se visualizzi l'errore `column garden_slots.moisture does not exist`, significa che la migrazione del database non è stata eseguita. Esegui `python3 db_setup.py` per risolvere.

---
*Documentazione creata il 13/02/2026*
