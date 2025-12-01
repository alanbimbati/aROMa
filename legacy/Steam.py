'''
from random import randint
from sqlalchemy.orm import Session
from model import Utente,Steam,db_connect, create_table
from sqlalchemy.orm import sessionmaker
from settings import *

class Steam:
    def titolone(self, gameList, chance):
        culo = randint(1, 100)
        if culo > (100 - chance):
            sculato = True
            gameList = gameList.filter_by(titolone=True)
        else:
            sculato = False
            gameList = gameList.filter_by(titolone=False)  
        return gameList, sculato
    
    def buySteamGame(self, probabilita):
        session = self.Session()
        steamGames = session.query(Steam).filter(Steam.preso_da!='')
        gameList, sculato = self.titolone(steamGames, probabilita)
        indexGame = randint(1, len(gameList.all()))
        game = gameList.all()[indexGame]
        return game, sculato

    def buyBronzeGame(self):
        return self.buySteamGame(10)

    def buySilverGame(self):
        return self.buySteamGame(50)

    def buyGoldGame(self):
        return self.buySteamGame(100)

    def buyPlatinumGame(self):
        session = self.Session()
        gameList = session.query(Steam).filter(Steam.preso_da!='').all()
        return gameList
        
    def selectSteamGame(self, gameTitle):
        session = self.Session()
        game = session.query(Steam).filter_by(titolo=gameTitle).first()
        return game
    
    def steamCoin(self,message):
        utente = self.getUtente(message.chat.id)
        if utente.premium == 1:
            if 'Bronze Coin' in message.text:
                costo = -50
                game,sculato = self.buyBronzeGame()
                sti = open('Stickers/bronze.webp', 'rb')
                bot.send_sticker(message.chat.id,sti)
                self.sendSteamGame(costo,message,game,sculato)
            elif 'Silver Coin' in message.text:
                costo = -100
                game,sculato = self.buySilverGame()
                sti = open('Stickers/silver.webp', 'rb')
                bot.send_sticker(message.chat.id,sti)
                self.sendSteamGame(costo,message,game,sculato)
            elif 'Gold Coin' in message.text:
                costo = -150
                game,sculato = self.buyGoldGame()
                sti = open('Stickers/gold.webp', 'rb')
                bot.send_sticker(message.chat.id,sti)
                self.sendSteamGame(costo,message,game,sculato)
            elif 'Platinum Coin' in message.text:
                costo = -200
                gameList = self.buyPlatinumGame()
                sti = open('Stickers/platinum.webp', 'rb')
                bot.send_sticker(message.chat.id,sti)
                markup = types.ReplyKeyboardMarkup()
                for game in gameList:
                    markup.add(game.titolo)
                msg = bot.reply_to(message,'Scegli il gioco',reply_markup=markup)
                bot.register_next_step_handler(msg, self.selectPlatinumSteamGame)
        else:
            bot.reply_to(message, "Devi prima essere un Utente Premium"+'\n\n'+self.infoUser(utente))

    def selectPlatinumSteamGame(self,message):
        game = self.selectSteamGame(message.text)
        self.sendSteamGame(200,message,game,100)


    def sendSteamGame(self,costo,message,game,sculato):
        utente = self.getUtente(message.chat.id)
        if utente.points>costo*-1:
            self.addPoints(utente,costo)
            risposta = "`"+game.titolo+"`\n*Steam Key*: `"+game.steam_key+"`"
            if sculato == True:
                bot.reply_to(message,"Complimenti! 🎉 Hai vinto un titolone 🎉!\n"+risposta,parse_mode="Markdown",reply_markup=self.startMarkup(utente))
            else:
                bot.reply_to(message,"Complimenti! 🎉 Ti sei aggiudicato: \n"+risposta,parse_mode="Markdown",reply_markup=self.startMarkup(utente))
            self.update_steam(game.steam_key,{'preso_da': utente.id_telegram})
        else:
            bot.reply_to(message,"Mi dispiace, ti servono "+str(costo*-1)+" "+PointsName)
        
    def steamMarkup(self):
        markup = types.ReplyKeyboardMarkup()
        markup.add('🥉 Bronze Coin (10% di chance di vincere un titolone casuale)')        
        markup.add('🥈 Silver Coin (50% di chance di vincere un titolone casuale)')        
        markup.add('🥇 Gold Coin (100% di chance di vincere un titolone casuale)')        
        markup.add('🎖 Platinum Coin (Gioco a scelta)')
        return markup
    
    def getUtente(self, target):
        session = self.Session()
        utente = None
        target = str(target)
            
        if target.startswith('@'):
            utente = session.query(Utente).filter_by(username = target).first()
        else:
            chatid = target
            if (chatid.isdigit()):
                chatid = int(chatid)
                utente = session.query(Utente).filter_by(id_telegram = chatid).first()
        return utente
'''