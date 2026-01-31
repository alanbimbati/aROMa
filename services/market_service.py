from database import Database
from models.market import MarketListing
from models.user import Utente
from models.items import Collezionabili
from services.event_dispatcher import EventDispatcher
from services.user_service import UserService
from services.item_service import ItemService
import datetime

class MarketService:
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()
        self.user_service = UserService()
        self.item_service = ItemService()

    def list_item(self, user_id, item_name, quantity, price_per_unit, days_valid=7):
        """
        List an item for sale.
        """
        session = self.db.get_session()
        try:
            # Check inventory
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user:
                return False, "Utente non trovato."

            # Calculate total quantity available
            total_qty = session.query(Collezionabili).filter_by(
                id_telegram=str(user_id), 
                oggetto=item_name,
                data_utilizzo=None
            ).count()
            
            if total_qty < quantity:
                return False, f"Non hai abbastanza oggetti (Hai {total_qty}, ne servono {quantity})."
            
            # Remove item from inventory
            self.item_service.remove_item(user_id, item_name, quantity, session=session)
            
            # Create listing
            listing = MarketListing(
                seller_id=user_id,
                item_name=item_name,
                quantity=quantity,
                price_per_unit=price_per_unit,
                expires_at=datetime.datetime.now() + datetime.timedelta(days=days_valid),
                status='active'
            )
            session.add(listing)
            session.commit()
            
            # Log event
            self.event_dispatcher.log_event(
                event_type='ITEM_LISTED',
                user_id=user_id,
                value=quantity,
                context={'item': item_name, 'price': price_per_unit, 'listing_id': listing.id}
            )
            
            return True, f"✅ Scalati {quantity}x {item_name}. Annuncio creato!"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def buy_item(self, buyer_id, listing_id):
        """
        Buy an item from the market.
        """
        session = self.db.get_session()
        try:
            buyer = session.query(Utente).filter_by(id_telegram=buyer_id).first()
            listing = session.query(MarketListing).filter_by(id=listing_id).first()
            
            if not listing or listing.status != 'active':
                return False, "Annuncio non più disponibile."
            
            if listing.seller_id == buyer_id:
                return False, "Non puoi acquistare i tuoi oggetti."
            
            # Check expiration
            if listing.expires_at < datetime.datetime.now():
                listing.status = 'expired'
                session.commit()
                return False, "Annuncio scaduto."
            
            total_price = listing.price_per_unit * listing.quantity
            
            if buyer.points < total_price:
                return False, f"Non hai abbastanza 🍑 ({buyer.points}/{total_price})."
            
            # Transact
            # 1. Deduct points from buyer
            buyer.points -= total_price
            
            # 2. Add points to seller
            seller = session.query(Utente).filter_by(id_telegram=listing.seller_id).first()
            if seller:
                seller.points += total_price
                
            # 3. Add item to buyer
            self.item_service.add_item(buyer_id, listing.item_name, listing.quantity, session=session)
            
            # 4. Update listing
            listing.status = 'sold'
            listing.buyer_id = buyer_id
            listing.sold_at = datetime.datetime.now()
            
            session.commit()
            
            # Log Events
            # Buyer bought
            self.event_dispatcher.log_event(
                event_type='ITEM_BOUGHT',
                user_id=buyer_id,
                value=total_price,
                context={'item': listing.item_name, 'seller': listing.seller_id}
            )
            
            # Seller sold
            self.event_dispatcher.log_event(
                event_type='ITEM_SOLD',
                user_id=listing.seller_id,
                value=total_price,
                context={'item': listing.item_name, 'buyer': buyer_id}
            )
            
            # Quick Sale?
            time_diff = (listing.sold_at - listing.created_at).total_seconds()
            if time_diff <= 60:
                self.event_dispatcher.log_event(
                    event_type='QUICK_SALE',
                    user_id=listing.seller_id,
                    value=time_diff,
                    context={'listing_id': listing.id}
                )
            
            return True, f"✅ Acquistato {listing.quantity}x {listing.item_name} per {total_price} 🍑!"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def get_active_listings(self, page=1, limit=10):
        """
        Get paginated active listings.
        """
        session = self.db.get_session()
        from sqlalchemy.orm import joinedload
        try:
            offset = (page - 1) * limit
            listings = session.query(MarketListing).options(joinedload(MarketListing.seller)).filter(
                MarketListing.status == 'active',
                MarketListing.expires_at > datetime.datetime.now()
            ).order_by(MarketListing.created_at.desc()).offset(offset).limit(limit).all()
            
            # Count for pagination
            total = session.query(MarketListing).filter(
                MarketListing.status == 'active',
                MarketListing.expires_at > datetime.datetime.now()
            ).count()
            
            # Expunge to detach from session but keep data (optional, but safer is eager load which we did)
             #session.expunge_all() 
            return listings, total
        finally:
            session.close()

    def cancel_listing(self, user_id, listing_id):
        """Cancel listing and return items."""
        session = self.db.get_session()
        try:
            listing = session.query(MarketListing).filter_by(id=listing_id, seller_id=user_id).first()
            if not listing or listing.status != 'active':
                return False, "Annuncio non annullabile."
            
            listing.status = 'cancelled'
            
            # Return items
            self.item_service.add_item(user_id, listing.item_name, listing.quantity, session=session)
            
            session.commit()
            return True, "Annuncio cancellato e oggetti restituiti."
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()
