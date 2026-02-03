
class GuideService:
    def __init__(self):
        self.content = {
            "mechanics": {
                "title": "⚙️ Meccaniche",
                "description": "Approfondimenti sulle meccaniche di gioco.",
                "items": {
                    "combat": {
                        "title": "⚔️ Combattimento",
                        "text": "Durante il combattimento puoi eseguire diverse azioni:\n\n"
                                "🗡️ **Attacco Base**: Infligge danni fisici basati sulla tua Forza.\n"
                                "✨ **Attacco Speciale**: Un attacco potente che consuma Mana. L'effetto e il danno dipendono dal personaggio equipaggiato.\n"
                                "💥 **Attacco ad Area (AoE)**: Colpisce fino a 5 nemici contemporaneamente!\n"
                                "   - **Danno**: Infligge il 70% del danno al bersaglio principale e il 50% agli altri.\n"
                                "   - **Cooldown**: Il tempo di recupero è **doppio** rispetto a un attacco normale.\n\n"
                                "🔥 **Aggro**: I nemici attaccano chi fa più danno, ma i Tank possono attirare l'attenzione (Aggro) usando abilità difensive."
                    },
                    "stats": {
                        "title": "📊 Statistiche",
                        "text": "Puoi allocare i punti statistica (/stats) per personalizzare il tuo personaggio:\n\n"
                                "❤️ **Vita (HP)**: +10 HP per punto.\n"
                                "💙 **Mana (MP)**: +5 MP per punto.\n"
                                "⚔️ **Danno**: +2 Danno fisico per punto.\n"
                                "🛡️ **Resistenza**: +1% resist (Max 75%).\n"
                                "💥 **Critico**: +1% probabilità.\n"
                                "⚡ **Velocità**: Riduce il tempo tra turni."
                    },
                    "armory": {
                        "title": "⚒️ Armeria & Crafting",
                        "text": "Nell'Armeria di Gilda puoi creare equipaggiamento potente.\n"
                                "Più alto è il livello dell'Armeria, migliore è la rarità che puoi creare:\n\n"
                                "⚪ **Comune**: Armeria Lv. 1\n"
                                "🟢 **Non Comune**: Armeria Lv. 2\n"
                                "🔵 **Raro**: Armeria Lv. 3\n"
                                "🟣 **Epico**: Armeria Lv. 4\n"
                                "🟠 **Leggendario**: Armeria Lv. 5\n\n"
                                "Gli oggetti craftati hanno statistiche casuali basate sulla loro rarità!"
                    },
                    "dragonballs": {
                        "title": "🐉 Sfere del Drago",
                        "text": "Trova le sfere per esprimere desideri!\n"
                                "🐉 **Shenron**: Desideri classici (Wumpa, EXP).\n"
                                "🐲 **Porunga**: 3 desideri alla volta (Nomek)."
                    }
                }
            },
            "items": {
                "title": "🎒 Oggetti",
                "description": "Lista degli oggetti e dei loro effetti.",
                "items": {
                    "potions": {
                        "title": "🧪 Pozioni",
                        "text": "Recupera le tue forze in battaglia o fuori:\n\n"
                                "❤️ **Pozione Piccola**: 30 HP\n"
                                "❤️ **Pozione Media**: 60 HP\n"
                                "❤️ **Pozione Grande**: 100 HP\n"
                                "❤️ **Pozione Completa**: Full HP\n\n"
                                "💙 **Pozione Mana Piccola**: 30 MP\n"
                                "💙 **Pozione Mana Media**: 60 MP\n"
                                "💙 **Pozione Mana Grande**: 100 MP\n"
                                "💙 **Pozione Mana Completa**: Full MP\n\n"
                                "💖 **Elisir**: Full HP + Full MP (+ Rimuove status)"
                    },
                    "special": {
                        "title": "✨ Oggetti Speciali",
                        "text": "Oggetti unici con effetti passivi:\n\n"
                                "👓 **Scouter / Visore**: Se equipaggiato (Accessorio), ti permette di vedere le statistiche esatte dei nemici! Rispondi al messaggio di un mostro per analizzarlo.\n"
                                "👂 **Orecchini Potara**: (In Sviluppo) Permetteranno la fusione tra due guerrieri.\n"
                                "📕 **Libri Abilità**: Insegnano nuove mosse o passived."
                    },
                    "utility": {
                        "title": "🛠️ Utilità",
                        "text": "📦 **Cassa Wumpa**: Contiene Wumpa casuali.\n"
                                "🚀 **Turbo**: +20% EXP per 30 min.\n"
                                "🎭 **Aku Aku / Uka Uka**: Invincibilità 30 min.\n"
                                "🧨 **TNT/Nitro**: Trappole o danni diretti."
                    }
                }
            },
            "guilds": {
                "title": "🏰 Gilde",
                "description": "Unisciti agli altri giocatori!",
                "items": {
                    "structures": {
                        "title": "🏗️ Strutture Gilda",
                        "text": "Ogni Gilda ha un hub con strutture potenziabili:\n\n"
                                "🏠 **Locanda**: Dove i membri riposano. Più alto è il livello, più veloce è il recupero HP/Mana (fino a 3.5x!).\n"
                                "🍻 **Birrificio**: Migliora la qualità della Birra. Al Lv.5, la Birra potenzia le pozioni del 40%!\n"
                                "🔞 **Bordello delle Elfe**: Fornisce il buff 'Vigore' (Mana cost -50%). Più alto è il livello, più dura l'effetto (fino a 2 ore).\n"
                                "🏘️ **Villaggio**: Determina quanti membri può ospitare la gilda. (Max Lv. 5).\n"
                                "⚒️ **Armeria**: Sblocca il crafting di rarità superiori."
                    },
                    "roles": {
                        "title": "👥 Ruoli",
                        "text": "👑 **Leader**: Può costruire, potenziare e gestire i membri.\n"
                                "👮 **Officer**: Può invitare e kickare.\n"
                                "👤 **Membro**: Può depositare Wumpa e usare le strutture."
                    }
                }
            },
            "features": {
                "title": "🌟 Modalità",
                "description": "Attività di gioco.",
                "items": {
                    "dungeons": {
                        "title": "🏰 Dungeon",
                        "text": "Affronta serie di nemici e boss per loot epico. I Dungeon scalano con il livello medio del gruppo."
                    },
                    "seasons": {
                        "title": "📅 Stagioni",
                        "text": "Eventi periodici con classifiche e premi esclusivi."
                    }
                }
            }
        }

    def get_categories(self):
        """Return list of (key, title) for main categories"""
        return [(k, v['title']) for k, v in self.content.items()]

    def get_category(self, category_key):
        """Return category details"""
        return self.content.get(category_key)

    def get_item(self, category_key, item_key):
        """Return specific item details"""
        cat = self.content.get(category_key)
        if cat:
            return cat['items'].get(item_key)
        return None
