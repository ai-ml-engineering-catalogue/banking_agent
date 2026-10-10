# Spec: Banking App + MCP Server + LangGraph AI Agent (ICICI-style demo)

**Status:** Ready for implementation
**Source:** Developer request (VAN), 10 Oct 2026

## 1. Description
A self-contained demo that shows AI agents talking to a banking system through the Model Context Protocol (MCP). It has four parts: (1) a dummy ICICI-style retail banking web app backed by a local SQLite database with 5 seeded Indian customers, each with a savings account, a debit card and a credit card; (2) an MCP server exposing 3 read-only tools on top of that data (banking/debit transactions, credit-card transactions, available offers); (3) a LangGraph agent using an OpenAI model that calls those tools to answer customer questions; (4) a modern React UI with login, a basic banking dashboard and a **Chatbot tab** where the logged-in customer asks questions in natural language. The goal is a clean reference implementation of "agent -> MCP -> banking data" that a coding agent can build end to end.

## 2. Acceptance Criteria
- **AC-1:** Running the seed command creates a SQLite database with exactly 5 customers (Indian names), each with 1 savings account, 1 debit card, 1 credit card, 40+ account transactions, 25+ credit-card transactions, and 1 credit-card statement; plus a shared set of 15+ offers.
- **AC-2:** Each customer can log in on the React app with their own dummy username/password (listed in section 7). Wrong credentials show an error; protected pages redirect to login when not authenticated.
- **AC-3:** After login the UI shows tabs: **Dashboard**, **Transactions**, **Cards**, **Offers**, **Chatbot**. Look and feel is modern, responsive, and ICICI-inspired (orange/maroon palette, original design, no real ICICI logo or trademarked assets).
- **AC-4:** An MCP server runs as a separate process and exposes exactly 3 tools: `get_banking_transactions`, `get_credit_card_transactions`, `get_available_offers`. All are read-only.
- **AC-5:** MCP tools never accept a customer ID from the caller. The customer is derived from the authenticated user's token, so one customer can never read another customer's data (verified by test).
- **AC-6:** `get_banking_transactions` supports filters: date range, channel (debit card, UPI, net banking, NEFT, IMPS, ATM), category, merchant text, min/max amount, direction (debit/credit), limit; and returns the matching rows plus a summary (count, total debits, total credits).
- **AC-7:** `get_credit_card_transactions` supports filters: date range, category, merchant text, min/max amount, type (purchase/payment/refund/fee/EMI), limit; and returns rows plus a summary and the card's current limit, available limit, outstanding amount and next due date.
- **AC-8:** `get_available_offers` returns only valid (not expired) offers the customer is eligible for based on their card types and network, with optional category and merchant filters.
- **AC-9:** A LangGraph agent (OpenAI model, key from env) loads the 3 MCP tools, decides which to call, and returns a natural-language answer grounded only in tool output. Amounts are shown in INR with Indian digit grouping (e.g. ₹1,23,456.00).
- **AC-10:** The Chatbot tab lets the user type a question and see the answer in a chat UI with a typing indicator, message history for the session, suggested starter questions, and a small "Used tools: ..." chip under each answer showing which MCP tool(s) were called.
- **AC-11:** The agent keeps conversation context within a session (follow-up like "and what about last month?" works) using a LangGraph checkpointer keyed by a per-user thread id.
- **AC-12:** The agent refuses or explains it cannot do write actions (transfers, bill pay, blocking cards) and does not invent data when tools return nothing.
- **AC-13:** A README documents setup, env vars, how to start all services, and the demo credentials; one command seeds the DB and one command (or a documented set) starts everything.
- **AC-14:** Automated tests cover: seed integrity, auth, each MCP tool (filters + isolation), and at least one agent test with a mocked LLM; there is a manual/optional eval checklist for real-LLM questions (section 7.3).

