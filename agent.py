# agent.py

import json
import re
import streamlit as st
from google import genai

# ── Configure Gemini ─────────────────────────────────────
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ── Language Detection ───────────────────────────────────
def detect_language(text: str) -> str:
    if any('\u0900' <= c <= '\u097F' for c in text):
        return "hindi"
    return "english"

# ── Entity Extraction ────────────────────────────────────
def extract_entities(text: str, current_data: dict) -> dict:
    updated = current_data.copy()
    text_lower = text.lower()

    numbers = re.findall(r'\d+', text)
    if numbers:
        num = int(numbers[0])
        if "monthly_income" not in updated:
            updated["monthly_income"] = num
        elif "loan_amount_requested" not in updated:
            updated["loan_amount_requested"] = num
        elif "property_value" not in updated:
            updated["property_value"] = num

    if "salary" in text_lower or "job" in text_lower:
        updated["employment_status"] = "salaried"
    elif "business" in text_lower:
        updated["employment_status"] = "self_employed"

    return updated

# ── Prompt Builder ───────────────────────────────────────
def build_prompt(user_message, extracted_data):
    return f"""
You are a Home Loan Counselor.

User: {user_message}

Collected Data:
{json.dumps(extracted_data, indent=2)}

Ask for missing:
- monthly_income
- property_value
- loan_amount_requested
- employment_status

Ask ONE question only.
"""

# ── Agent Class ──────────────────────────────────────────
class LoanAgent:

    def __init__(self):
        self.locked_language = None
        self.extracted_data = {}

    def chat(self, user_message: str) -> dict:

        if not self.locked_language:
            self.locked_language = detect_language(user_message)

        self.extracted_data = extract_entities(user_message, self.extracted_data)

        prompt = build_prompt(user_message, self.extracted_data)

        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt
            )

            reply = response.text

            return {
                "response": reply,
                "locked_language": self.locked_language,
                "extracted_data": self.extracted_data,
                "handoff_triggered": False
            }

        except Exception as e:
            print("NEW GEMINI ERROR:", e)

            return {
                "response": f"❌ Gemini failed: {str(e)}",
                "locked_language": self.locked_language,
                "extracted_data": self.extracted_data,
                "handoff_triggered": False
            }