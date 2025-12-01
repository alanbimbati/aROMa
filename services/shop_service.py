from database import Database
from models.user import Utente
from models.game import Steam, GameInfo
from services.user_service import UserService
from services.game_service import GameService
import random
from settings import PointsName
import datetime
from dateutil.relativedelta import relativedelta

class ShopService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.game_service = GameService()
        self.COSTO_PREMIUM = 250
        self.COSTO_MANTENIMENTO = 50

    def buy_steam_game(self, user, coin_type):
        session = self.db.get_session()
        try:
            if user.premium != 1:
                return False, "Devi essere Premium per comprare giochi Steam."

            costo = 0
            probabilita = 0
            
            if coin_type == 'Bronze Coin':
                costo = 50
                probabilita = 10
            elif coin_type == 'Silver Coin':
                costo = 100
                probabilita = 50
            elif coin_type == 'Gold Coin':
                costo = 150
                probabilita = 100
            elif coin_type == 'Platinum Coin':
                costo = 200
                probabilita = 100 # Special case
            
            if user.points < costo:
                return False, f"Non hai abbastanza {PointsName}."

            self.user_service.add_points(user, -costo)
            
            if coin_type == 'Platinum Coin':
                # Logic for platinum is different (choose game), handled in bot handler usually
                # But here we can return success and let handler ask for game
                return True, "Platinum"

            is_sculato = random.randint(1, 100) > (100 - probabilita)
            game_list = session.query(Steam).filter(Steam.preso_da == '').filter_by(titolone=is_sculato)
            from sqlalchemy import func
            game = game_list.order_by(func.random()).first()
            
            if game:
                game.preso_da = str(user.id_telegram)
                session.commit()
                return True, game
            else:
                return False, "Nessun gioco disponibile."
        finally:
            session.close()

    def buy_premium(self, user):
        if user.premium == 1:
            return False, "Sei già Premium."
        
        if user.points < self.COSTO_PREMIUM:
            return False, f"Ti servono {self.COSTO_PREMIUM} {PointsName}."

        self.user_service.update_user(user.id_telegram, {
            'points': user.points - self.COSTO_PREMIUM,
            'premium': 1,
            'abbonamento_attivo': 1,
            'scadenza_premium': datetime.datetime.now() + relativedelta(months=+1)
        })
        return True, "Abbonamento attivato!"

    def buy_game_from_channel(self, user, message_link):
        game = self.game_service.get_game_by_message_link(message_link)
        costo = 0 if (game and game.premium == 1 and user.premium == 1) else (5 if user.premium == 1 else 15)
        
        if user.points < costo:
            return False, f"Ti servono {costo} {PointsName}."
        
        self.user_service.add_points(user, -costo)
        return True, "Gioco acquistato!"