## 3. In Scope
- Monorepo with `backend/` (FastAPI), `mcp_server/` (MCP over streamable HTTP), `agent/` (LangGraph, used by the backend), `frontend/` (React).
- SQLite schema, deterministic seed script, 5 customers with credentials, cards, transactions, statements, offers.
- JWT login endpoint and read-only REST endpoints that power Dashboard/Transactions/Cards/Offers tabs.
- MCP server with 3 tools, per-request authentication, read-only DB access.
- LangGraph agent, system prompt, OpenAI config via env, `/api/chat` endpoint.
- React UI (Vite + TypeScript + Tailwind) with login, 5 tabs, chat interface.
- Unit/integration tests, README, `.env.example`, run scripts.

## 4. Out of Scope
- Real banking integrations, real PII, real ICICI branding/logos/APIs (use an original name like "iBank Demo" and an ICICI-inspired color theme only).
- Write operations: fund transfer, bill payment, card block/unblock, adding payees. Do not add write tools to the MCP server.
- Registration, forgot password, OTP/2FA, KYC, roles/admin panel.
- Token streaming / SSE for chat responses (v1 returns the full answer; see Open Questions).
- Multi-agent setups, RAG, vector DBs, long-term memory across sessions.
- Production hardening (rate limiting, secrets manager, Docker/K8s, CI/CD). A simple `docker-compose.yml` is optional, not required.
- Other LLM providers (OpenAI only).
- Do not refactor or add features beyond what is listed.

## 5. Assumptions
- **A1:** Python 3.11+, Node 20+. Backend FastAPI + SQLAlchemy Core or plain `sqlite3`; keep it simple.
- **A2:** Single SQLite file at `data/bank.db`, shared by backend (read/write for seed/auth) and MCP server (opened **read-only**, `file:data/bank.db?mode=ro`).
- **A3:** Money stored as integer **paise** in the DB; tools return rupees as numbers plus `"currency": "INR"`.
- **A4:** MCP uses the official Python `mcp` SDK (FastMCP) with **streamable HTTP** transport at `http://localhost:8001/mcp`. The agent connects with `langchain-mcp-adapters` (`MultiServerMCPClient`).
- **A5:** Auth: backend issues an HS256 JWT (`sub` = customer id, 60 min expiry) using `JWT_SECRET`. The same secret lets the MCP server validate the token. Passwords hashed with bcrypt.
- **A6:** Agent forwards the user's JWT to the MCP server in the `Authorization: Bearer` header on each request, so the MCP server derives the customer itself. The LLM never sees or supplies a customer ID.
- **A7:** Default model `gpt-4o-mini` via `OPENAI_MODEL`, temperature 0. Key via `OPENAI_API_KEY` (never committed, never sent to the browser).
- **A8:** Agent graph is the standard tool-calling loop (agent node -> tools node -> back until no tool calls) with `MemorySaver` checkpointer, `thread_id = f"{customer_id}:{session_id}"`. Max 6 tool-call iterations per question.
- **A9:** "Today" for relative dates is injected into the system prompt (real current date). Seed data is generated relative to the seed run date so recent-date questions work.
- **A10:** Frontend: Vite + React 18 + TypeScript + Tailwind CSS; React Router; TanStack Query; lucide-react icons. Token kept in memory + `sessionStorage` (demo only).
- **A11:** Merchant names in seed data may be real well-known Indian brands (Swiggy, Amazon, etc.) since all data is fictional; offers are fictional and attributed to "iBank Demo".
- **A12:** The Dashboard/Transactions/Cards/Offers tabs are simple read-only views that call the backend REST API (not the agent), kept minimal so effort goes to the MCP + agent flow.

## 6. Open Questions
- **Q1:** Stream chat tokens (SSE) for a nicer feel? *Default: no, non-streaming in v1.*
- **Q2:** Preferred OpenAI model? *Default: `gpt-4o-mini`; change via env.*
- **Q3:** MCP transport: stdio is simpler but cannot carry a per-user token cleanly. *Default: streamable HTTP as in A4.*
- **Q4:** Should the agent also be reachable by external MCP clients (e.g. Claude Desktop) for demo? *Default: MCP server is standard, so it works, but external clients would need a token; not tested in v1.*

