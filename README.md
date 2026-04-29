# 🍔 OfferRadar — AI-Powered Swiggy Deal Finder

> Chat with an AI agent that finds the best Swiggy food offers, ranks them by actual savings, and auto-applies the top coupon. Works with any MCP-compatible LLM — Claude, GPT-4o, Gemini, Llama, or local models via Ollama.

---

## What it does

Most people miss out on Swiggy coupons because finding and comparing them across restaurants is tedious. OfferRadar automates the whole thing:

1. You say what you're craving (e.g. *"I want biryani"*)
2. The agent searches nearby restaurants
3. Fetches available coupons **in parallel** across all results
4. Ranks them by actual ₹ savings for your order
5. Builds your cart and auto-applies the best coupon
6. Shows you exactly how much you saved

---

## Supported LLMs

OfferRadar uses **LiteLLM** as a universal LLM gateway. Switch models with one env var — no code changes:

| Provider | Example Model | Needs API Key |
|---|---|---|
| Anthropic | `claude-opus-4-5` | Yes |
| OpenAI | `gpt-4o` | Yes |
| Google | `gemini/gemini-1.5-pro` | Yes |
| Mistral | `mistral/mistral-large` | Yes |
| Groq | `groq/llama-3-70b` | Yes (free tier) |
| Ollama (local) | `ollama/llama3` | No |
| Any OpenAI-compatible API | custom base URL | Optional |

---

## Demo

```
You: I want to order biryani, find me the best deal

Agent: Searching restaurants near you...
       Found 8 places serving biryani. Fetching offers...

       🏆 Best Deal: Behrouz Biryani
          Coupon: FLAT60  →  Save ₹120 on ₹299+ order

       Runner-up: Paradise Biryani
          Coupon: SAVE30  →  Save ₹90 on ₹349+ order

       Add Behrouz to cart and apply FLAT60? (yes/no): yes
       ✅ Coupon applied. Final total: ₹179 + delivery
```

---

## Architecture

```
User (CLI)
    │
    ▼
LLM Agent (agent.py)
    │
    ├── LiteLLM Gateway (llm_client.py)
    │       ├── Anthropic Claude
    │       ├── OpenAI GPT-4o
    │       ├── Google Gemini
    │       ├── Groq / Llama 3
    │       └── Ollama (local)
    │
    └── Swiggy MCP Tools (swiggy_mcp.py)
            ├── search_restaurants()
            ├── fetch_food_coupons()   ← parallelized with asyncio.gather
            ├── update_food_cart()
            ├── apply_food_coupon()
            └── place_food_order()
                 │
                 ▼
         mcp.swiggy.com/food
```

Tool definitions are written once in `tools.py` using OpenAI-style JSON schema. LiteLLM translates them to each provider's native format automatically.

---

## Setup

### Install

```bash
git clone https://github.com/yourusername/offerradar
cd offerradar
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

```env
# Swiggy (required)
SWIGGY_MCP_TOKEN=your_swiggy_mcp_token
SWIGGY_ADDRESS_ID=your_address_id

# Pick your LLM
LLM_MODEL=claude-opus-4-5           # Anthropic
# LLM_MODEL=gpt-4o                  # OpenAI
# LLM_MODEL=gemini/gemini-1.5-pro   # Google
# LLM_MODEL=groq/llama-3-70b        # Groq
# LLM_MODEL=ollama/llama3           # Local — no API key needed

# API key for your provider (skip for Ollama)
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GROQ_API_KEY=...
```

### Run

```bash
python main.py
```

### Run fully local (free)

```bash
# Install Ollama: https://ollama.com
ollama pull llama3
LLM_MODEL=ollama/llama3 python main.py
```

---

## Project Structure

```
offerradar/
├── main.py              # CLI entry point
├── agent.py             # LLM agent + tool orchestration
├── llm_client.py        # LiteLLM wrapper (swappable LLM layer)
├── swiggy_mcp.py        # Swiggy MCP client
├── tools.py             # Tool definitions (JSON schema for LLM)
├── coupon_ranker.py     # Savings ranking logic
├── config.py            # Env config
├── requirements.txt
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Roadmap

- [ ] Instamart grocery deal finder
- [ ] Dineout table booking
- [ ] Streamlit web UI
- [ ] WhatsApp bot interface
- [ ] Streaming responses

---

## License

MIT
