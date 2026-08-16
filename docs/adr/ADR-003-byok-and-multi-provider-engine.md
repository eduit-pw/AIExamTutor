# ADR 003: BYOK (Bring Your Own Key) & Multi-Provider Architecture

## Status
Accepted

## Context
Running a centralized AI proxy backend to handle high-frequency multimodal Vision queries (OCR, image reasoning) for hundreds of exam students would incur significant cloud operational and maintenance costs.

## Decision
The application adopts a **Zero-Server BYOK (Bring Your Own Key)** architecture. The desktop client connects directly to OpenAI-compatible Vision API endpoints. Users can supply their own cloud API keys (OpenAI, Google Gemini, OpenRouter, Groq) or connect to local, free, offline AI servers (LMStudio, Ollama, OmniRoute, Custom Local Server). Configuration parameters are stored locally in the embedded SQLite database (`app_config` table).

## Consequences
### Positive
* Zero server operating costs for the project maintainer.
* Maximum student privacy: user data, images, and chat history stay strictly local.
* Offline support when connected to local LLM providers (e.g., LMStudio, Ollama).

### Negative / Trade-offs
* Students must obtain their own API key or have access to a local/school model endpoint.