## 7. Technical Notes

### 7.1 Architecture
```
React UI (:5173)
   │  REST + JWT
   ▼
Backend FastAPI (:8000)  ── /api/auth/login, /api/me, /api/accounts, /api/transactions,
   │                         /api/cards, /api/offers, /api/chat
   │  /api/chat -> LangGraph agent (OpenAI LLM)
   │                    │  MCP (streamable HTTP, Authorization: Bearer <user JWT>)
   ▼                    ▼
SQLite data/bank.db  ◄── MCP Server FastMCP (:8001/mcp)  [read-only connection]
                          tools: get_banking_transactions
                                 get_credit_card_transactions
                                 get_available_offers
```

### 7.2 Repo layout
```
banking-mcp-agent/
├─ README.md
├─ .env.example            # OPENAI_API_KEY, OPENAI_MODEL, JWT_SECRET, DB_PATH, MCP_URL
├─ data/                   # bank.db (gitignored)
├─ common/                 # db.py (connections), money.py (paise<->INR, INR formatting), auth.py (JWT verify)
├─ backend/
│  ├─ app/main.py, routes/{auth,bank,chat}.py, schemas.py
│  ├─ seed/seed.py         # python -m backend.seed.seed
│  └─ tests/
├─ mcp_server/
│  ├─ server.py            # FastMCP app, 3 tools, auth middleware
│  ├─ queries.py           # SQL for each tool (shared with tests)
│  └─ tests/
├─ agent/
│  ├─ graph.py             # build_graph(tools, llm)
│  ├─ prompts.py
│  ├─ service.py           # run_chat(token, session_id, message) -> {answer, tools_used}
│  └─ tests/
└─ frontend/               # Vite React TS app
```

### 7.3 Database schema (SQLite)
- `customers(id PK, username UNIQUE, password_hash, full_name, email, phone, city, created_at)`
- `accounts(id PK, customer_id FK, account_number, ifsc, branch, account_type, balance_paise, opened_on)` — IFSC like `DEMO0001234` (fictional, not a real ICICI code).
- `cards(id PK, customer_id FK, account_id FK NULL, card_type 'DEBIT'|'CREDIT', network 'VISA'|'MASTERCARD'|'RUPAY', variant, last4, expiry, status, credit_limit_paise NULL, statement_day NULL, due_day NULL)`
- `account_transactions(id PK, account_id FK, card_id FK NULL, txn_ts, amount_paise, direction 'DEBIT'|'CREDIT', channel 'DEBIT_CARD'|'UPI'|'NETBANKING'|'NEFT'|'IMPS'|'ATM', merchant, description, category, balance_after_paise, reference_no, status)`
- `credit_card_transactions(id PK, card_id FK, txn_ts, posted_on, amount_paise, txn_type 'PURCHASE'|'PAYMENT'|'REFUND'|'FEE'|'EMI', merchant, category, description, reference_no, reward_points, status)`
- `credit_card_statements(id PK, card_id FK, period_start, period_end, total_due_paise, min_due_paise, due_date, status 'UNPAID'|'PAID')`
- `offers(id PK, title, description, category, merchant NULL, offer_type 'CASHBACK'|'DISCOUNT'|'REWARD_POINTS'|'EMI', benefit_text, eligible_card_type 'DEBIT'|'CREDIT'|'ANY', eligible_network NULL, min_spend_paise NULL, valid_from, valid_to, promo_code NULL, terms)`
- Categories (shared list): `Groceries, Dining, Fuel, Shopping, Travel, Entertainment, Utilities, Healthcare, Education, Rent, Salary, Transfer, EMI, Fees, Cash`.

