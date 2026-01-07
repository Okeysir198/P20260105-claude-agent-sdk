# Business Rules

Configuration and context generation for debt collection.

## Public API

```python
from business_rules import (
    # Configuration
    AUTHORITIES,        # Authority contact info
    SCRIPT_TYPES,       # 12 script configurations
    FEES,               # Debicheck, clearance, recovery fees
    BUSINESS_HOURS,     # Hours, days, buffer
    get_campaign_deadline,

    # Context generation
    build_negotiation_context,
    build_payment_context,
    get_consequences,
    get_benefits,
)
```

## Configuration

### Authorities

| Key | Name | Contact |
|-----|------|---------|
| `cartrack` | Cartrack Accounts Department | 011-250-3000 |
| `viljoen` | Viljoen Attorneys | 010-140-0085 |

### Script Types

| Script | Authority | Discount | Max Payments |
|--------|-----------|----------|--------------|
| `ratio1_*` | Cartrack | None | 2 |
| `ratio2_3_*` | Cartrack | None | 2 |
| `recently_suspended_120` | Cartrack | 50%/40% | 3 |
| `prelegal_120/150` | Viljoen | Tiered | 3 |
| `legal_stage` | Viljoen | 70-75% | 6 |
| `booksale_stage` | Viljoen | 75-80% | 6 |

### Fees

```python
FEES = {
    "DEBICHECK_FEE": 10.0,
    "CREDIT_CLEARANCE_FEE": 1800.0,
    "RECOVERY_FEE": 25000.0,
}
```

### Business Hours

```python
BUSINESS_HOURS = {
    "start": time(7, 0),
    "end": time(18, 0),
    "days": [0, 1, 2, 3, 4, 5],  # Mon-Sat
    "closing_buffer_minutes": 30,
}
```

## Context Generation

```python
from business_rules import build_negotiation_context, build_complete_agent_context

# Generate dynamic context for negotiation agent
context = build_negotiation_context(userdata)
# Returns: {reason_for_call, consequences, benefits, discount, max_payments}

# Generate formatted string for agent instructions
content = build_complete_agent_context(userdata, agent_type="negotiation")
```

### Example 1: Negotiation Agent Context (prelegal_120 script)

```python
build_complete_agent_context(userdata, agent_type="negotiation")
```

**Returns:**
```
# Current Call Context

**Debtor:** John Smith
**Outstanding Amount:** R4,500.00
**Overdue Days:** 125
**Script Type:** prelegal_120

## Reason for Call
Your account has been handed over to Viljoen Attorneys due to non-payment. Your total arrears are R4,500.00. A letter of demand has been sent.

## Consequences of Non-Payment
- Your Cartrack App access will be suspended
- Vehicle positioning through control room will be unavailable
- Vehicle notifications will be suspended
- If your vehicle is stolen or hijacked, you may be charged a recovery fee of up to R25,000.00
- You have been or will be listed as a default payer on your credit profile
- A clearance fee of R1,800.00 applies if you wish to clear the listing after settling
- Failure to pay will result in legal action and summons
- Additional legal fees and court costs will apply

## Benefits of Payment
- Your account will be brought up to date
- Legal action will be stopped immediately
- All Cartrack services will be reinstated
- Cartrack App access restored
- Vehicle positioning through control room restored
- Vehicle notifications restored
- No recovery fee if vehicle is stolen or hijacked

## Discount Offer Available
- Settlement Discount: 50%
- Settlement Amount: R2,250.00
- Offer Deadline: December 31, 2025

## Maximum Payment Installments: 3 months
```

### Example 2: Payment Agent Context (installment arrangement)

```python
build_complete_agent_context(userdata, agent_type="payment")
```

**Returns:**
```
# Payment Processing Context

**Payment Type:** installment
**DebiCheck Fee:** R10.00 per month
**Monthly Subscription:** R199.00

## Payment Portal Options
- Credit/Debit Card
- Instant EFT
- SnapScan
- Zapper

## Installment Breakdown
- Original Balance: R4,500.00
- Discount: 40% (R1,800.00)
- Discounted Balance: R2,700.00
- Number of Months: 3
- Debt Installment: R900.00
- Subscription: R199.00
- DebiCheck Fee: R10.00
- **Total Monthly Payment: R1,109.00**
```

## Internal Modules

For advanced use, import directly:

```python
from business_rules.config import get_script_config, INSTALLMENT_RULES
from business_rules.discount_calculator import calculate_discount
from business_rules.helpers import format_currency
```
