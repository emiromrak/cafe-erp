# GitHub Copilot & Codex Instructions for CafeERP

## Project Context
CafeERP is an AI-powered café operations and decision support system tailored for the Turkish café industry. It bridges third-wave specialty coffee shops with traditional Turkish café operations (tea glasses, toasts, board game tables).

## Tech Stack
- **Backend:** FastAPI, Python 3.12, Pydantic, Uvicorn
- **AI / ML:** LightGBM, Pandas, Scikit-learn, Open-Meteo REST API, Deterministic NLU Engine
- **Database:** SQLite (`data/sample_cafe.db`) for MVP; PostgreSQL schema designed in `docs/ARCHITECTURE.md`
- **Mobile Bot:** Telegram Bot API (`telegram_bot.py`)
- **Next Frontend:** Next.js (Phase 2 Roadmap)

## Essential Rules for Code Generation
1. Never hardcode absolute file paths. Always use `Path(__file__).resolve().parent...`.
2. Do not use probabilistic LLM logic for financial, ciro, or inventory burn-rate calculations. Use deterministic SQLite queries and mathematical Python functions in `decision_engine.py` and `predictor.py`.
3. Always ensure SQLite database connections are properly closed (`conn.close()`).
4. Read secrets from `.env` via `python-dotenv`. Never hardcode secrets.
5. Refer to `CODEX.md` for full database schemas, API specs, and roadmap details.
