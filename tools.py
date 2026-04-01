# tools.py

# HomeFirst Loan Parameters (from HomeFirst website)
MIN_INCOME_SALARIED = 15000
MIN_INCOME_SELF_EMPLOYED = 20000
MAX_LOAN_AMOUNT = 7500000      # 75 Lakhs
FOIR_LIMIT = 0.50              # 50%
LTV_HIGH = 0.90                # 90% for loans < 30L
LTV_LOW = 0.80                 # 80% for loans >= 30L
LTV_THRESHOLD = 3000000        # 30 Lakhs
DEFAULT_RATE = 11.0            # 11% per annum
DEFAULT_TENURE = 20            # 20 years


def calculate_emi(principal: float, annual_rate: float = DEFAULT_RATE, tenure_years: int = DEFAULT_TENURE) -> dict:
    """
    Calculate monthly EMI using standard formula.
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    """
    monthly_rate = annual_rate / (12 * 100)
    n = tenure_years * 12

    if monthly_rate == 0:
        emi = principal / n
    else:
        emi = principal * monthly_rate * (1 + monthly_rate)**n / ((1 + monthly_rate)**n - 1)

    return {
        "principal": round(principal, 2),
        "annual_rate": annual_rate,
        "tenure_years": tenure_years,
        "monthly_emi": round(emi, 2),
        "total_payable": round(emi * n, 2),
        "total_interest": round((emi * n) - principal, 2)
    }


def _back_calculate_principal(max_emi: float, annual_rate: float, tenure_years: int) -> float:
    """Reverse EMI formula — find max loan given max affordable EMI."""
    r = annual_rate / (12 * 100)
    n = tenure_years * 12
    if r == 0:
        return max_emi * n
    return max_emi * ((1 + r)**n - 1) / (r * (1 + r)**n)


def check_loan_eligibility(
    monthly_income: float,
    loan_amount_requested: float,
    property_value: float,
    employment_status: str,
    existing_emi: float = 0,
    tenure_years: int = DEFAULT_TENURE,
    annual_rate: float = DEFAULT_RATE
) -> dict:
    """
    Check home loan eligibility using HomeFirst rules:
    - Minimum income check
    - LTV (Loan to Value) cap
    - FOIR (Fixed Obligation to Income Ratio) limit
    - Maximum loan cap
    """
    reasons = []
    eligible = True

    # 1. Minimum income check
    min_income = MIN_INCOME_SALARIED if employment_status.lower() == "salaried" else MIN_INCOME_SELF_EMPLOYED
    if monthly_income < min_income:
        eligible = False
        reasons.append(f"Income ₹{monthly_income:,.0f} is below minimum ₹{min_income:,} for {employment_status}")

    # 2. LTV check
    ltv_limit = LTV_HIGH if property_value <= LTV_THRESHOLD else LTV_LOW
    max_by_ltv = property_value * ltv_limit
    if loan_amount_requested > max_by_ltv:
        eligible = False
        reasons.append(f"Loan exceeds LTV cap. Max allowed: ₹{max_by_ltv:,.0f} ({int(ltv_limit*100)}% of property value)")

    # 3. FOIR check
    emi_result = calculate_emi(loan_amount_requested, annual_rate, tenure_years)
    new_emi = emi_result["monthly_emi"]
    total_obligations = existing_emi + new_emi
    foir = total_obligations / monthly_income

    if foir > FOIR_LIMIT:
        eligible = False
        max_emi_allowed = (monthly_income * FOIR_LIMIT) - existing_emi
        reasons.append(f"FOIR {foir:.0%} exceeds 50% limit. Max EMI you can afford: ₹{max_emi_allowed:,.0f}/month")

    # 4. Max loan cap
    if loan_amount_requested > MAX_LOAN_AMOUNT:
        eligible = False
        reasons.append(f"Requested amount exceeds HomeFirst maximum of ₹75 Lakhs")

    # Calculate max eligible loan
    max_emi_allowed = (monthly_income * FOIR_LIMIT) - existing_emi
    max_loan_by_foir = _back_calculate_principal(max_emi_allowed, annual_rate, tenure_years)
    max_eligible_loan = round(min(max_loan_by_foir, max_by_ltv, MAX_LOAN_AMOUNT), 2)

    return {
        "eligible": eligible,
        "status": "APPROVED" if eligible else "REJECTED",
        "loan_requested": loan_amount_requested,
        "max_eligible_loan": max_eligible_loan,
        "calculated_emi": new_emi,
        "foir_ratio": round(foir, 3),
        "ltv_ratio": round(loan_amount_requested / property_value, 3),
        "reasons": reasons if not eligible else ["All eligibility checks passed ✅"]
    }