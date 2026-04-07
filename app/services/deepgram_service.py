"""
Deepgram Service — STT (Nova-2 live streaming) + TTS (Aura).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Callable, Awaitable

import httpx
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

from app.core.config import (
    DEEPGRAM_API_KEY,
    DEEPGRAM_STT_MODEL,
    DEEPGRAM_TTS_MODEL,
)
from app.core.logger import get_logger

log = get_logger(__name__)

TranscriptCallback = Callable[[str, bool], Awaitable[None]]


class DeepgramSTTService:
    """
    Wraps a Deepgram Live WebSocket connection.
    Calls `on_transcript(text, is_final)` on each event.
    """

    def __init__(self, on_transcript: TranscriptCallback) -> None:
        self._on_transcript = on_transcript
        options = DeepgramClientOptions(options={"keepalive": "true"})
        self._dg = DeepgramClient(DEEPGRAM_API_KEY, options)
        self._connection = None

    async def connect(self) -> None:
        self._connection = self._dg.listen.asynclive.v("1")

        self._connection.on(
            LiveTranscriptionEvents.Transcript, self._handle_transcript
        )
        self._connection.on(
            LiveTranscriptionEvents.Error, self._handle_error
        )

        opts = LiveOptions(
            model=DEEPGRAM_STT_MODEL,
            language="en-US",
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
            punctuate=True,
            interim_results=True,
            endpointing=300,
        )
        started = await self._connection.start(opts)
        if not started:
            raise RuntimeError("Deepgram STT connection failed to start.")
        log.info("Deepgram STT connected.")

    async def send_audio(self, data: bytes) -> None:
        if self._connection:
            await self._connection.send(data)

    async def finish(self) -> None:
        if self._connection:
            await self._connection.finish()
            log.info("Deepgram STT connection closed.")

    async def _handle_transcript(self, *args, **kwargs) -> None:
        result = kwargs.get("result")
        if not result:
            return
        try:
            alt = result.channel.alternatives[0]
            text: str = alt.transcript.strip()
            is_final: bool = result.is_final
            if text:
                log.info("STT [final=%s]: %s", is_final, text)
                await self._on_transcript(text, is_final)
        except (AttributeError, IndexError) as exc:
            log.debug("STT parse skip: %s", exc)

    async def _handle_error(self, *args, **kwargs) -> None:
        log.error("Deepgram STT error: %s", kwargs)


class DeepgramTTSService:
    """
    Converts text to μ-law 8kHz audio bytes via Deepgram Aura REST API.
    Returns raw audio suitable for Twilio Media Streams.
    """

    TTS_URL = "https://api.deepgram.com/v1/speak"

    def __init__(self) -> None:
        self._headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        }

    async def synthesize(self, text: str) -> bytes:
        """Returns mulaw-encoded audio bytes."""
        params = {
            "model": DEEPGRAM_TTS_MODEL,
            "encoding": "mulaw",
            "sample_rate": 8000,
            "container": "none",
        }
        payload = {"text": text}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.TTS_URL,
                headers=self._headers,
                params=params,
                json=payload,
            )
            resp.raise_for_status()
            log.info("TTS synthesized %d chars → %d bytes", len(text), len(resp.content))
            return resp.content
