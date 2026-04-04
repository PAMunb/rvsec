"""
Property-based tests for the coordinate_extractor service using Hypothesis.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from rv_agent.services import coordinate_extractor

# --- Strategies for generating coordinates and bounds ---

# Strategy for a single coordinate value
coord_val = st.integers(min_value=0, max_value=2000)

# Strategy for a bounds string like "[x1,y1][x2,y2]"
bounds_strategy = st.tuples(coord_val, coord_val, coord_val, coord_val).map(
    lambda t: f"[{t[0]},{t[1]}][{t[2]},{t[3]}]"
)


@pytest.mark.hypothesis
class TestCoordinateExtractorHypothesis:
    """Property-based tests for coordinate extraction and validation."""

    @given(x1=coord_val, y1=coord_val, x2=coord_val, y2=coord_val)
    def test_parse_bounds_to_center(self, x1, y1, x2, y2):
        """Tests that parse_bounds_to_center correctly calculates the center."""
        bounds_str = f"[{x1},{y1}][{x2},{y2}]"
        center = coordinate_extractor.parse_bounds_to_center(bounds_str)

        expected_x = (x1 + x2) // 2
        expected_y = (y1 + y2) // 2

        assert center == (expected_x, expected_y)

    @given(bounds_str=st.text().filter(lambda s: "[" not in s))
    def test_parse_bounds_to_center_invalid_format(self, bounds_str):
        """Tests that invalid bound strings return None."""
        assert coordinate_extractor.parse_bounds_to_center(bounds_str) is None

    @given(
        gen_x=coord_val,
        gen_y=coord_val,
        tolerance=st.integers(min_value=1, max_value=100),
    )
    def test_validate_with_tolerance(self, gen_x, gen_y, tolerance):
        """
        Tests the distance calculation in validate_with_tolerance.
        - A point should be valid against itself.
        - A point just inside tolerance should be valid.
        - A point just outside tolerance should be invalid.
        """
        generated_point = (gen_x, gen_y)

        # 1. Test against itself
        ground_truth_self = [generated_point]
        assert (
            coordinate_extractor.validate_with_tolerance(
                generated_point, ground_truth_self, tolerance
            )
            is True
        )

        # 2. Test a point just inside the tolerance boundary
        # Create a point on the x-axis at the edge of the tolerance circle
        point_inside = (gen_x + tolerance, gen_y)
        ground_truth_edge = [(gen_x, gen_y)]
        assert (
            coordinate_extractor.validate_with_tolerance(
                point_inside, ground_truth_edge, tolerance
            )
            is True
        )

        # 3. Test a point just outside the tolerance boundary
        point_outside = (gen_x + tolerance + 1, gen_y)
        assert (
            coordinate_extractor.validate_with_tolerance(
                point_outside, ground_truth_edge, tolerance
            )
            is False
        )

    @given(
        elements=st.lists(
            st.fixed_dictionaries(
                {
                    "description": st.text(
                        alphabet=st.characters(blacklist_characters="\n"), max_size=50
                    )
                }
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_create_enhanced_description_format(self, elements):
        """Tests that the description format is a correct numbered list."""
        result = coordinate_extractor.create_enhanced_description_format(elements)

        lines = result.split("\n")
        assert len(lines) == len(elements)

        for i, line in enumerate(lines):
            assert line.startswith(f"{i + 1}. ")
            assert elements[i]["description"] in line

    def test_create_enhanced_description_format_empty(self):
        """Tests that an empty list of elements returns the correct message."""
        result = coordinate_extractor.create_enhanced_description_format([])
        assert result == "No interactive elements found."


# --- Strategies for XML generation ---

# Strategy for text that is safe to include in an XML attribute
safe_xml_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters='<>"&',  # Characters that would break XML attributes
    ),
    max_size=20,
)

# Strategy for individual attributes
text_attr = safe_xml_text
class_name_attr = st.text(
    alphabet=st.characters(whitelist_categories=("L",)), min_size=1, max_size=10
).map(lambda s: f"android.widget.{s}")
resource_id_attr = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")), min_size=1, max_size=20
).map(lambda s: f"com.example.app:id/{s}")

# Strategy to build a single XML node string
node_strategy = (
    st.fixed_dictionaries(
        {
            "clickable": st.booleans(),
            "bounds": bounds_strategy,
            "text": text_attr,
            "content-desc": text_attr,
            "resource-id": resource_id_attr,
            "class": class_name_attr,
        }
    )
    .map(
        # Convert boolean 'clickable' to lowercase 'true'/'false' string for XML
        lambda d: {**d, "clickable": str(d["clickable"]).lower()}
    )
    .map(lambda d: " ".join(f'{k}="{v}"' for k, v in d.items() if v is not None))
    .map(lambda attrs: f"<node {attrs} />")
)


class TestXmlExtractionHypothesis:
    """Property-based tests for XML extraction."""

    @given(nodes=st.lists(node_strategy, min_size=0, max_size=10))
    def test_extract_clickable_elements_with_coords_count(self, nodes):
        """Tests that the number of extracted elements matches the number of clickable nodes."""
        xml_content = f'<root>{"".join(nodes)}</root>'

        # Count how many generated nodes are actually clickable
        expected_count = sum(1 for node_str in nodes if 'clickable="true"' in node_str)

        elements = coordinate_extractor.extract_clickable_elements_with_coords(
            xml_content
        )

        assert len(elements) == expected_count

    @given(
        text=text_attr,
        desc=text_attr,
        res_id=resource_id_attr,
        cls=class_name_attr,
        bounds=bounds_strategy,
    )
    def test_description_format(self, text, desc, res_id, cls, bounds):
        """Tests that the enhanced description is formatted correctly."""
        xml_content = f"""<root>
            <node clickable="true" bounds="{bounds}" text="{text}" content-desc="{desc}" resource-id="{res_id}" class="{cls}" />
        </root>"""

        elements = coordinate_extractor.extract_clickable_elements_with_coords(
            xml_content
        )

        assert len(elements) == 1
        description = elements[0]["description"]

        if text:
            assert f'"{text}"' in description
        if desc:
            assert f'desc:"{desc}"' in description
        # resource_id is no longer included in description (LLM uses coordinates)
        if cls:
            assert cls.split(".")[-1] in description

        assert "at position (" in description
