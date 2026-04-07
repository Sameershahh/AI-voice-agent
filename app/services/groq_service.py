"""
Groq LLM Service — streaming inference with emergency detection.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import List

from groq import AsyncGroq

from app.core.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    SYSTEM_PROMPT,
    EMERGENCY_TRIGGER,
)
from app.core.logger import get_logger

log = get_logger(__name__)


class GroqService:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._history: List[dict] = []

    def reset(self) -> None:
        self._history.clear()

    async def stream_response(
        self, user_text: str
    ) -> AsyncIterator[tuple[str, bool]]:
        """
        Yields (token, is_emergency) tuples.
        Sets is_emergency=True on the token that contains EMERGENCY_TRIGGER.
        """
        self._history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

        accumulated = ""
        emergency_fired = False

        try:
            stream = await self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                stream=True,
                max_tokens=512,
                temperature=0.6,
            )

            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if not token:
                    continue

                accumulated += token
                is_emergency = (
                    not emergency_fired and EMERGENCY_TRIGGER in accumulated
                )
                if is_emergency:
                    emergency_fired = True
                    log.warning("Emergency keyword detected in LLM output.")

                yield token, is_emergency

            # Persist assistant turn
            self._history.append({"role": "assistant", "content": accumulated})
            log.info("LLM turn complete. History length: %d", len(self._history))

        except Exception as exc:
            log.error("Groq streaming error: %s", exc)
            yield "I'm sorry, I'm having trouble connecting right now.", False

    def get_summary(self) -> str:
        """Return a compact transcript for logging on disconnect."""
        lines = []
        for msg in self._history:
            role = "User" if msg["role"] == "user" else "Agent"
            lines.append(f"[{role}] {msg['content']}")
        return "\n".join(lines) if lines else "(no conversation)"
