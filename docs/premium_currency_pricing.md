# Premium Currency System: Cristalli aROMa ✨

## Conversion Rate

**Bitcoin Donations → Cristalli aROMa:**
```
1,000 satoshi = 1 Cristallo aROMa
```

**Examples:**
- 10,000 sats = 10 cristalli
- 100,000 sats ≈ 0.001 BTC = 100 cristalli  
- 1,000,000 sats ≈ 0.01 BTC = 1,000 cristalli

## Skin Pricing Formula

**Character Skins:**
```python
price = max(1, floor(character_level / 10))
```

**Pricing Table:**
| Character Level | Price (Cristalli aROMa) |
|-----------------|-------------------------|
| 1-9             | 1 ✨                    |
| 10-19           | 1 ✨                    |
| 20-29           | 2 ✨                    |
| 30-39           | 3 ✨                    |
| 40-49           | 4 ✨                    |
| 50-59           | 5 ✨                    |
| 60-69           | 6 ✨                    |
| 70-79           | 7 ✨                    |
| 80-89           | 8 ✨                    |
| 90-99           | 9 ✨                    |
| 100+            | 10 ✨                   |

**Rationale:**
- Higher level characters are more prestigious → higher skin cost
- Minimum 1 cristallo ensures all skins have value
- Linear scaling keeps pricing simple and fair

## Implementation Notes

- **Database:** `utente.cristalli_aroma` (Integer, default 0)
- **Alembic Migration:** `1dcb8f36137e_add_cristalli_aroma_premium_currency.py`
- **Admin Commands:** Use `UserService.add_cristalli(user_id, amount)` to grant cristalli
- **Payment Integration:** Bitcoin Lightning Network recommended for donations
- **No P2W:** Skins are purely cosmetic - no stats bonuses

## Future Features

- [ ] Bitcoin donation integration
- [ ] Cosmetic shop UI
- [ ] Skin preview system
- [ ] Gift cristalli to other users
- [ ] Special effects (auras, particles)
- [ ] Limited edition seasonal skins
