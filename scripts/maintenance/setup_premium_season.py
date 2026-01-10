import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Database, Base
from models.seasons import Season, SeasonProgress
from models.user import Utente

def setup_premium_season():
    # Point to the official DB
    engine = create_engine('sqlite:///points_official.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Create the season
        season_name = "Stagione 1: Inverno 2026"
        start_date = datetime.datetime.now()
        end_date = datetime.datetime(2026, 2, 2, 23, 59, 59)
        
        # Check if it already exists
        existing_season = session.query(Season).filter_by(name=season_name).first()
        if not existing_season:
            new_season = Season(
                name=season_name,
                start_date=start_date,
                end_date=end_date,
                is_active=True,
                exp_multiplier=1.0,
                description="Stagione inaugurale con pass gratuito per i membri Premium!"
            )
            session.add(new_season)
            session.commit()
            season_id = new_season.id
            print(f"Created new season: {season_name} (ID: {season_id})")
        else:
            season_id = existing_season.id
            print(f"Season already exists: {season_name} (ID: {season_id})")

        # 2. Find premium users
        premium_users = session.query(Utente).filter_by(premium=1).all()
        print(f"Found {len(premium_users)} premium users.")

        # 3. Grant season pass
        count = 0
        for user in premium_users:
            # Check if progress already exists
            progress = session.query(SeasonProgress).filter_by(user_id=user.id_telegram, season_id=season_id).first()
            if not progress:
                progress = SeasonProgress(
                    user_id=user.id_telegram,
                    season_id=season_id,
                    current_exp=0,
                    current_level=1,
                    has_premium_pass=True,
                    last_update=datetime.datetime.now()
                )
                session.add(progress)
                count += 1
            else:
                if not progress.has_premium_pass:
                    progress.has_premium_pass = True
                    count += 1
        
        session.commit()
        print(f"Successfully granted season pass to {count} users.")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    setup_premium_season()
