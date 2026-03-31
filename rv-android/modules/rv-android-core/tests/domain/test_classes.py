import pytest
from pydantic import ValidationError
from hypothesis import given, strategies as st, settings, HealthCheck

from rv_android_core.domain.classes import Method, Clazz, Classes


@pytest.fixture
def sample_method():
    """Fixture for a standard, reachable method."""
    return Method(
        class_name="TestClass",
        name="testMethod",
        params=["param1", "param2"],
        signature="TestClass.testMethod(param1,param2)",
        reachable=True,
        reaches_mop=False,
        directly_reaches_mop=False
    )


@pytest.fixture
def mop_method():
    """Fixture for a method that directly reaches a monitored operation."""
    return Method(
        class_name="TestClass",
        name="mopMethod",
        params=[],
        signature="TestClass.mopMethod()",
        reachable=True,
        reaches_mop=True,
        directly_reaches_mop=True
    )


@pytest.fixture
def sample_clazz():
    """Fixture for a standard Activity class."""
    return Clazz(name="TestActivity", component_type="activity", is_main=False)


@pytest.fixture
def classes_manager():
    """Fixture for a new Classes manager instance."""
    return Classes()


class TestMethod:
    def test_method_initialization(self, sample_method):
        assert sample_method.class_name == "TestClass"
        assert sample_method.name == "testMethod"
        assert sample_method.params == ["param1", "param2"]
        assert sample_method.reachable is True
        assert sample_method.reaches_mop is False
        assert sample_method.directly_reaches_mop is False

    def test_method_equality_and_hash(self, sample_method):
        method2 = Method(
            class_name="TestClass", name="testMethod", params=["param1", "param2"],
            signature="TestClass.testMethod(param1,param2)"
        )
        other_method = Method(
            class_name="OtherClass", name="otherMethod", params=[],
            signature="OtherClass.otherMethod()"
        )
        assert sample_method == method2
        assert sample_method != other_method
        assert sample_method != "not_a_method"
        assert hash(sample_method) == hash(method2)
        assert hash(sample_method) != hash(other_method)

    def test_method_representations(self, sample_method):
        assert repr(sample_method) == sample_method.signature
        string_repr = str(sample_method)
        assert sample_method.name in string_repr
        assert sample_method.signature in string_repr

    def test_method_to_json(self, sample_method):
        expected = {
            "class": "TestClass",
            "name": "testMethod",
            "params": ["param1", "param2"],
            "signature": "TestClass.testMethod(param1,param2)",
            "reachable": True,
            "reaches_mop": False,
            "directly_reaches_mop": False
        }
        assert sample_method.to_json() == expected

    @pytest.mark.parametrize("reaches_mop, directly_reaches_mop, expected", [
        (True, True, True),
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ])
    def test_is_monitored_operation_related(self, reaches_mop, directly_reaches_mop, expected):
        method = Method(
            class_name="TestClass", name="test", params=[], signature="TestClass.test()",
            reaches_mop=reaches_mop, directly_reaches_mop=directly_reaches_mop
        )
        assert method.is_monitored_operation_related() is expected

    def test_method_analysis_summary(self, sample_method):
        sample_method.reached = True
        summary = sample_method.get_analysis_summary()
        assert summary['signature'] == sample_method.signature
        assert summary['reachable'] is True
        assert summary['monitored_operations']['is_related'] is False
        assert summary['runtime_reached'] is True

    def test_method_creation_fails_with_invalid_data(self):
        with pytest.raises(ValidationError):
            Method(class_name="", name="name", params=[], signature="sig")
        with pytest.raises(ValidationError):
            Method(class_name="class", name="", params=[], signature="sig")
        with pytest.raises(ValidationError):
            Method(class_name="class", name="name", params=[], signature="")


