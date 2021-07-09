# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import telegram
import logging
from mcstatus import MinecraftServer
import re
from telegram.ext.dispatcher import run_async
import utils

logging.basicConfig(filename="command_logs.log",
                    filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

welcome_text = "༼ つ ◕ ◡ ◕ ༽つ\nMinecraft Server Status\n\n/status _url.example.com_\n/players _play.example.com_\n\nBot developed by @GSiesto"

btn_players = telegram.InlineKeyboardButton("Players", callback_data='pattern_players')
btn_status = telegram.InlineKeyboardButton("Status", callback_data='pattern_status')
btn_about = telegram.InlineKeyboardButton("About", callback_data='pattern_about')
keyboard = [[btn_status, btn_players, btn_about]]
reply_markup = telegram.InlineKeyboardMarkup(keyboard)


# ==========================
# Commands
# ==========================

def cmd_start(update, context):
    """Usage: /start"""
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
    context.bot.send_message(update.message.chat_id, text=welcome_text, parse_mode=telegram.ParseMode.MARKDOWN)


def cmd_status(update, context):
    """Usage: /status url"""
    logging.info("/status called")
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    chat_data = context.chat_data

    try:

        if len(context.args) != 1:
            error_incomplete(context.bot, update)
            logging.info("/status did't provide an url, /status minecraft.example.com", )
            return

        if not utils.validUrl(context.args[0]):
            error_url(context.bot, update, context.args)
            logging.info("Invalid URL, too long")
            return

        chat_data['url'] = context.args[0]
        chat_data['server'] = MinecraftServer.lookup(chat_data['url'])
        chat_data['status'] = chat_data['server'].status()

        info_status(context.bot, update.message.chat_id, chat_data['url'], chat_data['status'])
        logging.info("/status %s online" % context.args[0])
    except Exception as e:
        error_status(context.bot, update.message.chat_id, context.args)
        logging.exception(e)


def cmd_players(update, context):
    """Usage: /players url"""
    logging.info("/players called")
    context.bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)

    chat_data = context.chat_data
    flag_err_query = False

    try:

        if len(context.args) != 1:
            error_incomplete(context.bot, update)
            logging.error("You must provide an URL, /players minecraft.example.com", )
            return

        if not utils.validUrl(context.args[0]):
            error_url(context.bot, update, context.args)
            logging.info("Invalid URL, too long")
            return

        chat_data['url'] = context.args[0]
        query = MinecraftServer.lookup(chat_data['url'])
        
        try:
            chat_data['server'] = query
            chat_data['query'] = query.query()
        except:
            # https://github.com/Dinnerbone/mcstatus/issues/72
            chat_data['server'] = query
            chat_data['query'] = query.status() # At least show a few players
            flag_err_query = True
            logging.info("flag_err_query")

        info_players(context.bot, update.message.chat_id, chat_data['url'], chat_data['query'], error_query=flag_err_query)
        logging.info("/players %s online" % context.args[0])

    except Exception as e:
        error_status(context.bot, update.message.chat_id, context.args)
        logging.exception(e)


# ==========================
# CallBacks
# ==========================

def cb_status(update, context):
    logging.info("CallBack Status called")

    chat_data = context.chat_data

    try:

        chat_data['status'] = chat_data['server'].status()

        description_format = re.sub('§.', '', chat_data['status'].description)
        description_format = re.sub('', '', description_format)

        context.bot.editMessageText(
            text=(
                "(ﾉ◕ヮ◕)ﾉ:･ﾟ✧\n╭ ✅ *Online*\n*Url:* `{0}`\n*Description:*\n_{1}_\n*Version:* {"
                "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                    chat_data['url'],
                    description_format,
                    chat_data['status'].version.name,
                    chat_data['status'].latency,
                    chat_data['status'].players.online,
                    chat_data['status'].players.max,
                ))
            , reply_markup=reply_markup
            , chat_id=update.callback_query.message.chat_id
            , message_id=update.callback_query.message.message_id
            , parse_mode=telegram.ParseMode.MARKDOWN)

    except Exception as e:
        error_status_edit(update, context.bot, chat_data['url'])
        logging.exception(e)


def cb_players(update, context):
    logging.info("CallBack Players called")

    chat_data = context.chat_data
    flag_err_query = False

    try:
        query = MinecraftServer.lookup(chat_data['url'])
        
        try:
            chat_data['query'] = query.query()
        except Exception as e:
            # https://github.com/Dinnerbone/mcstatus/issues/72
            chat_data['server'] = query
            chat_data['query'] = query.status() # At least show a few players
            flag_err_query = True
            logging.info("flag_err_query")
        
        if not flag_err_query:
            context.bot.editMessageText(
                text="(•(•◡(•◡•)◡•)•)\n╭ ✅ *Online*\n*Url:* `{0}`\n*Users Online* {1}*:*\n{2}\n╰\n".format(
                    chat_data['url'],
                    len(chat_data['query'].players.names),
                    str("`" + "`, `".join(chat_data['query'].players.names) + "`")
                )
                , reply_markup=reply_markup
                , chat_id=update.callback_query.message.chat_id
                , message_id=update.callback_query.message.message_id
                , parse_mode=telegram.ParseMode.MARKDOWN)
        else:
            context.bot.editMessageText(
                text="(•(•◡(•◡•)◡•)•)\n╭ ✅ *Online*\n*Url:* `{0}`\n*Users Online* {1}\n*Max Users Allowed* {2}\n\n_The names of the players cannot be displayed since the server does not allow queries. _\n╰\n".format(
                    chat_data['url'],
                    str(chat_data['query'].players.online),
                    str(chat_data['query'].players.max)
                )
                , reply_markup=reply_markup
                , chat_id=update.callback_query.message.chat_id
                , message_id=update.callback_query.message.message_id
                , parse_mode=telegram.ParseMode.MARKDOWN)

    except Exception as e:
        error_players_edit(update, context.bot, chat_data['url'])
        logging.exception(e)


