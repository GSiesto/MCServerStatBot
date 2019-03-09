#-*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import logging
import commands
import os
import sys
from telegram.ext import Updater, CommandHandler

mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")

if mode == "dev":
    def run(updater):
        updater.start_polling()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
else:
    logging.error("No MODE specified!")
    sys.exit(1)

def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    # Commands Handlers
    start_handler = CommandHandler('start', commands.cmd_start)
    status_handler = CommandHandler('status', commands.cmd_status, pass_args=True)
    players_handler = CommandHandler('players', commands.cmd_players, pass_args=True)

    # Commands Dispatchers
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(status_handler)
    dispatcher.add_handler(players_handler)

    updater.start_polling()


if __name__ == '__main__':
    main()
