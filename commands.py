# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

"""Telegram command and callback handlers for MCServerStatBot."""

from __future__ import annotations

import asyncio
import os
import logging
import re
from collections import deque
from collections.abc import Sequence
from typing import Any, cast
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache

from mcstatus import JavaServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

import utils

__all__ = [
    "cmd_start",
    "cmd_status",
    "cmd_players",
    "cb_status",
    "cb_players",
    "cb_about",
    "CallbackData",
]

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 3.0  # seconds
MAX_PLAYER_NAMES_DISPLAY = 25

AFFILIATE_URL_ENV = "AFFILIATE_URL"
AFFILIATE_LABEL_ENV = "AFFILIATE_LABEL"
AFFILIATE_BLURB_ENV = "AFFILIATE_BLURB"

MESSAGE_CONTEXT_KEY = "message_context"
MESSAGE_CONTEXT_ORDER_KEY = "message_context_order"
MESSAGE_CONTEXT_LIMIT = 20

DEFAULT_AFFILIATE_LABEL = "Create your own MC server"
DEFAULT_AFFILIATE_BLURB = "Sponsored by our hosting partner\nClick to support the bot!"

DEVELOPER_CHANNEL_URL = "https://t.me/GSiesto"
DEVELOPER_HANDLE = "@GSiesto"


class CallbackData(str, Enum):
    """Canonical callback data keys for inline buttons."""

    STATUS = "pattern_status"
    PLAYERS = "pattern_players"
    ABOUT = "pattern_about"


WELCOME_TEXT = (
    "👋 *Welcome to MCServerStatBot!*\n"
    "I can check Minecraft Java servers for uptime, ping, and connected players.\n\n"
    "*Try these commands:*\n"
    "• `/status play.example.com`\n"
    "• `/players play.example.com`\n\n"
    "Run those commands anytime, each result includes inline buttons for quick refreshes."
)

ABOUT_TEXT = (
    "🤖 *MCServerStatBot*\n"
    "• Built for quick Minecraft Java status checks\n"
    "• Shows latency, MOTD, version, and players\n\n"
    f"✉️ Chat with the developer: [{DEVELOPER_HANDLE}]({DEVELOPER_CHANNEL_URL})\n"
    "📌 Follow updates and share feedback in the channel."
)


@dataclass(slots=True)
class ServerSnapshot:
    """Immutable summary of the current server state."""

    address: str
    fetched_at: datetime
    description: str
    version_name: str
    latency_ms: int
    players_online: int
    players_max: int
    player_names: tuple[str, ...]
    query_available: bool
    query_error: str | None


# ==========================
# Helper utilities
# ==========================

def _clean_description(raw_description: object | None) -> str:
    """Remove colour codes and return a safe server description string."""

    if raw_description is None:
        return "No description provided."

    if isinstance(raw_description, dict):
        text = raw_description.get("text") or ""
    else:
        text = str(raw_description)

    text = re.sub(r"§.", "", text)
    text = text.strip()
    return text or "No description provided."


def _extract_player_names_from_status(status: object) -> tuple[str, ...]:
    players = getattr(status, "players", None)
    sample = getattr(players, "sample", None)
    if not sample:
        return tuple()

    names: list[str] = []
    for entry in sample:
        name = getattr(entry, "name", None)
        if name is None and isinstance(entry, dict):
            name = entry.get("name")
        if name:
            names.append(str(name))
    return tuple(names)


def build_main_keyboard() -> InlineKeyboardMarkup:
    """Create the primary inline keyboard with fresh button instances."""

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("Status", callback_data=CallbackData.STATUS.value),
            InlineKeyboardButton("Players", callback_data=CallbackData.PLAYERS.value),
            InlineKeyboardButton("About", callback_data=CallbackData.ABOUT.value),
        ]
    ]

    affiliate_button = _affiliate_button()
    if affiliate_button:
        rows.append([affiliate_button])

    return InlineKeyboardMarkup(rows)


@lru_cache(maxsize=1)
def _get_affiliate_config() -> tuple[str, str, str] | None:
    url = (os.getenv(AFFILIATE_URL_ENV) or "").strip()
    if not url:
        return None

    label = (os.getenv(AFFILIATE_LABEL_ENV) or DEFAULT_AFFILIATE_LABEL).strip() or DEFAULT_AFFILIATE_LABEL
    blurb = (os.getenv(AFFILIATE_BLURB_ENV) or DEFAULT_AFFILIATE_BLURB).strip() or DEFAULT_AFFILIATE_BLURB
    return url, label, blurb


def _affiliate_button() -> InlineKeyboardButton | None:
    config = _get_affiliate_config()
    if not config:
        return None

    url, label, _ = config
    return InlineKeyboardButton(f"🙌 {label}", url=url)


