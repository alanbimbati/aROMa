from telebot import types
from settings import *
from sqlalchemy         import create_engine
from model import Livello, Steam,Utente, Abbonamento, Database
import Points
from telebot import util

@bot.message_handler(content_types=['left_chat_member'])
def esciDalGruppo(message):
    chatid = message.left_chat_member.id
    Database().update_user(chatid,{'points':0})
    bot.send_message(CANALE_LOG, f"I punti dell'utente {Utente().getUsernameAtLeastName()} sono stati azzerati perchè è uscito dal gruppo.")

@bot.message_handler(content_types=['new_chat_members'])
def newmember(message):
    punti = Points.Points()
    punti.welcome(message)

@bot.message_handler(commands=['start'])
def start(message):
    punti = Points.Points()
    punti.welcome(message)
    any(message)

@bot.message_handler(content_types=util.content_type_media)
def any(message):
    punti = Points.Points()
    steam = Steam()
    utenteSorgente,_=punti.checkBeforeAll(message)
    comando = punti.purgeSymbols(message)

    if message.chat.type=='private':
        utente = Utente().getUtente(message.chat.id)

        if hasattr(message.forward_from_chat,'id'):
            buy1game(message)
        elif 'Compra 1 gioco' in message.text:
            bot.reply_to(message, punti.album())
        elif message.text=='🎫 Compra un gioco steam':
            risposta = ''
            risposta += '50 🍑 = 🥉 Bronze Coin: 10% probabilità TITOLONE casuale\n'
            risposta += '100 🍑 = 🥈 Silver Coin: 50% TITOLONE casuale\n'
            risposta += '150 🍑 = 🥇 Gold Coin: 100% TITOLONE casuale\n'
            risposta += '200 🍑 = 🎖 Platinum Coin: TITOLONE a scelta della lista, visibile solo con l\'acquisto del suddetto Coin\n' 
            msg = bot.reply_to(message,risposta,reply_markup=Steam().steamMarkup())
            bot.register_next_step_handler(msg, steam.steamCoin)
        elif message.text.startswith('👤 Scegli il personaggio'):
            punti = Points.Points()
            is_premium = '🎖' in message.text
            livelli_disponibili = Livello().listaLivelliPremium() if is_premium else Livello().listaLivelliNormali()
            markup = types.ReplyKeyboardMarkup()
            for livello in livelli_disponibili:
                markup.add(f"{livello.nome}{'🔓' if utente.livello < livello.livello else ''}")
            msg = bot.reply_to(message, "Seleziona il tuo personaggio", reply_markup=markup)
            bot.register_next_step_handler(msg, punti.setCharacter)
        elif 'Compra abbonamento Premium (1 mese)' in message.text:
            Abbonamento().buyPremium(utenteSorgente)
        elif message.text == '✖️ Disattiva rinnovo automatico':
            Abbonamento().stop_abbonamento(utenteSorgente)
            utenteSorgente = Utente().getUtente(utenteSorgente.id_telegram)
            bot.reply_to(message, 'Abbonamento annullato, sarà comunque valido fino al '+str(utenteSorgente.scadenza_premium),reply_markup=Database().startMarkup(utenteSorgente))
        elif message.text == '✅ Attiva rinnovo automatico':
            Abbonamento().attiva_abbonamento(utenteSorgente)
            utenteSorgente = Utente().getUtente(utenteSorgente.id_telegram)
            bot.reply_to(message, 'Abbonamento attivato, il giorno '+str(utenteSorgente.scadenza_premium)+' si rinnoverà al costo di '+str(COSTO_MANTENIMENTO)+' '+PointsName,reply_markup=Database().startMarkup(utenteSorgente))
        elif 'classifica' in message.text.lower():
            punti.writeClassifica(message)
        else:
            bot.reply_to(message, "Cosa vuoi fare?", reply_markup=Database().startMarkup(utenteSorgente))

    # ADMINistrazione dei punti
    
    if Utente().isAdmin(utenteSorgente):
        # Assegnare punti
        if comando.startswith('+') or comando.startswith('-'):
            bot.reply_to(message,punti.addPointsToUsers(utenteSorgente,message))
        elif comando.lower() == 'restore':
            msg = bot.reply_to(message, 'Inviami il db')
            bot.register_next_step_handler(msg, punti.restore)
        elif comando.startswith('addLivello'):
            comandi = message.text
            comandi = comandi.split('/addLivello')[1:]
            for comando in comandi:
                parametri = comando.split(";")
                livello = int(parametri[1])
                nome = parametri[2]
                exp_to_lvl = int(parametri[3])
                link_img = parametri[4]
                saga = parametri[5]
                lv_premium = parametri[6]
                punti.addLivello(livello,nome,exp_to_lvl,link_img,saga,lv_premium)
        elif comando == 'backup':
            punti.backup()
        elif comando == 'backupall':
            bot.reply_to(message, "Ho finito i backup")
            #backup_all(PREMIUM_CHANNELS['pc'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['nintendo'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['ps4'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['ps3'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['ps2'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['ps1'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['psp'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['horror'],PREMIUM_CHANNELS['tutto'])
            #backup_all(PREMIUM_CHANNELS['hot'],PREMIUM_CHANNELS['tutto'],352)
            #backup_all(PREMIUM_CHANNELS['big_games'],PREMIUM_CHANNELS['tutto'],622)
            #backup_album(PREMIUM_CHANNELS['ps1'],CANALE_LOG)
        elif comando.startswith('checkPremium'):
            punti.checkScadenzaPremiumToAll()

    # COMANDI UTENTI
    if comando.lower().startswith('dona') or comando.lower().startswith('Dona'):
        if len(comando.split())==2:
            points = comando.split()[0][4:]
            utenteTarget = Utente().getUtente(comando.split()[1])
        elif len(comando.split())==3:
            points = comando.split()[1]
            utenteTarget = Utente().getUtente(comando.split()[2])
        else:
            points = 0
            utenteTarget = None
        
        messaggio = punti.donaPoints(utenteSorgente,utenteTarget,points)
        bot.reply_to(message,messaggio+'\n\n'+Utente().infoUser(utenteTarget),parse_mode='markdown')
    elif comando == 'me':
        bot.reply_to(message,Utente().infoUser(utenteSorgente),parse_mode='markdown')
    elif comando.startswith("status"):
        user = Utente().getUtente(comando.split()[1])
        bot.reply_to(message, Utente().infoUser(user),parse_mode='markdown')
    elif comando.startswith("classifica"):
        punti.writeClassifica(message)
    elif comando == 'stats':
        wumpaSupply,wumpaMax,wumpaMin,numUsers = punti.wumpaStats()
        risposta = "<b>Supply: </b>"+str(wumpaSupply)+" "+PointsName+"\n"
        risposta += "<b>WumpaMax: </b>"+str(wumpaMax)+" "+PointsName+"\n"
        risposta += "<b>wumpaMin: </b>"+str(wumpaMin)+" "+PointsName+"\n"
        risposta += "<b>numUsers: </b>"+str(numUsers)+" "+PointsName
        bot.reply_to(message, risposta, parse_mode="HTML")
    elif comando.startswith('premium'):
        listaPremium = Abbonamento().listaPremium()
        messaggio = '🎖 Utenti Premium 🎖\n\n'
        for i, premium in enumerate(listaPremium, start=1):
            messaggio += f'*[{i}]* {punti.infoUser(premium)}\n\n'
        bot.reply_to(message, messaggio, parse_mode='markdown')

    elif comando.startswith('livell'):
        livelli = punti.getLevels()
        messaggio = ''
        for lv in livelli:
            messaggio +=  '*['+str(lv.livello)+']* ['+lv.nome+']('+lv.link_img+')\t ['+lv.saga+']💪 '+str(lv.exp_to_lv)+' exp.\n'
        bot.reply_to(message,messaggio,parse_mode='markdown')
    elif 'album' in comando:
        bot.reply_to(message, punti.album(),parse_mode='markdown')

