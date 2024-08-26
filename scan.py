import anthropic
from telethon import TelegramClient
from telethon.tl.types import PeerChannel
from settings import *
from model import GameInfo
import os

claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
channel_id = int(PREMIUM_CHANNELS['tutto'])
tg_client = TelegramClient('user_session', api_id, api_hash)


def CLAUDEAPIgameToJson(gioco):
    scope = "Ritornami solo un json con i dettagli precisi di qeusto gioco, semancanti cercali e aggiungili: titolo, piattaforma (es. ps1,ps2,gba,switch,pc,android...), genere, descrizione, limgua,regione,anno"
    message = claude_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0,
        system=scope,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": scope+" "+gioco
                    }
                ]
            }
        ]
    )
    return message

def fromClaudeToDict(content):
    if type(content) is not type("stringa"):
        content = content[0].text
    content = str(content).replace("\n","")
    content = content.split("{")[1]
    content = content.split("}")[0]
    string = "{"+content+"}"
    string = string.replace("\n","")

    try:
        data = eval(string)
        return data
    except Exception as e:
        return e
  
  
async def scan_channel(channel,start_id,end_id):

    await tg_client.start(phone_number)
    
    # Ottieni l'oggetto del canale
    channel = await tg_client.get_entity(channel_id)
    
    # Recupera il primo messaggio del canale
    async for message in tg_client.iter_messages(channel, min_id=start_id, max_id=end_id):
        message_link = f"https://t.me/c/{str(channel_id)[4:]}/{message.id}"
        if "╔═" in message.text:
            if not GameInfo.find_by_message_link(message_link) and not GameInfo.find_error_by_message_link(message_link):  
                print("Cerco",message_link)        
                content = CLAUDEAPIgameToJson(message.text).content
                try:
                    game = fromClaudeToDict(content)
                    game['message_link'] = message_link
                    GameInfo.insert_from_dict(game)
                except Exception as e:
                    print("ERRORE nell'inserimento del gioco nel db: ", str(e))
                    GameInfo.insert_error_data(message_link,content[0].text,e)

def re_scan_errors(error_log_file):
    if not os.path.isfile(error_log_file):
        print(f"Il file {error_log_file} non esiste.")
        return

    # Legge tutte le righe del file, mantenendo la prima come intestazione
    with open(error_log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header = lines[0]
    error_lines = lines[1:]  # Escludi l'intestazione

    # Lista per conservare solo gli errori che non vengono risolti
    remaining_errors = []

    for line in error_lines:
        try:
            columns = line.strip().split('|')
            message_link = columns[0]
            content = columns[1]

            try:
                game = fromClaudeToDict(content)
                game['message_link'] = message_link
                GameInfo.insert_from_dict(game)

                # Verifica che l'inserimento sia avvenuto con successo
                if not GameInfo.find_by_message_link(message_link):
                    remaining_errors.append(line)
            except Exception as e:
                print("ERRORE nell'inserimento del gioco nel db: ", str(e))
                remaining_errors.append(line)
        except Exception as e:
            print("ERRORE lettura linea: ", str(e))
            remaining_errors.append(line)

    # Riscrivi il file degli errori, mantenendo solo gli errori non risolti
    with open(error_log_file, 'w', encoding='utf-8') as f:
        f.write(header)  # Scrivi di nuovo l'intestazione
        f.writelines(remaining_errors)  # Scrivi solo le righe che non sono state risolte

    print(f"Rilettura completata. {len(remaining_errors)} errori rimasti nel file degli errori.")



with tg_client:
   tg_client.loop.run_until_complete(scan_channel(channel_id,start_id=1, end_id=999999))

re_scan_errors('error_log.csv')