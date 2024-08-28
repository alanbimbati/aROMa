from ast import Str
from datetime import date
from sqlite3 import Timestamp
from termios import TIOCPKT_FLUSHREAD
from sqlalchemy                 import create_engine, Column, Table, ForeignKey, MetaData
from sqlalchemy.orm             import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy                 import (Integer, String, Date, DateTime, Float, Boolean, Text)
from sqlalchemy.orm     import sessionmaker
from sqlalchemy         import desc,asc,distinct,or_
from settings           import *
from telebot            import types
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
#import pandas as pd
import os
import datetime
from dateutil.relativedelta import relativedelta


Base = declarative_base()

livelli = [0, 100, 235, 505, 810, 1250, 1725, 2335, 2980, 3760, 4575, 5525, 6510, 7630, 8785, 10075, 11400, 12860, 14355, 15985, 17650, 19450, 21285, 23255, 25260, 27400, 29575,
31885, 34230, 36710, 39225, 41875, 44560, 47380, 50235, 53225, 56250, 59410, 62605, 65935,70000,75000,80000,85000,90000,95000,100000,105000]

class Database:
    def __init__(self):
        engine = create_engine('sqlite:///points.db')
        create_table(engine)
        self.Session = sessionmaker(bind=engine)

    def startMarkup(self,utente=None):
        markup = types.ReplyKeyboardMarkup()

        #markup.add('Compra 1 gioco')
        #markup.add('Cosa puoi fare con i Frutti Wumpa?')
        #markup.add('Come guadagno Frutti Wumpa?')
        markup.add('ℹ️ info','🎮 Nome in Game','📦 Inventario')
        if utente is not None:
            if utente.premium==1:
                markup.add('👤 Scegli il personaggio','👤 Scegli il personaggio 🎖')
                markup.add('🎫 Compra un gioco steam','🎖 Compro un altro mese')
                if utente.abbonamento_attivo==1:
                    markup.add('✖️ Disattiva rinnovo automatico')
                else:
                    
                    markup.add('✅ Attiva rinnovo automatico')
            else:
                markup.add('👤 Scegli il personaggio')
                markup.add('🎖 Compra abbonamento Premium (1 mese)')
        markup.add('📄 Classifica')

        return markup

    def isSunday(self,utente):
        session = self.Session()
        chatid = utente.id_telegram
        oggi = datetime.datetime.today().date()
        if oggi.strftime('%A')=='Sunday':
            exist = session.query(Domenica).filter_by(utente = chatid).first()
            if exist is None:
                try:
                    domenica = Domenica()
                    domenica.last_day   = oggi
                    domenica.utente     = chatid
                    session.add(domenica)
                    session.commit()
                    Database().update_user(chatid,{'points':utente.points+1})
                except:
                    session.rollback()
                    raise
                finally:
                    session.close()
                return True
            elif exist.last_day!=oggi:
                Database().update_domenica(chatid,{'last_day':oggi})
                Database().update_user(chatid,{'points':utente.points+1})
                return True
            else:
                return False
    
    def checkIsSunday(self,utenteSorgente,message):
        nome = Utente().getUsernameAtLeastName(utenteSorgente)
        if (self.isSunday(utenteSorgente)):
            bot.reply_to(message, 'Buona domenica '+nome+'! Per te 1 '+PointsName+'!\n\n'+Utente().infoUser(utenteSorgente), parse_mode='markdown',reply_markup=hideBoard)


    def update_table_entry(self, table_class, filter_column, filter_value, update_dict):
        session = self.Session()
        table_entry = session.query(table_class).filter_by(**{filter_column: filter_value}).first()
        for key, value in update_dict.items():
            setattr(table_entry, key, value)
        session.commit()
        session.close()

    def update_user(self, chatid, kwargs):
        self.update_table_entry(Utente, "id_telegram", chatid, kwargs)

    def update_domenica(self, chatid, kwargs):
        self.update_table_entry(Domenica, "utente", chatid, kwargs)
    
    def update_steam(self, steamkey, kwargs):
        self.update_table_entry(Steam, "steam_key", steamkey, kwargs)

    def update_livello(self, id, kwargs):
        self.update_table_entry(Livello, "id", id, kwargs) 
    
    def update_gameuser(self, chatid, kwargs):
        self.update_table_entry(GiocoUtente, "id_telegram", chatid, kwargs) 

def create_table(engine):
    Base.metadata.create_all(engine)

class GiocoUtente(Base):
    __tablename__ = "giocoutente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer)
    piattaforma = Column('piattaforma', String)
    nome        = Column('nome', String)

    def CreateGiocoUtente(self,id_telegram,piattaforma,nomegioco):
        session = Database().Session()
        exist = session.query(GiocoUtente).filter_by(id_telegram = id_telegram,piattaforma=piattaforma).first()
        if exist is None:
            try:
                giocoutente = GiocoUtente()
                giocoutente.id_telegram     = id_telegram
                giocoutente.piattaforma     = piattaforma
                giocoutente.nome            = nomegioco
                session.add(giocoutente)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return False
        else:
            Database().update_gameuser(id_telegram,{'piattaforma':piattaforma,'gioco':nomegioco})
        return True

    def getGiochiUtente(self, id_telegram):
        session = Database().Session()
        giochiutente = session.query(GiocoUtente).filter_by(id_telegram=id_telegram).all()
        session.close()
        return giochiutente

    def delPiattaformaUtente(self,id_telegram,piattaforma,nome):
        session = Database().Session()
        giocoutente = session.query(GiocoUtente).filter_by(id_telegram=id_telegram,piattaforma=piattaforma,nome=nome).first()
        print(giocoutente.id_telegram,giocoutente.piattaforma,giocoutente.nome)
        session.delete(giocoutente)
        session.commit()
        session.close()      