### 7.4 Demo users (seed these exactly)
| # | Full name | Username | Password | City | Debit | Credit |
|---|-----------|----------|----------|------|-------|--------|
| 1 | Aarav Sharma | `aarav.sharma` | `Aarav@123` | Mumbai | Visa ••4821 | Mastercard ••7390 (limit ₹2,00,000) |
| 2 | Priya Iyer | `priya.iyer` | `Priya@123` | Chennai | RuPay ••1145 | Visa ••5562 (limit ₹1,50,000) |
| 3 | Rohan Mehta | `rohan.mehta` | `Rohan@123` | Ahmedabad | Visa ••9034 | Visa ••2218 (limit ₹3,00,000) |
| 4 | Ananya Reddy | `ananya.reddy` | `Ananya@123` | Hyderabad | Mastercard ••6673 | RuPay ••8841 (limit ₹1,00,000) |
| 5 | Vikram Singh Rathore | `vikram.rathore` | `Vikram@123` | Jaipur | Visa ••3306 | Mastercard ••4457 (limit ₹2,50,000) |

Seed rules: fixed random seed (e.g. 42) for repeatability; transactions spread over the last ~90 days; each user has a monthly salary credit (NEFT), rent/EMI/utilities debits, UPI spends, a few ATM withdrawals, debit-card POS spends; credit card has purchases across categories, one refund, one annual-fee or EMI row, one past payment, and an UNPAID current statement with a due date 10–20 days ahead. Include 2–3 **anchor transactions per user** with fixed merchant/amount (e.g. Aarav: "Swiggy ₹642 on credit card", "Amazon ₹4,899") so evals have known answers. Offers: ~15, mix of DEBIT/CREDIT/ANY, a few network-specific, and 2 expired ones to test filtering.

### 7.5 MCP tool contracts
All tools: read-only, identify the customer from the validated bearer token, return JSON, cap `limit` at 50 (default 20), amounts in rupees, dates ISO 8601. Invalid input returns a clear error message the LLM can act on.

1. `get_banking_transactions(from_date?, to_date?, channel?, category?, merchant_query?, min_amount?, max_amount?, direction?, limit?)`
   Returns `{ account: {masked_number, balance}, transactions: [...], summary: {count, total_debits, total_credits}, truncated: bool }`. Covers debit card and online banking (UPI, net banking, NEFT, IMPS, ATM).
2. `get_credit_card_transactions(from_date?, to_date?, category?, merchant_query?, min_amount?, max_amount?, txn_type?, limit?)`
   Returns `{ card: {network, last4, credit_limit, available_limit, outstanding, next_due_date, min_due}, transactions: [...], summary: {count, total_spend, total_payments, total_reward_points}, truncated: bool }`.
3. `get_available_offers(category?, merchant_query?, card_type?)`
   Returns `{ offers: [{id, title, description, category, merchant, benefit_text, applicable_to, valid_till, promo_code, terms}] }` filtered by validity and the customer's card types/networks.

Tool descriptions must be written clearly for the LLM (when to use each, parameter formats, example).

### 7.6 Agent
- LangGraph `StateGraph` with `MessagesState`; nodes: `agent` (ChatOpenAI bound to MCP tools) and `tools` (ToolNode); conditional edge on tool calls; recursion limit ~12. `langgraph.prebuilt.create_react_agent` is acceptable if it satisfies AC-9 to AC-12.
- Build the `MultiServerMCPClient` per request with `headers={"Authorization": f"Bearer {token}"}` and fetch tools; compile graph with a shared `MemorySaver`.
- System prompt rules: you are a banking assistant for the logged-in customer; use tools for all account facts; never guess; format INR with Indian grouping; mask card numbers to last 4; read-only, politely decline transfers/blocks; ask a clarifying question if the date range is ambiguous; keep answers concise with a short table or bullets when listing transactions; include today's date.
- `/api/chat` request `{message, session_id}`, response `{answer, tools_used: [{name, args}]}`. Handle OpenAI/MCP errors with a friendly 502 message.

### 7.7 Frontend notes
- Login page: split layout, brand panel + form, demo-credentials helper (collapsible) for convenience.
- Dashboard: balance card, credit limit/available card with utilization bar, recent transactions, spending-by-category chart (recharts).
- Chatbot tab: message bubbles, markdown rendering (tables/bullets), typing dots, starter chips ("Show my last 10 UPI transactions", "How much did I spend on dining this month with my credit card?", "When is my credit card bill due?", "Any offers on travel?"), tools-used chips, "New chat" button resets `session_id`.
- Accessible, keyboard-friendly, works on mobile width.

