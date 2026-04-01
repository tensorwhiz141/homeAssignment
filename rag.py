# rag.py - No ChromaDB embedding issues, pure Python similarity search

import math

# ---- Mock HomeFirst FAQ Documents ----
FAQ_DOCUMENTS = [
    {
        "id": "faq_001",
        "text": "For salaried employees, required documents are: latest 3 months salary slips, 6 months bank statements, Form 16, PAN card, Aadhaar card, and property documents."
    },
    {
        "id": "faq_002",
        "text": "For self-employed individuals, required documents are: ITR for last 2 years, business proof or registration, 12 months bank statements, PAN card, Aadhaar card, and property documents."
    },
    {
        "id": "faq_003",
        "text": "HomeFirst Finance offers home loans ranging from Rs 2 Lakhs to Rs 75 Lakhs with interest rates starting at 11% per annum for eligible borrowers."
    },
    {
        "id": "faq_004",
        "text": "Loan tenure at HomeFirst can range from 5 years to 30 years. A longer tenure reduces your monthly EMI but increases the total interest paid over the loan period."
    },
    {
        "id": "faq_005",
        "text": "FOIR means Fixed Obligation to Income Ratio. HomeFirst requires FOIR to be below 50 percent. This means your total monthly EMI obligations should not exceed 50 percent of your gross monthly income."
    },
    {
        "id": "faq_006",
        "text": "LTV means Loan to Value ratio. HomeFirst finances up to 90 percent of property value for loans under Rs 30 Lakhs, and up to 80 percent of property value for loan amounts above Rs 30 Lakhs."
    },
    {
        "id": "faq_007",
        "text": "HomeFirst Finance specializes in home loans for the informal sector including daily wage workers, small business owners, street vendors, and self-employed individuals with irregular income."
    },
    {
        "id": "faq_008",
        "text": "There is no prepayment penalty for floating rate home loans at HomeFirst. For fixed rate loans, a foreclosure charge of 2 percent on the outstanding amount may apply."
    },
    {
        "id": "faq_009",
        "text": "Home loan tax benefits in India: Under Section 80C, principal repayment up to Rs 1.5 Lakhs per year is tax deductible. Under Section 24(b), interest paid up to Rs 2 Lakhs per year is deductible."
    },
    {
        "id": "faq_010",
        "text": "Processing fee at HomeFirst is typically 1 to 2 percent of the loan amount plus applicable GST. This fee is non-refundable once the loan application has been processed and reviewed."
    }
]


# ---- Pure Python Vector Search (no ChromaDB needed) ----

def _embed(text: str) -> list:
    """Simple character-hash embedding — 64 dimensions."""
    vec = [0.0] * 64
    for i, ch in enumerate(text.lower()):
        vec[i % 64] += ord(ch) / 1000.0
    magnitude = math.sqrt(sum(x**2 for x in vec)) or 1.0
    return [x / magnitude for x in vec]


def _cosine_similarity(a: list, b: list) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x**2 for x in a)) or 1.0
    mag_b = math.sqrt(sum(x**2 for x in b)) or 1.0
    return dot / (mag_a * mag_b)


# Pre-compute embeddings for all documents at import time
_DOC_EMBEDDINGS = [
    (doc, _embed(doc["text"])) for doc in FAQ_DOCUMENTS
]


def retrieve_context(query: str, n_results: int = 2) -> str:
    """
    Retrieve top-N relevant FAQ chunks using cosine similarity.
    Pure Python — no ChromaDB, no downloads, no timeouts.
    """
    try:
        query_vec = _embed(query)
        scored = [
            (doc["text"], _cosine_similarity(query_vec, emb))
            for doc, emb in _DOC_EMBEDDINGS
        ]
        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)
        top_docs = [text for text, score in scored[:n_results]]
        return "\n\n".join(top_docs)
    except Exception as e:
        print(f"[RAG ERROR] {e}")
        return ""


def is_policy_question(text: str) -> bool:
    """
    Detect if user message is a policy/FAQ question
    that needs RAG retrieval vs a regular data collection turn.
    """
    policy_keywords = [
        "document", "documents", "required", "need",
        "eligible", "eligibility", "criteria",
        "interest", "rate", "tenure", "process",
        "fee", "charge", "tax", "benefit", "section",
        "ltv", "foir", "prepay", "foreclose",
        "kagazat", "kagaz", "jaruri", "chahiye",
        "kitne", "kya chahiye", "kaise",
        "what", "how", "which", "when", "why"
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in policy_keywords)