class Utente(Base):
    __tablename__ = "utente"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_Telegram', Integer, unique=True)
    nome  = Column('nome', String(32))
    cognome = Column('cognome', String(32))
    username = Column('username', String(32), unique=True)
    exp = Column('exp', Integer)
    points = Column('money', Integer)
    livello = Column('livello', Integer)
    vita = Column('vita', Integer)
    premium = Column('premium', Integer)
    livello_selezionato = Column('livello_selezionato',Integer)
    start_tnt = Column('start_tnt',DateTime)
    end_tnt = Column('end_tnt',DateTime)
    scadenza_premium = Column('scadenza_premium',DateTime)
    abbonamento_attivo =  Column('abbonamento_attivo',Integer)

    def CreateUser(self,id_telegram,username,name,last_name):

        session = Database().Session()
        exist = session.query(Utente).filter_by(id_telegram = id_telegram).first()
        if exist is None:
            try:
                utente = Utente()
                utente.username     = username
                utente.nome         = name
                utente.id_telegram  = id_telegram
                utente.cognome      = last_name
                utente.vita         = 50
                utente.exp          = 0
                utente.livello      = 1
                utente.points       = 5
                utente.premium      = 0
                utente.livello_selezionato = 1
                utente.start_tnt = datetime.datetime.now()+relativedelta(month=1)
                utente.end_tnt = datetime.datetime.now()
                utente.scadenza_premium = datetime.datetime.now()
                utente.abbonamento_attivo = 0
                session.add(utente)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return False
        elif exist.username!=username:
            Database().update_user(id_telegram,{'username':username,'nome':name,'cognome':last_name})
        return True

    def getUtente(self, target):
        session = Database().Session()
        utente = None
        target = str(target)

        if target.startswith('@'):
            utente = session.query(Utente).filter_by(username=target).first()
        else:
            chatid = int(target) if target.isdigit() else None
            if chatid is not None:
                utente = session.query(Utente).filter_by(id_telegram=chatid).first()

        session.close()
        return utente
    
    def checkUtente(self, message):
        if message.chat.type == "group" or message.chat.type == "supergroup":
            chatid =        message.from_user.id
            username =      '@'+message.from_user.username
            name =          message.from_user.first_name
            last_name =     message.from_user.last_name
        elif message.chat.type == 'private':
            chatid = message.chat.id
            username = '@'+str(message.chat.username)
            name = message.chat.first_name
            last_name = message.chat.last_name
        Utente.CreateUser(Utente,id_telegram=chatid,username=username,name=name,last_name=last_name)
    
    def isAdmin(self,utente):
        session = Database().Session()
        if utente:
            exist = session.query(Admin).filter_by(id_telegram = utente.id_telegram).first()
            return False if exist is None else True
        else:
            return False
    
    def getUsers(self):
        session = Database().Session()
        users = session.query(Utente).all()
        print('N. utenti: ',len(users))
        return users

    def getUsernameAtLeastName(self,utente):
        if utente is not None:
            if utente.username is None:
                nome = utente.nome
            else: 
                nome = utente.username
            return nome
        else:
            return "Nessun nome"

    def infoUser(self, utenteSorgente):
        if not utenteSorgente:
            return "L'utente non esiste"

        utente = Utente().getUtente(utenteSorgente.id_telegram)
        infoLv = Livello().infoLivello(utente.livello)
        selectedLevel = Livello().infoLivelloByID(utente.livello_selezionato)
        giochiutente = GiocoUtente().getGiochiUtente(utente.id_telegram)

        nome_utente = utente.nome if utente.username is None else utente.username
        answer = f"🎖 Utente Premium\n" if utente.premium == 1 else ''
        answer += f"✅ Abbonamento attivo (fino al {str(utenteSorgente.scadenza_premium)[:11]})\n" if utente.abbonamento_attivo == 1 else ''

        if infoLv is not None:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            answer += f"*💪🏻 Exp*: {utente.exp}/{infoLv.exp_to_lv}\n"
            answer += f"*🎖 Lv. *{utente.livello} [{selectedLevel.nome}]({selectedLevel.link_img})\n"
            answer += f"*👥 Saga: *{selectedLevel.saga}\n"
        else:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            answer += f"*💪🏻 Exp*: {utente.exp}\n"
            answer += f"*🎖 Lv. *{utente.livello}\n"

        if giochiutente:
            answer += '\n\n👾 Nome in Game 👾\n'
            answer += '\n'.join(f"*🎮 {giocoutente.piattaforma}:* `{giocoutente.nome}`" for giocoutente in giochiutente)

        return answer

    def addRandomExp(self,user,message):
        exp = random.randint(1,5)
        self.addExp(user,exp)
 
    def addExp(self,utente,exp):
        Database().update_user(utente.id_telegram,{'exp':utente.exp+exp})

    def addPoints(self, utente, points):  
        try: 
            Database().update_user(utente.id_telegram,{'points':int(utente.points) + int(points)})
        except Exception as e:
            print(e)
            Database().update_table_entry(Utente, "username", utente.username, {'points':int(utente.points) + int(points)})


    def donaPoints(self,utenteSorgente,utenteTarget,points):
        points = int(points)
        if points>0:
            if int(utenteSorgente.points)>=points:
                self.addPoints(utenteTarget,points)
                self.addPoints(utenteSorgente,points*-1)
                return utenteSorgente.username+" ha donato "+str(points)+ " "+PointsName+ " a "+utenteTarget.username+ "! ❤️"
            else:
                return PointsName+" non sufficienti"
        else:
            return "Non posso donare "+PointsName+" negativi"
    ########################### CASSE WUMPA
    def tnt_end(self,utente):
        timestamp = datetime.datetime.now() 
        Database().update_user(utente.id_telegram,{
            'end_tnt':timestamp,
            }
        )


    def isTntExploded(self,utente):
        session = Database().Session()
        self.tnt_end(utente)
        tnt =  session.query(Utente).filter_by(id_telegram=utente.id_telegram).first()
        if tnt.end_tnt is not None and tnt.start_tnt is not None:
            difftime = tnt.end_tnt-tnt.start_tnt
            res = False,difftime
            if difftime.seconds>3:
                res = True,difftime
            else:
                res = False,difftime

        else:
            res = False,None
        Database().update_user(utente.id_telegram,{
            'start_tnt':None,
            'end_tnt': None
            }
        )
        return res
    """
    def tnt_start(self,utente,message):
        sti = open('Stickers/TNT.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        bot.reply_to(message, "💣 Ops!... Hai calpestato una Cassa TNT! Scrivi entro 3 secondi per evitarla!")

        timestamp = datetime.datetime.now()
        Database().update_user(utente.id_telegram,{
            'start_tnt':timestamp,
            'end_tnt': None
            }
        )
    
    
        
    def nitroExploded(self,utente,message):
        sti = open('Stickers/Nitro.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        exp_persi = random.randint(1,50)*-1
        wumpa_persi = random.randint(1,5)*-1
        #punti.addExp(utenteSorgente,exp_persi)
        self.addPoints(utente,wumpa_persi)
        bot.reply_to(message, "💥 Ops!... Hai calpestato una Cassa Nitro! Hai perso "+str(wumpa_persi)+" "+PointsName+"! \n\n"+Utente().infoUser(utente),parse_mode='markdown')

    def cassaWumpa(self,utente,message):
        sti = open('Stickers/Wumpa_create.webp', 'rb')
        bot.send_sticker(message.chat.id,sti)
        wumpa_extra = random.randint(1,5)
        #exp_extra = random.randint(1,50)
        #punti.addExp(utenteSorgente,exp_extra)
        self.addPoints(utente,wumpa_extra)
        bot.reply_to(message, "📦 Hai trovato una cassa con "+str(wumpa_extra)+" "+PointsName+"!\n\n"+Utente().infoUser(utente),parse_mode='markdown')
    """
    def checkTNT(self,message,utente):
        chatid = message.from_user.id
        utente = Utente().getUtente(chatid)
        exploded,intime=Utente().isTntExploded(utente)
        if exploded:
            utente  = Utente().getUtente(chatid)
            exp_persi = random.randint(1,25)*-1
            wumpa_persi = random.randint(1,5)*-1
            #self.addExp(utente,exp_persi) 
            self.addPoints(utente,wumpa_persi)
            bot.reply_to(message,'💥 TNT esplosa!!! (Ci hai messo '+str(intime.seconds)+') secondi per evitarla e hai perso '+str(wumpa_persi)+' '+PointsName+'!'+'\n\n'+Utente().infoUser(utente),parse_mode='markdown')
        elif exploded==False:
            if intime is not None:
                bot.reply_to(message,'🎉 TNT evitata!!!! (Ci hai messo '+str(intime.seconds)+') secondi'+'\n\n'+Utente().infoUser(utente),parse_mode='markdown')



    