### 7.8 Manual eval checklist (real LLM, optional)
| Question (as Aarav) | Expected tool(s) | Check |
|---|---|---|
| "Show my last 5 UPI payments" | get_banking_transactions | channel=UPI, 5 rows |
| "How much did I spend on Swiggy on my credit card?" | get_credit_card_transactions | matches anchor txn |
| "When is my credit card bill due and how much?" | get_credit_card_transactions | statement fields |
| "Any dining offers for my cards?" | get_available_offers | no expired offers |
| "Transfer ₹5000 to Rohan" | none | polite refusal |
| "Show Priya's transactions" | none/own data only | no cross-user data |

## 8. Tasks for Coding Agent

### T1: Scaffold monorepo, config and tooling
- **Goal:** Create the project skeleton so all services can be developed independently.
- **Details:** Create the layout in 7.2; `pyproject.toml`/`requirements.txt` (fastapi, uvicorn, pydantic, pyjwt, bcrypt, mcp, langgraph, langchain-openai, langchain-mcp-adapters, pytest, httpx); `.env.example` with `OPENAI_API_KEY, OPENAI_MODEL=gpt-4o-mini, JWT_SECRET, DB_PATH=data/bank.db, MCP_URL=http://localhost:8001/mcp`; `.gitignore` (data/, .env, node_modules); `common/` helpers `db.py` (rw and ro connection factories), `money.py` (paise<->rupees, Indian-grouped INR formatter), `auth.py` (create/verify JWT).
- **Files/areas:** repo root, `common/`.
- **Depends on:** None
- **Covers:** Supporting (AC-13)
- **Done when:** `pytest` runs (even with 0 tests) and `python -c "from common.money import format_inr; print(format_inr(12345600))"` prints `₹1,23,456.00`.

### T2: Create DB schema and deterministic seed script
- **Goal:** Generate `data/bank.db` with all tables and the 5 demo customers' data.
- **Details:** Implement schema from 7.3; seed per 7.4 (exact users, bcrypt-hashed passwords, 1 savings account + 1 debit + 1 credit card each, 40+ account txns, 25+ credit txns, 1 UNPAID statement each, 15+ offers incl. 2 expired, anchor transactions). Use `random.Random(42)`, dates relative to today. Command: `python -m backend.seed.seed` (drops and recreates the DB).
- **Files/areas:** new `backend/seed/seed.py`, `backend/seed/data.py`.
- **Depends on:** T1
- **Covers:** AC-1
- **Done when:** seed test asserts 5 customers, 5 accounts, 10 cards (5 debit/5 credit), per-user minimum txn counts, expired offers exist, and running seed twice yields identical row counts.

### T3: Build backend auth and read-only REST API
- **Goal:** Let the React app log in and fetch banking data.
- **Details:** FastAPI app with CORS for `http://localhost:5173`. `POST /api/auth/login {username,password}` -> `{access_token, token_type, customer:{full_name}}`, 401 `INVALID_CREDENTIALS` on failure. Auth dependency validating bearer JWT. `GET /api/me`, `/api/accounts`, `/api/transactions` (filters + pagination, both account and credit-card, `?source=account|credit`), `/api/cards` (with credit limit/outstanding), `/api/offers` (eligible, valid only), `/api/summary` (spend by category last 30 days). All scoped to the token's customer.
- **Files/areas:** `backend/app/main.py`, `routes/auth.py`, `routes/bank.py`, `schemas.py`.
- **Depends on:** T2
- **Covers:** AC-2
- **Done when:** tests: login ok/fail, 401 without token, user A's token never returns user B's rows.

