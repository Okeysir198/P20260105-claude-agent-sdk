# Call Scripts

Structured conversation frameworks for debt collection voice agents, organized by collection stage and debtor status. Ensures POPI compliance, consistency, and quality control.

## Quick Reference

```bash
# Script location
/home/ct-admin/Documents/Langgraph/P20251120-livekit-agent/livekit-agent/debt_collection/call_scripts/

# Files: .txt (agent consumption) + .docx (human review)
# Script integration: prompts/__init__.py
# Discount reference: DISCOUNT_MANDATE_TABLE.md
```

## Script Types

| Script Type | Days Overdue | Discount | Max Payments | Focus |
|-------------|-------------|----------|--------------|-------|
| **Ratio 1 - Inflow** | 30-60 | No | 2 | First contact, service suspension |
| **Ratio 1 - Failed PTP** | 30-60 | No | 2 | Broken payment promises |
| **Ratio 1 - Pro rata** | 30-60 | No | 2 | Prorated payments |
| **Ratio 1 - Short paid** | 30-60 | No | 2 | Partial payment received |
| **Ratio 2&3 - Inflow** | 60-90 | No | 2 | Escalated stage |
| **Ratio 2&3 - Failed PTP** | 60-90 | No | 2 | Broken promises (Ratio 2-3) |
| **Ratio 2&3 - Short paid** | 60-90 | No | 2 | Partial payment (Ratio 2-3) |
| **Recently Suspended 120+** | 120+ | 40-50% | 2-3 | Recent suspension campaign |
| **Pre-Legal 120+** | 120-149 | 30-70% | 2-3 | Final pre-attorney contact |
| **Pre-Legal 150+** | 150+ | 30-70% | 2-3 | Imminent legal action |

## Discount Table Reference

**Recently Suspended 120+:**
- Tier 1 (once-off by 25th): 50%
- Tier 2 (2 payments by 25th): 40%

**Pre-Legal (120-149 days):**
- <R1.5K: 30%
- R1.5K-R5K: 40%
- >R5K: 50%

**Pre-Legal (150+ days):**
- <R1.5K: 40%
- R1.5K-R5K: 50%
- >R5K: 70%

See `DISCOUNT_MANDATE_TABLE.md` for complete matrix.

## Script Structure (14 Sections)

| Section | Content | Critical Elements |
|---------|---------|-------------------|
| **1. Introduction** | Opening greeting | Agent name, company, request for debtor |
| **2. Verification** | POPI compliance | Recording disclosure, 3+ fields OR ID/Passport |
| **3. Reason for Call** | Account status | Outstanding amount, days overdue |
| **4. Negotiation** | Payment options | Consequences, benefits, discounts, installments |
| **5. Promise to Pay** | Payment commitment | Amount, date, method, bank details |
| **6. DebiCheck** | Mandate setup | R10/month fee, SMS authentication |
| **7. Subscription** | Ongoing charges | Separate from arrears (Ratio 1/2-3 only) |
| **8. Payment Portal** | Online payment | SMS link, card/Ozow/CapitecPay/Pay@ |
| **9. Consequences** | Non-payment risks | Service suspension, legal action, credit listing |
| **10. Update Details** | Contact info | Phone, email, banking, next of kin |
| **11. Referrals** | Incentive offer | 2 months free subscription |
| **12. Further Assistance** | Additional concerns | Open-ended offer |
| **13. Notes & Disposition** | Agent documentation | Call outcome logging |
| **14. Cancellation** | Account closure | Cancellation value, escalation to client services |

## Usage Workflow

### 1. Agent Integration

```python
# From prompts/__init__.py
from call_scripts import load_script

def generate_prompt(userdata: UserData) -> str:
    # Load script based on debtor profile
    script = load_script(userdata.debtor.script_type)

    # Extract relevant sections
    intro = extract_section(script, "Introduction")
    verification = extract_section(script, "Verification")

    # Personalize with template variables
    personalized = script.replace("{Client's Full Name}", userdata.debtor.full_name)
    personalized = personalized.replace("{Amount}", f"R{userdata.debtor.outstanding_amount:.2f}")

    # Sanitize before injection
    return sanitize_for_prompt(personalized)
```

### 2. Section Mapping to Agents

| Agent | Script Sections Used |
|-------|---------------------|
| **Introduction** | 1 (Introduction) |
| **Verification** | 2 (Verification) |
| **Negotiation** | 3-4 (Reason + Negotiation) |
| **Payment** | 5-8 (PTP + DebiCheck + Portal) |
| **Closing** | 10-14 (Updates + Referrals + Closing) |

### 3. Dynamic Variables

| Template Variable | Source | Example |
|------------------|--------|---------|
| `{Agent's Name}` | AI agent identifier | "Sophia" |
| `{Client's Full Name}` | DebtorProfile.full_name | "John Smith" |
| `{Client Name}` | First name only | "John" |
| `{Amount}` | DebtorProfile.outstanding_amount | "R2,500.00" |
| `{Balance}` | Total arrears | "R5,340.00" |
| `{Discount Percentage}` | Business rules | "50%" |
| `{Discounted amount}` | Calculated | "R1,500.00" |
| `{Subscription}` | Monthly fee | "R399.00" |
| `{Cancellation Value}` | Termination fee | "R1,800.00" |

### 4. Compliance Tracking

```python
# Log verification attempts
userdata.call.log_event(
    AuditEventType.VERIFICATION_SUCCESS,
    agent_id="verification",
    fields_verified=["id_number", "birth_date"]
)

# Track discount offered
userdata.call.log_event(
    AuditEventType.DISCOUNT_OFFERED,
    agent_id="negotiation",
    discount_percentage=50,
    discounted_amount=1500.00
)
```

### 5. Script Update Process