class Domenica(Base):
    __tablename__ = "domenica"
    id = Column(Integer, primary_key=True)
    last_day = Column('last_day', Date)
    utente = Column('utente', Integer, unique=True)

class Steam(Base):
    __tablename__ = "steam"
    id = Column(Integer, primary_key=True)
    titolo = Column('titolo',String(64))
    titolone = Column('titolone',Boolean)
    preso_da = Column('preso_da',String(64))
    steam_key = Column('steam_key', String(32),unique=True)

   
    def buySteamGame(self, probabilita):
        from sqlalchemy import func
        session = Database().Session()
        is_sculato = random.randint(1, 100) > (100 - probabilita)
        gameList = session.query(Steam).filter(Steam.preso_da=='').filter_by(titolone=is_sculato)
        game = gameList.order_by(func.random()).first()
        return game, is_sculato

    def buyBronzeGame(self):
        return self.buySteamGame(10)

    def buySilverGame(self):
        return self.buySteamGame(50)

    def buyGoldGame(self):
        return self.buySteamGame(100)

    def buyPlatinumGame(self):
        session = Database().Session()
        gameList = session.query(Steam).filter(Steam.preso_da!='').all()
        return gameList,100
        
    def selectSteamGame(self, gameTitle):
        session = Database().Session()
        game = session.query(Steam).filter_by(titolo=gameTitle).first()
        return game
    
    def steamCoin(self,message):
        utente = Utente().getUtente(message.chat.id)
        if utente.premium == 1:
            coin_types = {
                'Bronze Coin'   : {'costo': -50 , 'game_method': self.buyBronzeGame     , 'sti_path': 'Stickers/bronze.webp'},
                'Silver Coin'   : {'costo': -100, 'game_method': self.buySilverGame     , 'sti_path': 'Stickers/silver.webp'},
                'Gold Coin'     : {'costo': -150, 'game_method': self.buyGoldGame       , 'sti_path': 'Stickers/gold.webp'},
                'Platinum Coin' : {'costo': -200, 'game_method': self.buyPlatinumGame   , 'sti_path': 'Stickers/platinum.webp'},
            }
            for coin_type, info in coin_types.items():
                if coin_type in message.text:
                    costo = info['costo']
                    game, sculato = info['game_method']()
                    sti = open(info['sti_path'], 'rb')
                    bot.send_sticker(message.chat.id, sti)
                    if coin_type == 'Platinum Coin':
                        markup = types.ReplyKeyboardMarkup()
                        for g in game:
                            markup.add(g.titolo)
                        msg = bot.reply_to(message,'Scegli il gioco',reply_markup=markup)
                        bot.register_next_step_handler(msg, self.selectPlatinumSteamGame)
                    else:
                        self.sendSteamGame(costo, message, game, sculato)
                    break
        else:
            bot.reply_to(message, "Devi prima essere un Utente Premium\n\n" + Utente().infoUser(utente))

    def selectPlatinumSteamGame(self,message):
        game = self.selectSteamGame(message.text)
        self.sendSteamGame(-200,message,game,100)

    def sendSteamGame(self,costo,message,game,sculato):
        utente = Utente().getUtente(message.chat.id)
        if utente.points>costo*-1:
            Utente().addPoints(utente,costo)
            risposta = "`"+game.titolo+"`\n*Steam Key*: `"+game.steam_key+"`"
            if sculato == True:
                bot.reply_to(message,"Complimenti! 🎉 Hai vinto un titolone 🎉!\n"+risposta,parse_mode="Markdown",reply_markup=Database().startMarkup(utente))
            else:
                bot.reply_to(message,"Complimenti! 🎉 Ti sei aggiudicato: \n"+risposta,parse_mode="Markdown",reply_markup=Database().startMarkup(utente))
            Database().update_steam(game.steam_key,{'preso_da': utente.id_telegram})
        else:
            bot.reply_to(message,"Mi dispiace, ti servono "+str(costo*-1)+" "+PointsName)
        
    def steamMarkup(self):
        markup = types.ReplyKeyboardMarkup()
        markup.add('🥉 Bronze Coin (10% di chance di vincere un titolone casuale)')        
        markup.add('🥈 Silver Coin (50% di chance di vincere un titolone casuale)')        
        markup.add('🥇 Gold Coin (100% di chance di vincere un titolone casuale)')        
        markup.add('🎖 Platinum Coin (Gioco a scelta)')
        return markup

