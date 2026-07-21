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

STATUS_HINT_TEXT = (
    "ℹ️ *How to check a server*\n"
    "Start with `/status host.example.com` to pick a server, then use the buttons to refresh the results."
)

PLAYERS_HINT_TEXT = (
    "ℹ️ *How to list players*\n"
    "Run `/players host.example.com` first; once the bot has a server, the buttons can refresh the player list."
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


@dataclass(slots=True)
class MessageContextEntry:
    """Per-message context allowing callbacks to recover address and cached data."""

    address: str | None
    snapshot: ServerSnapshot | None


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
    url = (os.getenv(AFFILIATE_URL_ENV) or "").strip().strip("'\"")
    if not url:
        return None

    label = (os.getenv(AFFILIATE_LABEL_ENV) or DEFAULT_AFFILIATE_LABEL).strip().strip("'\"") or DEFAULT_AFFILIATE_LABEL

    blurb_raw = (os.getenv(AFFILIATE_BLURB_ENV) or DEFAULT_AFFILIATE_BLURB).strip()
    if blurb_raw.startswith("$'") and blurb_raw.endswith("'"):
        blurb_raw = blurb_raw[2:-1]
    elif blurb_raw.startswith('$"') and blurb_raw.endswith('"'):
        blurb_raw = blurb_raw[2:-1]
    else:
        blurb_raw = blurb_raw.strip("'\"")

    blurb = blurb_raw.replace("\\n", "\n").strip() or DEFAULT_AFFILIATE_BLURB
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
    lines = blurb.split("\n")
    escaped_lines = [escape_markdown(line, version=1) for line in lines]
    safe_blurb = "\n".join(escaped_lines)
    return f"🙌 {safe_blurb}"



def _chat_data(context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    return cast(dict[str, Any], context.chat_data)


def _clear_last_context(chat_data: dict[str, Any]) -> None:
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)


def _store_message_snapshot(
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int,
    snapshot: ServerSnapshot | None,
    *,
    address: str | None = None,
) -> None:
    chat_data = _chat_data(context)
    store = cast(dict[int, MessageContextEntry], chat_data.setdefault(MESSAGE_CONTEXT_KEY, {}))
    order = cast(deque[int], chat_data.setdefault(MESSAGE_CONTEXT_ORDER_KEY, deque()))

    entry = MessageContextEntry(address=address or (snapshot.address if snapshot else None), snapshot=snapshot)

    if message_id in store:
        store[message_id] = entry
        try:
            order.remove(message_id)
        except ValueError:
            pass
    else:
        store[message_id] = entry

    order.append(message_id)

    while len(order) > MESSAGE_CONTEXT_LIMIT:
        old_id = order.popleft()
        store.pop(old_id, None)


def _get_message_context(
    context: ContextTypes.DEFAULT_TYPE, message_id: int
) -> MessageContextEntry | None:
    chat_data = _chat_data(context)
    store = cast(dict[int, MessageContextEntry] | None, chat_data.get(MESSAGE_CONTEXT_KEY))
    if not store:
        return None

    entry = store.get(message_id)
    if isinstance(entry, MessageContextEntry):
        return entry

    if isinstance(entry, ServerSnapshot):  # legacy compatibility
        converted = MessageContextEntry(address=entry.address, snapshot=entry)
        store[message_id] = converted
        return converted

    return None


async def _run_in_thread(func, *args, timeout: float = DEFAULT_TIMEOUT):
    return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=timeout)


async def _lookup_server(address: str) -> JavaServer:
    try:
        return await _run_in_thread(JavaServer.lookup, address)
    except Exception as exc:
        logger.debug("JavaServer.lookup failed for %s (%s), falling back to direct parse", address, exc)
        host, port = utils.parse_address(address)
        return JavaServer(host, port)


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


def _ping_indicator(ms: int) -> str:
    if ms < 100:
        return "🟢"
    elif ms < 250:
        return "🟡"
    else:
        return "🔴"


def _capacity_info(online: int, max_players: int) -> str:
    if max_players > 0:
        pct = (online / max_players) * 100
        return f"{online} / {max_players} ({pct:.1f}%)"
    return f"{online} / {max_players}"


def _status_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    
    desc_lines = [line.strip() for line in snapshot.description.split("\n") if line.strip()]
    escaped_desc_lines = [escape_markdown(line, version=1) for line in desc_lines]
    formatted_motd = "\n".join(f"_{line}_" for line in escaped_desc_lines) or "_No description provided._"

    version_name = escape_markdown(snapshot.version_name, version=1)
    fetched = escape_markdown(snapshot.fetched_at.strftime("%Y-%m-%d %H:%M UTC"), version=1)
    ping_icon = _ping_indicator(snapshot.latency_ms)
    capacity = _capacity_info(snapshot.players_online, snapshot.players_max)

    base = (
        "🟢 *SERVER ONLINE*\n"
        f"🌐 `{safe_address}`\n\n"
        "💬 *MOTD*\n"
        f"{formatted_motd}\n\n"
        "📊 *Server Details*\n"
        f"• *Version:* `{version_name}`\n"
        f"• *Latency:* `{snapshot.latency_ms} ms` {ping_icon}\n"
        f"• *Players:* `{capacity}`\n\n"
        f"🕒 _Checked: {fetched}_"
    )

    return _message_with_affiliate_hint(base)


