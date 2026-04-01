# agent.py
import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from tools import calculate_emi, check_loan_eligibility

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ---------- Constants ----------
SUPPORTED_LANGUAGES = ["english", "hindi", "marathi", "tamil"]

# ---------- Tool schemas for Gemini ----------
calculate_emi_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="calculate_emi",
            description="Calculate monthly EMI for a home loan. Call this when you have principal, rate, and tenure.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "principal": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Loan amount in INR"),
                    "annual_rate": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Annual interest rate e.g. 11.0"),
                    "tenure_years": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Loan tenure in years"),
                },
                required=["principal", "annual_rate", "tenure_years"]
            )
        )
    ]
)

check_eligibility_tool = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="check_loan_eligibility",
            description="Check home loan eligibility. Call this once you have monthly_income, loan_amount_requested, property_value, and employment_status.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "monthly_income": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Monthly income in INR"),
                    "loan_amount_requested": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Loan amount in INR"),
                    "property_value": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Property value in INR"),
                    "employment_status": genai.protos.Schema(type=genai.protos.Type.STRING, description="salaried or self_employed"),
                    "existing_emi": genai.protos.Schema(type=genai.protos.Type.NUMBER, description="Existing EMI obligations, default 0"),
                    "tenure_years": genai.protos.Schema(type=genai.protos.Type.INTEGER, description="Loan tenure in years, default 20"),
                },
                required=["monthly_income", "loan_amount_requested", "property_value", "employment_status"]
            )
        )
    ]
)


# ---------- Language detection ----------
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


# ---------- Entity extraction ----------
def extract_entities(text: str, current_data: dict) -> dict:
    updated = current_data.copy()
    text_lower = text.lower()

    # Amount parsing: handles "50k", "15 lakh", "1500000"
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

    # Employment detection
    if any(w in text_lower for w in ["salaried", "job", "salary", "naukri", "service"]):
        updated["employment_status"] = "salaried"
    elif any(w in text_lower for w in ["self", "business", "khud", "apna", "freelance", "own"]):
        updated["employment_status"] = "self_employed"

    return updated


# ---------- System prompt builder ----------
def build_system_prompt(locked_language: str = None, extracted_data: dict = None) -> str:
    lang_instructions = {
        "english": "You MUST respond ONLY in English. Never switch languages.",
        "hindi": "आपको केवल हिंदी में जवाब देना है। कभी भाषा मत बदलो।",
        "marathi": "तुम्ही फक्त मराठीत उत्तर द्यायला हवे. भाषा बदलू नका.",
        "tamil": "நீங்கள் தமிழில் மட்டுமே பதில் அளிக்க வேண்டும்."
    }

    lang_rule = lang_instructions.get(locked_language, 
        "Detect the user's language in first 1-2 messages and lock to it permanently."
    )

    data_str = json.dumps(extracted_data or {}, indent=2)

    return f"""You are a friendly Home Loan Counselor for HomeFirst Finance.

LANGUAGE RULE (CRITICAL - NEVER BREAK): {lang_rule}

YOUR GOAL: Collect these 4 fields conversationally, one question at a time:
1. monthly_income — monthly salary/income in ₹
2. property_value — property price in ₹
3. loan_amount_requested — how much loan they want in ₹
4. employment_status — "salaried" or "self_employed"

CURRENTLY COLLECTED: {data_str}

STRICT RULES:
- NEVER calculate EMI or eligibility yourself. ALWAYS use the tools.
- NEVER mention numbers before calling a tool.
- Once all 4 fields are collected, IMMEDIATELY call check_loan_eligibility.
- Ask only ONE question per response.
- Politely redirect any non-home-loan questions back to home loans.
- Parse Hinglish naturally: "50k salary hai meri" = monthly_income: 50000
- If user is eligible AND says apply/proceed/yes/haan, say exactly: [HANDOFF TRIGGERED: Routing to Human RM]
"""


# ---------- Main Agent Class ----------
class LoanCounselorAgent:
    def __init__(self):
        self.conversation_history = []
        self.locked_language = None
        self.extracted_data = {}
        self.tool_called = False
        self.handoff_triggered = False

    def _get_model(self):
        return genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[calculate_emi_tool, check_eligibility_tool],
            system_instruction=build_system_prompt(self.locked_language, self.extracted_data)
        )

    def _execute_tool(self, tool_name: str, tool_args: dict) -> str:
        self.tool_called = True
        if tool_name == "calculate_emi":
            result = calculate_emi(**tool_args)
        elif tool_name == "check_loan_eligibility":
            result = check_loan_eligibility(**tool_args)
            self.extracted_data.update(tool_args)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        return json.dumps(result)

    def chat(self, user_message: str) -> dict:
        self.tool_called = False

        # Lock language on first 2 turns
        if not self.locked_language and len(self.conversation_history) <= 2:
            self.locked_language = detect_language(user_message)

        # Extract entities from message
        self.extracted_data = extract_entities(user_message, self.extracted_data)

        # Add to history
        self.conversation_history.append({
            "role": "user",
            "parts": [user_message]
        })

        # Start fresh chat with updated system prompt
        model = self._get_model()
        chat = model.start_chat(history=self.conversation_history[:-1])
        response = chat.send_message(user_message)

        final_text = ""

        # Handle tool calls in a loop (model may chain tools)
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fn = part.function_call
                tool_result_str = self._execute_tool(fn.name, dict(fn.args))

                # Return tool result to model
                response = chat.send_message(
                    genai.protos.Content(
                        role="user",
                        parts=[genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn.name,
                                response={"result": tool_result_str}
                            )
                        )]
                    )
                )
            else:
                # Text response — we're done
                final_text = "".join(
                    p.text for p in response.candidates[0].content.parts
                    if hasattr(p, "text")
                )
                break

        # Save assistant response to history
        self.conversation_history.append({
            "role": "model",
            "parts": [final_text]
        })

        # Check handoff
        if "HANDOFF TRIGGERED" in final_text:
            self.handoff_triggered = True

        return {
            "response": final_text,
            "locked_language": self.locked_language,
            "extracted_data": self.extracted_data,
            "tool_called": self.tool_called,
            "handoff_triggered": self.handoff_triggered
        }