# test_tools.py
from tools import calculate_emi, check_loan_eligibility

# Test 1: EMI calculation
emi = calculate_emi(principal=1500000, annual_rate=11.0, tenure_years=20)
print("EMI Test:", emi)

# Test 2: Eligible case
result = check_loan_eligibility(
    monthly_income=50000,
    loan_amount_requested=1500000,
    property_value=2000000,
    employment_status="salaried"
)
print("\nEligible Case:", result)

# Test 3: Rejected case (low income)
result2 = check_loan_eligibility(
    monthly_income=10000,
    loan_amount_requested=1500000,
    property_value=2000000,
    employment_status="salaried"
)
print("\nRejected Case:", result2)