def _players_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    capacity = _capacity_info(snapshot.players_online, snapshot.players_max)
    
    header = (
        "👥 *PLAYERS ONLINE*\n"
        f"🌐 `{safe_address}`\n"
        f"📊 *Online:* `{capacity}`"
    )

    if snapshot.player_names:
        formatted_names = _format_player_names(snapshot.player_names)
        parts = [header, "", formatted_names]

        if not snapshot.query_available:
            parts.extend(
                [
                    "",
                    "ℹ️ _Showing limited sample from status ping; full query protocol disabled on server._",
                ]
            )

        return _message_with_affiliate_hint("\n".join(parts))

    return _players_fallback_message(snapshot)


def _players_fallback_message(snapshot: ServerSnapshot) -> str:
    safe_address = escape_markdown(snapshot.address, version=1)
    capacity = _capacity_info(snapshot.players_online, snapshot.players_max)
    
    lines = [
        "👥 *PLAYERS ONLINE*",
        f"🌐 `{safe_address}`",
        f"📊 *Online:* `{capacity}`",
        "",
        "⚠️ _This server has queries disabled, so individual player names are not available._",
    ]

    if snapshot.query_error:
        safe_error = escape_markdown(snapshot.query_error, version=1)
        lines.extend(
            [
                "",
                f"ℹ️ _Query status: {safe_error}_",
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

    affiliate_button = _affiliate_button()
    affiliate_markup = InlineKeyboardMarkup([[affiliate_button]]) if affiliate_button else None

    await update.message.reply_text(
        _message_with_affiliate_hint(WELCOME_TEXT),
        reply_markup=affiliate_markup,
        disable_web_page_preview=True,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Usage: /status <host[:port]>"""

    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    await _send_typing(context, chat_id)
    logger.info("/status called")

    chat_data = _chat_data(context)

    args = context.args or []
    if len(args) != 1:
        _clear_last_context(chat_data)
        await error_incomplete(context, chat_id)
        logger.info("/status did not provide an address")
        return

    address = args[0].strip()
    if not utils.is_valid_server_address(address):
        _clear_last_context(chat_data)
        await error_url(context, chat_id, address)
        logger.info("Invalid server address supplied for /status")
        return

    chat_data["last_address"] = address
    chat_data.pop("last_snapshot", None)

    try:
        snapshot = await _build_snapshot(address, include_query=False)
    except Exception as exc:  # pragma: no cover - network failures
        await error_status(context, chat_id, address)
        logger.exception(exc)
        chat_data.pop("last_address", None)
        return

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

    chat_data = _chat_data(context)

    args = context.args or []
    if len(args) != 1:
        _clear_last_context(chat_data)
        await error_incomplete(context, chat_id)
        logger.info("/players did not provide an address")
        return

    address = args[0].strip()
    if not utils.is_valid_server_address(address):
        _clear_last_context(chat_data)
        await error_url(context, chat_id, address)
        logger.info("Invalid server address supplied for /players")
        return

    chat_data["last_address"] = address
    chat_data.pop("last_snapshot", None)

    try:
        snapshot = await _build_snapshot(address, include_query=True)
    except Exception as exc:  # pragma: no cover - network failures
        await error_status(context, chat_id, address)
        logger.exception(exc)
        chat_data.pop("last_address", None)
        return

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
    entry = _get_message_context(context, message_id)
    if entry:
        address = entry.address
        previous_snapshot = entry.snapshot
    else:
        address = cast(str | None, chat_data.get("last_address"))
        previous_snapshot = cast(ServerSnapshot | None, chat_data.get("last_snapshot"))

    if not address:
        chat_data.pop("last_address", None)
        chat_data.pop("last_snapshot", None)
        try:
            await query.edit_message_text(
                _message_with_affiliate_hint(STATUS_HINT_TEXT),
                reply_markup=build_main_keyboard(),
                disable_web_page_preview=True,
            )
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await asyncio.sleep(0.5)
            else:
                raise
        _store_message_snapshot(context, message_id, None, address=None)
        await query.answer()
        return

    fallback_notice: str | None = None

    try:
        snapshot = await _build_snapshot(address, include_query=False)
        _store_message_snapshot(context, message_id, snapshot)
        chat_data["last_snapshot"] = snapshot
        chat_data["last_address"] = snapshot.address
    except Exception as exc:  # pragma: no cover - network failures
        logger.exception(exc)
        if previous_snapshot:
            snapshot = previous_snapshot
            _store_message_snapshot(context, message_id, snapshot)
            chat_data["last_snapshot"] = snapshot
            chat_data["last_address"] = snapshot.address
            fallback_notice = "⚠️ _Showing cached data because the server timed out._"
        else:
            await error_status_edit(update, context, address)
            await query.answer()
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
    entry = _get_message_context(context, message_id)
    if entry:
        address = entry.address
        previous_snapshot = entry.snapshot
    else:
        address = cast(str | None, chat_data.get("last_address"))
        previous_snapshot = cast(ServerSnapshot | None, chat_data.get("last_snapshot"))

    if not address:
        chat_data.pop("last_address", None)
        chat_data.pop("last_snapshot", None)
        try:
            await query.edit_message_text(
                _message_with_affiliate_hint(PLAYERS_HINT_TEXT),
                reply_markup=build_main_keyboard(),
                disable_web_page_preview=True,
            )
        except BadRequest as exc:
            if "Message is not modified" in str(exc):
                await asyncio.sleep(0.5)
            else:
                raise
        _store_message_snapshot(context, message_id, None, address=None)
        await query.answer()
        return

    try:
        snapshot = await _build_snapshot(address, include_query=True)
        _store_message_snapshot(context, message_id, snapshot)
        chat_data["last_snapshot"] = snapshot
        chat_data["last_address"] = snapshot.address
        message_text = _players_message(snapshot)
    except Exception as exc:  # pragma: no cover - network failures
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
            chat_data["last_address"] = snapshot.address
            message_text = _players_fallback_message(snapshot)
        else:
            await error_players_edit(update, context, address)
            await query.answer()
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
    chat_data = _chat_data(context)
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=_message_with_affiliate_hint(
            "🔴 *SERVER OFFLINE*\n"
            f"🌐 `{safe_address}`\n\n"
            "⚙️ _Could not connect to the Minecraft server. Verify the address or port._"
        ),
        reply_markup=build_main_keyboard(),
    )
    _store_message_snapshot(context, message.message_id, None, address=None)


async def error_status_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE, address: str
) -> None:
    if not update.callback_query:
        return

    safe_address = escape_markdown(address, version=1)
    chat_data = _chat_data(context)
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)
    message = update.callback_query.message
    await update.callback_query.edit_message_text(
        text=_message_with_affiliate_hint(
            "🔴 *SERVER OFFLINE*\n"
            f"🌐 `{safe_address}`\n\n"
            "⚙️ _Could not connect to the Minecraft server. Verify the address or port._"
        ),
        reply_markup=build_main_keyboard(),
    )
    if message:
        _store_message_snapshot(context, message.message_id, None, address=None)


async def error_players_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE, address: str
) -> None:
    if not update.callback_query:
        return

    safe_address = escape_markdown(address, version=1)
    chat_data = _chat_data(context)
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)
    message = update.callback_query.message
    await update.callback_query.edit_message_text(
        text=_message_with_affiliate_hint(
            "⚠️ *REQUEST FAILED*\n"
            f"🌐 `{safe_address}`\n\n"
            "⚙️ _Could not connect or server queries are disabled._"
        ),
        reply_markup=build_main_keyboard(),
    )
    if message:
        _store_message_snapshot(context, message.message_id, None, address=None)


async def error_url(context: ContextTypes.DEFAULT_TYPE, chat_id: int, address: str) -> None:
    safe_address = escape_markdown(address, version=1)
    chat_data = _chat_data(context)
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=_message_with_affiliate_hint(
            "⚠️ *INVALID SERVER ADDRESS*\n"
            f"`{safe_address}`\n\n"
            "Please provide a hostname or IP like:\n"
            "• `play.hypixel.net`\n"
            "• `juega.orizon.gg`\n"
            "• `mc.example.com:25565`"
        ),
        reply_markup=build_main_keyboard(),
    )
    _store_message_snapshot(context, message.message_id, None, address=None)


async def error_incomplete(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    chat_data = _chat_data(context)
    chat_data.pop("last_address", None)
    chat_data.pop("last_snapshot", None)
    message = await context.bot.send_message(
        chat_id=chat_id,
        text=_message_with_affiliate_hint(
            "ℹ️ *SERVER ADDRESS REQUIRED*\n\n"
            "Use the command with a server address:\n"
            "• `/status juega.orizon.gg`\n"
            "• `/players play.hypixel.net`"
        ),
        reply_markup=build_main_keyboard(),
    )
    _store_message_snapshot(context, message.message_id, None, address=None)



def _message_with_affiliate_hint(message: str) -> str:
    hint = _affiliate_hint()
    if not hint:
        return message

    return f"{message}\n\n{hint}"
