# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import telegram
import logging
import schedule
from mcstatus import MinecraftServer
import re

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

welcome_text = "Hi, this is what you can do:\n_/health _urlexample.com__\n_/trace _urlexample.com_ minutes_"


def cmd_start(bot, update):
    bot.send_message(update.message.chat_id, text=welcome_text, parse_mode=telegram.ParseMode.MARKDOWN)


URL = None
STATUS = None
QUERY = None


def cmd_status(bot, update, args):

    btn_players = telegram.InlineKeyboardButton("Players", callback_data='pattern_players') #update.message.reply_text(
    btn_plugins = telegram.InlineKeyboardButton("Plugins", callback_data="I am plugins btn")
    btn_ping = telegram.InlineKeyboardButton("Ping", callback_data="I am ping btn")
    btn_about = telegram.InlineKeyboardButton("About", callback_data="I am about btn")

    keyboard = [[btn_players, btn_plugins], [btn_ping, btn_about]]

    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    global URL
    global STATUS
    global QUERY

    try:

        URL=args[0]
        server = MinecraftServer(URL)
        STATUS=server.status()


        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=(
                "👾 Minecraft Server Status 👾\n\n✅ *Online*\n\n╭\n*Url:* {0}\n*Description:*\n_{1}_\n*Version:* {"
                "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                    URL,
                    re.sub('(§.)?', '', str(STATUS.description)),
                    re.sub('(§.)?', '', str(STATUS.version.name)),
                    STATUS.latency,
                    STATUS.players.online,
                    STATUS.players.max,
                ))
            , reply_markup=reply_markup
            , parse_mode=telegram.ParseMode.MARKDOWN)

    except Exception as e:
        error(bot, update, args)
        logging.exception(e)


def cmd_players(bot, update, args):
    global URL
    global STATUS
    global QUERY

    try:
        URL = args[0]
        server = MinecraftServer(URL)
        STATUS = server.status()
        QUERY = server.query()

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text="👾 Minecraft Server Status 👾\n\n👥 *Url:*\n╭\n*Players:*\n{1}\n╰\n".format(
                URL,
                str(", ".join(QUERY.players.names))
            )
            , parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        bot.sendMessage(
            text="👾 Minecraft Server Status 👾\n\n👥 *Url:* {0}\n╭\n*Error:*\nCoulnd't retrieve data from this server\n╰\n".format(
                URL
            )
            , chat_id=update.message.chat_id
            , parse_mode=telegram.ParseMode.MARKDOWN)
        logging.exception(e)


def cb_players(bot, update):
    global URL
    global QUERY

    try:
        server = MinecraftServer(URL)
        QUERY = server.query()

        bot.editMessageText(
            text="👾 Minecraft Server Status 👾\n\n👥 *Url:*{0}\n╭\n*Players:*\n{1}\n╰\n".format(
                URL,
                str(", ".join(QUERY.players.names))
            )
            , chat_id = update.callback_query.message.chat_id
            , message_id = update.callback_query.message.message_id
            , parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        error_players(bot, update)
        logging.exception(e)


def cmd_track(bot, update, args):
    pass


def error(bot, update, args):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=("👾 Minecraft Server Status 👾\n\n🔻 *Offline*\n\n╭\n*Url:* {0}\n*Error Description:*\n{1}\n╰\n").format(
            args[0],
            str("_Couldn't connect to the server_")
        ), parse_mode=telegram.ParseMode.MARKDOWN)


def error_players(bot, update):
    global URL
    bot.editMessageText(
        text="👾 Minecraft Server Status 👾\n\n👥 *Url:* {0}\n╭\n*Error:*\nCoulnd't retrieve data from this server\n╰\n".format(
            URL
        )
        , chat_id=update.callback_query.message.chat_id
        , message_id=update.callback_query.message.message_id
        , parse_mode=telegram.ParseMode.MARKDOWN)
