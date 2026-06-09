#!/usr/bin/env python3
"""Web backend for the survey dashboard.

Serves the built dashboard (dashboard/dist) and exposes:

    GET  /                 -> the dashboard SPA
    GET  /responses.csv    -> the latest generated CSV
    POST /api/generate     -> regenerate responses.csv / responses.json

The "Generate" button in the dashboard hits POST /api/generate, which reruns
the same generation logic generate.py uses and rewrites the files in place.

Run locally:
    python server.py            # builds nothing — make sure dashboard/dist exists
                                # (cd dashboard && npm run build) and survey.json is present

Deploy (any host that runs Python):
    pip install -r requirements.txt
    cd dashboard && npm install && npm run build && cd ..
    gunicorn server:app         # or: python server.py
"""

from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_from_directory

from surveygen import load_survey, ResponseGenerator
# Reuse the exact CSV/JSON writers the CLI uses so output stays identical.
from generate import write_csv, write_json, _load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dashboard", "dist")
SURVEY_PATH = os.path.join(HERE, "survey.json")
CSV_PATH = os.path.join(HERE, "responses.csv")
JSON_PATH = os.path.join(HERE, "responses.json")

app = Flask(__name__, static_folder=DIST, static_url_path="")


@app.post("/api/generate")
def api_generate():
    """Regenerate the response files and report how many rows were written."""
    payload = request.get_json(silent=True) or {}
    try:
        n = int(payload.get("n", 200))
    except (TypeError, ValueError):
        n = 200
    n = max(1, min(n, 5000))  # keep it sane

    seed = payload.get("seed")
    try:
        seed = int(seed) if seed is not None else None
    except (TypeError, ValueError):
        seed = None

    _load_dotenv()
    survey = load_survey(SURVEY_PATH)
    gen = ResponseGenerator(survey, seed=seed)
    responses = gen.generate(n)

    # Optional LLM open-text rewrite, same trigger as the CLI.
    if os.environ.get("ENABLE_LLM_TEXT", "").strip().lower() == "true":
        try:
            from surveygen.llm import augment_open_text, LLMUnavailable, DEFAULT_MODELS

            provider = os.environ.get("LLM_PROVIDER", "gemini")
            model = DEFAULT_MODELS.get(provider)
            responses = augment_open_text(survey, responses, provider=provider, model=model)
        except Exception:  # noqa: BLE001 — never let LLM issues fail the endpoint
            pass

    write_csv(CSV_PATH, survey, responses)
    write_json(JSON_PATH, survey, responses)
    return jsonify({"ok": True, "n": len(responses), "survey": survey.title})


@app.get("/responses.csv")
def responses_csv():
    if not os.path.exists(CSV_PATH):
        return "responses.csv not found — click Generate or run generate.py", 404
    resp = send_from_directory(HERE, "responses.csv", mimetype="text/csv")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/")
def index():
    if not os.path.exists(os.path.join(DIST, "index.html")):
        return (
            "Dashboard not built yet. Run: cd dashboard && npm install && npm run build",
            500,
        )
    return send_from_directory(DIST, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
