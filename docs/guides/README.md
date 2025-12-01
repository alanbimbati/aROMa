# aROMa - Telegram bot for managing game ROMs
aROMa is a Python code built using the pyTelegramBotAPI and SQLAlchemy as an ORM over a SQLite3 database for managing game ROMs on Telegram. Please note that this code is for educational purposes only and the ROMs are only accessible with an original copy of the game.

## Some features of the bot include:

- Unlimited Telegram cloud storage for file archiving
- Automatic backups to a Telegram channel
- Gamification through reputation management (see Reputator Bot https://github.com/alanbimbati/TemplateTelegramBot)
- Fun chat management inspired by Crash Bandicoot (crates, TNT, and Nitro will appear in the Telegram chat)

To ensure proper functionality, please configure the settings.py file by inserting the bot token and optionally, the test bot token by setting the TEST flag to 1.


# aROMa - Telegram Bot Dockerized

This repository contains a Telegram bot named **aROMa**, which has been containerized using Docker. This `README.md` will guide you through the steps to build, run, and test the bot using Docker.

## Prerequisites

Ensure you have the following tools installed on your system:

- [Docker](https://www.docker.com/get-started) (and Docker Compose if needed)
- [Python](https://www.python.org/) (for local development and testing)
- [Git](https://git-scm.com/) (to clone the repository)

## Getting Started

### Clone the Repository

Start by cloning the repository:

```bash
git clone https://github.com/alanbimbati/aROMa.git
cd aROMa
```

Set Up the Environment
Ensure all necessary files are present in the aROMa directory:
```bash
.
├── Dockerfile
├── aROMa
│   ├── main.py
│   ├── requirements.txt
│   └── other dependencies
```

Build the Docker Image
Build the Docker image using the included Dockerfile:

```bash
sudo docker build -t my-telegram-bot .
```

### Run the Container

Start a new container based on the newly created image:

```bash
sudo docker run -d --name my-bot-container my-telegram-bot
```

### Check the Logs
To ensure the bot is running correctly, check the container logs:

```bash
sudo docker logs my-bot-container
```

Configuration
If you need to configure environment variables or modify parameters, you can do so directly in the Dockerfile or use a .env file and pass it to the container. For example:

Create a .env file (if using environment variables):

```bash
TELEGRAM_BOT_TOKEN=your_token
```
Modify the Dockerfile (if necessary) to include environment variables:

Dockerfile
```bash
ENV TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
```
Run the container with the .env file (optional):

```bash
sudo docker run --env-file .env -d --name my-bot-container my-telegram-bot
```
