from flask import Flask, request, jsonify
from openai import OpenAI
import os

app = Flask(__name__)

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


@app.route("/")
def home():
    return jsonify({
        "service": "AI Property Description API",
        "status": "ok"
    })


@app.route("/generate-description", methods=["POST"])
def generate_description():

    data = request.get_json()

    if not data:
        return jsonify({
            "error": "JSON data is required"
        }), 400

    prompt = f"""
Create a professional real-estate property description.

Property information:

Title: {data.get("title", "")}
Location: {data.get("location", "")}
Price: {data.get("price", "")}
Bedrooms: {data.get("bedrooms", "")}
Bathrooms: {data.get("bathrooms", "")}
Area: {data.get("area", "")}
Features: {data.get("features", "")}

Requirements:
- Write 150-200 words.
- Use professional real-estate language.
- Keep the information factual.
- Do not invent features.
- Make it suitable for a real-estate portal.
"""

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        return jsonify({
            "success": True,
            "description": response.output_text
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500