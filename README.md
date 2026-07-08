# KrickBot — AI-Powered Cricket Analytics Chatbot

An AI-powered chatbot that answers cricket questions using a MariaDB database, with a self-updating knowledge base that stays current without model retraining.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
# Edit .env with your MariaDB credentials (see .env.example)

# 3. Run database migration (creates sync_state watermark table)
python -m scripts.create_sync_state

# 4. Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check — returns DB connection status |
| GET | `/sync/status` | Shows watermark state for all tracked tables |

## Architecture

See [Cricket_Chatbot_Solution_Design.md](Cricket_Chatbot_Solution_Design.md) and [cricket_chatbot_technical_spec.md](cricket_chatbot_technical_spec.md) for full details.

## Change History

See [current_state.md](current_state.md) for a detailed log of all changes, decisions, and verification results.