class TestClazz:
    def test_clazz_initialization(self, sample_clazz):
        assert sample_clazz.name == "TestActivity"
        assert sample_clazz.component_type == "activity"
        assert sample_clazz.is_main is False
        assert not sample_clazz.methods
        assert not sample_clazz.fields

    def test_add_method(self, sample_clazz, sample_method):
        assert sample_clazz.add_method(sample_method) is True
        assert len(sample_clazz.methods) == 1
        assert sample_clazz.add_method(sample_method) is False  # Duplicate
        assert len(sample_clazz.methods) == 1

    def test_add_field(self, sample_clazz):
        sample_clazz.add_field("testField")
        assert "testField" in sample_clazz.fields
        sample_clazz.add_field("testField")  # Duplicates are ignored in sets
        assert len(sample_clazz.fields) == 1

    def test_get_methods(self, sample_clazz, sample_method, mop_method):
        unreachable_method = Method(
            class_name="TestClass", name="unreachable", params=[],
            signature="TestClass.unreachable()", reachable=False
        )
        sample_clazz.add_method(sample_method)
        sample_clazz.add_method(mop_method)
        sample_clazz.add_method(unreachable_method)

        reachable_methods = sample_clazz.get_reachable_methods()
        assert len(reachable_methods) == 2
        assert sample_method in reachable_methods
        assert mop_method in reachable_methods

        mop_methods = sample_clazz.get_monitored_operation_methods()
        assert mop_methods == [mop_method]

    def test_clazz_representations(self, sample_clazz):
        assert repr(sample_clazz) == "[TestActivity,activity,False]"
        string_repr = str(sample_clazz)
        assert sample_clazz.name in string_repr
        assert "methods=0" in string_repr

    def test_clazz_to_json_and_summary(self, sample_clazz, sample_method):
        sample_clazz.add_method(sample_method)
        sample_clazz.add_field("testField")

        json_data = sample_clazz.to_json()
        assert json_data["name"] == "TestActivity"
        assert len(json_data["methods"]) == 1
        assert len(json_data["fields"]) == 1

        summary = sample_clazz.get_analysis_summary()
        assert summary['name'] == sample_clazz.name
        assert summary['methods']['total'] == 1
        assert summary['methods']['reachable'] == 1
        assert summary['fields']['total'] == 1


class TestClasses:
    def test_add_and_get_clazz(self, classes_manager):
        clazz = classes_manager.add_clazz("TestActivity", "activity", False)
        assert clazz.name == "TestActivity"
        assert classes_manager.get_clazz("TestActivity") is clazz
        assert classes_manager.get_clazz("NonExistent") is None

    def test_add_existing_clazz_returns_same_instance(self, classes_manager):
        clazz1 = classes_manager.add_clazz("TestClass", None, False)
        clazz2 = classes_manager.add_clazz("TestClass", "activity", True)  # Should not update
        assert clazz1 is clazz2
        assert clazz1.component_type is None  # Original value
        assert not clazz1.is_main

    def test_get_main_activity(self, classes_manager):
        assert classes_manager.get_main_activity() is None
        classes_manager.add_clazz("OtherActivity", "activity", False)
        assert classes_manager.get_main_activity() is None
        main_activity = classes_manager.add_clazz("MainActivity", "activity", True)
        assert classes_manager.get_main_activity() is main_activity

    def test_add_method_flow(self, classes_manager, sample_method):
        # Fail because class doesn't exist
        assert not classes_manager.add_method(sample_method)
        assert not classes_manager.methods

        # Success
        classes_manager.add_clazz("TestClass", "activity", False)
        assert classes_manager.add_method(sample_method)
        assert len(classes_manager.methods) == 1

        # Fail because method is duplicate
        assert not classes_manager.add_method(sample_method)
        assert len(classes_manager.methods) == 1

    def test_get_method(self, classes_manager, sample_method):
        assert classes_manager.get_method(sample_method.signature) is None
        classes_manager.add_clazz(sample_method.class_name, None, False)
        classes_manager.add_method(sample_method)
        assert classes_manager.get_method(sample_method.signature) is sample_method

    def test_get_monitored_operation_methods(self, classes_manager, sample_method, mop_method):
        assert not classes_manager.get_monitored_operation_methods()
        classes_manager.add_clazz("TestClass", None, False)
        classes_manager.add_method(sample_method)
        assert not classes_manager.get_monitored_operation_methods()
        classes_manager.add_method(mop_method)
        assert classes_manager.get_monitored_operation_methods() == [mop_method]

    def test_analysis_summary(self, classes_manager, sample_method):
        classes_manager.add_clazz("TestClass", "activity", False)
        classes_manager.add_method(sample_method)
        summary = classes_manager.get_analysis_summary()
        assert summary['classes']['total'] == 1
        assert summary['methods']['total'] == 1
        assert summary['methods']['reachable'] == 1
        assert summary['methods']['reachability_percentage'] == 100.0

    def test_analysis_summary_with_no_methods(self, classes_manager):
        classes_manager.add_clazz("EmptyClass", None, False)
        summary = classes_manager.get_analysis_summary()
        assert summary['methods']['total'] == 0
        assert summary['methods']['reachability_percentage'] == 0

    def test_to_json(self, classes_manager, sample_method):
        classes_manager.add_clazz("TestClass", "activity", False)
        classes_manager.add_method(sample_method)
        json_data = classes_manager.to_json()
        assert len(json_data["classes"]) == 1
        assert json_data["classes"][0]['name'] == "TestClass"


