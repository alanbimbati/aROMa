from sqlalchemy.sql import functions
from sqlalchemy         import create_engine, false, null, true
from sqlalchemy         import update
from sqlalchemy         import desc,asc
from sqlalchemy.orm     import sessionmaker
from model import Utente,Domenica,Steam,Admin,Livello,Database,Abbonamento, create_table
import datetime
from settings import *
import datetime
from dateutil.relativedelta import relativedelta
import random

class Points:    

    def classifica(self):   
        session = self.Session()
        utenti = session.query(Utente).order_by(desc(Utente.livello),desc(Utente.points),desc(Utente.premium)).all()
        session.close()
        return utenti
        
    def deleteAccount(self,chatid):
        session = self.Session()
        utente = session.query(Utente).filter_by(id_telegram = chatid).first()  
        session.delete(utente)
        session.commit()

    def wumpaStats(self):
        session = self.Session()
        wumpaSupply = session.query(
            functions.sum(Utente.points)
        ).scalar()

        wumpaMax = session.query(
            functions.max(Utente.points)
        ).scalar()

        wumpaMin = session.query(
            functions.min(Utente.points)
        ).scalar()

        numPremium = session.query(
            functions.sum(Utente.premium)
        ).scalar()

        abbonamentiAttivi = session.query(
            functions.sum(Utente.abbonamento_attivo)
        ).scalar()

        numUsers = session.query(functions.count(Utente.id)).scalar()
        return wumpaSupply,wumpaMax,wumpaMin,numUsers,numPremium,abbonamentiAttivi


    def addAdmin(self,utente):
        session = self.Session()
        chatid = utente.id_telegram
        
        exist = session.query(Admin).filter_by(id_telegram = utente.id_telegram).first()
        if exist is None:
            try:
                admin = Admin()
                admin.id_telegram     = chatid
                session.add(admin)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return True
        else:
            return False

    def backup(self):
        doc = open('points.db', 'rb')
        bot.send_document(CANALE_LOG, doc, caption="aROMa #database #backup")
        doc.close()
    
    def restore(self,message):
        try:
            if message.document.file_name=='points.db':
                f = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(f.file_path)
                with open('points.db', 'wb') as new_file:
                    new_file.write(downloaded_file)
                bot.reply_to(message, "Database ripristinato")
        except:
            bot.reply_to(message, "Il db non è corretto")

    def writeClassifica(self,message):
        utenti = self.classifica()
        messaggio = ''
        for i in range(20):
            if len(utenti)>i:
                messaggio += '\n*['+str(i+1)+']* '+Utente.infoUser(utenti[i]) +'\n\n'
        bot.reply_to(message, messaggio, parse_mode='markdown')

    def setCharacter(self,message):
        utente = Utente().getUtente(message.chat.id)  
        selectedLevel = Livello().GetLevelByNameLevel(message.text)
        Livello().setSelectedLevel(utente,selectedLevel.livello,selectedLevel.lv_premium)
        bot.reply_to(message, "Personaggio "+ message.text +" selezionato!"+"\n\n"+Utente().infoUser(utente),parse_mode='markdown',reply_markup=Database.startMarkup(Database,utente))
        #bot.send_message(CANALE_LOG, "L' utente "+Utente().getUsernameAtLeastName(utente)+" ha selezionato il personaggio "+ message.text +"\n\n"+Utente().infoUser(utente),parse_mode='markdown',reply_markup=Database.startMarkup(Database,utente))

    
    def purgeSymbols(self,message):
        if message.text is not None:
            if message.text[0] == '!' or message.text[0] == '/':
                return message.text[1:]
            else:
                return message.text
        else:
            return ""

    def checkBeforeAll(self,message):
        Utente().checkUtente(message)

        if message.chat.type == "group" or message.chat.type == "supergroup":
            chatid = message.from_user.id
            utenteSorgente = Utente().getUtente(chatid)

            Database().checkIsSunday(utenteSorgente,message)
            Utente().checkTNT(message,utenteSorgente)  
            ############## GRUPPO ###################
            if message.chat.id == GRUPPO_AROMA:
                Utente().addRandomExp(utenteSorgente,message)
                Utente().checkCasse(utenteSorgente,message)
        elif message.chat.type == 'private':
            chatid = message.chat.id
        utenteSorgente = Utente().getUtente(chatid)
        Abbonamento().checkScadenzaPremium(utenteSorgente)
        Livello().checkUpdateLevel(utenteSorgente,message)
        utenteSorgente = Utente().getUtente(chatid)

        return utenteSorgente,chatid

    def album(self):
        answer = ''
        answer += 'Inoltrami un gioco dagli album per acquistarlo.'+'\n\n'
        answer += '1️⃣ [PS1](t.me/albumps1): Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '2️⃣ [PS2](t.me/albumps2): Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '3️⃣ [PS3](t.me/albumps3) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '4️⃣ [PS4](t.me/albumps4) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '📲 [PSP](t.me/albumpsp) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '💻 [PC](https://t.me/+_Hmuw95wjwM3ZmY0) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '🐶 [Nintendo](t.me/albumnintendo) Costa 15 '+PointsName+' per gioco'+'\n'
        answer += '📽 [Cinema](t.me/aROMaCinema) Costa 5 '+PointsName+' per film'+'\n'
        answer += '🎖 [Premium](t.me/aROMaPremium) Costa 0 '+PointsName+', canale esclusivo agli utenti Premium.'+'\n\n'
        answer += '[Come guadagnare Frutti Wumpa?](https://t.me/aROMadivideogiochi/2486)'+'\n'
        answer += '[Cosa puoi fare con i Frutti Wumpa?](https://t.me/aROMadivideogiochi/2402)'
        return answer




    def welcome(self,message):
        bot.reply_to(message,self.album(),parse_mode='markdown')
        alreadyExist = Utente.checkUtente(Utente,message)
        if alreadyExist == False:
            bot.reply_to(message, 'Benvenuto su aROMa! Per te 5 '+PointsName+'!', reply_markup=hideBoard)
    
    def isValidUsername(self,username):
        if username[0]=='@':
            return true
        else:
            return false

    def addPointsToUsers(self,utente, message):
        # Verifica che l'utente che richiede l'operazione sia un amministratore
        if not Utente().isAdmin(utente):
            return "Solo gli amministratori possono aggiungere o rimuovere punti"

        # Split del comando in parti, separando l'operazione (+ o -) dai nomi degli utenti
        parts       = message.text.split()
        op          = parts[0][0]
        points      = parts[0][1:]
        points = int(points) if op == '+' else -int(points)
        usernames   = parts[1:]
        # Verifica che il comando sia ben formato
        answer = ''
        if len(usernames) == 0:
            answer += "Comando non valido: specificare almeno un utente\n"
        else:
            # Aggiungi o rimuovi i punti per ogni utente
            for username in usernames:
                try:
                    utente = Utente().getUtente(username)
                    print(utente.username)
                    risposta = 'Complimenti! Hai ottenuto {} {}' if op == '+' else 'Hai mangiato {} deliziosi {}!'
                    Utente().addPoints(utente, points)
                    answer += username+': '+risposta.format(str(points), PointsName)+'\n'
                except Exception as e:
                    answer += f'Errore Telegram: {str(e)}\n'
                    answer +=  'Comando non valido: username ({}) non trovato\n'.format(username)
                try:
                    bot.send_message(utente.id_telegram, risposta.format(str(points), PointsName)+Utente().infoUser(utente),parse_mode='markdown')
                except Exception as e:
                    bot.reply_to(message, risposta.format(str(points), PointsName)+Utente().infoUser(utente),parse_mode='markdown')

        if answer == '': answer='nulla da fare'
        return answer