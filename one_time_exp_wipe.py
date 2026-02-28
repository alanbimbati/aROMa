import os
from db_setup import init_database
from database import Database
from models.user import Utente

FLAG_FILE = "EXP_WIPE_DONE.flag"

def run_one_time_wipe():
    # Protezione: evita doppia esecuzione
    if os.path.exists(FLAG_FILE):
        print("⚠️ Script già eseguito in passato. Bloccato.")
        return

    print("⚙️  Avvio dimezzamento EXP e Wumpa...")

    init_database()
    db = Database()

    session = db.get_session()
    try:
        users = session.query(Utente).all()
        modified = 0

        for u in users:
            original_exp = u.exp or 0
            original_wumpa = u.points or 0

            new_exp = min(original_exp // 2, 100000)
            new_wumpa = original_wumpa // 2

            if new_exp != original_exp or new_wumpa != original_wumpa:
                u.exp = new_exp
                u.points = new_wumpa
                modified += 1

        session.commit()

        # Crea file flag per bloccare riesecuzioni
        with open(FLAG_FILE, "w") as f:
            f.write("DONE")

        print(f"✅ Operazione completata. Utenti modificati: {modified}")

    except Exception as e:
        session.rollback()
        print(f"❌ Errore durante il wipe: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    run_one_time_wipe()