class TestDomainIntegrations:
    def test_full_scenario(self, classes_manager):
        # 1. Add classes
        main_activity = classes_manager.add_clazz("com.app.MainActivity", "activity", True)
        util_class = classes_manager.add_clazz("com.app.Util", None, False)

        # 2. Define methods
        entry_point = Method(class_name="com.app.MainActivity", name="onCreate", params=["Bundle"], signature="com.app.MainActivity.onCreate(Bundle)", reachable=True)
        util_method = Method(class_name="com.app.Util", name="doSomething", params=[], signature="com.app.Util.doSomething()", reachable=True)
        mop_method = Method(class_name="com.app.Util", name="encrypt", params=["String"], signature="com.app.Util.encrypt(String)", reachable=True, directly_reaches_mop=True)
        unreachable_method = Method(class_name="com.app.Util", name="legacy", params=[], signature="com.app.Util.legacy()", reachable=False)

        # 3. Add methods
        assert classes_manager.add_method(entry_point)
        assert classes_manager.add_method(util_method)
        assert classes_manager.add_method(mop_method)
        assert classes_manager.add_method(unreachable_method)

        # 4. Verify state
        assert classes_manager.get_clazz("com.app.MainActivity") is main_activity
        assert len(main_activity.methods) == 1
        assert len(util_class.methods) == 3
        assert len(classes_manager.methods) == 4
        assert classes_manager.get_main_activity() is main_activity
        
        mop_methods = classes_manager.get_monitored_operation_methods()
        assert len(mop_methods) == 1
        assert mop_method in mop_methods

        # 5. Check summaries
        util_summary = util_class.get_analysis_summary()
        assert util_summary['methods']['total'] == 3
        assert util_summary['methods']['reachable'] == 2
        assert util_summary['methods']['monitored_operations_related'] == 1

        global_summary = classes_manager.get_analysis_summary()
        assert global_summary['classes']['total'] == 2
        assert global_summary['methods']['total'] == 4
        assert global_summary['methods']['reachable'] == 3
        assert global_summary['methods']['reachability_percentage'] == 75.0


# --- Property-Based Tests ---

# Strategy for generating valid Java identifiers
java_identifier = st.from_regex(r'[a-zA-Z_][a-zA-Z0-9_]*', fullmatch=True)
# Strategy for generating fully qualified class names
java_class_name = st.lists(java_identifier, min_size=1, max_size=5).map(".".join)

# Strategy for creating Method objects
method_strategy = st.builds(
    Method,
    class_name=java_class_name,
    name=java_identifier,
    params=st.lists(java_class_name, max_size=5),
    signature=st.text(min_size=1, max_size=100).filter(lambda s: s and not s.isspace()),
    reachable=st.booleans(),
    reaches_mop=st.booleans(),
    directly_reaches_mop=st.booleans(),
    reached=st.booleans()
)

@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
@given(method=method_strategy)
def test_method_properties_are_consistent(method):
    """Property-based test to check Method invariants."""
    if method.directly_reaches_mop or method.reaches_mop:
        assert method.is_monitored_operation_related()
    else:
        assert not method.is_monitored_operation_related()
    
    summary = method.get_analysis_summary()
    assert summary['signature'] == method.signature
    assert summary['monitored_operations']['is_related'] == method.is_monitored_operation_related()

@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
@given(name=java_class_name, component_type=st.sampled_from(["activity", "service", "receiver", "provider", None]), is_main=st.booleans(), methods=st.sets(method_strategy))
def test_clazz_with_random_data(name, component_type, is_main, methods):
    """Property-based test for Clazz consistency."""
    clazz = Clazz(name=name, component_type=component_type, is_main=is_main)
    for method in methods:
        clazz.add_method(method)
    
    assert len(clazz.methods) == len(methods)
    
    mop_methods_in_set = {m for m in methods if m.is_monitored_operation_related()}
    assert len(clazz.get_monitored_operation_methods()) == len(mop_methods_in_set)

    reachable_methods_in_set = {m for m in methods if m.reachable}
    assert len(clazz.get_reachable_methods()) == len(reachable_methods_in_set)

