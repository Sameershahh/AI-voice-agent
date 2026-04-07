from decouple import config

# ── Third-party Keys ───────────────────────────────────
GROQ_API_KEY: str = config("GROQ_API_KEY")
DEEPGRAM_API_KEY: str = config("DEEPGRAM_API_KEY")
TWILIO_ACCOUNT_SID: str = config("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: str = config("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER: str = config("TWILIO_PHONE_NUMBER")

# ── Emergency ──────────────────────────────────────────
EMERGENCY_FALLBACK_NUMBER: str = config("EMERGENCY_FALLBACK_NUMBER")

# ── App ────────────────────────────────────────────────
HOST: str = config("HOST", default="0.0.0.0")
PORT: int = config("PORT", default=8000, cast=int)
PUBLIC_URL: str = config("PUBLIC_URL", default="http://localhost:8000")

# ── LLM ────────────────────────────────────────────────
GROQ_MODEL: str = "llama-3.3-70b-versatile"
DEEPGRAM_STT_MODEL: str = "nova-2"
DEEPGRAM_TTS_MODEL: str = "aura-asteria-en"

# ── Business Logic ─────────────────────────────────────
# Edit this prompt to configure the agent for a specific business.
SYSTEM_PROMPT: str = """
You are a professional clinic receptionist for "MediCare Clinic".
Your responsibilities:
- Greet patients warmly and professionally
- Schedule, confirm, or cancel appointments
- Answer common questions about clinic hours, location, and services
- Collect basic patient information (name, DOB, reason for visit)
- Triage urgency: if a patient describes symptoms of a medical emergency
  (chest pain, difficulty breathing, stroke symptoms, severe bleeding, etc.),
  IMMEDIATELY respond with the exact phrase: "EMERGENCY_DETECTED"
  followed by brief reassurance, then stop speaking.

Clinic Hours: Mon-Fri 8am-6pm, Sat 9am-2pm
Location: 123 Health Street, Suite 400
Phone: (555) 123-4567

Keep responses concise — this is a phone call. Speak naturally.
""".strip()

# ── Emergency trigger phrase (must match LLM output exactly) ──
EMERGENCY_TRIGGER: str = "EMERGENCY_DETECTED"