1. **Edit .txt file** (authoritative source)
2. **Update matching .docx** for humans
3. **Test parsing:** `python -c "from prompts import load_script; print(load_script('ratio1_inflow'))"`
4. **Verify template variables:** Check all `{Variable}` resolve
5. **Run tests:** `cd eval && python run_tests.py --tags script_types`
6. **Commit both files:** `git add *.txt *.docx && git commit -m "Update: script changes"`

## Key Sections Explained

### Verification (Section 2)

**POPI Requirements:**
- Call recording disclosure
- Minimum 3 fields OR full ID/Passport
- Available fields: Username, DOB, vehicle, contact, address
- Third-party protocol: No debt details disclosed

**Agent Implementation:**
```python
# tools/tool02_verification.py
@function_tool()
async def verify_field(field_name: str, provided_value: str, context) -> str:
    result = fuzzy_match(provided_value, expected_value, field_name)

    # Log attempt
    userdata.call.log_verification_attempt(field_name, result["matched"])

    if result["matched"]:
        userdata.call.verified_fields.add(field_name)
        return "Field verified"
    else:
        return "Field does not match our records"
```

### Negotiation (Section 4)

**Components:**
1. **Consequences:**
   - Service suspension (Cartrack app, positioning, notifications)
   - Recovery fee (R25,000 if vehicle stolen/hijacked)
   - Legal action (Pre-Legal scripts)
   - Credit bureau listing (affects credit applications)
   - Clearance fee (R1,800 to remove listing)

2. **Benefits:**
   - Service restoration
   - Legal action stopped
   - Account in good standing
   - No recovery fees
   - Credit profile protected

3. **Settlement Options:**
   - Immediate payment (same-day debit)
   - Discount offers (script-dependent)
   - Installment arrangements (2-3 months)

**Agent Implementation:**
```python
# tools/tool03_negotiation.py
@function_tool()
async def offer_settlement(discount_percentage: float, context) -> str:
    userdata = context.userdata
    balance = userdata.debtor.outstanding_amount
    discounted_amount = balance * (1 - discount_percentage / 100)

    userdata.call.discount_offered = discount_percentage
    userdata.call.discount_amount = discounted_amount

    return f"Offering {discount_percentage}% discount: pay R{discounted_amount:.2f}"
```

### Payment Portal (Section 8)

**Features:**
- SMS link delivery
- Multiple methods: Card, Ozow, CapitecPay, Pay@
- Recurring payment setup
- WhatsApp support

**Agent Guidance:**
```python
@function_tool()
async def send_portal_link(context) -> str:
    userdata = context.userdata
    userdata.call.payment_type = "portal"

    # Simulate SMS send
    portal_url = "https://cartrack.payment-portal.co.za/pay?ref=XXX"

    return f"SMS sent with payment link. Methods: Card, Ozow, CapitecPay, Pay@"
```

## File Formats

### .txt Files (Agent Consumption)
- UTF-8 with BOM
- Numbered sections (1-14)
- Plain text formatting
- Version-controlled in git
- Primary format for AI agents

### .docx Files (Human Review)
- Formatted with headings, bullets
- Printable for training
- Used by QA and supervisors
- Not consumed by voice agents

**Important:** .txt files are authoritative. Update both formats together.

## Updating Scripts Checklist

- [ ] Authorization obtained (Collections Manager, Compliance, Legal)
- [ ] Edit .txt file first
- [ ] Update matching .docx file
- [ ] Verify template variables intact
- [ ] Test parsing: `python -c "from prompts import load_script; print(load_script('type'))"`
- [ ] Check prompt length limits
- [ ] Run unit tests: `python eval/run_tests.py --tags script_types`
- [ ] QA approval received
- [ ] Compliance sign-off
- [ ] Commit both files together
- [ ] Update DISCOUNT_MANDATE_TABLE.md if discounts changed

## Compliance Notes

### POPI Act
- **Section 9:** Prior authorization before processing personal information
- **Section 11:** Security safeguards for banking and identity data
- **Section 18:** Data subject notification (call recording disclosure)

### National Credit Act (NCA)
- **Regulation 17:** Debt collection conduct standards
- Prohibition on harassment and coercion
- Required disclosures for legal action and credit bureau listing

### Audit Requirements
- Call recordings: 5 years retention (NCA)
- Payment arrangements: 7 years retention (tax/legal)
- Audit logs: Permanent retention (POPI accountability)

## Troubleshooting

### Script not loading
**Cause:** File path incorrect or script type mismatch

**Solution:**
```bash
# Check file exists
ls call_scripts/*.txt

# Verify script type in config
grep "script_type" business_rules/config.py
```

### Template variables not replacing
**Cause:** Variable name mismatch or missing data

**Solution:**
```python
# Debug variable replacement
from prompts import load_script
script = load_script("ratio1_inflow")
print([var for var in script if "{" in var])  # Find all variables
```

### Prompt too long (LLM context limit)
**Cause:** Script + prompt exceeds model context window

**Solution:**
```python
# Use sanitize_for_prompt with max_length
from prompts import sanitize_for_prompt
shortened = sanitize_for_prompt(script_content, max_length=5000)
```

## Related Documentation

- **Business Rules:** `business_rules/config.py` - Script types, fees, discounts
- **Discount Table:** `DISCOUNT_MANDATE_TABLE.md` - Complete discount matrix
- **Prompt Templates:** `prompts/` - Agent prompt generation
- **Tools:** `tools/` - Payment validation, verification logic
- **Shared State:** `shared_state.py` - DebtorProfile, CallState

---

**Last Updated:** 2025-12-05
**Maintained By:** Debt Collection Operations Team
**Review Cycle:** Quarterly or upon regulatory changes
**Contact:** collections@cartrack.com
