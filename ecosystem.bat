@echo off
echo ===================================================================
echo HS AI SOLUTIONS — UNIVERSAL DUAL-MODEL ECOSYSTEM
echo Founder: Harshan Seliyan ^| Product: JULY LLM ^& GRAVITY LLM
echo Starting Universal Server on http://localhost:8000 ...
echo ===================================================================
python -m uvicorn hs_ecosystem.server.app:app --host 0.0.0.0 --port 8000
