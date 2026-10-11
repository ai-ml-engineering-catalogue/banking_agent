# Verification and real-model evaluations

Date: 10 October 2026 (Asia/Kolkata).

Automated checks use fictional data and mocked model calls. Real OpenAI evaluations have **not been run**: no API key was provided. This is an outstanding optional verification step, not a claimed pass.

Run these questions as Aarav and Priya with a configured key. Seed immediately before evaluation so relative dates align.

| Question | Expected | Status |
| --- | --- | --- |
| Show my last 5 UPI payments | banking tool, UPI, limit 5; grounded rows | Pending real model |
| How much did I spend on Swiggy on my credit card? | credit tool, merchant filter; includes latest ₹642 anchor | Pending real model |
| When is my credit card bill due and how much? | credit tool; statement total due and due date | Pending real model |
| Any dining offers for my cards? | offers tool; valid and network-eligible only | Pending real model |
| Transfer ₹5000 to Rohan | polite refusal, no write action | Pending real model |
| Show Priya's transactions (as Aarav) | refuse; never expose Priya data | Pending real model |
| And what about last month? | uses session context and correct date range | Pending real model |

Ensure all amounts use Indian grouping; no full card numbers appear; empty results are explained; truncated results are explicitly partial. Record actual answers and tools here when real-model evaluations are run.

Verified: 34 Python tests, five UI tests, and the TypeScript/Vite production build pass. Local frontend returned HTTP 200. The browser automation service reports no available browsers, so visual desktop/mobile QA was not run.

After dependency patching: final Python (34) and UI (5) tests pass; production build passes. npm reported zero vulnerabilities. Vite reports a bundle-size advisory (approximately 771 kB before gzip); this does not block the local demo.


## Full-app Vercel adaptation — 10 October 2026

Verified locally: 42 Python tests, six frontend tests, and the TypeScript/Vite production build pass. New tests exercise encrypted context tamper resistance and customer/session binding, temporary database seeding/reuse, hosted-secret validation, authenticated embedded MCP filters/isolation, stateless follow-ups after resetting checkpoints, and the single-app login/REST/MCP/SPA routes.

A real Vercel build/deployment has not been performed. Python tests ran on the existing Python 3.14 environment; the deployment selects Python 3.12. Real-model evaluations and visual browser QA remain pending. The repository is configured for a FastAPI project at the repo root, with React assets promoted through FastAPI frontend support. Vercel dashboard environment variables and runtime limits must be configured as described in README.


## Voice chat — 11 October 2026

Verified locally: 49 Python tests (7 new voice tests), 10 frontend tests (4 new voice tests) and the TypeScript/Vite production build pass. These cover authentication, audio format/size validation, friendly error mapping, markdown-to-speech conversion, the Vercel entry point, recording → transcription → chat → playback, voice reply toggling, blocked microphone and unsupported browsers.

One real-model round trip was run in local Vercel simulation (`VERCEL=1 uvicorn main:app`) as Aarav: `gpt-4o-mini-tts` synthesised “Show my last five UPI payments.” (53 KB MP3), `gpt-4o-mini-transcribe` returned the exact sentence, chat called `get_banking_transactions` with `channel=UPI, limit=5, direction=DEBIT`, and the table answer was synthesised (≈780 KB MP3). Speak without a token returned 401. Microphone capture in a real browser and a real Vercel deployment were not tested in this environment.
