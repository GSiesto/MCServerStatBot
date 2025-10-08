# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    Defaults,
)

import commands


def setup_logging() -> None:
    """Configure lightweight logging for console (and optional file) output."""

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE")

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_path = Path(log_file).expanduser()
        if log_path.parent and not log_path.parent.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)

        handlers.append(
            RotatingFileHandler(
                log_path,
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=getattr(logging, log_level, logging.INFO),
        handlers=handlers,
    )

    logging.captureWarnings(True)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main() -> None:
    """Entry point for the Telegram bot."""

    setup_logging()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("Environment variable TELEGRAM_BOT_TOKEN is not set.")
        sys.exit(1)

    application = (
        Application.builder()
        .token(token)
        .defaults(Defaults(parse_mode=ParseMode.MARKDOWN))
        .build()
    )

    application.add_handler(CommandHandler("start", commands.cmd_start))
    application.add_handler(CommandHandler("status", commands.cmd_status))
    application.add_handler(CommandHandler("players", commands.cmd_players))

    application.add_handler(
        CallbackQueryHandler(
            commands.cb_status,
            pattern=fr"^{commands.CallbackData.STATUS.value}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            commands.cb_players,
            pattern=fr"^{commands.CallbackData.PLAYERS.value}$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            commands.cb_about,
            pattern=fr"^{commands.CallbackData.ABOUT.value}$",
        )
    )

    application.add_error_handler(log_error)

    application.run_polling()


async def log_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log any uncaught exceptions raised while handling updates."""

    logging.exception("Unhandled exception while processing update %s", update, exc_info=context.error)


if __name__ == "__main__":
    main()
