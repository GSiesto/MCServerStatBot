#-*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import telegram
import logging
import schedule
from mcstatus import MinecraftServer
import re

welcome_text = "Hi, this is what you can do:\n_/health _urlexample.com__\n_/trace _urlexample.com_ minutes_"

def cmd_start(bot, update):
    bot.send_message(update.message.chat_id, text=welcome_text, parse_mode=telegram.ParseMode.MARKDOWN)


def cmd_status(bot, update, args):
    try:
        server = MinecraftServer(args[0])
        status = server.status()
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=("👾 _Minecraft Server Status_ 👾\n\n✅ *Online*\n╭\n*Url:* {0}\n*Description:*\n_{1}_\n╰\n╭\n*Version:* {2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                args[0],
                re.sub('(§.{1})?', '', unicode(status.description).encode('utf8')),
                re.sub('(§.{1})?', '', unicode(status.version.name).encode('utf8')),
                status.latency,
                status.players.online,
                status.players.max
            ))
          , parse_mode=telegram.ParseMode.MARKDOWN)
    except (RuntimeError, TypeError, NameError):
        error(bot, update, args)
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def cmd_players(bot, update, args):
    try:
        server = MinecraftServer(args[0])
        query = server.query()
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text=("👥 *Url:* {0}\n╭\n*Players:*\n{1}\n╰\n").format(
                args[0],
                ", ".join(query.players.names)
            ), parse_mode=telegram.ParseMode.MARKDOWN)
    except (RuntimeError, TypeError, NameError):
        error(bot, update, args)
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def cmd_track(bot, update, args):
    pass


def error(bot, update, args):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=("👾 _Minecraft Server Status_ 👾\n\n🔻 Offline\n╭\n*Url:* {0}\n*Error Description:*\n{1}\n╰\n").format(
            args[0],
            str("_Couldn't connect to the server_")
    ), parse_mode=telegram.ParseMode.MARKDOWN)
