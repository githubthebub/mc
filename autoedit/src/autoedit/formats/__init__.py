"""Input formats. Each format turns its input into what the pipeline needs: a source video, a
word-level transcript, a focus track (where the eye should be), and format extras for the EDL."""

from __future__ import annotations

from .base import Format


def get_format(name: str) -> Format:
    if name == "talking-head":
        from .talking_head import TalkingHead
        return TalkingHead()
    if name == "chat-skit":
        from .chat_skit import ChatSkit
        return ChatSkit()
    raise ValueError(f"unknown format: {name}")
