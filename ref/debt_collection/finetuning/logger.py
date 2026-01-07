"""Conversation sample logging for fine-tuning datasets.

Enable with: ENABLE_FINETUNING_LOG=true
Output: finetuning/samples/YYYY-MM-DD.jsonl

Usage:
    from finetuning import log_sample, ConversationSample

    sample = ConversationSample(
        timestamp=datetime.now().isoformat(),
        prompt_version="v1",
        agent_id="introduction",
        user_input="Yes, speaking",
        agent_response="Thank you for confirming...",
        tools_called=["confirm_person"],
        outcome="success"
    )
    log_sample(sample)
"""
import os
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional

ENABLED = os.getenv("ENABLE_FINETUNING_LOG", "false").lower() == "true"
SAMPLES_DIR = Path(__file__).parent / "samples"


@dataclass
class ConversationSample:
    """Single conversation turn for fine-tuning."""
    timestamp: str
    prompt_version: str
    agent_id: str
    user_input: str
    agent_response: str
    tools_called: list[str]
    outcome: str  # "success", "failure", "unclear"
    metadata: Optional[dict] = field(default_factory=dict)


def log_sample(sample: ConversationSample) -> None:
    """Append sample to daily JSONL file (no-op if disabled)."""
    if not ENABLED:
        return

    SAMPLES_DIR.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = SAMPLES_DIR / f"{date_str}.jsonl"

    with open(file_path, "a") as f:
        f.write(json.dumps(asdict(sample)) + "\n")


def get_sample_count() -> int:
    """Count total samples logged."""
    if not SAMPLES_DIR.exists():
        return 0
    count = 0
    for f in SAMPLES_DIR.glob("*.jsonl"):
        with open(f) as fp:
            count += sum(1 for _ in fp)
    return count


def is_logging_enabled() -> bool:
    """Check if fine-tuning logging is enabled."""
    return ENABLED
