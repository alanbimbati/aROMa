from database import Database
from models.game import GameInfo, Steam, GiocoUtente
from sqlalchemy import or_, distinct

class GameService:
    def __init__(self):
        self.db = Database()

    def search_games(self, query):
        session = self.db.get_session()
        try:
            if query.lower() == "premium":
                return session.query(GameInfo).filter(GameInfo.premium == 1).all()
            
            platforms = session.query(distinct(GameInfo.platform)).all()
            platforms = [p[0].lower() for p in platforms if p[0]]

            query_words = query.lower().split()
            platform_filters = [word for word in query_words if word.lower() in platforms]
            stop_words = {'il', 'la', 'lo', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra'}
            search_terms = [word for word in query_words if word not in platform_filters and word not in stop_words]

            sql_query = session.query(GameInfo)

            if platform_filters:
                platform_filter = or_(*[GameInfo.platform.ilike(f'%{pf}%') for pf in platform_filters])
                sql_query = sql_query.filter(platform_filter)

            for term in search_terms:
                search_filter = or_(GameInfo.title.ilike(f'%{term}%'))
                sql_query = sql_query.filter(search_filter)

            results = sql_query.all()
            return results
        except Exception as e:
            print(f"Errore durante la ricerca: {e}")
            return []
        finally:
            session.close()

    def get_game_by_message_link(self, message_link):
        session = self.db.get_session()
        game = session.query(GameInfo).filter_by(message_link=message_link).first()
        session.close()
        return game

    def is_premium_game(self, message_link):
        game = self.get_game_by_message_link(message_link)
        return game.premium == 1 if game else False
