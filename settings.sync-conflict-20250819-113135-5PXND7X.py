PROMOZIONI = {
    "Halloween":    {
        "nome":                 "Halloween",
        "periodo_inizio":       "20231030",
        "periodo_fine":         "20231105",
        "COSTO_PREMIUM":        150,
        "COSTO_MANTENIMENTO":   25

    },
    "Natale": {
        "nome":                 "Natale",
        "periodo_inizio":       "20231224",
        "periodo_fine":         "20240108",
        "COSTO_PREMIUM":        100,
        "COSTO_MANTENIMENTO":   25
    },
    "SanValentino": {
        "nome":                 "SanValentino",
        "periodo_inizio":       "20240214",
        "periodo_fine":         "20240214",
        "COSTO_PREMIUM":        125,
        "COSTO_MANTENIMENTO":   25
    },    
}

CANALE_LOG          =    '-1001469821841'
TEST                =    1

TEST_TOKEN      = '1722321202:AAH0ejhh_A5kLePfD9bt9CGYBXZbE9iA6AU'
AROMA_TOKEN     = 'ORIGINAL_TOKEN'

TEST_GRUPPO     = -1001721979634
AROMA_GRUPPO    = -1001457029650

if TEST:
    BOT_TOKEN       = TEST_TOKEN
    GRUPPO_AROMA    = TEST_GRUPPO
else:
    BOT_TOKEN       = AROMA_TOKEN
    GRUPPO_AROMA    = AROMA_GRUPPO

PointsName = 'Frutti Wumpa 🍑'

PREMIUM_CHANNELS = {
    'ps1'       :    '-1001187652609',
    'ps2'       :    '-1001369506956',
    'ps3'       :    '-1001407069920',
    'ps4'       :    '-1001738986067',
    'pc'        :    '-1001148989565',
    'psp'       :    '-1001497940192',
    'nintendo'  :    '-1001199307271',
    'big_games' :    '-1001238395413',
    'horror'    :    '-1001298605336',
    'hot'       :    '-1001475722596',
    'tutto'     :    '-1001835474623'
}

ALBUM = {
    'newps1'    :    '-1001734213795',
    'newps2'    :    '-1001889106515',
    'newps3'    :    '-1001854528728',
    'newps4'    :    '-1001636502550',
    'newpsp'    :    '-1001672257356'
}

MISCELLANIA = {
    'Anime'     :    '-1001270876099',
    'Movie'     :    '-1001483847400',
    'AndroidWin':    '-1001162604677',
    'Guide'     :    '-1001458426171',
    'Stickers'  :    '-1001172025269',
    'Wallpaper' :    '-1001293777327',
    'Music'     :    '-1001395413398'
}


from telebot import TeleBot
from telebot import types
bot = TeleBot(BOT_TOKEN, threaded=False)
hideBoard = types.ReplyKeyboardRemove()  