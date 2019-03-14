# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import telegram
import logging
import schedule
from functools import wraps
from mcstatus import MinecraftServer
import re

from telegram import ChatAction
from telegram.ext import CommandHandler, Job

import utils

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
welcome_text = "👾 Minecraft Server Status 👾\n\n/status _url.example.com_\n/players _play.example.com_\n/track " \
               "_play.example.com_ _minutes_\n/untrack _play.example.com_\n\nBot developed by @GSiesto "

URL = None
STATUS = None
QUERY = None

TRACKER = dict()


def cmd_start(bot, update):
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    bot.send_message(update.message.chat_id, text=welcome_text, parse_mode=telegram.ParseMode.MARKDOWN)


def cmd_status(bot, update, args):
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    if not utils.validUrl(args[0]):
        error_url(bot, update, args)
        logging.error("Invalid URL, too long")
        return


    btn_players = telegram.InlineKeyboardButton("Players",
                                                callback_data='pattern_players')
    btn_plugins = telegram.InlineKeyboardButton("Plugins", callback_data="I am plugins btn")
    btn_ping = telegram.InlineKeyboardButton("Ping", callback_data="I am ping btn")
    btn_about = telegram.InlineKeyboardButton("About", callback_data="I am about btn")

    keyboard = [[btn_players, btn_plugins], [btn_ping, btn_about]]

    reply_markup = telegram.InlineKeyboardMarkup(keyboard)

    try:
        global URL, STATUS, QUERY

        URL = args[0]
        server = MinecraftServer.lookup(URL)
        STATUS = server.status()

        description_format = re.sub('(§.)', '', str(STATUS.description['text']))
        description_format = re.sub('[ \t]', '', description_format)

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=(
                "👾 Minecraft Server Status 👾\n\n    ✅ *Online*\n╭\n*Url:* {0}\n*Description:*\n_{1}_\n*Version:* {"
                "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                    URL,
                    description_format,
                    STATUS.version.name,
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
    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    try:
        global URL, STATUS, QUERY

        URL = args[0]
        server = MinecraftServer.lookup(URL)
        QUERY = server.query()

        bot.sendMessage(
            chat_id=update.message.chat_id,
            text="👾 Minecraft Server Status 👾\n\n   👥 *Players*\n╭\n*Url:* {0}\n*Users Online* ({1})*:*{2}\n╰\n".format(
                URL,
                len(QUERY.players.names),
                str(", ".join(QUERY.players.names) + '```')
            )
            , parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        bot.sendMessage(
            text="👾 Minecraft Server Status 👾\n\n   👥 *Url:* {0}\n╭\n*Error:*\nCoulnd't retrieve data from this server\n╰\n".format(
                URL
            )
            , chat_id=update.message.chat_id
            , parse_mode=telegram.ParseMode.MARKDOWN)
        logging.exception(e)


def cb_players(bot, update):
    global URL, STATUS, QUERY

    try:
        server = MinecraftServer.lookup(URL)
        QUERY = server.query()

        bot.editMessageText(
            text="👾 Minecraft Server Status 👾\n\n   👥 *Players*\n╭\n*Url:* {0}\n*Users Online* ({1})*:*{2}\n╰\n".format(
                URL,
                str(", ``".join(QUERY.players.names) + '```')
            )
            , chat_id=update.callback_query.message.chat_id
            , message_id=update.callback_query.message.message_id
            , parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        error_players(bot, update)
        logging.exception(e)


def cmd_track(bot, update, job_queue, args):
    global URL

    URL = args[0]

    bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    bot.sendMessage(
        text="👾 Minecraft Server Status 👾\n\n   🔘 *Tracking* each 1 minute\n*Url:* {0}".format(
            URL
        )
        , chat_id=update.message.chat_id
        , parse_mode=telegram.ParseMode.MARKDOWN)
    job_queue.run_repeating(tracker, interval=5, first=0, context=(update.message.chat_id, job_queue))
    #chat_id = update.message.chat_id
    #job = Job(tracker, 5, repeat=True, context=(chat_id, job_queue))
    #job_queue.put(job)


def tracker(bot, job):
    #try:
        global URL, QUERY, TRACKER

        chat_id, job_queue = job.context


        bot.sendMessage(
            chat_id=chat_id,
            text="HOLA", parse_mode=telegram.ParseMode.MARKDOWN)

        #TODO control args

        #if TRACKER.get("state") == "offline":
        # TODO change for cmd_status
        #URL = args[0]
        """server = MinecraftServer.lookup(URL)
        STATUS = server.status()

        description_format = re.sub('(§.)', '', str(STATUS.description['text']))
        description_format = re.sub('[ \t]', '', description_format)

        bot.sendMessage(
            chat_id=,
            text=(
                "👾 Minecraft Server Status 👾\n\n    ✅ *Online*\n╭\n*Url:* {0}\n*Description:*\n_{1}_\n*Version:* {"
                "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                    URL,
                    description_format,
                    STATUS.version.name,
                    STATUS.latency,
                    STATUS.players.online,
                    STATUS.players.max,
                ))
            , parse_mode=telegram.ParseMode.MARKDOWN)

        TRACKER = {
            "url": URL,
            "state": "online"
        }
    except Exception as e:

        if TRACKER.get("state") == "online":
            # TODO change for cmd_status
            description_format = re.sub('(§.)', '', str(STATUS.description['text']))
            description_format = re.sub('[ \t]', '', description_format)

            bot.sendMessage(
                chat_id=job.context,
                text=(
                    "👾 Minecraft Server Status 👾\n\n    ✅ *Online*\n╭\n*Url:* {0}\n*Description:*\n_{1}_\n*Version:* {"
                    "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                        URL,
                        description_format,
                        STATUS.version.name,
                        STATUS.latency,
                        STATUS.players.online,
                        STATUS.players.max,
                    ))
                , parse_mode=telegram.ParseMode.MARKDOWN)

        TRACKER = {
            "url": URL,
            "state": "offline"
        }
        logging.exception(e)
        """


def error(bot, update, args):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=("👾 Minecraft Server Status 👾\n\n  ⭕ *Offline*\n\n╭\n*Url:* {0}\n*Error Description:*\n{1}\n╰\n").format(
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


def error_url(bot, update, args):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=("👾 Minecraft Server Status 👾\n\n️   🔻 *Error*\n╭\n*Url:* {0}\n*Error Description:*\n{1}\n╰\n╭\n*Correct Examples:*\n_play.minecraft.net_\n_minecraftgame.org_\n╰").format(
            args[0],
            str("_The url introduced is not valid, please, try again_")
        )
        , parse_mode=telegram.ParseMode.MARKDOWN)