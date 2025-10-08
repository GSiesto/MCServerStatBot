# -*- coding: utf-8 -*-
# Guillermo Siesto
# github.com/GSiesto

"""Utility helpers for MCServerStatBot."""

from __future__ import annotations

import re

_SERVER_ADDRESS_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+(?::\d{1,5})?$")
_MAX_ADDRESS_LENGTH = 255


def is_valid_server_address(address: str | None) -> bool:
    """Validate a Minecraft server address or hostname.

    Accepts optional ``:port`` suffix and enforces a conservative length limit to
    avoid extremely long or malicious payloads.
    """

    if not address:
        return False

    if len(address) > _MAX_ADDRESS_LENGTH:
        return False

    return bool(_SERVER_ADDRESS_PATTERN.match(address))