import os
import re
import logging
from urllib.parse import urlparse

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

SERPAPI_URL = "https://serpapi.com/search.json"
SEARCH_TIMEOUT_SECONDS = 20

PROPERTY_SITES = [
    "99acres.com",
    "magicbricks.com",
    "housing.com",
    "nobroker.in",
    "olx.in",
]


def build_search_query(user_query: str) -> str:
    """
    Search public web-indexed property pages. This does not scrape websites
    directly; it uses the SerpApi Google Search API and returns source links.
    """
    cleaned = re.sub(r"\s+", " ", user_query).strip()
    # Keep the user's wording, while making the location explicit for search.
    if "agra" not in cleaned.lower():
        cleaned += " Agra Uttar Pradesh India"
    return f'{cleaned} (shop OR commercial shop OR retail space) rent'


def search_public_web(query: str, api_key: str) -> list[dict]:
    params = {
        "engine": "google",
        "q": query,
        "location": "Agra, Uttar Pradesh, India",
        "google_domain": "google.co.in",
        "gl": "in",
        "hl": "en",
        "num": 10,
        "api_key": api_key,
    }
    response = requests.get(SERPAPI_URL, params=params, timeout=SEARCH_TIMEOUT_SECONDS)
    response.raise_for_status()
    payload = response.json()

    if payload.get("error"):
        raise RuntimeError(payload["error"])

    results = []
    for item in payload.get("organic_results", []):
        link = item.get("link")
        if not link:
            continue
        parsed = urlparse(link)
        if parsed.scheme not in ("http", "https"):
            continue

        results.append({
            "title": item.get("title", "Property listing/search result"),
            "url": link,
            "snippet": item.get("snippet", ""),
            "source": parsed.netloc.removeprefix("www."),
            "position": item.get("position"),
        })

    return results


@app.get("/")
def home():
    return jsonify({
        "service": "Real Agra Service",
        "status": "ok",
        "message": "POST a JSON object with a 'query' field to search public property websites.",
        "search_endpoint": "/search",
        "example": {
            "query": "Shop for rent under Rs. 20000 Shastripuram to Kargil road, Agra, Uttar Pradesh, India"
        },
        "required_environment_variable": "SERPAPI_KEY",
    })


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/search", methods=["GET", "POST"])
@app.route("/", methods=["POST"])
def search():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        user_query = data.get("query") or request.form.get("query")
    else:
        user_query = request.args.get("query")

    if not isinstance(user_query, str) or not user_query.strip():
        return jsonify({
            "status": "error",
            "error": "Missing query",
            "example": {
                "query": "Shop for rent under Rs. 20000 Shastripuram to Kargil road, Agra, Uttar Pradesh, India"
            },
        }), 400

    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        return jsonify({
            "status": "error",
            "error": "Search is not configured",
            "detail": "Add SERPAPI_KEY in Render Environment settings. Get a key from https://serpapi.com/.",
        }), 503

    query = build_search_query(user_query)
    try:
        results = search_public_web(query, serpapi_key)
        return jsonify({
            "status": "success",
            "user_query": user_query.strip(),
            "web_search_query": query,
            "location": "Agra, Uttar Pradesh, India",
            "result_count": len(results),
            "results": results,
            "message": (
                "These are public web search results, not verified availability. "
                "Open each source link to confirm rent, exact location, and whether the property is still available."
                if results else
                "No public search results were returned. Try a broader query or search again later."
            ),
        })
    except requests.Timeout:
        app.logger.warning("Property web search timed out")
        return jsonify({
            "status": "error",
            "error": "Property search timed out",
            "detail": "The search provider did not respond in time. Please try again.",
        }), 504
    except requests.RequestException:
        app.logger.exception("Property search provider request failed")
        return jsonify({
            "status": "error",
            "error": "Could not reach the search provider",
            "detail": "Please check the SerpApi account/key and try again.",
        }), 502
    except Exception:
        app.logger.exception("Unexpected property search error")
        return jsonify({
            "status": "error",
            "error": "Property search failed",
            "detail": "Check the Render logs for the server-side error.",
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