def _affiliate_hint() -> str | None:
    config = _get_affiliate_config()
    if not config:
        return None

    _, _, blurb = config
    safe_blurb = escape_markdown(blurb, version=1)
    return f"🙌 {safe_blurb}"


def _chat_data(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    return cast(dict[str, Any], context.chat_data)


def _store_message_snapshot(
    context: ContextTypes.DEFAULT_TYPE, message_id: int, snapshot: ServerSnapshot
) -> None:
    chat_data = _chat_data(context)
    store = cast(dict[int, ServerSnapshot], chat_data.setdefault(MESSAGE_CONTEXT_KEY, {}))
    order = cast(deque[int], chat_data.setdefault(MESSAGE_CONTEXT_ORDER_KEY, deque()))

    if message_id in store:
        store[message_id] = snapshot
        try:
            order.remove(message_id)
        except ValueError:
            pass
    else:
        store[message_id] = snapshot

    order.append(message_id)

    while len(order) > MESSAGE_CONTEXT_LIMIT:
        old_id = order.popleft()
        store.pop(old_id, None)


def _get_message_snapshot(
    context: ContextTypes.DEFAULT_TYPE, message_id: int
) -> ServerSnapshot | None:
    chat_data = _chat_data(context)
    store = cast(dict[int, ServerSnapshot] | None, chat_data.get(MESSAGE_CONTEXT_KEY))
    if not store:
        return None

    snapshot = store.get(message_id)
    if isinstance(snapshot, ServerSnapshot):
        return snapshot
    return None


async def _run_in_thread(func, *args, timeout: float = DEFAULT_TIMEOUT):
    return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=timeout)


async def _lookup_server(address: str) -> JavaServer:
    return await _run_in_thread(JavaServer.lookup, address)


async def _fetch_status(server: JavaServer):
    return await _run_in_thread(server.status)


async def _fetch_query(server: JavaServer):
    return await _run_in_thread(server.query)


async def _send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


async def _build_snapshot(address: str, *, include_query: bool) -> ServerSnapshot:
    server = await _lookup_server(address)
    status = await _fetch_status(server)

    description = _clean_description(getattr(status, "description", None))
    version_name = str(getattr(getattr(status, "version", None), "name", "Unknown"))
    latency_ms = int(round(getattr(status, "latency", 0) or 0))
    players = getattr(status, "players", None)
    online = int(getattr(players, "online", 0) or 0)
    maximum = int(getattr(players, "max", 0) or 0)

    player_names: tuple[str, ...] = _extract_player_names_from_status(status)
    query_available = False
    query_error: str | None = None

    if include_query:
        try:
            query = await _fetch_query(server)
            names = getattr(getattr(query, "players", None), "names", None)
            if names:
                player_names = tuple(sorted(str(name) for name in names))
            query_available = True
        except Exception as exc:  # pragma: no cover - network failures
            query_error = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            logger.info("Query failed for %s (%s)", address, query_error)
            logger.debug("Query failure details for %s", address, exc_info=exc)
            query_available = False

    return ServerSnapshot(
        address=address,
        fetched_at=datetime.now(timezone.utc),
        description=description,
        version_name=version_name,
        latency_ms=latency_ms,
        players_online=online,
        players_max=maximum,
        player_names=player_names,
        query_available=query_available,
        query_error=query_error,
    )


def _format_player_names(names: Sequence[str]) -> str:
    if not names:
        return "`No players listed`"

    trimmed = list(names[:MAX_PLAYER_NAMES_DISPLAY])
    escaped = [f"`{escape_markdown(name, version=1)}`" for name in trimmed]

    lines: list[str] = []
    for idx in range(0, len(escaped), 5):
        lines.append(" ".join(escaped[idx : idx + 5]))

    remaining = len(names) - len(trimmed)
    if remaining > 0:
        lines.append(f"`…and {remaining} more`")

    return "\n".join(lines)


def _status_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    description = escape_markdown(snapshot.description, version=1)
    version_name = escape_markdown(snapshot.version_name, version=1)
    fetched = escape_markdown(snapshot.fetched_at.strftime("%Y-%m-%d %H:%M:%SZ"), version=1)

    base = (
        "✅ *Server Online*\n"
        f"🌐 `{safe_address}`\n"
        f"🕒 Checked: {fetched}\n\n"
        "📝 *Description*\n"
        f"_{description}_\n\n"
        f"📦 *Version:* {version_name}\n"
        f"📶 *Ping:* {snapshot.latency_ms} ms\n"
        f"👥 *Players:* {snapshot.players_online}/{snapshot.players_max}"
    )

    return _message_with_affiliate_hint(base)