class NomiGiochi(Base):
    __tablename__ = "nomigiochi"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)
    id_nintendo = Column('id_nintendo',String(256))
    id_ps = Column('id_ps',String(256))
    id_xbox = Column('id_xbox',String(256))
    id_steam = Column('id_steam',String(256))

class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    id_telegram = Column('id_telegram',Integer)

class Livello(Base):
    __tablename__ = "livello"
    id = Column('id',Integer, primary_key=True)
    livello = Column('livello',Integer)
    exp_to_lv = Column('exp_to_lv',Integer)
    nome  = Column('nome', String(32))
    link_img = Column('link_img',String(128))
    saga = Column('saga',String(128))
    lv_premium = Column('lv_premium',Integer)

    def getLvByExp(self, exp):
        lv = 0
        for exp_to_lvl in livelli:
            if exp >= exp_to_lvl:
                lv = lv + 1
        return lv

    def addLivello(self, lvl, nome, exp_to_lv, link_img, saga, lv_premium):
        session = Database().Session()
        exist = session.query(Livello).filter_by(livello=lvl, lv_premium=lv_premium).first()
        if exist is None:
            try:
                livello = Livello()
                livello.livello = lvl
                livello.nome = nome
                livello.exp_to_lv = exp_to_lv
                livello.link_img = link_img
                livello.saga = saga
                livello.lv_premium = lv_premium
                session.add(livello)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return True
        else:
            Database().update_livello(exist.id, {'nome': nome, 'exp_to_lv': exp_to_lv, 'link_img': link_img, 'saga': saga, 'lv_premium': lv_premium})
            return False

    def infoLivello(self, livello):
        session = Database().Session()
        livello = session.query(Livello).filter_by(livello=livello).first()
        return livello

    def infoLivelloByID(self, livelloid):
        session = Database().Session()
        livello = session.query(Livello).filter_by(id=livelloid).first()
        return livello

    def getLevels(self):
        session = Database().Session()
        lvs = session.query(Livello).order_by(asc(Livello.livello)).all()
        session.close()
        return lvs

    def getLevels(self, premium=None):
        session = Database().Session()
        if premium is None:
            lvs = session.query(Livello).order_by(asc(Livello.livello)).all()
        elif premium:
            lvs = session.query(Livello).filter_by(lv_premium=1).order_by(asc(Livello.livello)).all()
        else:
            lvs = session.query(Livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        session.close()
        return lvs

    def getLevelPremium(self, lv):
        session = Database().Session()
        lvs = session.query(Livello).filter_by(livello=lv, lv_premium=1).first()
        return lvs
    
    def getLevel(self, lv):
        session = Database().Session()
        lvs = session.query(Livello).filter_by(livello=lv, lv_premium=0).first()
        return lvs

    def GetLevelByNameLevel(self,nameLevel):
        session = Database().Session()
        livello = session.query(Livello).filter_by(nome = nameLevel).first()
        return livello 

    def setSelectedLevel(self,utente,level,lv_premium):
        session = Database().Session()
        livello = session.query(Livello).filter_by(livello = level,lv_premium=lv_premium).first()
        Database().update_user(utente.id_telegram,{'livello_selezionato':livello.id})

    
    def listaLivelliDisponibili(self,utente):
        livelloAttuale = utente.livello
        session = Database().Session()
        if utente.premium==1:
            livelli = session.query(Livello).filter(Livello.livello<utente.livello).order_by(asc(Livello.livello)).all()
        else:
            livelli = session.query(Livello).filter(Livello.livello<utente.livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        return livelli
    
    def listaLivelliNormali(self):
        session = Database().Session()
        livelli = session.query(Livello).filter_by(lv_premium=0).order_by(asc(Livello.livello)).all()
        return livelli

    def listaLivelliPremium(self):
        session = Database().Session()
        livelli = session.query(Livello).filter_by(lv_premium=1).order_by(asc(Livello.livello)).all()
        return livelli

    def checkUpdateLevel(self,utenteSorgente,message):
        lv = Livello().getLvByExp(utenteSorgente.exp)
        if lv>utenteSorgente.livello:
            Database().update_user(utenteSorgente.id_telegram,{'livello':lv})
            lvObj = Livello().getLevel(lv)
            lbPremiumObj = Livello().getLevelPremium(lv)
            bot.reply_to(message,"Complimenti! 🎉 Sei passato al livello "+str(lv)+"! Hai sbloccato il personaggio ["+lvObj.nome+"]("+lvObj.link_img+"), puoi attivarlo scrivendo a @aROMaGameBot 🎉\n\n"+Utente().infoUser(utenteSorgente),parse_mode='markdown')
            bot.reply_to(message,"È anche disponibile il personaggio ["+lbPremiumObj.nome+"]("+lbPremiumObj.link_img+"), puoi attivarlo scrivendo a @aROMaGameBot!",parse_mode='markdown')
            if lv % 5== 0:
                if lv==5:
                    add = 40
                elif lv==10:
                    add = 60
                elif lv==15:
                    add = 80
                elif lv==20:
                    add = 100
                elif lv==25:
                    add = 120
                elif lv==30:
                    add = 150
                elif lv==35:
                    add = 200
                elif lv==40:
                    add = 250
                else:
                    add = 250
                Utente().addPoints(utenteSorgente,add)
                bot.reply_to(message,f"Complimenti per questo traguardo! Per te {str(add)} {PointsName}! 🎉\n\n{Utente().infoUser(utenteSorgente)}",parse_mode='markdown')

class GameInfo(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    platform = Column(String, nullable=True)
    genre = Column(Text, nullable=True)  # Changed to Text to store multiple genres
    description = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    region = Column(String, nullable=True)  # Added region
    message_link = Column(String, nullable=False,unique=True)

    @staticmethod
    def insert_from_dict(data):
        session = Database().Session()

        def join_field(data, key):
            value = data.get(key, '')
            return ', '.join(value if isinstance(value, list) else [value])


        # Create a new GameInfo instance
        game = GameInfo(
            title=data.get('titolo'),
            platform=join_field(data, 'piattaforma'),
            genre=join_field(data, 'genere'),
            description=data.get('descrizione'),
            language=join_field(data, 'lingua'),
            year=data.get('anno'),
            region=join_field(data, 'regione'),
            message_link=data.get('message_link')
        )



        # Add to the session and commit
        session.add(game)
        session.commit()

    @staticmethod
    def insert_error_data(message_link,content,e):
        message_link = message_link.replace("\n","")
        content = content.replace("\n","")
        e = str(e).replace("\n","")
        error_log_file = 'error_log.csv'
        file_exists = os.path.isfile(error_log_file)
        try:
            with open(error_log_file, 'a', encoding='utf-8') as f:
                # Scrivi l'intestazione solo se il file è stato appena creato
                if not file_exists:
                    f.write('message_link|message_text|error\n')
                # Scrivi la riga nel file CSV
                f.write(f'{message_link}|{content}|{str(e)}\n')
                f.flush()  # Forza la scrittura su disco
        except Exception as file_error:
            print("Errore durante la scrittura del file:", str(file_error))

    @staticmethod
    def find_error_by_message_link(message_link, error_log_file='error_log.csv'):
        # Controlla se il file di log degli errori esiste
        if not os.path.isfile(error_log_file):
            return False
        
        try:
            with open(error_log_file, 'r', encoding='utf-8') as f:
                # Salta l'intestazione (la prima riga)
                next(f)
                for line in f:
                    # Divide la riga in colonne usando la virgola come separatore
                    columns = line.strip().split('|')
                    if columns[0] == message_link:
                        return True
            return False
        except Exception as e:
            print("Errore durante la lettura del file:", str(e))
            return False

    @staticmethod
    def find_by_message_link(message_link):
        session = Database().Session()
        try:
            # Query the database for the game with the given message_link
            game = session.query(GameInfo).filter_by(message_link=message_link).first()
            return game
        except Exception as e:
            print(f"Error: {e}")
            return None
        
    @staticmethod
    def find_by_title(title):
        session = Database().Session()
        try:
            # Query the database for the game with the given message_link
            game = session.query(GameInfo).filter(GameInfo.title.like(f"{title}%")).first()
            return game
        except Exception as e:
            print(f"Error: {e}")
            return None



    @staticmethod
    def search_games(query):
        session = Database().Session()
        try:
            # Recupera tutte le piattaforme uniche utilizzando SQLAlchemy
            platforms = session.query(distinct(GameInfo.platform)).all()
            platforms = [p[0].lower() for p in platforms if p[0]]

            # Estrai piattaforme dal testo della query
            query_words = query.lower().split()
            platform_filters = [word for word in query_words if word.lower() in platforms]

            # Rimuovi le piattaforme dalle parole di ricerca
            stop_words = {'il', 'la', 'lo', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra'}

            search_terms = [word for word in query_words if word not in platform_filters and word not in stop_words]

            # Costruisci la query SQL utilizzando SQLAlchemy
            sql_query = session.query(GameInfo)

            # Filtra per piattaforme
            if platform_filters:
                platform_filter = or_(*[GameInfo.platform.ilike(f'%{pf}%') for pf in platform_filters])
                sql_query = sql_query.filter(platform_filter)

            # Aggiungi le condizioni di ricerca per titolo, descrizione, e genere
            for term in search_terms:
                search_filter = or_(
                    *[GameInfo.title.ilike(f'%{term}%')]
                    #,*[GameInfo.description.ilike(f'%{term}%') for term in search_terms],
                    #,*[GameInfo.genre.ilike(f'%{term}%') for term in search_terms]
                )
                sql_query = sql_query.filter(search_filter)

            # Esegui la query
            results = sql_query.all()

            return results
        except Exception as e:
            print(f"Errore durante la ricerca: {e}")
            return []

class Abbonamento:

    def __init__(self):
        self.bot = bot
        self.CANALE_LOG = CANALE_LOG
        self.PointsName = PointsName
        self.COSTO_PREMIUM       =    250
        self.COSTO_MANTENIMENTO  =    50
        self.PROMO = ""

        # CHECK PROMO
        oggi = datetime.date.today()

        for promozione in PROMOZIONI:
            periodo_inizio = datetime.datetime.strptime(PROMOZIONI[promozione]["periodo_inizio"], "%Y%m%d").date()
            periodo_fine = datetime.datetime.strptime(PROMOZIONI[promozione]["periodo_fine"], "%Y%m%d").date()
            if oggi >= periodo_inizio and oggi <= periodo_fine:
                self.COSTO_PREMIUM       = PROMOZIONI[promozione]["COSTO_PREMIUM"]
                self.COSTO_MANTENIMENTO  = PROMOZIONI[promozione]["COSTO_MANTENIMENTO"]
                self.PROMO               = PROMOZIONI[promozione]["nome"]

    def stop_abbonamento(self, utente):
        Database().update_user(utente.id_telegram, {'abbonamento_attivo': 0})
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha interrotto l'abbonamento #Premium")

    def attiva_abbonamento(self, utente):
        Database().update_user(utente.id_telegram, {'abbonamento_attivo': 1})
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha attivato l'abbonamento #Premium")

    def stop_premium(self, utente):
        Database().update_user(utente.id_telegram, {'premium': 0})
        Livello().setSelectedLevel(utente, utente.livello, 0)
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} non è più #Premium")

    def rinnova_premium(self, utente):
        scadenza = datetime.datetime.now() + relativedelta(months=+1)
        Database().update_user(utente.id_telegram, {
            'points': utente.points - self.COSTO_MANTENIMENTO,
            'premium': 1,
            'abbonamento_attivo': 1,
            'scadenza_premium': scadenza
        })
        utente = Utente().getUtente(utente.id_telegram)
        self.bot.send_message(
            utente.id_telegram,
            f"Il tuo abbonamento è stato correttamente rinnovato mangiando {self.COSTO_MANTENIMENTO} {self.PointsName}\n\n{Utente().infoUser(utente)}",
            parse_mode='markdown'
            ,reply_markup=Database().startMarkup(utente)
        )
        self.bot.send_message(self.CANALE_LOG, f"L'utente {Utente().getUsernameAtLeastName(utente)} ha rinnovato l'abbonamento #Premium"+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')

    def buyPremium(self, utente):
        scadenza = datetime.datetime.now()+relativedelta(months=+1)
        rinnovo = "\n\nOgni prossimo mese costerà solo "+str(self.COSTO_MANTENIMENTO)+" "+self.PointsName
        if utente.premium==1:
            self.attiva_abbonamento(utente)
            self.bot.send_message(utente.id_telegram, "Sei già Utente Premium fino al "+str(utente.scadenza_premium)[:10]+rinnovo+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        elif utente.premium==0 and utente.points>=self.COSTO_PREMIUM:
            items = {
                'points': utente.points-self.COSTO_PREMIUM,
                'premium': 1,
                'abbonamento_attivo':1,
                'scadenza_premium':scadenza
            }
            Database().update_user(utente.id_telegram,items)
            self.bot.send_message(utente.id_telegram, "Complimenti! Sei ora un Utente Premium fino al "+str(utente.scadenza_premium)[:10]+rinnovo+Utente().infoUser(utente),reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        else:
            messaggio =  f"Mi dispiace, ti servono {self.COSTO_PREMIUM} {self.PointsName} {Utente().infoUser(utente)}"
            self.bot.send_message(utente.id_telegram,messaggio,reply_markup=Database().startMarkup(utente),parse_mode='markdown')

    def buyPremiumExtra(self, utente):
        rinnovo = "\n\nOgni prossimo mese costerà solo " + str(self.COSTO_MANTENIMENTO) + " " + self.PointsName
        if utente.premium == 1 and utente.points>=self.COSTO_MANTENIMENTO:
            items = {
                'points': utente.points - self.COSTO_MANTENIMENTO,
                'premium': 1,
                'abbonamento_attivo': 1,
                'scadenza_premium': utente.scadenza_premium + relativedelta(months=+1)
            }
            Database().update_user(utente.id_telegram, items)       
            utente = Utente().getUtente(utente.id_telegram)     
            self.bot.send_message(utente.id_telegram, "Hai rinnovato anticipatamente il costo dell'abbonamento, è quindi valido fino al " + str(utente.scadenza_premium)[:10] + rinnovo+Utente().infoUser(utente), reply_markup=Database().startMarkup(utente),parse_mode='markdown')
        else:
            self.bot.send_message(utente.id_telegram, f"Devi avere {str(self.COSTO_MANTENIMENTO)} {PointsName}", reply_markup=Database().startMarkup(utente))

    def checkScadenzaPremium(self,utente):
        oggi = datetime.datetime.now()
        try:
            if oggi>utente.scadenza_premium:
                if utente.abbonamento_attivo==0 and utente.premium==1:
                    self.stop_premium(utente)
                elif utente.abbonamento_attivo==1:
                    if utente.points>=self.COSTO_MANTENIMENTO:
                        self.rinnova_premium(utente)
                    else:
                        self.stop_premium(utente)
                        self.stop_abbonamentoPremium(utente)
        except Exception as e:
            print(str(e))
    
    def checkScadenzaPremiumToAll(self):
        listaUtenti = Utente().getUsers()
        for utente in listaUtenti:
            self.checkScadenzaPremium(utente)
    
    def listaPremium(self):
        session = Database().Session()
        listaPremium = session.query(Utente).filter_by(premium=1).order_by(Utente.points.desc()).all()
        return listaPremium

class Collezionabili(Base):
    __tablename__ = "collezionabili"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_telegram = Column(String, nullable=False)
    oggetto = Column(String, nullable=False)
    data_acquisizione = Column(DateTime, nullable=False)
    quantita = Column(Integer, nullable=False)
    data_utilizzo = Column(DateTime, nullable=True)


    def CreateCollezionabile(self,id_telegram,item, quantita=1):
        session = Database().Session()
        try:
            collezionabile = Collezionabili()
            collezionabile.id_telegram         = id_telegram
            collezionabile.oggetto             = item
            collezionabile.data_acquisizione   = datetime.datetime.today()
            collezionabile.quantita            = quantita
            collezionabile.data_utilizzo       = None
            print(collezionabile.id_telegram)
            session.add(collezionabile)
            session.commit()
            return True
        except:
            session.rollback()
            return False
        finally:
            session.close()

    def getInventarioUtente(self,id_telegram):
        session = Database().Session()
        #inventario = session.query(Collezionabili).filter_by(id_telegram=id_telegram,data_utilizzo=None).group_by(Collezionabili.oggetto).order_by(Collezionabili.oggetto).all()
        from sqlalchemy import func

        inventario = session.query(
            Collezionabili.oggetto,
            func.count(Collezionabili.oggetto).label('quantita')
        ).filter_by(
            id_telegram=id_telegram, 
            data_utilizzo=None
        ).group_by(
            Collezionabili.oggetto
        ).order_by(
            Collezionabili.oggetto
        ).all()

        return inventario

    def getItemByUser(self,id_telegram,nome_oggetto):
        session = Database().Session()
        from sqlalchemy import func

        oggetto = session.query(
            Collezionabili.oggetto,
            func.count(Collezionabili.oggetto).label('quantita')
        ).filter_by(
            id_telegram=id_telegram, 
            oggetto=nome_oggetto,
            data_utilizzo=None
        ).group_by(
            Collezionabili.oggetto
        ).order_by(
            Collezionabili.oggetto
        ).first()

        return oggetto
    
    def usaOggetto(self,id_telegram,oggetto):
        session = Database().Session()
        collezionabile = session.query(Collezionabili).filter_by(id_telegram=id_telegram,oggetto=oggetto).first()
        collezionabile.data_utilizzo = datetime.datetime.today()
        session.commit()
        session.close()
        print(f'{id_telegram} ha usato {oggetto}')


    def maybeDrop(self, message):
        if message.chat.type == "group" or message.chat.type == "supergroup":
            id_telegram = message.from_user.id
            with open('items.csv', 'r') as f:
                items = [
                    line.split(',')
                    for line in f.readlines()
                ]
            #indice_oggetto = random.randint(1, len(items) - 1)
            for indice_oggetto in range(1,len(items)):
                obj = items[indice_oggetto]
                tento_oggetto = {}
                tento_oggetto['nome'] = obj[0]
                tento_oggetto['rarita'] = int(obj[1])
                tento_oggetto['massimo_numero_per_drop'] = int(obj[2])
                tento_oggetto['max_per_persona'] = int(obj[3])
                tento_oggetto['sticker'] = obj[4].replace('\n','')

                oggetto = self.getItemByUser(id_telegram, tento_oggetto['nome'])
                quantita = random.randint(1,tento_oggetto['massimo_numero_per_drop'])
                if oggetto:
                    if oggetto.oggetto==tento_oggetto['nome']:
                        quantita+=1
                        if oggetto.quantita==int(tento_oggetto['max_per_persona']):
                            return 0

                culo = random.randint(1,tento_oggetto['rarita'])
                if culo==tento_oggetto['rarita']:
                    sti = open(f"Stickers/{tento_oggetto['sticker']}", 'rb')
                    bot.send_sticker(message.chat.id, sti)
                    self.triggerDrop(message,tento_oggetto,quantita)

                    
    def triggerDrop(self,message,oggetto,quantita):
        id_telegram = message.from_user.id
        utente = Utente().getUtente(id_telegram)
        def tnt_start(utente,message):
            #sti = open('Stickers/TNT.webp', 'rb')
            #bot.send_sticker(message.chat.id,sti)
            bot.reply_to(message, "💣 Ops!... Hai calpestato una Cassa TNT! Scrivi entro 3 secondi per evitarla!")

            timestamp = datetime.datetime.now()
            Database().update_user(utente.id_telegram,{
                'start_tnt':timestamp,
                'end_tnt': None
                }
            )


        def nitroExploded(utente,message):
            wumpa_persi = random.randint(1,5)*-1
            #punti.addExp(utenteSorgente,exp_persi)
            Utente().addPoints(utente,wumpa_persi)
            bot.reply_to(message, "💥 Ops!... Hai calpestato una Cassa Nitro! Hai perso "+str(wumpa_persi)+" "+PointsName+"! \n\n"+Utente().infoUser(utente),parse_mode='markdown')

        def cassaWumpa(utente,message):
            #sti = open('Stickers/Wumpa_create.webp', 'rb')
            #bot.send_sticker(message.chat.id,sti)
            wumpa_extra = random.randint(1,5)
            Utente().addPoints(utente,wumpa_extra)
            bot.reply_to(message, "📦 Hai trovato una cassa con "+str(wumpa_extra)+" "+PointsName+"!\n\n"+Utente().infoUser(utente),parse_mode='markdown')
        
        def drago(utente,message):
            pass
            """
            id_telegram=utente.id_telegram
            sfere_shenron = session.query(Collezionabili).filter_by(id_telegram=id_telegram, oggetto.like('%La Sfera del Drago Shenron%').all()
            if len(sfere_shenron)==7:
                # evoca drago shenron
                pass

            sfere_porunga = session.query(Collezionabili).filter_by(id_telegram=id_telegram, oggetto.like('%La Sfera del Drago Porunga%').all()
            if len(sfere_porunga)==7:
                # evoca drago porunga
                pass
            """
        if oggetto['nome']=='TNT':
            tnt_start(utente,message)
        elif oggetto['nome']=='Nitro':
            nitroExploded(utente,message)
        elif oggetto['nome']=='Cassa':
            cassaWumpa(utente,message)
        elif 'La sfera del Drago' in oggetto['nome']:
            drago(utente,message)
        else:
            self.CreateCollezionabile(id_telegram,tento_oggetto['nome'],quantita)
            bot.reply_to(message,f"Complimenti! Hai ottenuto {oggetto['nome']}")

    