def cb_about(update, context):
    logging.info("CallBack About called")

    try:
        context.bot.editMessageText(
            text=welcome_text
            , chat_id=update.callback_query.message.chat_id
            , reply_markup=reply_markup
            , message_id=update.callback_query.message.message_id
            , parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        logging.exception(e)


# ==========================
# Info
# ==========================

def info_status(bot, chat_id, _url, _status):
    description_format = re.sub('§.', '', _status.description)
    description_format = re.sub('', '', description_format)

    bot.sendMessage(
        chat_id=chat_id,
        text=(
            "(ﾉ◕ヮ◕)ﾉ:･ﾟ✧\n╭ ✅ *Online*\n*Url:* `{0}`\n*Description:*\n_{1}_\n*Version:* {"
            "2}\n*Ping:* {3}ms\n*Players:* {4}/{5}\n╰".format(
                _url,
                description_format,
                _status.version.name,
                _status.latency,
                _status.players.online,
                _status.players.max,
            ))
        , reply_markup=reply_markup
        , parse_mode=telegram.ParseMode.MARKDOWN)


def info_players(bot, chat_id, _url, _query, error_query=False):
    
    if not error_query:
        bot.sendMessage(
            chat_id=chat_id,
            text="(•(•◡(•◡•)◡•)•)\n╭ ✅ *Online*\n*Url:* `{0}`\n*Users Online* {1}*:*\n{2}\n╰\n".format(
                _url,
                len(_query.players.names),
                str("`" + "`, `".join(_query.players.names) + "`")
            )
            , reply_markup=reply_markup
            , parse_mode=telegram.ParseMode.MARKDOWN)
    else:
        bot.sendMessage(
            chat_id=chat_id,
            text="(•(•◡(•◡•)◡•)•)\n╭ ✅ *Online*\n*Url:* `{0}`\n*Users Online* {1}\n*Max Users Allowed* {2}\n\n_The names of the players cannot be displayed since the server does not allow queries. _\n╰\n".format(
                _url,
                str(_query.players.online),
                str(_query.players.max)
            )
            , reply_markup=reply_markup
            , parse_mode=telegram.ParseMode.MARKDOWN)
        


# ==========================
# Error
# ==========================

def error_status(bot, chat_id, args):
    bot.sendMessage(
        chat_id=chat_id,
        text="(╯°□°）╯ ︵ ┻━┻\n╭ ⭕ *Offline*\n*Url:* `{0}`\n*Error Description:*\n{1}\n╰\n".format(
            args[0],
            str("_Could not connect to the server_")
        )
        , reply_markup=reply_markup
        , parse_mode=telegram.ParseMode.MARKDOWN)


def error_status_edit(update, bot, param_url):
    bot.editMessageText(
        text="(╯°□°）╯ ︵ ┻━┻\n╭ ⭕ *Offline*\n*Url:* `{0}`\n*Error Description:*\n{1}\n╰\n".format(
            param_url,
            str("_Could not connect to the server_")
        )
        , reply_markup=reply_markup
        , chat_id=update.callback_query.message.chat_id
        , message_id=update.callback_query.message.message_id
        , parse_mode=telegram.ParseMode.MARKDOWN)


def error_players_edit(update, bot, param_url):
    bot.editMessageText(
        text="(╯°□°）╯ ︵ ┻━┻\n╭ 🔻 *Error*\n*Url:* `{0}`\n*Error Description:*\n_Could not connect to the "
             "server_\n_The server may not allow Query requests_\n╰\n".format(param_url)
        , reply_markup=reply_markup
        , chat_id=update.callback_query.message.chat_id
        , message_id=update.callback_query.message.message_id
        , parse_mode=telegram.ParseMode.MARKDOWN)


def error_url(bot, update, args):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=("(╯°□°）╯ ︵ ┻━┻\n╭ 🔻 *Error*\n*Url:* `{0}`\n*Error Description:*\n{1}\n\n*Correct "
              "Examples:*\n_play.minecraft.net_\n_minecraftgame.org_\n╰").format(
            args[0],
            str("_The url introduced is not valid, please, try again_")
        )
        , reply_markup=reply_markup
        , parse_mode=telegram.ParseMode.MARKDOWN)


def error_incomplete(bot, update):
    bot.sendMessage(
        chat_id=update.message.chat_id,
        text=(
            "(╯°□°）╯ ︵ ┻━┻\n╭ 🔻 *Error*\n_You must provide an url please, try again_\n\n*Correct "
            "Examples:*\n_/status play.minecraft.net_\n_/status minecraftgame.org:25898_\n╰ "
        )
        , reply_markup=reply_markup
        , parse_mode=telegram.ParseMode.MARKDOWN)