def _players_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    header = (
        "👥 *Players Online*\n"
        f"🌐 `{safe_address}`\n"
        f"🟢 Currently: {snapshot.players_online} / {snapshot.players_max} players"
    )

    if snapshot.player_names:
        formatted_names = _format_player_names(snapshot.player_names)
        parts = [header, "", formatted_names]

        if not snapshot.query_available:
            parts.extend(
                [
                    "",
                    "ℹ️ _Showing the limited sample returned by the status ping; the server may not expose its full player list._",
                ]
            )

        return _message_with_affiliate_hint("\n".join(parts))

    return _players_fallback_message(snapshot)


def _players_fallback_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    lines = [
        "👥 Players Online",
        f"🌐 {safe_address}",
        f"🟢 Currently: {snapshot.players_online} / {snapshot.players_max} players",
        "",
        "⚠️ This server has queries disabled, so individual player names aren't available.",
    ]

    if snapshot.query_error:
        safe_error = escape_markdown(snapshot.query_error, version=1)
        lines.extend(
            [
                "",
                f"ℹ️ Query failed with: {safe_error}",
            ]
        )

    return _message_with_affiliate_hint("\n".join(lines))


async def _send_status_message(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, snapshot: ServerSnapshot
) -> None:
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=_status_message(snapshot),
        reply_markup=build_main_keyboard(),
        disable_web_page_preview=True,
    )
    _store_message_snapshot(context, message.message_id, snapshot)


async def _send_players_message(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, snapshot: ServerSnapshot
) -> None:
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=_players_message(snapshot),
        reply_markup=build_main_keyboard(),
        disable_web_page_preview=True,
    )
    _store_message_snapshot(context, message.message_id, snapshot)


