"""
Voice Routes
  POST /voice          — Twilio webhook, returns TwiML to open media stream
  WS   /wss/media-stream — Bidirectional audio bridge
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import Optional

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.core.logger import get_logger
from app.services.deepgram_service import DeepgramSTTService, DeepgramTTSService
from app.services.groq_service import GroqService
from app.services.twilio_service import (
    build_stream_twiml,
    redirect_call_to_emergency,
)

router = APIRouter()
log = get_logger(__name__)


@router.post("/voice", response_class=Response)
async def voice_webhook(request: Request) -> Response:
    """Twilio hits this when a call comes in."""
    twiml = build_stream_twiml()
    log.info("Incoming call — streaming TwiML returned.")
    return Response(content=twiml, media_type="application/xml")


@router.websocket("/wss/media-stream")
async def media_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    log.info("WebSocket connected.")

    groq_svc = GroqService()
    tts_svc = DeepgramTTSService()
    call_sid: Optional[str] = None
    stream_sid: Optional[str] = None
    emergency_triggered = False

    # ── Audio send queue (serialize writes to Twilio WS) ──────────────────
    audio_queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue()

    async def audio_sender() -> None:
        """Pull audio from queue and send to Twilio."""
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break
            if stream_sid:
                payload = base64.b64encode(chunk).decode("utf-8")
                msg = json.dumps({
                    "event": "media",
                    "streamSid": stream_sid,
                    "media": {"payload": payload},
                })
                try:
                    await websocket.send_text(msg)
                except Exception as exc:
                    log.error("WS send error: %s", exc)
            audio_queue.task_done()

    # ── STT callback ──────────────────────────────────────────────────────
    async def on_transcript(text: str, is_final: bool) -> None:
        nonlocal emergency_triggered
        if not is_final or emergency_triggered:
            return

        log.info("Final transcript → Groq: %s", text)

        full_response = ""
        async for token, is_emergency in groq_svc.stream_response(text):
            full_response += token
            if is_emergency and not emergency_triggered:
                emergency_triggered = True
                if call_sid:
                    loop = asyncio.get_event_loop()
                    loop.run_in_executor(
                        None, redirect_call_to_emergency, call_sid
                    )
                return  # Stop TTS pipeline on emergency

        # TTS — synthesize full response (chunk if needed)
        if full_response.strip():
            try:
                audio_bytes = await tts_svc.synthesize(full_response)
                # Send in 160-byte μ-law frames (20ms @ 8kHz)
                chunk_size = 160
                for i in range(0, len(audio_bytes), chunk_size):
                    await audio_queue.put(audio_bytes[i : i + chunk_size])
            except Exception as exc:
                log.error("TTS error: %s", exc)

    # ── Deepgram STT ──────────────────────────────────────────────────────
    stt_svc = DeepgramSTTService(on_transcript=on_transcript)

    try:
        await stt_svc.connect()
    except RuntimeError as exc:
        log.error("STT connect failed: %s", exc)
        await websocket.close()
        return

    sender_task = asyncio.create_task(audio_sender())

    try:
        async for raw_message in websocket.iter_text():
            data = json.loads(raw_message)
            event = data.get("event")

            if event == "start":
                meta = data.get("start", {})
                call_sid = meta.get("callSid")
                stream_sid = meta.get("streamSid")
                log.info("Stream started | call_sid=%s stream_sid=%s", call_sid, stream_sid)
                
                # 👋 Welcome Greeting
                try:
                    welcome_text = "Hello! Thank you for calling MediCare Clinic. How can I help you today?"
                    audio_bytes = await tts_svc.synthesize(welcome_text)
                    chunk_size = 160
                    for i in range(0, len(audio_bytes), chunk_size):
                        await audio_queue.put(audio_bytes[i : i + chunk_size])
                except Exception as exc:
                    log.error("Welcome TTS error: %s", exc)

            elif event == "media":
                payload = data["media"]["payload"]
                audio_bytes = base64.b64decode(payload)
                await stt_svc.send_audio(audio_bytes)

            elif event == "stop":
                log.info("Stream stopped by Twilio.")
                break

    except WebSocketDisconnect:
        log.warning("WebSocket disconnected.")

    except Exception as exc:
        log.error("Unexpected WS error: %s", exc, exc_info=True)

    finally:
        # ── Graceful teardown ─────────────────────────────────────────────
        await stt_svc.finish()
        await audio_queue.put(None)  # signal sender to stop
        await sender_task

        summary = groq_svc.get_summary()
        log.info("Session ended. Transcript summary:\n%s", summary)
        groq_svc.reset()

        try:
            await websocket.close()
        except Exception:
            pass
        log.info("WebSocket closed cleanly.")
