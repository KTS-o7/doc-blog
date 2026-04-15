+++
title = "Building a Local AI Stack: Hermes, Bifrost, Telegram, and Camoufox"
date = 2026-04-15T00:00:00+05:30
draft = false
math = false
+++

I wanted a persistent AI agent that lives on my machine, reaches cloud models through a single gateway, and talks back to me on Telegram. Not a SaaS. Not a wrapper. Something I own end-to-end.

This is the story of setting that up in one session, and the parts that went sideways.

## The Stack

Four moving parts:

- **Bifrost** -- LLM gateway already running on localhost:24242, routing to Ollama cloud models
- **Hermes Agent** -- open-source AI agent framework by Nous Research, pointed at Bifrost
- **Ollama** -- cloud relay for gemma4 and qwen3.5 cloud models via ollama.com
- **Camoufox** -- Firefox fork with TLS fingerprint spoofing for scraping tasks

The goal was to have Hermes run as a Telegram bot so I could assign it tasks from my phone, with all model traffic flowing through Bifrost so routing stays centralized.

## Bifrost First

Bifrost was already up on port 24242 with Ollama configured. The only addition needed was an `ollama-cloud` provider pointing at `https://ollama.com` rather than localhost. This is a non-obvious distinction.

The trap: Ollama's OpenAI-compatible endpoint (`/v1/chat/completions`) does not work for cloud models. It hangs. Cloud models only work through Ollama's native `/api/chat` endpoint. Pointing Bifrost directly at `https://ollama.com` instead of `localhost:11434` bypasses the broken compat layer and hits the right path.

Once the provider was registered and `OLLAMA_API_KEY` was set in `.zshrc`, both cloud models confirmed working:

```bash
ollama pull gemma4:31b-cloud
ollama pull qwen3.5:cloud
```

## Installing Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

That puts everything under `~/.hermes/`. The setup wizard runs next:

```bash
hermes setup
```

It walks through provider selection interactively. I pointed it at the Bifrost custom endpoint (`http://localhost:24242/v1`) and picked `ollama-cloud/gemma4:31b-cloud` as the default model.

Key config paths:

```
~/.hermes/config.yaml    -- main settings
~/.hermes/.env           -- secrets and API keys
~/.hermes/skills/        -- reusable agent procedures
~/.hermes/sessions/      -- full conversation history (searchable)
```

After setup, a quick smoke test confirmed the agent was up and routing through Bifrost correctly:

```bash
hermes chat -q "what model are you using and where does traffic go"
```

## Context Window

The default context length was under 20k tokens. Ollama cloud models support much larger windows. One config set:

```bash
hermes config set model.context_length 200000
```

Takes effect on the next session restart.

## Telegram Bot

This is where Hermes gets genuinely useful. The gateway turns it into a bot that accepts tasks from any platform you connect.

Create a bot via BotFather, get the token, then add it to `~/.hermes/.env`:

```bash
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_ALLOWED_USERS=<your-numeric-telegram-id>
```

`TELEGRAM_ALLOWED_USERS` takes the numeric user ID, not the username. Lock it down. Anyone who finds the bot URL can send it commands if this is not set.

Start the gateway:

```bash
hermes gateway run
```

For persistent background operation, install it as a service:

```bash
hermes gateway install
hermes gateway start
```

A set of aliases in `.zshrc` makes it easier to manage day to day:

```bash
alias hermes-gateway-start="hermes gateway start"
alias hermes-gateway-stop="hermes gateway stop"
alias hermes-gateway-log="tail -f ~/.hermes/logs/gateway.log"
```

First run hit a missing Python dependency and failed silently. The fix was running `hermes gateway run` in the foreground once to see the real error, installing the missing package, then moving back to the service.

## Camoufox

Camoufox is a Firefox fork built for scraping. It spoofs TLS fingerprints so sites see a legitimate browser rather than a Playwright or CDP signature. It exposes a CDP endpoint that Hermes's browser tool connects to.

```bash
git clone https://github.com/daijro/camoufox
cd camoufox && npm install
python -m camoufox fetch   # ~300MB download
```

The `camoufox fetch` step downloads the actual browser binary and does not run automatically via postinstall. If you skip it, the first start fails silently. Run it manually and wait for the download to finish before starting the server.

Start it on port 9377:

```bash
python -m camoufox server --port 9377 &
```

Smoke test via Hermes:

```bash
hermes chat -q "use the browser to fetch the title of example.com"
```

Aliases for day-to-day:

```bash
alias camofox-start="python -m camoufox server --port 9377 &"
alias camofox-stop="pkill -f 'camoufox server'"
```

## What Actually Went Wrong

**Ollama native vs compat endpoint.** Already covered above, but it cost a couple of hours. If a cloud model hangs at the provider level, check whether your gateway is talking to the right API path.

**Camoufox silent failure.** The binary fetch is not in postinstall. No error, just no browser. Always run `python -m camoufox fetch` explicitly before the first start.

**Hermes gateway dependency.** First start printed nothing useful. Run in foreground before daemonizing so you can see the actual error.

**Bifrost and empty API keys.** Ollama initially rejected non-empty dummy keys in the Authorization header. Setting the key to an empty string before switching to the real `OLLAMA_API_KEY` got things unstuck. The order mattered.

**Session corruption in OpenCode.** An OpenCode session used to orchestrate this setup got a zombie assistant message from an interrupted stream. The message had an empty string for content. Bifrost converted that empty string to null before forwarding, and the upstream provider rejected the entire next request with `messages.315.member.content must not be null`. Every retry included the same zombie in history, so the error was permanent until manually fixed.

The fix is to delete the zombie row directly from the OpenCode SQLite database:

```bash
sqlite3 ~/.local/share/opencode/opencode.db \
  "DELETE FROM message WHERE id = '<zombie-message-id>' AND session_id = '<session-id>';"
```

There is no built-in repair command. Back up the database before editing it.

## Final State

Services running when done:

```
bifrost    :24242  -- Ollama cloud routes
ollama     :11434  -- cloud relay (gemma4, qwen3.5)
camoufox   :9377   -- CDP browser endpoint
hermes     gateway -- Telegram bot (restricted to single user)
```

The agent receives messages on Telegram, runs tool calls locally (terminal, browser, file ops, web search), and routes all model traffic through Bifrost.

## What's Left

The original plan included running a local Qwen3.5-27B model via llama.cpp with Metal acceleration. That is a 13.5GB download and a build-from-source step, so it was deferred to the next session. The cloud routing setup works fine in the meantime.

## References

- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Hermes docs: https://hermes-agent.nousresearch.com/docs/
- Bifrost: https://github.com/maximhq/bifrost
- Camoufox: https://github.com/daijro/camoufox
- OpenCode: https://opencode.ai
