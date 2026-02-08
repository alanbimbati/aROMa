# 💎 Raffineria (Refinery)

La Raffineria permette di trasformare le risorse grezze ottenute dai mostri in materiali raffinati necessari per forgiare equipaggiamento potente.

## 🛠️ Come Funziona

1. **Ottieni Risorse**: Sconfiggi i mostri per ottenere risorse grezze. Le trovi sconfiggendo mob nel mondo o nei Dungeon.
2. **Accedi alla Raffineria**: Usa il comando `/guild` → Armeria → Raffineria
3. **Raffina**: Seleziona la risorsa del giorno e scegli la quantità da raffinare
4. **Attendi**: La raffinazione richiede tempo reale (30 secondi per unità, ridotto dal livello Armeria)
5. **Ricevi Automaticamente**: Una volta terminata, riceverai automaticamente i materiali con una notifica

> [!NOTE]
> La raffineria permette di lavorare **solo una risorsa al giorno**. La risorsa cambia ogni 24 ore.

## 📊 Formula di Raffinazione

### Quantità Totale Prodotta

La massa totale di materiali prodotti dalla raffinazione dipende da:

```
Massa Totale = Quantità Grezza × (0.8 + Rarità Risorsa × 0.2) × (1 + Livello Armeria × 0.05)
```

**Esempio**: 10 risorse Rare (Rarità 3) con Armeria Lv. 2
- Massa = 10 × (0.8 + 3 × 0.2) × (1 + 2 × 0.05)
- Massa = 10 × 1.4 × 1.1 = **15.4 → 15 materiali totali**

### Distribuzione per Qualità (Tier)

I materiali prodotti vengono distribuiti in 3 tier:
- **🔩 Rottami (Tier 1)**: Materiale base
- **💎 Materiale Pregiato (Tier 2)**: Materiale raro
- **💍 Diamante (Tier 3)**: Materiale rarissimo

#### Probabilità Base (Livello Professione 0, Livello Personaggio 1)

**Materiale Pregiato (T2)**:
```
Chance T2 = MIN(15%, (2% + Livello Professione × 0.3% + Livello Personaggio × 0.05%) × (1 + Rarità Risorsa × 0.05))
```

**Diamante (T3)**:
```
Chance T3 = MIN(5%, (0.5% + Livello Professione × 0.15% + Livello Personaggio × 0.02%) × (1 + Rarità Risorsa × 0.03))
```

#### Tabella Probabilità per Livello

| Livello Professione | Livello Personaggio | Chance T2 (Risorsa Comune) | Chance T3 (Risorsa Comune) |
|:---:|:---:|:---:|:---:|
| 0 | 1-49 | ~2-4% | ~0.5-1% |
| 10 | 50 | ~6% | ~2% |
| 20 | 75 | ~10% | ~3.5% |
| 30 | 100 | ~14% | ~5% (cap) |

> [!IMPORTANT]
> Le risorse più rare (Epiche/Leggendarie) forniscono un piccolo bonus alle probabilità, ma l'impatto maggiore viene dal livello della tua Professione e del tuo Personaggio.

### Esempio Pratico

**Scenario**: Livello 49, Professione 0, 10 Ferro Vecchio (Rarità 1)

1. **Calcolo Massa**:
   - Massa = 10 × (0.8 + 1 × 0.2) × 1.0 = **10 materiali**

2. **Calcolo Probabilità**:
   - T2 = (2 + 0 × 0.3 + 49 × 0.05) × 1.05 ≈ **4.5%**
   - T3 = (0.5 + 0 × 0.15 + 49 × 0.02) × 1.03 ≈ **1.5%**

3. **Distribuzione Attesa**:
   - Diamanti: 10 × 1.5% × RNG(0.8-1.2) ≈ **0-1** (rarissimo)
   - Materiale Pregiato: 9-10 × 4.5% × RNG(0.8-1.2) ≈ **0-1**
   - Rottami: **9-10** (il resto)

**Risultato tipico**: 9-10 Rottami, 0-1 Materiale Pregiato, quasi mai Diamanti

## 📈 Rarietà delle Risorse

**Tipologie di Risorse**:
- **⚪ Comuni**: Es. Ferro Vecchio, Cuoio, Legna. Facili da trovare, resa base
- **🟢 Non Comuni**: Es. Ferro, Pelle Dura, Cristallo Blu. Resa migliorata
- **🔵 Rare**: Es. Mithril, Seta, Essenza Energetica. Alta resa
- **🟣 Epiche**: Es. Adamantite, Frammento Antico. Ottima resa
- **🟠 Leggendarie**: Es. Oricalco, Nucleo Stellare. Massima resa

## ⬆️ Upgrade dei Materiali

Se possiedi molti materiali di basso livello, puoi convertirli in materiali di tier superiore tramite **"Upgrade Materiali"**.

**Tasso di Conversione**: **10 : 1** (Istantaneo)
- 10 **Rottami** 🔩 → 1 **Materiale Pregiato** 💎
- 10 **Materiale Pregiato** 💎 → 1 **Diamante** 💍

Questa operazione è **istantanea** e non occupa slot di raffinazione.

## ⏱️ Tempo di Raffinazione

```
Tempo Totale = Quantità × 30 secondi × (1 - Livello Armeria × 0.1)
```

**Riduzione minima**: 80% (con Armeria Lv. 8+, riduzione massima al 20% del tempo base)

**Esempio**: 50 risorse con Armeria Lv. 3
- Tempo = 50 × 30s × (1 - 3 × 0.1) = 50 × 30s × 0.7 = **17.5 minuti**

## 💡 Strategie e Consigli

### Progressione
1. **Livello Basso (1-30)**: Raffina costantemente per costruire uno stock di Rottami. I Diamanti saranno rarissimi
2. **Livello Medio (30-60)**: Inizia a vedere più Materiale Pregiato. Investi nella Professione per aumentare le chance
3. **Livello Alto (60+)**: Con Professione alta, puoi farmmare efficientemente materiali premium

### Ottimizzazione
- **Investi nella Professione**: Ogni livello aumenta significativamente le probabilità di materiali rari
- **Armeria di Gilda**: I livelli dell'Armeria velocizzano la raffinazione e aumentano la resa
- **Risorse Rare**: Risparmia le risorse Epiche/Leggendarie per quando hai Armeria e Professione alti
- **Conversione 10:1**: Usa l'upgrade solo quando hai eccesso di materiali bassi e ne serve uno raro urgente

### Diamanti
> [!CAUTION]
> I Diamanti sono **estremamente rari** e preziosi. Usali solo per craftare equipaggiamento Leggendario di tier massimo!

## 📋 Riepilogo Formule

| Elemento | Formula |
|:---|:---|
| **Massa Totale** | `Quantità × (0.8 + Rarità × 0.2) × (1 + LvArmeria × 0.05)` |
| **Chance T2 (cap 15%)** | `(2 + LvProf × 0.3 + LvChar × 0.05) × (1 + Rarità × 0.05)` |
| **Chance T3 (cap 5%)** | `(0.5 + LvProf × 0.15 + LvChar × 0.02) × (1 + Rarità × 0.03)` |
| **Tempo** | `Quantità × 30s × MAX(0.2, 1 - LvArmeria × 0.1)` |
| **Upgrade** | `10 materiali → 1 materiale tier superiore (istantaneo)` |