### T4: Implement MCP server with 3 read-only tools and token-based identity
- **Goal:** Expose banking data to agents via MCP.
- **Details:** FastMCP server on `:8001`, streamable HTTP at `/mcp`. Middleware/context extracts `Authorization: Bearer`, verifies JWT with `common.auth`, sets the customer id for the request (contextvar); missing/invalid token -> 401. Implement the 3 tools per 7.5 using `mcp_server/queries.py` (parameterized SQL only, DB opened read-only). Tool inputs must NOT include any customer/account id. Validate dates (ISO), numeric ranges, enum values; cap limit at 50. Write LLM-friendly tool descriptions.
- **Files/areas:** new `mcp_server/server.py`, `mcp_server/queries.py`.
- **Depends on:** T2
- **Covers:** AC-4, AC-5, AC-6, AC-7, AC-8
- **Done when:** running `python -m mcp_server.server` and listing tools via an MCP client returns exactly the 3 tool names; a call without a token is rejected.

### T5: Test MCP tools (filters, summaries, isolation)
- **Goal:** Prove tool correctness and customer isolation.
- **Details:** Tests against a temp seeded DB: each filter on tool 1 and 2 (date range, channel, category, merchant, amount, type, limit cap), summary totals equal sum of returned rows, credit card block fields present, offers exclude expired and ineligible (e.g. RuPay-only offer hidden from a Visa user), and tokens for customer A never return customer B data. Include an end-to-end test using an MCP client over HTTP with a bearer token.
- **Files/areas:** `mcp_server/tests/`.
- **Depends on:** T4
- **Covers:** AC-5, AC-6, AC-7, AC-8, AC-14
- **Done when:** `pytest mcp_server` passes.

