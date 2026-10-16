import os
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Configure these as environment variables in Render.
# OPENAI_API_KEY is required.
# OPENAI_MODEL defaults to "gpt-6-luna"; change it if your provider uses another model ID.
MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You are a real-estate search assistant for Agra, Uttar Pradesh, India.
Interpret the user's property-search request clearly and accurately.
Do not invent property listings, prices, addresses, availability, or URLs.
If no live property-search tool or listing database is connected, explain that
you can interpret the request but cannot verify current listings.
Return a concise answer and, where useful, a JSON-like summary of:
- property_type
- transaction_type (rent or sale)
- maximum_monthly_rent_inr
- location
- user_query
Use Indian rupee amounts and Indian location conventions.
"""


@app.get("/")
def health_check():
    return jsonify({
        "service": "Real Agra Service",
        "status": "ok",
        "message": "Send a POST request with JSON: {\"query\": \"your property search\"}",
        "model": MODEL,
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/")
@app.post("/search")
def search():
    data = request.get_json(silent=True) or {}
    query = data.get("query") or request.args.get("query")

    if not isinstance(query, str) or not query.strip():
        return jsonify({
            "error": "Missing query",
            "example": {
                "query": "Shop for rent under Rs. 20000 Shastripuram to Kargil road, Agra, Uttar Pradesh, India"
            },
        }), 400

    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({
            "error": "Server is not configured",
            "detail": "Set the OPENAI_API_KEY environment variable in Render."
        }), 500

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=SYSTEM_PROMPT,
            input=query.strip(),
        )
        answer = response.output_text

        return jsonify({
            "query": query.strip(),
            "model": MODEL,
            "answer": answer,
            "note": "This endpoint uses the AI model to interpret the search. Live listings require a connected property database or search API."
        })
    except Exception as exc:
        # Return a useful error without exposing credentials or internal details.
        app.logger.exception("AI request failed")
        return jsonify({
            "error": "AI request failed",
            "detail": str(exc),
            "model": MODEL,
        }), 502


if __name__ == "__main__":
    # Local development only. Render should use the Gunicorn start command.
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
