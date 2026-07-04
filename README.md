<div align="center">

# 📮 Mail Agent

**A self-hosted email assistant that turns your inbox into a job-application board.**

Sync your mail over IMAP · read & translate messages · let Claude extract every
application into a Kanban board — the app runs in your browser, but your emails,
database, and passwords never leave your own computer.

English · [简体中文](./README.zh-CN.md)

🔗 App: <https://mail-agent.vercel.app/> · Source: <https://github.com/54younger/mail_agent>

</div>

---

## Table of contents

- [What it does](#what-it-does)
- [Why your data stays private](#why-your-data-stays-private)
- [Get started in 3 steps](#get-started-in-3-steps)
- [First-run setup in the app](#first-run-setup-in-the-app)
- [Using the app day to day](#using-the-app-day-to-day)
- [Mailbox providers & credentials](#mailbox-providers--credentials)
- [Prefer to run everything on your own machine?](#prefer-to-run-everything-on-your-own-machine)
- [Troubleshooting](#troubleshooting)
- [Configuration reference](#configuration-reference)

---

## What it does

Mail Agent has one purpose: **tracking your job hunt from the emails you already
receive.** It gives you three screens:

| Screen | What you get |
| --- | --- |
| **Job board · 求职看板** | A Kanban/company view of every application. Claude reads your mail and pulls out *company · position · applied date · status*, groups repeat emails per company, and shows a stats dashboard (funnel, status donut, application trend). Statuses only move forward — a status you edit by hand is authoritative and won't be quietly downgraded by a later email. |
| **Inbox · 收件箱** | A paginated mail reader (newest 100 per page). Open any message to read it safely, and **translate** non-English mail into English (or Chinese, Japanese, Korean, French, German, Spanish) with one click. |
| **Settings · 设置** | Connect one or more mailboxes, paste your model API key, pick which model handles each task, tweak the extraction prompt, and choose the translation language. |

## Why your data stays private

Mail Agent is split in two:

- A **website** (the screens above), hosted for you at
  <https://mail-agent.vercel.app/>. It's just the interface — it stores nothing.
- A small **backend** that you run **on your own computer**. It holds your mailbox
  connection, your local database, and your API keys, and does all the syncing and
  extracting.

The website talks **only to the backend on your own machine** (`http://127.0.0.1:8765`).
Your emails and passwords never travel to any shared server — there's nothing to sign up
for and no account to create. Your IMAP auth code and API keys are stored encrypted on
your machine and are never written to the database or shared anywhere.

## Get started in 3 steps

**1 · Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)** (free).
This is what runs the little backend on your computer.

**2 · Start your backend.** Open a terminal and run:

```bash
docker run -d --name mailagent -p 127.0.0.1:8765:8765 \
  -v mailagent-data:/data \
  ghcr.io/54younger/mail-agent:latest
```

That's the whole command — no options to fill in. It downloads the backend, starts it,
and keeps your data in a `mailagent-data` volume that survives restarts and upgrades.

**3 · Open the app: <https://mail-agent.vercel.app/>**

The website automatically connects to the backend on your computer. If you open it before
the backend is ready, it shows a short "start your backend" screen and connects on its own
once the container is up. Then follow [first-run setup](#first-run-setup-in-the-app).

> **Which browsers work?** Use **Chrome, Edge, or Firefox**. Safari is not supported (it
> blocks the secure website from talking to your local backend).

To stop the backend later: `docker stop mailagent`. To start it again:
`docker start mailagent`. To upgrade: `docker pull ghcr.io/54younger/mail-agent:latest`,
then remove and re-run the container (your data in the volume is kept).

## First-run setup in the app

Once the app loads, do these **in order**. Everything happens in the browser — there are
no config files to edit.

**1 · Connect a mailbox** — go to **Settings · 设置 → Bind account**
- Pick your provider (Gmail, Outlook, QQ, 163, 126) or choose **Other** for a custom IMAP
  server.
- Enter your **email address** and an **app-specific auth code** — this is a code you
  generate in your mailbox's security settings, **not** your normal login password (see
  [providers](#mailbox-providers--credentials)).
- The server address and port are filled in for you (secure IMAP, port `993`).
- Saving connects the mailbox and starts the first sync. You can connect more than one.

**2 · Add a model API key** — still in **Settings · 设置**
- Simplest: paste a **Claude API key**, which is used for everything by default.
- Advanced: configure each task separately (next step).

**3 · (Optional) Choose models per task**
The backend uses three independent roles, each with its own model and key:

| Task | Default model | What it does |
| --- | --- | --- |
| `extract` | `claude-sonnet-5` | Reads your mail and extracts job applications |
| `translate` | `claude-haiku-4-5` | Translates email bodies |
| `classify` | `claude-haiku-4-5` | Lightweight classification |

Each task can point at **Claude** or any **OpenAI-compatible** service (DeepSeek, Together,
a local Ollama, …) by setting a custom base URL, model name, and key — and the extraction
prompt is editable if you want to tune it.

**4 · (Optional) Set the translation language**
Default is **English**. You can switch it to Chinese, Japanese, Korean, French, German, or
Spanish.

**5 · Extract** — open **Job board · 求职看板** and click **Extract**. Claude reads your
synced mail and fills in the board. Re-run it whenever new mail arrives; anything you edit
by hand always wins.

> **App language:** the interface is in **English by default** and switches to **中文** from
> the toggle at the bottom of the sidebar — this is separate from the email translation
> language above.

## Using the app day to day

- **Job board · 求职看板** — companies with their current stage, a stats dashboard
  (funnel / status donut / trend), and a drawer per application showing its status timeline.
  Edit a status and it becomes the source of truth.
- **Inbox · 收件箱** — browse newest-first, 100 per page; open a message to read it and hit
  **Translate** for a clean translation into your chosen language.
- **Sync** — the sync bar lets you pull new mail on demand (incremental or full re-sync);
  background sync keeps new mail flowing in automatically.

## Mailbox providers & credentials

163 / QQ / 126 / Gmail / Outlook and most providers require an **app-specific auth code**
(not your login password) **and IMAP turned on** in the mailbox's web settings. Generate the
code in your mail provider's security settings and paste *that* into the connect form. If a
connection fails, the wizard shows guidance for your provider (for example, 163's IMAP
security-verification steps).

## Prefer to run everything on your own machine?

You don't have to use the hosted website — you can run the whole thing (interface + backend)
locally. Clone the repo first:

```bash
git clone https://github.com/54younger/mail_agent.git
cd mail_agent
```

Then pick one:

**Docker Compose (one container, serves everything at `http://127.0.0.1:8765`)**

```bash
docker compose up --build          # then open http://127.0.0.1:8765
```

**One command, no Docker** (builds the interface, then starts the backend that serves it):

```bash
./start.sh                         # then open http://127.0.0.1:8765
```

**Developer mode with hot reload (two terminals):**

```bash
# terminal 1 — backend at http://127.0.0.1:8765
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python run.py

# terminal 2 — interface at http://localhost:5173
cd frontend
pnpm install
pnpm dev
```

Requirements for these local options: Python 3.11+, and (for the non-Docker ones) Node 18+
with `pnpm` or `npm`. In every case the backend binds to `127.0.0.1` only, so it's never
reachable from the internet.

## Troubleshooting

- **The app says "start your backend"** — your Docker container isn't running. Start it
  (`docker start mailagent`) and the page reconnects automatically.
- **`address already in use` on port 8765** — something is already using the port. Stop any
  old backend: `docker stop mailagent`, or on a local run
  `lsof -ti :8765 | xargs kill -9`, then start again.
- **Safari can't connect** — expected; Safari blocks a secure site from reaching your local
  backend. Use Chrome, Edge, or Firefox.
- **Connecting a mailbox fails** — you almost certainly used your login password instead of
  an **app-specific auth code**, or IMAP isn't enabled in your mailbox settings.

## Configuration reference

Almost everything is configured inside the app. These environment variables exist for the
self-host options above:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MAIL_AGENT_HOST` | `127.0.0.1` | Backend bind host (`0.0.0.0` inside Docker) |
| `MAIL_AGENT_PORT` | `8765` | Backend port |
| `MAIL_AGENT_DATA_DIR` | — | Pre-set the data folder (skips the first-run folder prompt) |
| `MAIL_AGENT_CORS_ORIGINS` | `https://mail-agent.vercel.app` (Docker) | Website origin(s) allowed to call your backend |

The interface is Vite + React + TypeScript; the backend is FastAPI + SQLAlchemy + SQLite +
imap-tools + Claude. The earlier Flutter desktop version is archived under
[`legacy/`](legacy/). Roadmap: [`PLAN.md`](PLAN.md).
