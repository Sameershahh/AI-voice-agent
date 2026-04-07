import os
import uvicorn
from pyngrok import ngrok, conf
from twilio.rest import Client
from app.core.config import HOST, PORT

def update_twilio_webhook(url: str):
    """Programmatically update the Twilio inbound phone number webhook."""
    try:
        from decouple import config as decouple_config
        sid = decouple_config("TWILIO_ACCOUNT_SID")
        token = decouple_config("TWILIO_AUTH_TOKEN")
        phone = decouple_config("TWILIO_PHONE_NUMBER")
    except Exception:
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        phone = os.environ.get("TWILIO_PHONE_NUMBER")

    if not all([sid, token, phone]):
        print("⚠️  Twilio keys missing — skipping auto-sync.")
        return

    client = Client(sid, token)
    numbers = client.incoming_phone_numbers.list(phone_number=phone)
    if numbers:
        pn = numbers[0]
        pn.update(voice_url=f"{url}/voice", voice_method="POST")
        print(f"✅ Twilio Webhook synced to: {url}/voice")
    else:
        print(f"⚠️  Twilio number {phone} not found in account — skipping auto-sync.")

if __name__ == "__main__":
    # ── Configure & start ngrok tunnel ─────────────────────────
    try:
        from decouple import config as decouple_config
        ngrok_token = decouple_config("NGROK_AUTH_TOKEN", default=None)
    except Exception:
        ngrok_token = os.environ.get("NGROK_AUTH_TOKEN")

    if ngrok_token:
        conf.get_default().auth_token = ngrok_token

    # Open basic tunnel on the server port
    # bind_tls=True ensures https://
    public_url = ngrok.connect(PORT, "http", bind_tls=True).public_url
    print(f"\n{'='*60}")
    print(f"  🌐 NGROK TUNNEL ACTIVE")
    print(f"  Public URL:  {public_url}")
    print(f"{'='*60}\n")

    # Sync Twilio
    update_twilio_webhook(public_url)

    # Dynamically patch PUBLIC_URL so the app uses the live tunnel URL
    os.environ["PUBLIC_URL"] = public_url

    # ── Start the server ───────────────────────────────────────
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
        ws_ping_interval=20,
        ws_ping_timeout=20,
    )
