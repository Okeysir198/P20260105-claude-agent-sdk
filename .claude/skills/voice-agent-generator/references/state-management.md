# State Management Patterns

Reference patterns for voice agent state management.

> **IMPORTANT**: When using Optional fields in state, always check for None
> before performing comparisons. For example:
> ```python
> def is_complete(self) -> bool:
>     if self.count is None:  # Check None first!
>         return False
>     return 1 <= self.count <= 10  # Now safe to compare
> ```

## State Architecture Overview

```
UserData (container)
├── profile: Profile (frozen=True, immutable)
├── session: SessionState (mutable call state)
├── agents: Dict[str, Agent] (agent instances)
├── prev_agent: Optional[Agent] (for context transfer)
└── metadata fields (session_id, job_context, etc.)
```

## UserData Container

The main container aggregates all state:

```python
# shared_state.py

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

from state import Profile, SessionState

if TYPE_CHECKING:
    from livekit.agents import Agent

@dataclass
class UserData:
    """
    Main session state container for voice agent calls.

    Aggregates profile, session state, and agent tracking.
    """

    profile: Profile
    session: SessionState = field(default_factory=SessionState)
    agents: Dict[str, "Agent"] = field(default_factory=dict)
    prev_agent: Optional["Agent"] = None

    # Metadata
    session_id: Optional[str] = None
    call_start_time: Optional[str] = None
    current_agent_id: Optional[str] = None
    job_context: Optional[Any] = None

    def summarize(self) -> str:
        """Generate text summary for agent context."""
        lines = [
            f"Session: {self.session_id or 'N/A'}",
            "",
            f"Profile: {self.profile.full_name}",
        ]

        # Add relevant profile fields
        if self.profile.email:
            lines.append(f"  Email: {self.profile.email}")

        # Add session progress
        progress = self.session.get_progress()
        lines.extend([
            "",
            "Progress:",
            f"  Step 1: {'done' if progress['step1'] else 'pending'}",
            f"  Step 2: {'done' if progress['step2'] else 'pending'}",
        ])

        return "\n".join(lines)

    def cleanup(self) -> None:
        """Clean up resources at end of call."""
        self.agents.clear()
        self.prev_agent = None
        self.job_context = None
```

## Profile (Immutable)

Use `frozen=True` for data that should not change during call:

```python
# state/profile.py

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Profile:
    """
    Immutable profile loaded from job metadata.

    Contains customer/user information for the call.
    """

    # Required fields
    full_name: str
    user_id: str

    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

    # Domain-specific fields
    account_number: Optional[str] = None
    account_status: str = "active"
    balance: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.full_name or not self.full_name.strip():
            raise ValueError("Full name is required")
        if not self.user_id or not self.user_id.strip():
            raise ValueError("User ID is required")

    @classmethod
    def from_metadata(cls, metadata: Dict[str, Any]) -> "Profile":
        """Create Profile from job metadata dictionary."""
        defaults = {
            "full_name": "",
            "user_id": "",
            "account_status": "active",
        }
        return cls(**{**defaults, **metadata})

    def format_balance(self) -> str:
        """Format balance as currency string."""
        if self.balance is None:
            return "N/A"
        return f"${self.balance:,.2f}"
```

## SessionState (Mutable)

Track call progression and mutable state:

