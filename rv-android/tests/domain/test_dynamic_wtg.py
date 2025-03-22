from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import networkx as nx
import pytest

from rvandroid.domain.dynamic_wtg import DynamicTransition, ActivityNode, DynamicTransitionGraph


class TestDynamicTransition:
    """Tests for the DynamicTransition class"""

    @pytest.fixture
    def sample_transition(self):
        """Create a sample dynamic transition for testing"""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        return DynamicTransition(
            source_activity="com.example.app.MainActivity",
            target_activity="com.example.app.SettingsActivity",
            action_id="settings_button",
            action_type="click",
            timestamp=timestamp
        )

    def test_transition_initialization(self, sample_transition):
        """Test DynamicTransition constructor"""
        assert sample_transition.source_activity == "com.example.app.MainActivity"
        assert sample_transition.target_activity == "com.example.app.SettingsActivity"
        assert sample_transition.action_id == "settings_button"
        assert sample_transition.action_type == "click"
        assert sample_transition.timestamp == datetime(2023, 1, 1, 12, 0, 0)
        assert sample_transition.count == 1

    def test_increment_count(self, sample_transition):
        """Test increment_count method"""
        # Store original timestamp
        original_timestamp = sample_transition.timestamp

        # Wait to ensure new timestamp is different
        with patch('rvandroid.domain.dynamic_wtg.datetime') as mock_datetime:
            new_timestamp = original_timestamp + timedelta(seconds=10)
            mock_datetime.now.return_value = new_timestamp

            sample_transition.increment_count()

            assert sample_transition.count == 2
            assert sample_transition.timestamp == new_timestamp

    def test_to_dict(self, sample_transition):
        """Test to_dict method"""
        dict_data = sample_transition.to_dict()

        assert dict_data["source_activity"] == "com.example.app.MainActivity"
        assert dict_data["target_activity"] == "com.example.app.SettingsActivity"
        assert dict_data["action_id"] == "settings_button"
        assert dict_data["action_type"] == "click"
        assert dict_data["timestamp"] == "2023-01-01T12:00:00"
        assert dict_data["count"] == 1

    def test_from_dict(self):
        """Test from_dict method"""
        data = {
            "source_activity": "com.example.app.MainActivity",
            "target_activity": "com.example.app.SettingsActivity",
            "action_id": "settings_button",
            "action_type": "click",
            "timestamp": "2023-01-01T12:00:00",
            "count": 5
        }

        transition = DynamicTransition.from_dict(data)

        assert transition.source_activity == "com.example.app.MainActivity"
        assert transition.target_activity == "com.example.app.SettingsActivity"
        assert transition.action_id == "settings_button"
        assert transition.action_type == "click"
        assert transition.timestamp == datetime(2023, 1, 1, 12, 0, 0)
        assert transition.count == 5

    def test_equality(self, sample_transition):
        """Test equality comparison"""
        # Same transition
        transition2 = DynamicTransition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )
        assert sample_transition == transition2

        # Different action_id
        transition3 = DynamicTransition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "different_button",
            "click"
        )
        assert sample_transition != transition3

        # Different source
        transition4 = DynamicTransition(
            "com.example.app.DifferentActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )
        assert sample_transition != transition4

        # Different target
        transition5 = DynamicTransition(
            "com.example.app.MainActivity",
            "com.example.app.DifferentActivity",
            "settings_button",
            "click"
        )
        assert sample_transition != transition5

        # Different object type
        assert sample_transition != "not a transition"

    def test_hash(self, sample_transition):
        """Test hash computation"""
        expected_hash = hash((
            sample_transition.source_activity,
            sample_transition.target_activity,
            sample_transition.action_id
        ))
        assert hash(sample_transition) == expected_hash


class TestActivityNode:
    """Tests for the ActivityNode class"""

    @pytest.fixture
    def sample_node(self):
        """Create a sample activity node for testing"""
        return ActivityNode("com.example.app.MainActivity")

    def test_activity_node_initialization(self, sample_node):
        """Test ActivityNode constructor"""
        assert sample_node.name == "com.example.app.MainActivity"
        assert sample_node.visit_count == 0
        assert sample_node.first_visit is None
        assert sample_node.last_visit is None
        assert sample_node.ui_elements_tested == set()

    def test_record_visit(self, sample_node):
        """Test record_visit method"""
        # First visit
        with patch('rvandroid.domain.dynamic_wtg.datetime') as mock_datetime:
            first_time = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = first_time

            sample_node.record_visit()

            assert sample_node.visit_count == 1
            assert sample_node.first_visit == first_time
            assert sample_node.last_visit == first_time

        # Second visit
        with patch('rvandroid.domain.dynamic_wtg.datetime') as mock_datetime:
            second_time = datetime(2023, 1, 1, 12, 30, 0)
            mock_datetime.now.return_value = second_time

            sample_node.record_visit()

            assert sample_node.visit_count == 2
            assert sample_node.first_visit == first_time  # Unchanged
            assert sample_node.last_visit == second_time  # Updated

    def test_record_tested_element(self, sample_node):
        """Test record_tested_element method"""
        sample_node.record_tested_element("button1")
        assert "button1" in sample_node.ui_elements_tested

        # Add another element
        sample_node.record_tested_element("button2")
        assert len(sample_node.ui_elements_tested) == 2
        assert "button2" in sample_node.ui_elements_tested

        # Add duplicate (should not change set size)
        sample_node.record_tested_element("button1")
        assert len(sample_node.ui_elements_tested) == 2

    def test_get_coverage_percentage(self, sample_node):
        """Test get_coverage_percentage method"""
        # No elements tested with zero total elements
        assert sample_node.get_coverage_percentage(0) == 100.0

        # No elements tested with some total elements
        assert sample_node.get_coverage_percentage(10) == 0.0

        # Test some elements
        sample_node.record_tested_element("button1")
        sample_node.record_tested_element("button2")

        # 2 out of 4 elements tested
        assert sample_node.get_coverage_percentage(4) == 50.0

        # Test all elements
        sample_node.record_tested_element("button3")
        sample_node.record_tested_element("button4")

        # 4 out of 4 elements tested
        assert sample_node.get_coverage_percentage(4) == 100.0

    def test_to_dict(self, sample_node):
        """Test to_dict method"""
        # Add visits and tested elements
        with patch('rvandroid.domain.dynamic_wtg.datetime') as mock_datetime:
            visit_time = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = visit_time

            sample_node.record_visit()

        sample_node.record_tested_element("button1")
        sample_node.record_tested_element("button2")

        dict_data = sample_node.to_dict()

        assert dict_data["name"] == "com.example.app.MainActivity"
        assert dict_data["visit_count"] == 1
        assert dict_data["first_visit"] == "2023-01-01T12:00:00"
        assert dict_data["last_visit"] == "2023-01-01T12:00:00"
        assert "button1" in dict_data["ui_elements_tested"]
        assert "button2" in dict_data["ui_elements_tested"]
        assert len(dict_data["ui_elements_tested"]) == 2

    def test_from_dict(self):
        """Test from_dict method"""
        data = {
            "name": "com.example.app.MainActivity",
            "visit_count": 5,
            "first_visit": "2023-01-01T10:00:00",
            "last_visit": "2023-01-01T14:00:00",
            "ui_elements_tested": ["button1", "button2", "button3"]
        }

        node = ActivityNode.from_dict(data)

        assert node.name == "com.example.app.MainActivity"
        assert node.visit_count == 5
        assert node.first_visit == datetime(2023, 1, 1, 10, 0, 0)
        assert node.last_visit == datetime(2023, 1, 1, 14, 0, 0)
        assert len(node.ui_elements_tested) == 3
        assert "button1" in node.ui_elements_tested
        assert "button2" in node.ui_elements_tested
        assert "button3" in node.ui_elements_tested


class TestDynamicTransitionGraph:
    """Tests for the DynamicTransitionGraph class"""

    @pytest.fixture
    def sample_graph(self):
        """Create a sample dynamic transition graph for testing"""
        return DynamicTransitionGraph()

    def test_graph_initialization(self, sample_graph):
        """Test DynamicTransitionGraph constructor"""
        assert isinstance(sample_graph.graph, nx.DiGraph)
        assert sample_graph.activities == {}
        assert sample_graph.transitions == []
        assert sample_graph.current_activity is None

    def test_add_activity(self, sample_graph):
        """Test add_activity method"""
        # Add new activity
        activity = sample_graph.add_activity("com.example.app.MainActivity")

        assert isinstance(activity, ActivityNode)
        assert activity.name == "com.example.app.MainActivity"
        assert "com.example.app.MainActivity" in sample_graph.activities
        assert sample_graph.activities["com.example.app.MainActivity"] == activity
        assert "com.example.app.MainActivity" in sample_graph.graph.nodes()

        # Add same activity again (should return existing one)
        activity2 = sample_graph.add_activity("com.example.app.MainActivity")
        assert activity2 == activity

    def test_record_visit(self, sample_graph):
        """Test record_visit method"""
        # Record first visit
        sample_graph.record_visit("com.example.app.MainActivity")

        assert "com.example.app.MainActivity" in sample_graph.activities
        assert sample_graph.activities["com.example.app.MainActivity"].visit_count == 1
        assert sample_graph.current_activity == "com.example.app.MainActivity"

        # Record another visit (different activity)
        sample_graph.record_visit("com.example.app.SettingsActivity")

        assert "com.example.app.SettingsActivity" in sample_graph.activities
        assert sample_graph.activities["com.example.app.SettingsActivity"].visit_count == 1
        assert sample_graph.current_activity == "com.example.app.SettingsActivity"

        # Record another visit to first activity
        sample_graph.record_visit("com.example.app.MainActivity")

        assert sample_graph.activities["com.example.app.MainActivity"].visit_count == 2
        assert sample_graph.current_activity == "com.example.app.MainActivity"

    def test_normalize_activity_name(self, sample_graph):
        """Test activity name normalization"""
        # Replace slashes with dots
        sample_graph.record_visit("com/example/app/MainActivity")
        assert "com.example.app.MainActivity" in sample_graph.activities

        # Remove trailing dots
        sample_graph.record_visit("com.example.app.SettingsActivity..")
        assert "com.example.app.SettingsActivity." in sample_graph.activities

    def test_record_transition(self, sample_graph):
        """Test record_transition method"""
        # Record first transition
        transition = sample_graph.record_transition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )

        assert isinstance(transition, DynamicTransition)
        assert len(sample_graph.transitions) == 1
        assert sample_graph.transitions[0] == transition
        assert sample_graph.graph.has_edge("com.example.app.MainActivity", "com.example.app.SettingsActivity")

        # Check edge attributes
        edge_data = sample_graph.graph["com.example.app.MainActivity"]["com.example.app.SettingsActivity"]
        assert edge_data["count"] == 1
        assert transition in edge_data["transitions"]

        # Record same transition again
        transition2 = sample_graph.record_transition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )

        assert transition2 == transition
        assert transition.count == 2
        assert len(sample_graph.transitions) == 1
        edge_data = sample_graph.graph["com.example.app.MainActivity"]["com.example.app.SettingsActivity"]
        assert edge_data["count"] == 2

    def test_record_action(self, sample_graph):
        """Test record_action method"""
        sample_graph.record_action("com.example.app.MainActivity", "button1")

        assert "com.example.app.MainActivity" in sample_graph.activities
        node = sample_graph.activities["com.example.app.MainActivity"]
        assert "button1" in node.ui_elements_tested

        # Test normalization
        sample_graph.record_action("com/example/app/SettingsActivity", "button2")
        assert "com.example.app.SettingsActivity" in sample_graph.activities
        node = sample_graph.activities["com.example.app.SettingsActivity"]
        assert "button2" in node.ui_elements_tested

    def test_record_current_to_next(self, sample_graph):
        """Test record_current_to_next method"""
        # No current activity set
        assert sample_graph.record_current_to_next("com.example.app.SettingsActivity", "button1", "click") is None

        # Set current activity
        sample_graph.record_visit("com.example.app.MainActivity")

        # Record transition from current
        transition = sample_graph.record_current_to_next("com.example.app.SettingsActivity", "button1", "click")

        assert isinstance(transition, DynamicTransition)
        assert transition.source_activity == "com.example.app.MainActivity"
        assert transition.target_activity == "com.example.app.SettingsActivity"
        assert sample_graph.current_activity == "com.example.app.SettingsActivity"

    def test_get_unexplored_activities(self, sample_graph):
        """Test get_unexplored_activities method"""
        # Add some activities to the graph
        sample_graph.add_activity("com.example.app.MainActivity")
        sample_graph.add_activity("com.example.app.SettingsActivity")
        sample_graph.add_activity("com.example.app.ProfileActivity")

        # Only some activities have been visited
        visited = {"com.example.app.MainActivity", "com.example.app.SettingsActivity"}
        unexplored = sample_graph.get_unexplored_activities(visited)

        assert len(unexplored) == 1
        assert "com.example.app.ProfileActivity" in unexplored

    def test_get_least_visited_activities(self, sample_graph):
        """Test get_least_visited_activities method"""
        # Add activities with different visit counts
        sample_graph.record_visit("com.example.app.MainActivity")
        sample_graph.record_visit("com.example.app.SettingsActivity")
        sample_graph.record_visit("com.example.app.ProfileActivity")
        sample_graph.record_visit("com.example.app.MainActivity")
        sample_graph.record_visit("com.example.app.MainActivity")

        # Get least visited
        least_visited = sample_graph.get_least_visited_activities(2)

        assert len(least_visited) == 2
        # ProfileActivity and SettingsActivity both have 1 visit
        # They could be in either order since they have the same count
        first_activity, first_count = least_visited[0]
        second_activity, second_count = least_visited[1]

        assert first_count == 1
        assert second_count == 1
        assert {first_activity, second_activity} == {"com.example.app.SettingsActivity",
                                                     "com.example.app.ProfileActivity"}

    def test_get_actions_for_coverage(self, sample_graph):
        """Test get_actions_for_coverage method"""
        # Add activity and record some actions
        sample_graph.record_visit("com.example.app.MainActivity")
        sample_graph.record_action("com.example.app.MainActivity", "button1")
        sample_graph.record_action("com.example.app.MainActivity", "button3")

        # All available actions
        all_actions = ["button1", "button2", "button3", "button4"]

        # Get actions that would increase coverage
        uncovered_actions = sample_graph.get_actions_for_coverage("com.example.app.MainActivity", all_actions)

        assert len(uncovered_actions) == 2
        assert "button2" in uncovered_actions
        assert "button4" in uncovered_actions

        # Non-existent activity
        assert sample_graph.get_actions_for_coverage("com.example.app.NonExistent", all_actions) == []

    def test_suggest_next_activity(self, sample_graph):
        """Test suggest_next_activity method"""
        # No current activity
        assert sample_graph.suggest_next_activity() is None

        # Setup graph with activities and transitions
        sample_graph.record_visit("com.example.app.MainActivity")
        sample_graph.record_transition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )
        sample_graph.record_transition(
            "com.example.app.MainActivity",
            "com.example.app.ProfileActivity",
            "profile_button",
            "click"
        )

        # Create an isolated activity with no neighbors (not connected in the graph)
        sample_graph.record_visit("com.example.app.IsolatedActivity")

        # Set main activity as current (has neighbors)
        sample_graph.current_activity = "com.example.app.MainActivity"

        # Instead of asserting a specific result, just verify that a non-None result is returned
        # This avoids dependence on specific sorting behavior
        result = sample_graph.suggest_next_activity()
        assert result is not None
        assert result in ["com.example.app.SettingsActivity", "com.example.app.ProfileActivity"]

        # No neighbors case - using the isolated activity
        sample_graph.current_activity = "com.example.app.IsolatedActivity"
        assert sample_graph.suggest_next_activity() is None

    def test_to_dict(self, sample_graph):
        """Test to_dict method"""
        # Setup graph with activities and transitions
        sample_graph.record_visit("com.example.app.MainActivity")
        sample_graph.record_visit("com.example.app.SettingsActivity")
        sample_graph.record_transition(
            "com.example.app.MainActivity",
            "com.example.app.SettingsActivity",
            "settings_button",
            "click"
        )

        dict_data = sample_graph.to_dict()

        assert "activities" in dict_data
        assert "transitions" in dict_data
        assert "current_activity" in dict_data

        assert len(dict_data["activities"]) == 2
        assert "com.example.app.MainActivity" in dict_data["activities"]
        assert "com.example.app.SettingsActivity" in dict_data["activities"]

        assert len(dict_data["transitions"]) == 1
        transition_data = dict_data["transitions"][0]
        assert transition_data["source_activity"] == "com.example.app.MainActivity"
        assert transition_data["target_activity"] == "com.example.app.SettingsActivity"
        assert transition_data["action_id"] == "settings_button"

        assert dict_data["current_activity"] == "com.example.app.SettingsActivity"

    def test_from_dict(self):
        """Test from_dict method"""
        data = {
            "activities": {
                "com.example.app.MainActivity": {
                    "name": "com.example.app.MainActivity",
                    "visit_count": 2,
                    "first_visit": "2023-01-01T10:00:00",
                    "last_visit": "2023-01-01T11:00:00",
                    "ui_elements_tested": ["button1", "button2"]
                },
                "com.example.app.SettingsActivity": {
                    "name": "com.example.app.SettingsActivity",
                    "visit_count": 1,
                    "first_visit": "2023-01-01T11:30:00",
                    "last_visit": "2023-01-01T11:30:00",
                    "ui_elements_tested": ["settings_button1"]
                }
            },
            "transitions": [
                {
                    "source_activity": "com.example.app.MainActivity",
                    "target_activity": "com.example.app.SettingsActivity",
                    "action_id": "settings_button",
                    "action_type": "click",
                    "timestamp": "2023-01-01T11:00:00",
                    "count": 1
                }
            ],
            "current_activity": "com.example.app.SettingsActivity"
        }

        graph = DynamicTransitionGraph.from_dict(data)

        # Check activities
        assert len(graph.activities) == 2
        assert "com.example.app.MainActivity" in graph.activities
        assert "com.example.app.SettingsActivity" in graph.activities

        main_activity = graph.activities["com.example.app.MainActivity"]
        assert main_activity.name == "com.example.app.MainActivity"
        assert main_activity.visit_count == 2
        assert main_activity.first_visit == datetime(2023, 1, 1, 10, 0, 0)
        assert main_activity.last_visit == datetime(2023, 1, 1, 11, 0, 0)
        assert "button1" in main_activity.ui_elements_tested
        assert "button2" in main_activity.ui_elements_tested

        # Check transitions
        assert len(graph.transitions) == 1
        transition = graph.transitions[0]
        assert transition.source_activity == "com.example.app.MainActivity"
        assert transition.target_activity == "com.example.app.SettingsActivity"
        assert transition.action_id == "settings_button"
        assert transition.action_type == "click"
        assert transition.timestamp == datetime(2023, 1, 1, 11, 0, 0)
        assert transition.count == 1

        # Check graph structure
        assert graph.graph.has_edge("com.example.app.MainActivity", "com.example.app.SettingsActivity")
        edge_data = graph.graph["com.example.app.MainActivity"]["com.example.app.SettingsActivity"]
        assert edge_data["count"] == 1
        assert len(edge_data["transitions"]) == 1

        # Check current activity
        assert graph.current_activity == "com.example.app.SettingsActivity"

    @patch('rvandroid.domain.dynamic_wtg.json')
    @patch('rvandroid.domain.dynamic_wtg.os.path.exists')
    def test_load_from_file_success(self, mock_exists, mock_json):
        """Test load_from_file method success case"""
        # Mock file existence
        mock_exists.return_value = True

        # Sample data to be returned when reading the file
        sample_data = {
            "activities": {
                "com.example.app.MainActivity": {
                    "name": "com.example.app.MainActivity",
                    "visit_count": 1,
                    "first_visit": "2023-01-01T10:00:00",
                    "last_visit": "2023-01-01T10:00:00",
                    "ui_elements_tested": []
                }
            },
            "transitions": [],
            "current_activity": "com.example.app.MainActivity"
        }

        # Mock json.load to return our sample data
        mock_json.load.return_value = sample_data

        # Mock open function
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_open.__enter__.return_value = mock_file

        with patch('builtins.open', return_value=mock_open):
            graph = DynamicTransitionGraph.load_from_file("test_file.json")

            # Verify file was checked for existence
            mock_exists.assert_called_once_with("test_file.json")

            # Verify file was opened and read
            mock_json.load.assert_called_once()

            # Verify graph was created properly
            assert graph is not None
            assert "com.example.app.MainActivity" in graph.activities
            assert graph.current_activity == "com.example.app.MainActivity"

    @patch('rvandroid.domain.dynamic_wtg.os.path.exists')
    def test_load_from_file_nonexistent(self, mock_exists):
        """Test load_from_file method with nonexistent file"""
        # Mock file non-existence
        mock_exists.return_value = False

        graph = DynamicTransitionGraph.load_from_file("nonexistent_file.json")

        # Verify file was checked for existence
        mock_exists.assert_called_once_with("nonexistent_file.json")

        # Verify no graph was returned
        assert graph is None

    @patch('rvandroid.domain.dynamic_wtg.os.path.exists')
    def test_load_from_file_error(self, mock_exists):
        """Test load_from_file method with error during loading"""
        # Mock file existence
        mock_exists.return_value = True

        # Mock open to raise an exception
        with patch('builtins.open', side_effect=IOError("Test error")):
            graph = DynamicTransitionGraph.load_from_file("error_file.json")

            # Verify file was checked for existence
            mock_exists.assert_called_once_with("error_file.json")

            # Verify no graph was returned
            assert graph is None
