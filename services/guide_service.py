
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
                                "   - **Cooldown**: Il tempo di recupero è **doppio** rispetto a un attacco normale.\n"
                                "   - **Speciale AoE**: Alcuni personaggi possono lanciare la loro abilità speciale ad area!"
                    },
                    "stats": {
                        "title": "📊 Statistiche",
                        "text": "Puoi allocare i punti statistica ottenuti salendo di livello (/stats) per personalizzare il tuo personaggio:\n\n"
                                "❤️ **Vita (HP)**: Aumenta la tua salute massima (+10 per punto). Più vita hai, più colpi puoi subire.\n"
                                "💙 **Mana (MP)**: Aumenta il tuo mana massimo (+5 per punto). Il mana serve per usare le abilità speciali.\n"
                                "⚔️ **Danno Base**: Aumenta i danni inflitti dai tuoi attacchi fisici (+2 per punto).\n"
                                "🛡️ **Resistenza**: Riduce i danni subiti in percentuale (+1% per punto, MAX 75%). Fondamentale per sopravvivere ai boss.\n"
                                "💥 **Critico**: Aumenta la probabilità di infliggere danni critici (+1% per punto).\n"
                                "   - Attacco Normale: Danno x2.0\n"
                                "   - Attacco Speciale: Moltiplicatore variabile in base al personaggio.\n"
                                "⚡ **Velocità**: Riduce il tempo di attesa (Cooldown) tra un attacco e l'altro (+1 per punto).\n"
                                "   - Formula: Ogni punto aumenta la velocità di recupero del 5%."
                    },
                    "elements": {
                        "title": "🔥 Elementi (In Sviluppo)",
                        "text": "Ogni personaggio e nemico ha un elemento.\n\n🔥 Fuoco > 🍃 Erba\n🍃 Erba > 💧 Acqua\n💧 Acqua > 🔥 Fuoco\n\nSfrutta il vantaggio elementale per fare più danni! (Funzione in fase di sviluppo)"
                    },
                    "dragonballs": {
                        "title": "🐉 Sfere del Drago",
                        "text": "Esistono due set di Sfere del Drago, ognuno con un drago diverso:\n\n"
                                "🐉 **Shenron**: Il drago della Terra. Esaudisce desideri classici come ricchezza (Wumpa) o esperienza.\n"
                                "🐲 **Porunga**: Il drago di Namecc. È più potente e può esaudire 3 desideri alla volta, offrendo ricompense diverse o più rare.\n\n"
                                "Le sfere possono essere trovate casualmente scrivendo in chat (con un pizzico di fortuna) o sconfiggendo i nemici."
                    }
                }
            },
            "items": {
                "title": "🎒 Oggetti",
                "description": "Lista degli oggetti e dei loro effetti.",
                "items": {
                    "potions": {
                        "title": "🧪 Pozioni",
                        "text": "❤️ **Pozione Salute**: Ripristina una parte dei tuoi HP.\n"
                                "💙 **Pozione Mana**: Ripristina una parte dei tuoi MP.\n"
                                "💖 **Elisir Completo**: Ripristina completamente HP e MP."
                    },
                    "utility": {
                        "title": "🛠️ Utilità",
                        "text": "📦 **Cassa**: Contiene una quantità casuale di Wumpa Fruit.\n"
                                "🚀 **Turbo**: Aumenta l'esperienza guadagnata del 20% per 30 minuti.\n"
                                "🎭 **Aku Aku / Uka Uka**: Ti rende INVINCIBILE per 10 minuti, proteggendoti da danni e trappole."
                    },
                    "offensive": {
                        "title": "💣 Offensivi & Trappole",
                        "text": "🧨 **TNT / Nitro**: Possono essere usati in due modi:\n"
                                "1. **Contro un giocatore**: Gli fa perdere Wumpa Fruit.\n"
                                "2. **Contro un nemico**: Fa cadere Wumpa Fruit extra dal nemico.\n"
                                "3. **Come trappola**: Se usati senza bersaglio, esplodono al prossimo messaggio in chat!\n\n"
                                "🎯 **Mira un giocatore**: Ruba Wumpa Fruit a un altro giocatore.\n"
                                "🥊 **Colpisci un giocatore**: Fa perdere Wumpa a un giocatore, facendoli cadere a terra per chiunque li raccolga."
                    }
                }
            },
            "features": {
                "title": "🌟 Funzionalità",
                "description": "Scopri cosa puoi fare nel mondo di aROMa.",
                "items": {
                    "dungeons": {
                        "title": "🏰 Dungeon",
                        "text": "Affronta serie di nemici e boss in dungeon tematici. I dungeon offrono ricompense uniche e sono il modo migliore per salire di livello."
                    },
                    "guilds": {
                        "title": "🏰 Gilde (In Sviluppo)",
                        "text": "Crea o unisciti a una Gilda per giocare con gli amici. Le gilde offriranno bonus passivi, un magazzino condiviso e raid esclusivi. (Funzione in fase di sviluppo)"
                    },
                    "seasons": {
                        "title": "📅 Stagioni",
                        "text": "Le Stagioni sono eventi periodici che trasformano il mondo di gioco. Ogni stagione ha un tema unico, cambia le meccaniche, i nemici e offre un Pass Stagionale con ricompense esclusive."
                    },
                    "market": {
                        "title": "🏪 Mercato (In Sviluppo)",
                        "text": "🚧 **IN SVILUPPO** 🚧\n\nIl Mercato permetterà ai giocatori di vendere e comprare oggetti tra di loro usando i Wumpa Fruit. Sarà il cuore dell'economia di gioco!"
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
