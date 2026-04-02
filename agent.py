# agent.py

import json
import re
import streamlit as st
import google.generativeai as genai

from tools import calculate_emi, check_loan_eligibility

# ── Configure Gemini API ─────────────────────────────────
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY"))

# ── Supported Languages ──────────────────────────────────
SUPPORTED_LANGUAGES = ["english", "hindi", "marathi", "tamil"]

# ── Language Detection ───────────────────────────────────
def detect_language(text: str) -> str:
    hindi_words = ["hai", "mera", "meri", "kya", "nahi", "aur", "main",
                   "hoon", "rupaye", "chahiye", "mujhe", "loan", "ghar"]

    marathi_indicators = ["आहे", "माझे", "काय", "नाही", "आणि", "मला"]
    tamil_indicators = ["என்", "இல்லை", "வேண்டும்", "ஆகும்"]

    text_lower = text.lower()

    has_devanagari = any('\u0900' <= c <= '\u097F' for c in text)
    has_tamil = any(c in text for c in tamil_indicators)
    has_marathi = any(c in text for c in marathi_indicators)
    hindi_score = sum(1 for w in hindi_words if w in text_lower.split())

    if has_tamil:
        return "tamil"
    if has_marathi:
        return "marathi"
    if has_devanagari or hindi_score >= 2:
        return "hindi"

    return "english"

# ── Entity Extraction ────────────────────────────────────
def extract_entities(text: str, current_data: dict) -> dict:
    updated = current_data.copy()
    text_lower = text.lower()

    # Amount parsing
    lakh_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|L)\b', text, re.IGNORECASE)
    k_matches = re.findall(r'(\d+(?:\.\d+)?)\s*k\b', text, re.IGNORECASE)
    plain_matches = re.findall(r'₹?\s*(\d{5,})', text)

    amounts = []
    for m in lakh_matches:
        amounts.append(float(m) * 100000)
    for m in k_matches:
        amounts.append(float(m) * 1000)
    for m in plain_matches:
        amounts.append(float(m))

    # Assign guessed values
    if amounts:
        if "monthly_income" not in updated:
            updated["monthly_income"] = amounts[0]
        elif "loan_amount_requested" not in updated:
            updated["loan_amount_requested"] = amounts[0]
        elif "property_value" not in updated:
            updated["property_value"] = amounts[0]

    # Employment detection
    if any(w in text_lower for w in ["salaried", "job", "salary", "naukri"]):
        updated["employment_status"] = "salaried"
    elif any(w in text_lower for w in ["business", "self", "freelance", "own"]):
        updated["employment_status"] = "self_employed"

    return updated

# ── Prompt Builder ───────────────────────────────────────
def build_prompt(user_message: str, extracted_data: dict, language: str) -> str:

    return f"""
You are a smart and friendly Home Loan Counselor.

User message:
{user_message}

Current collected data:
{json.dumps(extracted_data, indent=2)}

Your job:
- Ask for missing information:
  1. monthly_income
  2. property_value
  3. loan_amount_requested
  4. employment_status
- Ask ONE question at a time
- Be conversational and natural
- If all data is available → respond with eligibility summary
- Do NOT hallucinate numbers

Language: {language}
"""

# ── MAIN AGENT CLASS ─────────────────────────────────────
class LoanAgent:

    def __init__(self):
        self.conversation_history = []
        self.locked_language = None
        self.extracted_data = {}
        self.handoff_triggered = False

    def _get_model(self):
        return genai.GenerativeModel(
            model_name="gemini-2.5-flash"
        )

    def chat(self, user_message: str) -> dict:

        # Lock language early
        if not self.locked_language:
            self.locked_language = detect_language(user_message)

        # Extract entities
        self.extracted_data = extract_entities(user_message, self.extracted_data)

        # Build prompt
        prompt = build_prompt(user_message, self.extracted_data, self.locked_language)

        # Call model
        model = self._get_model()
        response = model.generate_content(prompt)

        final_text = response.text if response else "Sorry, I couldn't process that."

        # Optional: basic eligibility trigger
        required_fields = ["monthly_income", "loan_amount_requested", "property_value", "employment_status"]

        if all(field in self.extracted_data for field in required_fields):
            eligibility = check_loan_eligibility(**self.extracted_data)
            final_text += f"\n\n📊 Eligibility Result:\n{json.dumps(eligibility, indent=2)}"

        return {
            "response": final_text,
            "locked_language": self.locked_language,
            "extracted_data": self.extracted_data,
            "handoff_triggered": self.handoff_triggered
        }