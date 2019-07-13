# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import logging
import commands
import os
import sys
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler


mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Commands Handlers
    dispatcher.add_handler(CommandHandler('start', commands.cmd_start))
    dispatcher.add_handler(CommandHandler('status', commands.cmd_status, pass_args=True, pass_chat_data=True))
    dispatcher.add_handler(CommandHandler('players', commands.cmd_players, pass_args=True, pass_chat_data=True))

    # CallBack Handlers
    dispatcher.add_handler(CallbackQueryHandler(commands.cb_status, pattern='pattern_status', pass_chat_data=True))
    dispatcher.add_handler(CallbackQueryHandler(commands.cb_players, pattern='pattern_players', pass_chat_data=True))
    dispatcher.add_handler(CallbackQueryHandler(commands.cb_about, pattern='pattern_about'))

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
