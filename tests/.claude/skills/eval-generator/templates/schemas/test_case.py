"""Pydantic models for test case schema validation.

Provides STRICT validation for test case YAML files.
All assertion types use canonical snake_case format.
"""

from enum import Enum
from typing import Optional, Union, Any
from pydantic import BaseModel, Field, model_validator, field_validator


class AssertionType(str, Enum):
    """Canonical assertion types (snake_case only)."""
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    CONTAINS_ANY = "contains_any"
    CONTAINS_ALL = "contains_all"
    EQUALS = "equals"
    MATCHES = "matches"
    CONTAINS_FUNCTION_CALL = "contains_function_call"
    LLM_RUBRIC = "llm_rubric"

    @classmethod
    def normalize(cls, value: str) -> "AssertionType":
        """Normalize hyphenated to snake_case and return enum.

        Raises:
            ValueError: If the assertion type is unknown.
        """
        normalized = value.replace("-", "_").lower()
        try:
            return cls(normalized)
        except ValueError:
            valid_types = [t.value for t in cls]
            raise ValueError(
                f"Unknown assertion type: '{value}'. "
                f"Valid types: {valid_types}"
            )


class Assertion(BaseModel):
    """A single assertion to validate against agent response."""
    type: str
    value: Optional[Union[str, list[str]]] = None
    rubric: Optional[str] = None  # For llm_rubric type
    model: Optional[str] = None   # LLM model for llm_rubric

    @field_validator("type")
    @classmethod
    def validate_and_normalize_type(cls, v: str) -> str:
        """Validate and normalize assertion type to snake_case."""
        # Normalize and validate - will raise ValueError if invalid
        normalized_type = AssertionType.normalize(v)
        return normalized_type.value

    @model_validator(mode="after")
    def validate_assertion_requirements(self) -> "Assertion":
        """Validate that required fields exist for each assertion type."""
        assertion_type = self.type

        # contains_function_call requires value
        if assertion_type == AssertionType.CONTAINS_FUNCTION_CALL.value:
            if not self.value:
                raise ValueError(
                    "contains_function_call assertion requires 'value' "
                    "specifying the function name"
                )

        # llm_rubric requires rubric or value
        if assertion_type == AssertionType.LLM_RUBRIC.value:
            if not self.rubric and not self.value:
                raise ValueError(
                    "llm_rubric assertion requires 'rubric' or 'value' "
                    "specifying the evaluation criteria"
                )

        # contains, equals, matches require value
        if assertion_type in (
            AssertionType.CONTAINS.value,
            AssertionType.NOT_CONTAINS.value,
            AssertionType.CONTAINS_ANY.value,
            AssertionType.CONTAINS_ALL.value,
            AssertionType.EQUALS.value,
            AssertionType.MATCHES.value,
        ):
            if self.value is None:
                raise ValueError(
                    f"{assertion_type} assertion requires 'value'"
                )

        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        result: dict[str, Any] = {"type": self.type}
        if self.value is not None:
            result["value"] = self.value
        if self.rubric is not None:
            result["rubric"] = self.rubric
        if self.model is not None:
            result["model"] = self.model
        return result


class Turn(BaseModel):
    """A single conversation turn in a test case."""
    user_input: str = Field(..., min_length=1)
    assertions: list[Assertion] = Field(default_factory=list)
    expected_agent: Optional[str] = None  # Expected agent after this turn

    @field_validator("user_input")
    @classmethod
    def validate_user_input(cls, v: str) -> str:
        """Ensure user_input is not empty."""
        if not v.strip():
            raise ValueError("user_input cannot be empty or whitespace only")
        return v


class TestCase(BaseModel):
    """A complete test case with turns and metadata."""
    name: str = Field(..., min_length=1)
    turns: list[Turn] = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    test_type: Optional[str] = None
    description: Optional[str] = None
    test_data: Optional[dict[str, Any]] = None
    start_agent: Optional[str] = None
    max_turns: Optional[int] = None

    # Internal metadata fields (added during loading)
    _source_file: Optional[str] = None
    _agent_id: Optional[str] = None
    _sub_agent_id: Optional[str] = None
    _default_test_data: Optional[dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty."""
        if not v.strip():
            raise ValueError("Test case name cannot be empty")
        return v

    @field_validator("turns")
    @classmethod
    def validate_turns(cls, v: list[Turn]) -> list[Turn]:
        """Ensure at least one turn exists."""
        if not v:
            raise ValueError("Test case must have at least one turn")
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        result: dict[str, Any] = {
            "name": self.name,
            "turns": [
                {
                    "user_input": t.user_input,
                    "assertions": [a.to_dict() for a in t.assertions],
                    **({"expected_agent": t.expected_agent} if t.expected_agent else {})
                }
                for t in self.turns
            ],
        }

        if self.tags:
            result["tags"] = self.tags
        if self.test_type:
            result["test_type"] = self.test_type
        if self.description:
            result["description"] = self.description
        if self.test_data:
            result["test_data"] = self.test_data
        if self.start_agent:
            result["start_agent"] = self.start_agent
        if self.max_turns:
            result["max_turns"] = self.max_turns

        return result


class TestCaseFile(BaseModel):
    """Schema for a test case YAML file."""
    agent_id: str = Field(default="default")
    sub_agent_id: Optional[str] = None
    description: Optional[str] = None
    default_test_data: Optional[dict[str, Any]] = None
    test_cases: list[TestCase] = Field(..., min_length=1)

    @field_validator("test_cases")
    @classmethod
    def validate_test_cases(cls, v: list[TestCase]) -> list[TestCase]:
        """Ensure at least one test case exists."""
        if not v:
            raise ValueError("Test file must have at least one test case")
        return v


class TestCaseValidationError(Exception):
    """Raised when test case validation fails in STRICT mode."""

    def __init__(self, file_path: str, errors: list[str]):
        self.file_path = file_path
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with file path and all errors."""
        error_list = "\n  - ".join(self.errors)
        return f"Invalid test file '{self.file_path}':\n  - {error_list}"


def validate_test_file(raw: dict, file_path: str = "<unknown>") -> TestCaseFile:
    """Validate raw YAML dict against schema with STRICT mode.

    Args:
        raw: Raw dictionary from YAML parsing
        file_path: Path to the file (for error messages)

    Returns:
        Validated TestCaseFile instance

    Raises:
        TestCaseValidationError: If validation fails
    """
    from pydantic import ValidationError

    try:
        return TestCaseFile.model_validate(raw)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        raise TestCaseValidationError(file_path, errors)


def validate_assertion_type(type_str: str) -> str:
    """Validate and normalize an assertion type string.

    Args:
        type_str: The assertion type (may use hyphens or underscores)

    Returns:
        Normalized assertion type in snake_case

    Raises:
        ValueError: If the assertion type is unknown
    """
    return AssertionType.normalize(type_str).value
