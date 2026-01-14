############ Sposta questo file nella cartella padre! Qui è solo come backup

# Usa un'immagine base di Python
FROM python:3.10-slim

# Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Copia i file nel container
COPY . /app

# Imposta la directory di lavoro
WORKDIR /app

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Definisci il comando di avvio del bot
CMD ["python3", "main.py"]
