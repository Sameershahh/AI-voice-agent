"""
Twilio utility helpers — TwiML generation + REST API calls.
"""
from __future__ import annotations

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream, Dial

from app.core.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_PHONE_NUMBER,
    EMERGENCY_FALLBACK_NUMBER,
    PUBLIC_URL,
)
from app.core.logger import get_logger

log = get_logger(__name__)

_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def build_stream_twiml() -> str:
    """TwiML that opens a bidirectional media stream."""
    response = VoiceResponse()
    connect = Connect()
    import os
    public = os.environ.get("PUBLIC_URL", PUBLIC_URL)
    stream_url = public.replace("https://", "wss://").replace("http://", "ws://").rstrip('/') + "/wss/media-stream"
    stream = Stream(url=stream_url)
    stream.parameter(name="track", value="inbound_track")
    connect.append(stream)
    response.append(connect)
    return str(response)


def build_emergency_twiml() -> str:
    """TwiML that immediately dials the emergency fallback number."""
    response = VoiceResponse()
    response.say(
        "Connecting you to emergency services now. Please stay on the line.",
        voice="alice",
    )
    dial = Dial()
    dial.number(EMERGENCY_FALLBACK_NUMBER)
    response.append(dial)
    log.warning("Emergency TwiML generated → dialling %s", EMERGENCY_FALLBACK_NUMBER)
    return str(response)


def redirect_call_to_emergency(call_sid: str) -> None:
    """Use Twilio REST API to update a live call to the emergency TwiML."""
    try:
        _client.calls(call_sid).update(
            twiml=build_emergency_twiml()
        )
        log.warning("Call %s redirected to emergency fallback.", call_sid)
    except Exception as exc:
        log.error("Failed to redirect call %s: %s", call_sid, exc)
