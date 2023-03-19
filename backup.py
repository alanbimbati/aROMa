from xml.sax.handler import property_interning_dict
from telebot import types
from telebot import TeleBot
from telebot import util
from settings import BOT_TOKEN,CANALE_LOG
import schedule
import time
bot = TeleBot(BOT_TOKEN, threaded=False)
import Points

def backup():
    doc = open('points.db', 'rb')
    bot.send_document(CANALE_LOG, doc, caption="aROMa #database #backup")
    doc.close()

schedule.every().day.at("09:00").do(backup)
schedule.every().hour.do(Points.Points().checkScadenzaPremium)

while True:
    schedule.run_pending()
    time.sleep(60)