def sendFileGame(chatid,from_chat,messageid):
    content_type = 'photo'
    while content_type != 'sticker' and content_type=='photo':
        try:
            message = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
            content_type = message.content_type
        except:
            pass
        messageid += 1
    
    while content_type != 'sticker' and content_type!='photo':
        try:
            message = bot.forward_message(chatid, from_chat, messageid, protect_content=True)
            content_type = message.content_type
        except:
            pass
        messageid += 1

def isPremiumChannel(from_chat):
    premium = False
    if from_chat==int(PREMIUM_CHANNELS['tutto']): premium= True
    return premium

def isMiscellaniaChannel(from_chat):
    premium = False
    for i in MISCELLANIA:
        if from_chat==int(MISCELLANIA[i]): premium = True
    return premium

def buy1game(message):

    punti = Points.Points()
    chatid = message.chat.id
    utenteSorgente  = Utente().getUtente(chatid)
    from_chat =  message.forward_from_chat.id

    if from_chat is not None:
        costo = 5 if isMiscellaniaChannel(from_chat) else 15
        messageid = message.forward_from_message_id
        
        if message.content_type=='photo':
            if  utenteSorgente.premium==1 and (isPremiumChannel(from_chat) or isMiscellaniaChannel(from_chat)):
                status = sendFileGame(chatid,from_chat,messageid)
                if status == -1:
                    bot.reply_to(message,"C'è un problema con questo gioco, contatta un admin")
            #elif utenteSorgente.premium==0 and (isPremiumChannel(from_chat)):
                #bot.reply_to(message, "Mi dispiace, solo gli Utenti Premium possono acquistare questo gioco"+'\n\n'+Utente().infoUser(utenteSorgente),parse_mode='markdown')
            elif utenteSorgente.points>=costo:
                status = sendFileGame(chatid,from_chat,messageid)
                if status == -1:
                    bot.reply_to(message,"C'è un problema con questo gioco, contatta un admin")
                Database().update_user(chatid, {'points':utenteSorgente.points-costo})
                bot.reply_to(message, "Hai mangiato "+str(costo)+" "+PointsName+"\n\n"+Utente().infoUser(utenteSorgente),parse_mode='markdown')
            else:
                bot.reply_to(message, "Mi dispiace, ti servono "+str(costo)+" "+PointsName+" per comprare questo gioco"+"\n\n"+Utente().infoUser(utenteSorgente),parse_mode='markdown')
        
        bot.send_message(CANALE_LOG,"L'utente "+utenteSorgente.username+" ha acquistato da "+message.forward_from_chat.title+" https://t.me/c/"+str(from_chat)[4:]+"/"+str(messageid))

def backup_all(from_chat, to_chat,until_message=9999):
    import time
    messageid = 1
    condition = True
    while (condition and messageid<until_message):
        try:
            condition = bot.copy_message(to_chat,from_chat, messageid)
        except Exception as e:
            errore = str(e)
            print(errore)
            if "Too Many Requests" in errore:
                seconds = int(errore.split()[17])
                time.sleep(seconds)
                messageid-=1
        messageid+=1

bot.infinity_polling()

