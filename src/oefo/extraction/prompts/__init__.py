"""
Prompt templates for financial document extraction.

Provides source-type specific prompts for Claude Vision API extraction.
"""

from typing import Optional


def get_prompt(source_type: str, language: Optional[str] = None) -> str:
    """
    Get extraction prompt for the specified source type.

    Args:
        source_type: Type of document ('regulatory', 'dfi', 'corporate', 'bond').
        language: Optional language code for multilingual handling.

    Returns:
        Extraction prompt string.

    Raises:
        ValueError: If source_type is not recognized.
    """
    if source_type == "regulatory":
        from . import regulatory
        return regulatory.get_prompt(language)

    elif source_type == "dfi":
        from . import dfi
        return dfi.get_prompt(language)

    elif source_type == "corporate":
        from . import corporate
        return corporate.get_prompt(language)

    elif source_type == "bond":
        from . import bond
        return bond.get_prompt(language)

    else:
        raise ValueError(
            f"Unknown source_type: {source_type}. "
            f"Supported: 'regulatory', 'dfi', 'corporate', 'bond'"
        )


__all__ = [
    "get_prompt",
]
