# Telephony AI Agent

The Telephony AI Agent is an enterprise-ready, low-latency infrastructure for deploying autonomous voice assistants over traditional telephony networks. This system integrates high-speed speech-to-text (STT), large language model (LLM) reasoning, and neural text-to-speech (TTS) to provide a seamless, bidirectional voice interface.

## System Architecture

The service operates as a real-time bridge between telephony providers and AI processing pipelines:

1. **Telephony Layer**: Utilizes Twilio Media Streams to capture and broadcast bidirectional audio via Secure WebSockets (WSS). 
2. **Speech Recognition Layer**: Employs Deepgram's Nova-2 model to process 8kHz mu-law audio streams into finalized text transcripts with sub-second latency.
3. **Reasoning Layer**: Interfaces with the Groq Llama-3.3-70b model to generate contextually aware responses based on enterprise-defined system prompts.
4. **Synthesis Layer**: Uses Deepgram's Aura text-to-speech engine to generate human-like audio, which is then fragmented into 20ms frames for smooth playback over telephony channels.
5. **Emergency Logic**: A dedicated triage system monitors LLM output for critical trigger phrases. Upon detection, the system initiates an immediate call redirection via the Twilio REST API to a pre-defined fallback number.

## Requirements

- Python 3.10+
- Twilio Account SID and Auth Token
- Deepgram API Key (Aura and Nova-2 access)
- Groq API Key (Llama-3.3 access)
- Publicly accessible endpoint (via ngrok or static deployment)

## Installation

1. Initialize the environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Configuration:
   Create a `.env` file based on the provided `.env.example`. Ensure all API credentials and the `PUBLIC_URL` are correctly defined.

## Configuration Parameters

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Authentication for the reasoning engine. |
| `DEEPGRAM_API_KEY` | Authentication for transcription and synthesis services. |
| `TWILIO_ACCOUNT_SID` | Primary identifier for Twilio API interactions. |
| `TWILIO_AUTH_TOKEN` | Authentication secret for Twilio API operations. |
| `TWILIO_PHONE_NUMBER` | The E.164 formatted number assigned to the agent. |
| `EMERGENCY_FALLBACK_NUMBER` | The target destination for critical call redirection. |
| `PUBLIC_URL` | The fully qualified domain name of the serving instance. |

## Execution

The system provides a unified entry point that manages the lifecycle of the application:

```bash
python run.py
```

This script performs the following operations:
- Establishes a secure tunnel (if using ngrok).
- Synchronizes the Twilio phone number's voice webhook with the active deployment URL.
- Initializes the FastAPI application and WebSocket listeners.

## Customization

The agent's behavior is governed by the `SYSTEM_PROMPT` located in `app/core/config.py`. Modification of this prompt allows for the reconfiguration of the agent across various business domains (e.g., medical triage, technical support, or scheduling services).

## Technical Specifications

- **Audio Encoding**: 8-bit PCMU (G.711 mu-law)
- **Sampling Rate**: 8000 Hz
- **Channel Configuration**: Mono
- **Frame Size**: 160 bytes (20ms payload)
- **Logging**: All session interactions and transcripts are persisted to the `logs/` directory for auditing and performance analysis.
