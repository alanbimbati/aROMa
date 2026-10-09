"""Publish (or update) the aROMa Nostr profile. Needs NOSTR_NSEC in the environment."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))

from services import nostr_service

if __name__ == '__main__':
    if not nostr_service.is_configured():
        sys.exit("NOSTR_NSEC non impostata.")
    ok = nostr_service.publish_profile(
        name="aROMa di videogiochi",
        about="Il bot RPG di aROMa. Qui trovi i badge degli achievement sbloccati dagli eroi.",
        picture=os.getenv("NOSTR_PROFILE_PICTURE"),
    )
    print("Profilo pubblicato." if ok else "Nessun relay ha accettato il profilo.")
