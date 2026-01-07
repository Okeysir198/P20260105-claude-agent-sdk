"""Generic userdata handling via dataclass introspection.

Provides utilities for applying test data overrides and building template
variables from any dataclass-based UserData structure without hardcoded
field names.
"""

from dataclasses import fields as dataclass_fields, replace, is_dataclass
from typing import Any, Optional


def _is_frozen_dataclass(obj: Any) -> bool:
    """Check if an object is a frozen dataclass instance."""
    if not is_dataclass(obj) or isinstance(obj, type):
        return False
    # The frozen flag is stored in __dataclass_params__ (Python 3.10+)
    # or we can try to set an attribute and catch FrozenInstanceError
    params = getattr(obj, '__dataclass_params__', None)
    if params is not None:
        return getattr(params, 'frozen', False)
    # Fallback: try to detect by attempting assignment
    try:
        # Get first field name
        if not obj.__dataclass_fields__:
            return False
        first_field = next(iter(obj.__dataclass_fields__))
        current_value = getattr(obj, first_field)
        object.__setattr__(obj, first_field, current_value)
        return False
    except Exception:
        return True


def apply_test_data_overrides(userdata: Any, test_data: dict) -> None:
    """Apply test-specific data overrides using generic introspection.

    Works with any dataclass structure without hardcoded field names.
    Handles both frozen (via dataclasses.replace) and mutable dataclasses.

    Supports two naming patterns in test_data:
    1. Direct field names matching nested dataclass fields (e.g., "full_name")
    2. Prefixed names for explicit targeting (e.g., "debtor_full_name" for debtor.full_name)

    Args:
        userdata: The userdata object to modify (typically a dataclass)
        test_data: Dictionary of field overrides to apply
    """
    if not test_data or not is_dataclass(userdata):
        return

    # Get userdata field info
    userdata_fields = {f.name: f for f in dataclass_fields(userdata)}

    for field_name, field_info in userdata_fields.items():
        field_value = getattr(userdata, field_name, None)

        # Skip None values and non-dataclass fields
        if field_value is None or not is_dataclass(field_value):
            continue

        # Get valid field names for this nested dataclass
        nested_fields = {f.name for f in dataclass_fields(field_value)}

        # Collect updates for this nested dataclass from test_data
        # Match both "field_name" and "prefix_field_name" patterns
        updates = {}
        for key, value in test_data.items():
            # Direct match (e.g., "full_name" in debtor)
            if key in nested_fields:
                updates[key] = value
            # Prefixed match (e.g., "debtor_full_name" -> "full_name")
            elif key.startswith(f"{field_name}_"):
                nested_key = key[len(field_name) + 1:]
                if nested_key in nested_fields:
                    updates[nested_key] = value

        if not updates:
            continue

        # Apply updates based on whether dataclass is frozen or mutable
        if _is_frozen_dataclass(field_value):
            # Frozen: use dataclasses.replace() and reassign
            setattr(userdata, field_name, replace(field_value, **updates))
        else:
            # Mutable: set attributes directly
            for key, value in updates.items():
                setattr(field_value, key, value)

    # Also handle top-level userdata fields directly
    for key, value in test_data.items():
        if key in userdata_fields and not is_dataclass(getattr(userdata, key, None)):
            try:
                setattr(userdata, key, value)
            except (AttributeError, TypeError):
                # Skip frozen or read-only fields
                pass


def build_template_variables(userdata: Any = None, config: Optional[dict] = None) -> dict:
    """Build template variables from userdata via generic introspection.

    Flattens nested dataclasses with underscore prefix for template substitution.
    Only includes primitive types (str, int, float, bool).

    Args:
        userdata: Optional userdata object (typically a dataclass)
        config: Optional config dict with 'variables' key

    Returns:
        Dictionary of {variable_name: value} for template substitution
    """
    variables = {}

    # Add config variables first (can be overridden by userdata)
    if config:
        variables.update(config.get("variables", {}))

    if userdata is None:
        return variables

    # Generic introspection - works with any dataclass or object
    for attr_name in dir(userdata):
        if attr_name.startswith('_'):
            continue

        try:
            value = getattr(userdata, attr_name, None)
        except Exception:
            continue

        # Skip methods and callables
        if callable(value):
            continue

        # Handle primitive types directly
        if isinstance(value, (str, int, float, bool)):
            variables[attr_name] = value
        # Handle nested dataclasses - flatten with prefix
        elif is_dataclass(value) and not isinstance(value, type):
            for field in dataclass_fields(value):
                nested_attr = field.name
                try:
                    nested_val = getattr(value, nested_attr, None)
                    if isinstance(nested_val, (str, int, float, bool)):
                        variables[f"{attr_name}_{nested_attr}"] = nested_val
                except Exception:
                    continue

    return variables