```python
# state/session.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .types import CallOutcome, PersonType


@dataclass
class SessionState:
    """
    Mutable state tracking call progression.

    Maintains current state including completed steps,
    verification status, and collected information.
    """

    # Phase tracking
    current_phase: str = "introduction"
    person_confirmed: bool = False
    person_type: Optional[PersonType] = None

    # Verification
    identity_verified: bool = False
    verified_fields: Set[str] = field(default_factory=set)
    verification_attempts: int = 0

    # Domain-specific state
    # (Add fields relevant to your agent's workflow)
    request_type: Optional[str] = None
    request_details: Optional[str] = None
    request_fulfilled: bool = False

    # Callback management
    callback_scheduled: bool = False
    callback_datetime: Optional[str] = None
    callback_reason: Optional[str] = None

    # Call outcome
    call_outcome: Optional[CallOutcome] = None
    call_notes: List[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        """Append timestamped note to call notes."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.call_notes.append(f"[{timestamp}] {note}")

    def mark_verified(self, field_name: str) -> None:
        """Mark a field as successfully verified."""
        self.verified_fields.add(field_name)
        self.verification_attempts += 1

    def is_phase_complete(self, phase: str) -> bool:
        """Check if a specific phase is complete."""
        checks = {
            "introduction": self.person_confirmed,
            "verification": self.identity_verified,
            "main": self.request_fulfilled,
            "closing": self.call_outcome is not None,
        }
        return checks.get(phase, False)

    def get_progress(self) -> Dict[str, bool]:
        """Get completion status of each phase."""
        return {
            "introduction": self.is_phase_complete("introduction"),
            "verification": self.is_phase_complete("verification"),
            "main": self.is_phase_complete("main"),
            "closing": self.is_phase_complete("closing"),
        }
```

## Types (Enums)

Define enumerated types for constrained values:

```python
# state/types.py

from enum import Enum


class PersonType(Enum):
    """Type of person answering the call."""
    CORRECT = "correct"
    WRONG = "wrong"
    THIRD_PARTY = "third_party"


class CallOutcome(Enum):
    """Final outcome of a call."""
    SUCCESS = "success"
    CALLBACK = "callback"
    ESCALATION = "escalation"
    REFUSAL = "refusal"
    DISCONNECTED = "disconnected"


class VerificationStatus(Enum):
    """Identity verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class RequestStatus(Enum):
    """Status of customer request."""
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

## State Package Init

Export types from state package:

```python
# state/__init__.py

from .types import (
    PersonType,
    CallOutcome,
    VerificationStatus,
    RequestStatus,
)
from .profile import Profile
from .session import SessionState

__all__ = [
    # Types
    "PersonType",
    "CallOutcome",
    "VerificationStatus",
    "RequestStatus",
    # Classes
    "Profile",
    "SessionState",
]
```

## Test Data Factory

Create test data for development:

```python
# shared_state.py (continued)

def get_test_profile_data() -> Dict[str, Any]:
    """Default test profile for local development."""
    return {
        "full_name": "John Smith",
        "user_id": "12345",
        "email": "john.smith@example.com",
        "phone": "555-123-4567",
        "account_number": "ACC-001",
        "account_status": "active",
        "balance": 150.00,
    }


def create_test_userdata() -> UserData:
    """Create test UserData instance for eval framework."""
    data = get_test_profile_data()
    profile = Profile.from_metadata(data)
    return UserData(profile=profile)
```

## State Access in Tools

Access state via RunContext:

```python
from livekit.agents.voice import RunContext
from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def my_tool(context: RunContext_T) -> str:
    """Example tool accessing state."""
    userdata = context.userdata

    # Read immutable profile
    name = userdata.profile.full_name
    balance = userdata.profile.balance

    # Update mutable session state
    userdata.session.request_type = "inquiry"
    userdata.session.add_note("Customer inquired about balance")

    # Check progress
    if userdata.session.identity_verified:
        return f"{name}, your balance is {userdata.profile.format_balance()}."

    return "Please verify your identity first."
```

## State Access in Agents

Access state via self.session:

```python
class MyAgent(Agent):
    async def on_enter(self) -> None:
        """Access state on agent activation."""
        userdata: UserData = self.session.userdata

        # Read state for context
        summary = userdata.summarize()

        # Update chat context with state
        chat_ctx = self.chat_ctx.copy()
        chat_ctx.add_message(
            role="system",
            content=f"Current state:\n{summary}",
        )
        await self.update_chat_ctx(chat_ctx)
```