# ==========================
# Commands
# ==========================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /start"""

    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    _chat_data(context).clear()
    await _send_typing(context, chat_id)
    await update.message.reply_text(
        _message_with_affiliate_hint(WELCOME_TEXT),
        disable_web_page_preview=True,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /status <host[:port]>"""

    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    await _send_typing(context, chat_id)
    logger.info("/status called")

    args = context.args or []
    if len(args) != 1:
        await error_incomplete(context, chat_id)
        logger.info("/status did not provide an address")
        return

    address = args[0].strip()
    if not utils.is_valid_server_address(address):
        await error_url(context, chat_id, address)
        logger.info("Invalid server address supplied for /status")
        return

    try:
        snapshot = await _build_snapshot(address, include_query=False)
    except (asyncio.TimeoutError, OSError) as exc:  # pragma: no cover - network failures
        await error_status(context, chat_id, address)
        logger.exception(exc)
        return

    chat_data = _chat_data(context)
    chat_data["last_address"] = snapshot.address
    chat_data["last_snapshot"] = snapshot

    await _send_status_message(context, chat_id, snapshot)
    logger.info("/status %s online", address)


async def cmd_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /players <host[:port]>"""

    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    await _send_typing(context, chat_id)
    logger.info("/players called")

    args = context.args or []
    if len(args) != 1:
        await error_incomplete(context, chat_id)
        logger.info("/players did not provide an address")
        return

    address = args[0].strip()
    if not utils.is_valid_server_address(address):
        await error_url(context, chat_id, address)
        logger.info("Invalid server address supplied for /players")
        return

    try:
        snapshot = await _build_snapshot(address, include_query=True)
    except (asyncio.TimeoutError, OSError) as exc:  # pragma: no cover - network failures
        await error_status(context, chat_id, address)
        logger.exception(exc)
        return

    chat_data = _chat_data(context)
    chat_data["last_address"] = snapshot.address
    chat_data["last_snapshot"] = snapshot

    await _send_players_message(context, chat_id, snapshot)
    logger.info("/players %s online", address)


# ==========================
# Callbacks
# ==========================

async def cb_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Status' inline button press."""
    logger.info("Callback status called")

    query = update.callback_query
    if not query or not update.effective_chat:
        return

    message = query.message
    if not message:
        await query.answer()
        return

    message_id = message.message_id
    chat_data = _chat_data(context)
    stored_snapshot = _get_message_snapshot(context, message_id)
    address = stored_snapshot.address if stored_snapshot else cast(str | None, chat_data.get("last_address"))
    previous_snapshot = stored_snapshot or cast(ServerSnapshot | None, chat_data.get("last_snapshot"))

    if not address:
        await query.answer("Run /status first to choose a server.", show_alert=True)
        return

    fallback_notice: str | None = None

    try:
        snapshot = await _build_snapshot(address, include_query=False)
        _store_message_snapshot(context, message_id, snapshot)
        chat_data["last_snapshot"] = snapshot
    except (asyncio.TimeoutError, OSError) as exc:  # pragma: no cover - network failures
        logger.exception(exc)
        if previous_snapshot:
            snapshot = previous_snapshot
            _store_message_snapshot(context, message_id, snapshot)
            fallback_notice = "⚠️ _Showing cached data because the server timed out._"
        else:
            await error_status_edit(update, context, address)
            await query.answer("Server unavailable.", show_alert=True)
            return

    try:
        message_text = _status_message(snapshot)
        if fallback_notice:
            message_text = f"{message_text}\n\n{fallback_notice}"

        await query.edit_message_text(
            message_text,
            reply_markup=build_main_keyboard(),
            disable_web_page_preview=True,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            await asyncio.sleep(0.5)
            await query.answer()
            return
        else:
            raise

    await query.answer()


async def cb_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'Players' inline button press."""
    logger.info("Callback players called")

    query = update.callback_query
    if not query or not update.effective_chat:
        return

    message = query.message
    if not message:
        await query.answer()
        return

    message_id = message.message_id
    chat_data = _chat_data(context)
    stored_snapshot = _get_message_snapshot(context, message_id)
    address = stored_snapshot.address if stored_snapshot else cast(str | None, chat_data.get("last_address"))
    previous_snapshot = stored_snapshot or cast(ServerSnapshot | None, chat_data.get("last_snapshot"))

    if not address:
        await query.answer("Run /players first to choose a server.", show_alert=True)
        return

    try:
        snapshot = await _build_snapshot(address, include_query=True)
        _store_message_snapshot(context, message_id, snapshot)
        chat_data["last_snapshot"] = snapshot
        message_text = _players_message(snapshot)
    except (asyncio.TimeoutError, OSError) as exc:  # pragma: no cover - network failures
        logger.exception(exc)
        if previous_snapshot:
            error_detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            snapshot = replace(
                previous_snapshot,
                fetched_at=datetime.now(timezone.utc),
                player_names=tuple(),
                query_available=False,
                query_error=error_detail,
            )
            _store_message_snapshot(context, message_id, snapshot)
            chat_data["last_snapshot"] = snapshot
            message_text = _players_fallback_message(snapshot)
        else:
            await error_players_edit(update, context, address)
            await query.answer("Could not refresh player list.", show_alert=True)
            return

    try:
        await query.edit_message_text(
            message_text,
            reply_markup=build_main_keyboard(),
            disable_web_page_preview=True,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            await asyncio.sleep(0.5)
            await query.answer()
            return
        else:
            raise

    await query.answer()


async def cb_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'About' inline button press."""
    logger.info("Callback about called")

    query = update.callback_query
    if not query:
        return

    try:
        await query.edit_message_text(
            _message_with_affiliate_hint(ABOUT_TEXT),
            reply_markup=build_main_keyboard(),
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            await asyncio.sleep(0.5)
            await query.answer()
        else:
            raise


    await query.answer()

# ==========================
# Error helpers
# ==========================

async def error_status(context: ContextTypes.DEFAULT_TYPE, chat_id: int, address: str) -> None:
    safe_address = escape_markdown(address, version=1)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "❌ *Server Offline*\n"
            f"🌐 `{safe_address}`\n"
            "⚙️ _Could not connect to the server._"
        ),
        reply_markup=build_main_keyboard(),
    )


async def error_status_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE, address: str
) -> None:
    if not update.callback_query:
        return

    safe_address = escape_markdown(address, version=1)
    await update.callback_query.edit_message_text(
        text=(
            "❌ *Server Offline*\n"
            f"🌐 `{safe_address}`\n"
            "⚙️ _Could not connect to the server._"
        ),
        reply_markup=build_main_keyboard(),
    )


async def error_players_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE, address: str
) -> None:
    if not update.callback_query:
        return

    safe_address = escape_markdown(address, version=1)
    await update.callback_query.edit_message_text(
        text=(
            "⚠️ *Request Failed*\n"
            f"🌐 `{safe_address}`\n"
            "⚙️ _Could not connect to the server._\n"
            "🔒 _This server might have queries disabled._"
        ),
        reply_markup=build_main_keyboard(),
    )


async def error_url(context: ContextTypes.DEFAULT_TYPE, chat_id: int, address: str) -> None:
    safe_address = escape_markdown(address, version=1)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "⚠️ *Invalid server address*\n"
            f"`{safe_address}`\n\n"
            "Please provide a hostname like:\n"
            "• `play.minecraft.net`\n"
            "• `minecraftgame.org`"
        ),
        reply_markup=build_main_keyboard(),
    )


async def error_incomplete(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "ℹ️ *Server address required*\n"
            "Use the command like this:\n"
            "• `/status play.minecraft.net`\n"
            "• `/players minecraftgame.org:25565`"
        ),
        reply_markup=build_main_keyboard(),
    )


def _message_with_affiliate_hint(message: str) -> str:
    hint = _affiliate_hint()
    if not hint:
        return message

    return f"{message}\n\n{hint}"