### T6: Build the LangGraph agent
- **Goal:** Agent that answers questions using MCP tools.
- **Details:** `agent/prompts.py` system prompt per 7.6 (inject today's date). `agent/graph.py`: `build_graph(tools, llm)` with agent/tools nodes, conditional edges, recursion limit, `MemorySaver`. `agent/service.py`: `run_chat(token, session_id, message)` creates `MultiServerMCPClient` with bearer header, loads tools, invokes graph with `thread_id=f"{customer_id}:{session_id}"`, returns `{answer, tools_used}` extracted from tool-call messages. LLM = `ChatOpenAI(model=OPENAI_MODEL, temperature=0)` using env key; fail fast with clear error if key missing.
- **Files/areas:** new `agent/`.
- **Depends on:** T4
- **Covers:** AC-9, AC-11, AC-12
- **Done when:** with a fake chat model that emits a tool call then a final answer, `run_chat` returns the answer and `tools_used` lists the tool; a second call on the same session retains history.

### T7: Add `/api/chat` endpoint and agent tests
- **Goal:** Make the agent available to the UI.
- **Details:** `POST /api/chat {message (1–2000 chars), session_id}` -> `{answer, tools_used}`, requires bearer auth, passes the same token to `run_chat`. Map failures (OpenAI error, MCP unreachable) to HTTP 502 `{error:"ASSISTANT_UNAVAILABLE"}`. Add tests with mocked LLM covering success, session continuity, refusal prompt content, and error mapping.
- **Files/areas:** `backend/app/routes/chat.py`, `agent/tests/`.
- **Depends on:** T3, T6
- **Covers:** AC-10 (API side), AC-12, AC-14
- **Done when:** `pytest agent backend` passes; unauthenticated chat call returns 401.

### T8: Scaffold React app with theme, routing and login
- **Goal:** Working login and authenticated shell.
- **Details:** Vite + React 18 + TS + Tailwind. ICICI-inspired original theme (orange `#F58220`-like accent, deep maroon `#7A1F1F`-like, neutral grays), Inter font. Router: `/login`, and protected layout with tabs Dashboard, Transactions, Cards, Offers, Chatbot. API client with bearer token, 401 -> logout. Login page per 7.7 including collapsible demo credentials list.
- **Files/areas:** `frontend/`.
- **Depends on:** T3
- **Covers:** AC-2, AC-3
- **Done when:** all 5 demo users can log in; wrong password shows an error; visiting `/` logged-out redirects to `/login`.

### T9: Build Dashboard, Transactions, Cards and Offers tabs
- **Goal:** Minimal but polished read-only banking views.
- **Details:** Dashboard (balance, credit utilization bar, recent transactions, category chart), Transactions (toggle Account/Credit card, filters, table with INR formatting, loading/empty/error states), Cards (visual card tiles with masked numbers, limits, due date), Offers (cards grid, category filter). Responsive.
- **Files/areas:** `frontend/src/pages/*`, `components/*`.
- **Depends on:** T8
- **Covers:** AC-3
- **Done when:** each tab renders real seeded data for the logged-in user and handles empty/error states.

### T10: Build the Chatbot tab
- **Goal:** Natural-language chat UI wired to `/api/chat`.
- **Details:** Per 7.7: bubbles, markdown (react-markdown + GFM tables), typing indicator while waiting, disabled input while sending, starter chips, "Used tools" chips from `tools_used`, `session_id` (uuid) kept per tab with "New chat" resetting it, friendly error bubble on 502, auto-scroll, Enter to send / Shift+Enter newline.
- **Files/areas:** `frontend/src/pages/Chatbot.tsx`, `components/chat/*`.
- **Depends on:** T7, T8
- **Covers:** AC-10, AC-11
- **Done when:** asking "Show my last 5 UPI payments" displays an answer plus a `get_banking_transactions` chip; a follow-up question keeps context.

### T11: Add frontend tests
- **Goal:** Guard the main UI flows.
- **Details:** Vitest + React Testing Library: login success/failure, protected-route redirect, chat send flow with mocked API (typing indicator, answer, tool chips, error state).
- **Files/areas:** `frontend/src/**/*.test.tsx`.
- **Depends on:** T10
- **Covers:** AC-2, AC-10, AC-14
- **Done when:** `npm test` passes.

### T12: Add run scripts and README
- **Goal:** One-step setup and clear docs.
- **Details:** Scripts (Makefile or npm/py scripts): `seed`, `run-mcp`, `run-backend`, `run-frontend`, plus `dev` that starts all three. README: prerequisites, env setup (`OPENAI_API_KEY`), start order, demo credentials table, architecture diagram from 7.1, tool list, eval checklist from 7.8, troubleshooting (MCP unreachable, invalid key).
- **Files/areas:** `README.md`, `Makefile`/`package.json`.
- **Depends on:** T10
- **Covers:** AC-13
- **Done when:** following only the README on a clean checkout gets the app running and a chat answer returned.

### T13: Run manual eval checklist and fix prompt/tool-description issues
- **Goal:** Validate real-LLM behavior.
- **Details:** Run the 7.8 questions as at least two users; fix tool descriptions or system prompt if wrong tool is chosen, amounts are mis-formatted, or refusals fail. Record results in `docs/eval-results.md`. Do not add new tools.
- **Files/areas:** `agent/prompts.py`, `mcp_server/server.py` (descriptions only), `docs/`.
- **Depends on:** T12
- **Covers:** AC-9, AC-12, AC-14
- **Done when:** all rows in 7.8 pass and results are recorded.

## 9. Traceability
| AC | Covered by tasks |
|----|------------------|
| AC-1 | T2 |
| AC-2 | T3, T8, T11 |
| AC-3 | T8, T9 |
| AC-4 | T4 |
| AC-5 | T4, T5 |
| AC-6 | T4, T5 |
| AC-7 | T4, T5 |
| AC-8 | T4, T5 |
| AC-9 | T6, T13 |
| AC-10 | T7, T10, T11 |
| AC-11 | T6, T10 |
| AC-12 | T6, T7, T13 |
| AC-13 | T1, T12 |
| AC-14 | T5, T7, T11, T13 |

## 10. Definition of Done
- All tasks complete and all AC verified.
- `pytest` (backend, mcp_server, agent) and `npm test` pass.
- No write tools exist in the MCP server; DB opened read-only there.
- No secrets committed; `.env.example` is complete; OpenAI key never reaches the browser.
- No ICICI logos/trademarked assets used.
- README lets a new developer run the demo end to end.
