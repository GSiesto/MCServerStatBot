#-*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import logging
import commands
import os
import sys
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

import data

mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Commands Handlers
    start_handler = CommandHandler('start', commands.cmd_start)
    status_handler = CommandHandler('status', commands.cmd_status, pass_args=True)
    players_handler = CommandHandler('players', commands.cmd_players, pass_args=True)
    track_handler = CommandHandler('track', commands.cmd_track, pass_job_queue=True, pass_args=True)

    # Commands Dispatchers
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(status_handler)
    dispatcher.add_handler(players_handler)
    dispatcher.add_handler(track_handler)

    dispatcher.add_handler(CommandHandler('put', data.put, pass_user_data=True))
    dispatcher.add_handler(CommandHandler('get', data.get, pass_user_data=True))

    # Callback Handlers
    dispatcher.add_handler(CallbackQueryHandler(commands.cb_players, pattern='pattern_players'))


    if mode == "dev":
        updater.start_polling()
    elif mode == "prod":
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")

        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
    else:
        logging.error("No MODE specified!")
        sys.exit(1)

