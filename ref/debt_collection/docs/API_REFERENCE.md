# API Reference

> **Note:** This reference documents the intended API design. Always verify function signatures
> against the actual source code, as implementations may have evolved.

## Table of Contents

1. [Shared State API](#shared-state-api)
2. [Agent Classes API](#agent-classes-api)
3. [Tools API](#tools-api)
4. [Business Rules API](#business-rules-api)
5. [Utility Functions API](#utility-functions-api)
6. [Configuration API](#configuration-api)

---

## Shared State API

### Module: `shared_state.py`

> **Alternative:** The modular state implementation is available in `state/` folder:
> - `state/types.py` - Enums and type definitions
> - `state/profile.py` - DebtorProfile (frozen dataclass)
> - `state/session.py` - CallState (mutable dataclass)

#### Enums

##### `AuditEventType`

```python
class AuditEventType(Enum):
    """Event types for POPI compliance audit logging."""

    CALL_STARTED = "call_started"
    IDENTITY_CONFIRMED = "identity_confirmed"
    IDENTITY_FAILED = "identity_failed"
    VERIFICATION_ATTEMPT = "verification_attempt"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"
    PAYMENT_CAPTURED = "payment_captured"
    BANK_DETAILS_ACCESSED = "bank_details_accessed"
    BANK_DETAILS_UPDATED = "bank_details_updated"
    AGENT_TRANSITION = "agent_transition"
    ESCALATION = "escalation"
    CALLBACK_SCHEDULED = "callback_scheduled"
    CALL_ENDED = "call_ended"
```

#### Dataclasses

##### `AuditEvent`

```python
@dataclass
class AuditEvent:
    """Audit event for POPI compliance tracking."""

    event_type: AuditEventType
    timestamp: str
    agent_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
```

**Methods:**

```python
@classmethod
def create(
    cls,
    event_type: AuditEventType,
    agent_id: Optional[str] = None,
    **details
) -> "AuditEvent":
    """Create an audit event with current timestamp.

    Args:
        event_type: Type of audit event
        agent_id: ID of the agent performing the action
        **details: Additional event-specific details

    Returns:
        AuditEvent instance with ISO-formatted timestamp

    Example:
        >>> event = AuditEvent.create(
        ...     AuditEventType.VERIFICATION_SUCCESS,
        ...     agent_id="verification",
        ...     field_name="id_number"
        ... )
    """
```

##### `DebtorProfile`

```python
@dataclass(frozen=True)
class DebtorProfile:
    """Immutable debtor profile loaded from job metadata."""

    # Identity (Required)
    full_name: str
    user_id: str
    username: str

    # Identity Documents
    id_number: Optional[str] = None
    passport_number: Optional[str] = None
    birth_date: Optional[str] = None

    # Contact Information
    email: Optional[str] = None
    contact_number: Optional[str] = None
    alternative_number: Optional[str] = None
    residential_address: Optional[str] = None

    # Vehicle Information
    vehicle_registration: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_color: Optional[str] = None
    vin_number: Optional[str] = None

    # Banking Information
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    branch_code: Optional[str] = None
    salary_date: Optional[str] = None
    has_reversal_history: bool = False

    # Debt Information
    outstanding_amount: Optional[float] = None
    overdue_days: Optional[int] = None
    account_status: str = "active"
    monthly_subscription: Optional[float] = None
    cancellation_fee: Optional[float] = None
    partial_payment_received: Optional[float] = None
    agreed_amount: Optional[float] = None

    # Next of Kin
    next_of_kin_name: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_contact: Optional[str] = None
```

**Properties:**

```python
@property
def shortfall_amount(self) -> Optional[float]:
    """Calculate shortfall for short_paid scripts.

    Returns:
        Shortfall amount if both partial payment and agreed amount available

    Example:
        >>> debtor = DebtorProfile(
        ...     partial_payment_received=1000.0,
        ...     agreed_amount=1500.0
        ... )
        >>> debtor.shortfall_amount
        500.0
    """
```

**Methods:**

```python
@classmethod
def from_job_metadata(cls, metadata: dict) -> "DebtorProfile":
    """Create DebtorProfile instance from job metadata dictionary.

    Args:
        metadata: Dictionary containing debtor information

    Returns:
        DebtorProfile instance with parsed data

    Example:
        >>> metadata = {
        ...     'full_name': 'John Smith',
        ...     'user_id': '12345',
        ...     'outstanding_amount': 5000.0
        ... }
        >>> debtor = DebtorProfile.from_job_metadata(metadata)
    """

def get_verification_fields(self) -> Dict[str, Any]:
    """Get all available fields for identity verification.

    Returns:
        Dictionary mapping field names to values (excludes None values)

    Example:
        >>> fields = debtor.get_verification_fields()
        >>> print(fields.keys())
        dict_keys(['username', 'id_number', 'email', 'contact_number'])
    """

def get_banking_info(self) -> Dict[str, Any]:
    """Get banking information for payment processing.

    Returns:
        Dictionary with available banking details

    Example:
        >>> banking = debtor.get_banking_info()
        >>> print(banking['bank_name'])
        'Standard Bank'
    """
```

##### `CallState`

```python
@dataclass
class CallState:
    """Mutable state tracking call progression."""

    # Script Configuration
    script_type: str = "standard"
    authority: Optional[str] = None
    authority_contact: Optional[str] = None

    # Introduction Phase
    person_confirmed: bool = False
    person_type: Optional[str] = None
    third_party_relationship: Optional[str] = None

    # Verification Phase
    identity_verified: bool = False
    verified_fields: Set[str] = field(default_factory=set)
    unavailable_fields: Set[str] = field(default_factory=set)
    verification_attempts: int = 0
    failed_verification_fields: List[str] = field(default_factory=list)
    current_field_attempts: int = 0
    max_field_attempts: int = 3

    # Negotiation Phase
    reason_explained: bool = False
    consequences_explained: bool = False
    benefits_explained: bool = False
    discount_offered: bool = False
    discount_amount: Optional[float] = None
    discount_accepted: bool = False
    tier1_offered: bool = False
    tier2_offered: bool = False

    # Payment Phase
    payment_type: Optional[str] = None
    payment_method: Optional[str] = None
    payment_arrangements: List[Dict[str, Any]] = field(default_factory=list)
    payment_confirmed: bool = False
    debicheck_sent: bool = False
    portal_link_sent: bool = False

    # Bank Validation
    bank_validation_status: Optional[str] = None
    bank_details_updated: bool = False

    # Details Update Phase
    contact_details_updated: bool = False
    banking_details_updated: bool = False
    next_of_kin_updated: bool = False

    # Closing Phase
    subscription_explained: bool = False
    referral_offered: bool = False
    referral_accepted: bool = False

    # Cancellation Phase
    cancellation_requested: bool = False
    cancellation_ticket_id: Optional[str] = None

    # Callback Management
    callback_scheduled: bool = False
    callback_datetime: Optional[str] = None
    callback_reason: Optional[str] = None

    # Escalation
    escalation_reason: Optional[str] = None
    escalation_notes: Optional[str] = None

    # Call Outcome
    call_outcome: Optional[str] = None
    call_notes: str = ""

    # POPI Compliance Audit Log
    audit_log: List[AuditEvent] = field(default_factory=list)
```

**Methods:**

```python
def add_verified_field(self, field_name: str) -> None:
    """Add a successfully verified field.

    Args:
        field_name: Name of the verified field

    Example:
        >>> call_state.add_verified_field("id_number")
    """

def add_unavailable_field(self, field_name: str) -> None:
    """Mark a field as unavailable/unknown.

    Args:
        field_name: Name of the unavailable field
    """

def increment_verification_attempts(self) -> int:
    """Increment and return verification attempt counter.

    Returns:
        Updated attempt count
    """

def add_failed_verification_field(self, field_name: str) -> None:
    """Record a field that failed verification.

    Args:
        field_name: Name of the failed field
    """

def reset_field_attempts(self) -> None:
    """Reset the current field attempt counter."""

def increment_field_attempts(self) -> int:
    """Increment and return current field attempt counter.

    Returns:
        Updated field attempt count
    """

def add_payment_arrangement(
    self,
    amount: float,
    date: str,
    method: str,
    description: Optional[str] = None
) -> None:
    """Add a payment arrangement to the list.

    Args:
        amount: Payment amount
        date: Payment date (ISO format or DD/MM/YYYY)
        method: Payment method
        description: Optional description

    Example:
        >>> call_state.add_payment_arrangement(
        ...     amount=1500.0,
        ...     date="2025-01-15",
        ...     method="debicheck"
        ... )
    """

def append_call_notes(self, note: str) -> None:
    """Append a note to the call notes with timestamp.

    Args:
        note: Note text to append
    """

def get_progress_summary(self) -> Dict[str, bool]:
    """Get summary of call progress through major phases.

    Returns:
        Dictionary with boolean flags for each phase completion

    Example:
        >>> progress = call_state.get_progress_summary()
        >>> print(progress)
        {
            'introduction_complete': True,
            'verification_complete': True,
            'negotiation_complete': False,
            'payment_complete': False,
            'closing_complete': False
        }
    """

def log_event(
    self,
    event_type: AuditEventType,
    agent_id: Optional[str] = None,
    **details
) -> None:
    """Log an audit event for POPI compliance.

    Args:
        event_type: Type of audit event
        agent_id: ID of the agent performing the action
        **details: Additional event-specific details
    """

def log_verification_attempt(
    self,
    field_name: str,
    success: bool,
    agent_id: Optional[str] = None
) -> None:
    """Log a verification attempt with result.

    Args:
        field_name: Name of the field being verified
        success: Whether verification was successful
        agent_id: ID of the agent performing verification
    """

def log_payment_capture(
    self,
    amount: float,
    method: str,
    agent_id: Optional[str] = None
) -> None:
    """Log payment capture event.

    Args:
        amount: Payment amount
        method: Payment method
        agent_id: ID of the agent capturing payment
    """

def log_agent_transition(
    self,
    from_agent: Optional[str],
    to_agent: str
) -> None:
    """Log agent-to-agent transition.

    Args:
        from_agent: Name of the agent being transitioned from
        to_agent: Name of the agent being transitioned to
    """

def get_audit_summary(self) -> Dict[str, Any]:
    """Get summary of audit log for compliance reporting.

    Returns:
        Dictionary containing total event count and detailed event list

    Example:
        >>> summary = call_state.get_audit_summary()
        >>> print(summary['total_events'])
        15
    """
```

##### `UserData`

```python
@dataclass
class UserData:
    """Main session state container for debt collection calls."""

    debtor: DebtorProfile
    call: CallState = field(default_factory=CallState)
    agents: Dict[str, "Agent"] = field(default_factory=dict)
    prev_agent: Optional["Agent"] = None

    # Metadata
    session_id: Optional[str] = None
    call_start_time: Optional[str] = None
    current_agent_id: Optional[str] = None
    ctx: Optional[Any] = None
```

**Methods:**

```python
def summarize(self) -> str:
    """Generate YAML-formatted summary of session state.

    Returns:
        YAML string containing debtor info, call progress, and key state

    Example:
        >>> print(userdata.summarize())
        session_id: abc123
        debtor:
          name: John Smith
          outstanding_amount: R5,000.00
        call:
          script_type: ratio1_inflow
          progress:
            verification_complete: true
    """

def get_context_for_agent(self, agent_name: str) -> str:
    """Generate agent-specific context including handoff information.

    Args:
        agent_name: Name of the agent requesting context

    Returns:
        Formatted context string for the agent

    Example:
        >>> context = userdata.get_context_for_agent("verification")
        >>> print(context)
        # Session Context for verification
        ...
    """

def record_agent_transition(
    self,
    from_agent: Optional["Agent"],
    to_agent: "Agent"
) -> None:
    """Record an agent-to-agent transition.

    Args:
        from_agent: The agent being transitioned from (None if first)
        to_agent: The agent being transitioned to
    """
```

---

## Agent Classes API

### Module: `sub_agents/base_agent.py`

#### `BaseAgent`

```python
class BaseAgent(Agent):
    """Base class for all debt collection agents."""

    async def on_enter(self) -> None:
        """Called when this agent becomes active.

        Handles:
        - Loading previous agent's chat context
        - Adding current call state as system message
        - Triggering initial reply generation

        Example:
            >>> class MyAgent(BaseAgent):
            ...     async def on_enter(self):
            ...         await super().on_enter()
            ...         # Custom logic here
        """
```

### Module: `sub_agents/agent01_introduction.py`

#### `IntroductionAgent`

```python
class IntroductionAgent(BaseAgent):
    """Introduction agent for initial contact and identity confirmation."""

    def __init__(self, tts: Any):
        """Initialize Introduction agent.

        Args:
            tts: Text-to-speech provider instance
        """

    async def on_enter(self) -> None:
        """Handle agent entry with context preservation."""
```

**Available Tools:**
- `confirm_person`
- `handle_wrong_person`
- `handle_third_party`
- `schedule_callback`

### Module: `sub_agents/agent02_verification.py`

#### `VerificationAgent`

```python
class VerificationAgent(BaseAgent):
    """Verification agent for POPI-compliant identity verification."""

    def __init__(self, tts: Any):
        """Initialize Verification agent.

        Args:
            tts: Text-to-speech provider instance
        """
```

**Available Tools:**
- `verify_field`
- `mark_unavailable`
- `schedule_callback`

### Module: `sub_agents/agent03_negotiation.py`

#### `NegotiationAgent`

```python
class NegotiationAgent(BaseAgent):
    """Negotiation agent for payment arrangement negotiation."""

    def __init__(self, userdata: UserData, tts: Any):
        """Initialize Negotiation agent.

        Args:
            userdata: Session user data
            tts: Text-to-speech provider instance
        """
```

**Available Tools:**
- `offer_settlement`
- `offer_installment`
- `accept_arrangement`
- `explain_consequences`
- `explain_benefits`
- `escalate`
- `handle_cancellation_request`
- `schedule_callback`

### Module: `sub_agents/agent04_payment.py`

#### `PaymentAgent`

```python
class PaymentAgent(BaseAgent):
    """Payment agent for payment details capture and processing."""

    def __init__(self, userdata: UserData, tts: Any):
        """Initialize Payment agent.

        Args:
            userdata: Session user data
            tts: Text-to-speech provider instance
        """
```

**Available Tools:**
- `capture_immediate_debit`
- `validate_bank_details`
- `update_bank_details`
- `setup_debicheck`
- `send_portal_link`
- `confirm_portal_payment`
- `confirm_arrangement`
- `schedule_callback`

### Module: `sub_agents/agent05_closing.py`

#### `ClosingAgent`

```python
class ClosingAgent(BaseAgent):
    """Closing agent for call wrap-up and referrals."""

    def __init__(self, tts: Any):
        """Initialize Closing agent.

        Args:
            tts: Text-to-speech provider instance
        """
```

**Available Tools:**
- `offer_referral`
- `update_contact_details`
- `update_next_of_kin`
- `explain_subscription`
- `end_call`

---

## Tools API

### Module: `tools/common_tools.py`

#### `transfer_to_agent`

```python
async def transfer_to_agent(agent_name: str) -> str:
    """Transfer control to another agent (internal use).

    Args:
        agent_name: Name of the target agent

    Returns:
        Confirmation message

    Example:
        >>> result = await transfer_to_agent("verification")
    """
```

#### `fuzzy_match`

```python
def fuzzy_match(
    input_value: str,
    expected_value: str,
    threshold: float = 0.8
) -> bool:
    """Check if input matches expected value using fuzzy matching.

    Args:
        input_value: User's spoken input
        expected_value: Expected correct value
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        True if similarity >= threshold

    Example:
        >>> fuzzy_match("oh eight five oh one", "0850123456", threshold=0.8)
        True
    """
```

#### `validate_business_hours`

```python
def validate_business_hours(datetime_str: str) -> tuple[bool, str]:
    """Validate if datetime falls within business hours.

    Business hours: Mon-Sat 07:00-18:00 SAST

    Args:
        datetime_str: ISO format datetime string

    Returns:
        Tuple of (is_valid, message)

    Example:
        >>> valid, msg = validate_business_hours("2025-01-15T14:00:00")
        >>> print(valid)
        True
    """
```

#### `schedule_callback`

```python
@function_tool
async def schedule_callback(
    ctx: RunContext[UserData],
    datetime_str: str,
    reason: str
) -> str:
    """Schedule a callback with the customer.

    Args:
        ctx: Runtime context with user data
        datetime_str: Callback datetime (ISO format)
        reason: Reason for callback

    Returns:
        Confirmation message

    Raises:
        ValueError: If datetime is outside business hours

    Example:
        >>> result = await schedule_callback(
        ...     ctx,
        ...     "2025-01-15T14:00:00",
        ...     "Follow up on payment arrangement"
        ... )
    """
```

#### `escalate`

```python
@function_tool
async def escalate(
    ctx: RunContext[UserData],
    reason: str,
    notes: Optional[str] = None
) -> str:
    """Escalate call to supervisor.

    Args:
        ctx: Runtime context with user data
        reason: Escalation reason
        notes: Additional notes

    Returns:
        Confirmation message with transfer instructions

    Example:
        >>> result = await escalate(
        ...     ctx,
        ...     "Customer disputes debt validity",
        ...     "Requires manager review"
        ... )
    """
```

### Module: `tools/tool01_introduction.py`

#### `confirm_person`

```python
@function_tool
async def confirm_person(ctx: RunContext[UserData]) -> str:
    """Confirm that the person on the call is the debtor.

    Args:
        ctx: Runtime context with user data

    Returns:
        Confirmation message with handoff to verification agent

    Side Effects:
        - Sets person_confirmed = True
        - Sets person_type = "self"
        - Logs IDENTITY_CONFIRMED event
        - Triggers handoff to verification agent

    Example:
        >>> result = await confirm_person(ctx)
    """
```

#### `handle_wrong_person`

```python
@function_tool
async def handle_wrong_person(ctx: RunContext[UserData]) -> str:
    """Handle case where wrong person answered the call.

    Args:
        ctx: Runtime context with user data

    Returns:
        Message with handoff to closing agent

    Side Effects:
        - Sets person_type = "wrong_person"
        - Logs IDENTITY_FAILED event
        - Triggers handoff to closing agent

    Example:
        >>> result = await handle_wrong_person(ctx)
    """
```

#### `handle_third_party`

```python
@function_tool
async def handle_third_party(
    ctx: RunContext[UserData],
    relationship: str
) -> str:
    """Handle case where third party answered the call.

    Args:
        ctx: Runtime context with user data
        relationship: Relationship to debtor (e.g., "spouse", "parent")

    Returns:
        Message with handoff to closing agent

    Side Effects:
        - Sets person_type = "third_party"
        - Sets third_party_relationship
        - Logs event
        - Triggers handoff to closing agent

    Example:
        >>> result = await handle_third_party(ctx, "spouse")
    """
```

### Module: `tools/tool02_verification.py`

#### `verify_field`

```python
@function_tool
async def verify_field(
    ctx: RunContext[UserData],
    field_name: str,
    user_input: str
) -> str:
    """Verify a debtor information field using fuzzy matching.

    Args:
        ctx: Runtime context with user data
        field_name: Name of field to verify (e.g., "id_number")
        user_input: User's spoken input

    Returns:
        Verification result message

    Side Effects:
        - Adds field to verified_fields if successful
        - Adds field to failed_verification_fields if failed
        - Increments verification_attempts
        - Logs verification attempt
        - Triggers handoff if verification complete (2+ fields)

    Example:
        >>> result = await verify_field(
        ...     ctx,
        ...     "id_number",
        ...     "eight five oh one one two five six seven eight nine oh one"
        ... )
    """
```

#### `mark_unavailable`

```python
@function_tool
async def mark_unavailable(
    ctx: RunContext[UserData],
    field_name: str
) -> str:
    """Mark a field as unavailable/unknown to the caller.

    Args:
        ctx: Runtime context with user data
        field_name: Name of field that's unavailable

    Returns:
        Confirmation message

    Side Effects:
        - Adds field to unavailable_fields

    Example:
        >>> result = await mark_unavailable(ctx, "birth_date")
    """
```

### Module: `tools/tool03_negotiation.py`

#### `offer_settlement`

```python
@function_tool
async def offer_settlement(
    ctx: RunContext[UserData],
    discount_percentage: Optional[float] = None
) -> str:
    """Offer a settlement payment arrangement.

    Args:
        ctx: Runtime context with user data
        discount_percentage: Optional custom discount (overrides calculated)

    Returns:
        Settlement offer details

    Side Effects:
        - Sets discount_offered = True
        - Sets discount_amount

    Example:
        >>> result = await offer_settlement(ctx, discount_percentage=50.0)
    """
```

#### `offer_installment`

```python
@function_tool
async def offer_installment(
    ctx: RunContext[UserData],
    num_payments: int,
    discount_percentage: Optional[float] = None
) -> str:
    """Offer an installment payment arrangement.

    Args:
        ctx: Runtime context with user data
        num_payments: Number of installment payments
        discount_percentage: Optional custom discount

    Returns:
        Installment offer details

    Raises:
        ValueError: If num_payments exceeds script maximum

    Example:
        >>> result = await offer_installment(ctx, num_payments=3)
    """
```

#### `accept_arrangement`

```python
@function_tool
async def accept_arrangement(
    ctx: RunContext[UserData],
    arrangement_type: str,
    amount: float
) -> str:
    """Accept a payment arrangement and handoff to payment agent.

    Args:
        ctx: Runtime context with user data
        arrangement_type: Type ("settlement" or "installment")
        amount: Agreed payment amount

    Returns:
        Confirmation message with handoff to payment agent

    Side Effects:
        - Sets discount_accepted = True
        - Logs payment arrangement
        - Triggers handoff to payment agent

    Example:
        >>> result = await accept_arrangement(
        ...     ctx,
        ...     "settlement",
        ...     2500.0
        ... )
    """
```

#### `explain_consequences`

```python
@function_tool
async def explain_consequences(ctx: RunContext[UserData]) -> str:
    """Explain consequences of non-payment based on script type.

    Args:
        ctx: Runtime context with user data

    Returns:
        Script-specific consequence message

    Side Effects:
        - Sets consequences_explained = True

    Example:
        >>> result = await explain_consequences(ctx)
    """
```

#### `explain_benefits`

```python
@function_tool
async def explain_benefits(ctx: RunContext[UserData]) -> str:
    """Explain benefits of payment based on account status.

    Args:
        ctx: Runtime context with user data

    Returns:
        Benefits message (active vs cancelled accounts)

    Side Effects:
        - Sets benefits_explained = True

    Example:
        >>> result = await explain_benefits(ctx)
    """
```

### Module: `tools/tool04_payment.py`

#### `capture_immediate_debit`

```python
@function_tool
async def capture_immediate_debit(
    ctx: RunContext[UserData],
    bank_name: str,
    account_number: str,
    branch_code: str
) -> str:
    """Capture bank details for immediate debit.

    Args:
        ctx: Runtime context with user data
        bank_name: Bank name
        account_number: Account number
        branch_code: Branch code

    Returns:
        Confirmation message

    Raises:
        ValueError: If validation fails

    Side Effects:
        - Validates bank details
        - Logs BANK_DETAILS_ACCESSED event
        - Sets payment_method = "immediate_debit"

    Example:
        >>> result = await capture_immediate_debit(
        ...     ctx,
        ...     "Standard Bank",
        ...     "1234567890",
        ...     "051001"
        ... )
    """
```

#### `validate_bank_details`

```python
@function_tool
async def validate_bank_details(
    ctx: RunContext[UserData],
    bank_name: str,
    account_number: str,
    branch_code: str
) -> str:
    """Validate bank details without capturing.

    Args:
        ctx: Runtime context with user data
        bank_name: Bank name
        account_number: Account number
        branch_code: Branch code

    Returns:
        Validation result message

    Example:
        >>> result = await validate_bank_details(
        ...     ctx,
        ...     "FNB",
        ...     "62123456789",
        ...     "250655"
        ... )
    """
```

#### `update_bank_details`

```python
@function_tool
async def update_bank_details(
    ctx: RunContext[UserData],
    bank_name: str,
    account_number: str,
    branch_code: str
) -> str:
    """Update bank details on file.

    Args:
        ctx: Runtime context with user data
        bank_name: New bank name
        account_number: New account number
        branch_code: New branch code

    Returns:
        Confirmation message

    Side Effects:
        - Validates new bank details
        - Logs BANK_DETAILS_UPDATED event
        - Sets bank_details_updated = True

    Example:
        >>> result = await update_bank_details(
        ...     ctx,
        ...     "Capitec",
        ...     "1234567890",
        ...     "470010"
        ... )
    """
```

#### `setup_debicheck`

```python
@function_tool
async def setup_debicheck(
    ctx: RunContext[UserData],
    bank_name: str,
    account_number: str,
    branch_code: str,
    amount: float
) -> str:
    """Setup DebiCheck mandate (R10/month fee).

    Args:
        ctx: Runtime context with user data
        bank_name: Bank name
        account_number: Account number
        branch_code: Branch code
        amount: Monthly debit amount

    Returns:
        Setup confirmation with SMS instructions

    Side Effects:
        - Validates bank details
        - Checks reversal history (warns if present)
        - Logs PAYMENT_CAPTURED event
        - Sets debicheck_sent = True
        - Sets payment_method = "debicheck"

    Example:
        >>> result = await setup_debicheck(
        ...     ctx,
        ...     "ABSA",
        ...     "4081234567",
        ...     "632005",
        ...     500.0
        ... )
    """
```

#### `send_portal_link`

```python
@function_tool
async def send_portal_link(ctx: RunContext[UserData]) -> str:
    """Send payment portal link via SMS.

    Args:
        ctx: Runtime context with user data

    Returns:
        Confirmation message

    Side Effects:
        - Sets portal_link_sent = True
        - Sets payment_method = "portal"

    Example:
        >>> result = await send_portal_link(ctx)
    """
```

#### `confirm_portal_payment`

```python
@function_tool
async def confirm_portal_payment(ctx: RunContext[UserData]) -> str:
    """Confirm portal payment received.

    Args:
        ctx: Runtime context with user data

    Returns:
        Confirmation message with handoff to closing

    Side Effects:
        - Sets payment_confirmed = True
        - Logs PAYMENT_CAPTURED event
        - Triggers handoff to closing agent

    Example:
        >>> result = await confirm_portal_payment(ctx)
    """
```

#### `confirm_arrangement`

```python
@function_tool
async def confirm_arrangement(ctx: RunContext[UserData]) -> str:
    """Confirm payment arrangement is complete.

    Args:
        ctx: Runtime context with user data

    Returns:
        Confirmation message with handoff to closing

    Side Effects:
        - Sets payment_confirmed = True
        - Triggers handoff to closing agent

    Example:
        >>> result = await confirm_arrangement(ctx)
    """
```

### Module: `tools/tool05_closing.py`

#### `offer_referral`

```python
@function_tool
async def offer_referral(ctx: RunContext[UserData]) -> str:
    """Offer customer referral program.

    Args:
        ctx: Runtime context with user data

    Returns:
        Referral program details

    Side Effects:
        - Sets referral_offered = True

    Example:
        >>> result = await offer_referral(ctx)
    """
```

#### `update_contact_details`

```python
@function_tool
async def update_contact_details(
    ctx: RunContext[UserData],
    email: Optional[str] = None,
    contact_number: Optional[str] = None,
    address: Optional[str] = None
) -> str:
    """Update customer contact details.

    Args:
        ctx: Runtime context with user data
        email: New email address
        contact_number: New contact number
        address: New residential address

    Returns:
        Confirmation message

    Side Effects:
        - Sets contact_details_updated = True

    Example:
        >>> result = await update_contact_details(
        ...     ctx,
        ...     email="john.new@example.com",
        ...     contact_number="0829876543"
        ... )
    """
```

#### `update_next_of_kin`

```python
@function_tool
async def update_next_of_kin(
    ctx: RunContext[UserData],
    name: str,
    relationship: str,
    contact: str
) -> str:
    """Update next of kin information.

    Args:
        ctx: Runtime context with user data
        name: Next of kin name
        relationship: Relationship to debtor
        contact: Contact number

    Returns:
        Confirmation message

    Side Effects:
        - Sets next_of_kin_updated = True

    Example:
        >>> result = await update_next_of_kin(
        ...     ctx,
        ...     "Jane Smith",
        ...     "Spouse",
        ...     "0821112222"
        ... )
    """
```

#### `explain_subscription`

```python
@function_tool
async def explain_subscription(ctx: RunContext[UserData]) -> str:
    """Explain subscription continuation/cancellation details.

    Args:
        ctx: Runtime context with user data

    Returns:
        Subscription status message based on account status

    Side Effects:
        - Sets subscription_explained = True

    Example:
        >>> result = await explain_subscription(ctx)
    """
```

#### `end_call`

```python
@function_tool
async def end_call(
    ctx: RunContext[UserData],
    outcome: str,
    notes: Optional[str] = None
) -> str:
    """End the call with specified outcome.

    Args:
        ctx: Runtime context with user data
        outcome: Call outcome (payment_arranged, callback_scheduled, etc.)
        notes: Optional additional notes

    Returns:
        Closing message

    Side Effects:
        - Sets call_outcome
        - Appends call_notes
        - Logs CALL_ENDED event

    Example:
        >>> result = await end_call(
        ...     ctx,
        ...     "payment_arranged",
        ...     "DebiCheck mandate sent, customer confirmed receipt"
        ... )
    """
```

---

## Business Rules API

### Module: `business_rules/config.py`

#### Constants

```python
AUTHORITIES: Dict[str, Dict[str, str]]
"""Authority contact information.

Keys: 'cartrack', 'viljoen'

Example:
    >>> AUTHORITIES['cartrack']
    {'name': 'Cartrack Accounts Department', 'contact': '011-250-3000'}
"""

SCRIPT_TYPES: Dict[str, Dict[str, Any]]
"""Script type configurations.

Keys: 'ratio1_inflow', 'ratio1_failed_ptp', 'ratio2_3_inflow',
      'recently_suspended_120', 'prelegal_120', 'prelegal_150',
      'legal_stage', 'booksale_stage'

Example:
    >>> SCRIPT_TYPES['prelegal_150']
    {
        'authority': 'viljoen',
        'discount_enabled': True,
        'max_payments': 3,
        'consequence_level': 'attorney',
        'discount_tiers': {...}
    }
"""

FEES: Dict[str, float]
"""Fee structure.

Keys: 'DEBICHECK_FEE', 'CREDIT_CLEARANCE_FEE', 'RECOVERY_FEE'

Example:
    >>> FEES['DEBICHECK_FEE']
    10.0
"""

INSTALLMENT_RULES: Dict[str, Any]
"""Installment payment rules based on balance.

Keys: 'tier1', 'tier2', 'tier3'

Example:
    >>> INSTALLMENT_RULES['tier1']
    {'max_balance': 1500.0, 'min_months': 3, 'description': '...'}
"""
```

#### Functions

```python
def get_script_config(script_type: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific script type.

    Args:
        script_type: Script type identifier

    Returns:
        Configuration dict or None if not found

    Example:
        >>> config = get_script_config('ratio1_inflow')
        >>> print(config['authority'])
        'cartrack'
    """

def get_authority_info(authority_key: str) -> Optional[Dict[str, str]]:
    """Get authority contact information.

    Args:
        authority_key: Authority identifier ('cartrack' or 'viljoen')

    Returns:
        Authority info dict or None if not found

    Example:
        >>> info = get_authority_info('viljoen')
        >>> print(info['contact'])
        '010-140-0085'
    """

def get_fee(fee_type: str) -> Optional[float]:
    """Get fee amount by type.

    Args:
        fee_type: Fee type key

    Returns:
        Fee amount or None if not found

    Example:
        >>> fee = get_fee('DEBICHECK_FEE')
        >>> print(fee)
        10.0
    """

def get_discount_tiers(script_type: str) -> Optional[Dict[str, Any]]:
    """Get discount tier configuration for a script type.

    Args:
        script_type: Script type identifier

    Returns:
        Discount tiers dict or None if not applicable

    Example:
        >>> tiers = get_discount_tiers('prelegal_150')
        >>> print(tiers['210_plus']['tier1']['percentage'])
        60
    """

def get_campaign_deadline(
    tier: int,
    script_type: str = "recently_suspended_120"
) -> date:
    """Get campaign deadline for a script with deadline configuration.

    Args:
        tier: Campaign tier (1 or 2)
        script_type: Script type to get deadline configuration from

    Returns:
        Campaign deadline date

    Example:
        >>> deadline = get_campaign_deadline(tier=1)
        >>> print(deadline)
        2025-01-25
    """
```

### Module: `business_rules/discount_calculator.py`

```python
def calculate_discount(
    balance: float,
    script_type: str,
    payment_type: str,
    overdue_days: Optional[int] = None
) -> float:
    """Calculate discount amount based on business rules.

    Args:
        balance: Outstanding balance amount
        script_type: Script type identifier
        payment_type: 'settlement' or 'installment'
        overdue_days: Days overdue (required for tiered discounts)

    Returns:
        Discount amount in Rands

    Raises:
        ValueError: If script_type unknown or discount not applicable

    Example:
        >>> discount = calculate_discount(
        ...     balance=5000.0,
        ...     script_type='prelegal_150',
        ...     payment_type='settlement',
        ...     overdue_days=210
        ... )
        >>> print(discount)
        3500.0  # 70% discount
    """

def calculate_installment_schedule(
    balance: float,
    num_payments: int,
    start_date: str,
    salary_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Calculate installment payment schedule.

    Args:
        balance: Total balance to be paid
        num_payments: Number of installment payments
        start_date: Start date (ISO format YYYY-MM-DD)
        salary_date: Day of month for salary (1-31)

    Returns:
        List of payment dictionaries with date and amount

    Example:
        >>> schedule = calculate_installment_schedule(
        ...     balance=3000.0,
        ...     num_payments=3,
        ...     start_date='2025-01-15',
        ...     salary_date='25'
        ... )
        >>> print(schedule[0])
        {'payment_number': 1, 'date': '2025-01-25', 'amount': 1000.0}
    """
```

---

## Utility Functions API

### Module: `utils/fuzzy_match.py`

```python
def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching.

    Args:
        text: Input text

    Returns:
        Normalized text (lowercase, stripped, no extra spaces)

    Example:
        >>> normalize_text("  HELLO   World  ")
        'hello world'
    """

def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance (number of edits to transform s1 to s2)

    Example:
        >>> levenshtein_distance("kitten", "sitting")
        3
    """

def similarity_score(s1: str, s2: str) -> float:
    """Calculate similarity score (0.0-1.0) between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score (1.0 = identical, 0.0 = completely different)

    Example:
        >>> similarity_score("hello", "hallo")
        0.8
    """

def fuzzy_match_field(
    user_input: str,
    expected_value: str,
    threshold: float = 0.8
) -> bool:
    """Check if user input matches expected value using fuzzy matching.

    Args:
        user_input: User's spoken input
        expected_value: Expected correct value
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        True if similarity >= threshold

    Example:
        >>> fuzzy_match_field("oh eight five oh one", "0850123456")
        True
    """
```

### Module: `utils/spoken_digits.py`

```python
def normalize_spoken_digits(text: str) -> str:
    """Normalize spoken digits to numeric form.

    Converts:
    - "oh" -> "0"
    - "zero" -> "0"
    - "one" through "nine" -> "1" through "9"

    Args:
        text: Input text with spoken digits

    Returns:
        Text with spoken digits converted to numeric

    Example:
        >>> normalize_spoken_digits("oh eight five oh one")
        '0 8 5 0 1'
    """

def extract_digits(text: str) -> str:
    """Extract only digits from text.

    Args:
        text: Input text

    Returns:
        String containing only digits

    Example:
        >>> extract_digits("My ID is 850112-5678-901")
        '8501125678901'
    """
```

### Module: `utils/date_parser.py`

```python
def parse_callback_datetime(user_input: str) -> Optional[datetime]:
    """Parse user's callback datetime input.

    Supports formats:
    - ISO format: "2025-01-15T14:00:00"
    - Natural language: "tomorrow at 2pm", "next Monday at 10am"

    Args:
        user_input: User's datetime input

    Returns:
        Parsed datetime or None if invalid

    Example:
        >>> dt = parse_callback_datetime("2025-01-15T14:00:00")
        >>> print(dt)
        2025-01-15 14:00:00
    """

def is_business_hours(dt: datetime) -> bool:
    """Check if datetime falls within business hours.

    Business hours: Mon-Sat 07:00-18:00 SAST

    Args:
        dt: Datetime to check

    Returns:
        True if within business hours

    Example:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 1, 15, 14, 0)  # Wed 2pm
        >>> is_business_hours(dt)
        True
    """

def format_business_hours_message() -> str:
    """Get formatted business hours message.

    Returns:
        Business hours description string

    Example:
        >>> print(format_business_hours_message())
        'Monday to Saturday, 07:00 to 18:00'
    """
```

---

## Configuration API

### Module: `sub_agents/base_agent.py`

#### Configuration Functions

```python
def load_config() -> dict:
    """Load agent configuration from agent.yaml.

    Returns:
        Configuration dictionary

    Example:
        >>> config = load_config()
        >>> print(config['id'])
        'debt_collection'
    """

def get_agent_id() -> str:
    """Get agent ID from config.

    Returns:
        Agent ID string

    Example:
        >>> agent_id = get_agent_id()
        >>> print(agent_id)
        'debt_collection'
    """

def get_sub_agent_config(agent_id: str) -> dict:
    """Get configuration for a specific sub-agent.

    Args:
        agent_id: ID of the sub-agent

    Returns:
        Sub-agent configuration dictionary

    Example:
        >>> config = get_sub_agent_config('verification')
        >>> print(config['name'])
        'Verification Agent'
    """

def get_instructions(
    agent_id: str,
    userdata: Optional[UserData] = None
) -> str:
    """Get instructions for a specific agent.

    Supports three sources:
    1. Inline string in YAML
    2. Path to .yaml file
    3. Python function (starts with 'func:')

    Args:
        agent_id: ID of the agent
        userdata: Optional UserData for dynamic prompts

    Returns:
        Fully formatted instructions string

    Example:
        >>> instructions = get_instructions('verification', userdata)
        >>> print(instructions[:50])
        'You are the Verification Agent...'
    """

def get_agent_tools(agent_id: str) -> list:
    """Get tools list for a specific agent from config.

    Args:
        agent_id: ID of the agent

    Returns:
        List of tool functions

    Example:
        >>> tools = get_agent_tools('verification')
        >>> print([t.__name__ for t in tools])
        ['verify_field', 'mark_unavailable', 'schedule_callback']
    """

def get_llm_config() -> dict:
    """Get LLM configuration from config.

    Returns:
        Dict containing LLM model, temperature, and settings

    Example:
        >>> llm_config = get_llm_config()
        >>> print(llm_config)
        {'provider': 'openai', 'model': 'gpt-4o-mini', 'temperature': 0.7}
    """
```

#### TTS Configuration

```python
def get_tts(agent_type: Optional[str] = None) -> Any:
    """Get TTS instance for the configured provider.

    Args:
        agent_type: Agent type to get voice for (optional)

    Returns:
        TTS instance configured for the specified agent type

    Example:
        >>> tts = get_tts('verification')
        >>> # Returns Cartesia TTS with verification agent voice
    """
```

**TTS Configuration Constants:**

```python
TTS_PROVIDER: str
"""Currently configured TTS provider ('cartesia', 'chatterbox', 'kokoro', 'supertonic')"""

TTS_CONFIG: Dict[str, Any]
"""TTS configuration for all providers including voice IDs per agent type"""
```

### Module: `prompts/__init__.py`

#### Prompt Functions

```python
def load_base_prompt(filename: str) -> str:
    """Load base prompt from YAML file.

    Args:
        filename: YAML filename (e.g., 'prompt01_introduction.yaml')

    Returns:
        Prompt string from file

    Example:
        >>> prompt = load_base_prompt('prompt01_introduction.yaml')
        >>> print(prompt[:50])
        'You are the Introduction Agent...'
    """

def sanitize_for_prompt(value: Any, max_length: int = 200) -> str:
    """Sanitize value for prompt injection prevention.

    Args:
        value: Value to sanitize
        max_length: Maximum length to truncate to

    Returns:
        Sanitized string

    Example:
        >>> sanitized = sanitize_for_prompt("Hello\x00World\n\n\n", max_length=10)
        >>> print(sanitized)
        'Hello Worl...'
    """

def get_negotiation_prompt(
    userdata: UserData,
    variables: dict
) -> str:
    """Generate dynamic negotiation prompt.

    Args:
        userdata: Session user data
        variables: Configuration variables

    Returns:
        Complete negotiation prompt with script-specific context

    Example:
        >>> prompt = get_negotiation_prompt(userdata, variables)
        >>> # Returns prompt customized for script type and debtor
    """

def get_payment_prompt(
    userdata: UserData,
    variables: dict
) -> str:
    """Generate dynamic payment prompt.

    Args:
        userdata: Session user data
        variables: Configuration variables

    Returns:
        Complete payment prompt with bank validation warnings

    Example:
        >>> prompt = get_payment_prompt(userdata, variables)
        >>> # Returns prompt with reversal history warnings if applicable
    """
```

---

## Error Handling

### Common Exceptions

```python
class ValidationError(Exception):
    """Raised when input validation fails."""

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""

class StateError(Exception):
    """Raised when call state is inconsistent."""
```

### Error Handling Pattern

```python
try:
    result = await some_tool(ctx, param1, param2)
except ValueError as e:
    logger.error(f"Invalid parameter: {e}", exc_info=True)
    return f"I'm sorry, there was an issue with the information provided: {e}"
except ValidationError as e:
    logger.warning(f"Validation failed: {e}")
    return f"I couldn't validate that information: {e}"
except Exception as e:
    logger.critical(f"Unexpected error: {e}", exc_info=True)
    return "I'm sorry, an unexpected error occurred. Let me transfer you to a supervisor."
```

---

## Type Aliases

```python
from typing import TYPE_CHECKING
from livekit.agents.voice import RunContext

if TYPE_CHECKING:
    from shared_state import UserData

RunContext_T = RunContext[UserData]
"""Type alias for RunContext with UserData"""
```

---

## Constants

### Agent IDs

```python
INTRODUCTION = "introduction"
VERIFICATION = "verification"
NEGOTIATION = "negotiation"
PAYMENT = "payment"
CLOSING = "closing"
```

### Configuration Constants

```python
MAX_TOOL_STEPS = 5
"""Maximum number of tool execution steps per turn"""

SYNC_TRANSCRIPTION = True
"""Whether to synchronize transcription with audio"""

CHAT_CONTEXT_MAX_ITEMS = 6
"""Maximum items from previous agent to include in handoff"""

DEFAULT_PORT = 8083
"""Default port for agent server"""
```

---

## Complete Example Usage

```python
from livekit.agents import AgentServer, JobContext
from shared_state import DebtorProfile, CallState, UserData
from sub_agents import IntroductionAgent, get_tts
from tools import confirm_person

# Initialize server
server = AgentServer(port=8083)

@server.rtc_session(agent_name="debt_collection")
async def entrypoint(ctx: JobContext):
    # Create debtor profile
    debtor = DebtorProfile(
        full_name="John Smith",
        user_id="12345",
        username="jsmith",
        outstanding_amount=5000.0,
        overdue_days=45
    )

    # Create call state
    call_state = CallState(
        script_type="ratio1_inflow",
        authority="Cartrack Accounts Department",
        authority_contact="011-250-3000"
    )

    # Create user data
    userdata = UserData(debtor=debtor, call=call_state)

    # Initialize agent
    intro_agent = IntroductionAgent(tts=get_tts("introduction"))

    # Start session (simplified for example)
    # In reality, use AgentSession with full configuration
    await intro_agent.on_enter()
```
