import pytest
from rvandroid.domain.classes import Method, Clazz, Classes

@pytest.fixture
def sample_method():
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
def sample_clazz():
    return Clazz("TestActivity", True, False)

@pytest.fixture
def classes_manager():
    return Classes()

class TestMethod:
    def test_method_initialization(self, sample_method):
        assert sample_method.class_name == "TestClass"
        assert sample_method.name == "testMethod"
        assert sample_method.params == ["param1", "param2"]
        assert sample_method.reachable is True
        assert sample_method.reaches_mop is False
        assert sample_method.directly_reaches_mop is False

    def test_method_equality(self, sample_method):
        method2 = Method(
            "TestClass", "testMethod", ["param1", "param2"],
            "TestClass.testMethod(param1,param2)", True, False, False
        )
        assert sample_method == method2

    def test_method_hash(self, sample_method):
        assert hash(sample_method) == hash(sample_method.signature)

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

class TestClazz:
    def test_clazz_initialization(self, sample_clazz):
        assert sample_clazz.name == "TestActivity"
        assert sample_clazz.is_activity is True
        assert sample_clazz.is_main_activity is False
        assert len(sample_clazz.methods) == 0
        assert len(sample_clazz.fields) == 0

    def test_add_method(self, sample_clazz, sample_method):
        assert sample_clazz.add_method(sample_method) is True
        assert sample_clazz.add_method(sample_method) is False  # Duplicate
        assert len(sample_clazz.methods) == 1

    def test_add_field(self, sample_clazz):
        sample_clazz.add_field("testField")
        assert len(sample_clazz.fields) == 1
        assert "testField" in sample_clazz.fields

    def test_clazz_to_json(self, sample_clazz, sample_method):
        sample_clazz.add_method(sample_method)
        sample_clazz.add_field("testField")
        json_data = sample_clazz.to_json()
        assert json_data["name"] == "TestActivity"
        assert json_data["is_activity"] is True
        assert json_data["is_main_activity"] is False
        assert len(json_data["methods"]) == 1
        assert len(json_data["fields"]) == 1

class TestClasses:
    def test_add_and_get_clazz(self, classes_manager):
        clazz = classes_manager.add_clazz("TestActivity", True, False)
        assert clazz.name == "TestActivity"
        assert classes_manager.get_clazz("TestActivity") == clazz
        assert classes_manager.get_clazz("NonExistent") is None

    def test_get_classes(self, classes_manager):
        classes_manager.add_clazz("TestActivity1", True, False)
        classes_manager.add_clazz("TestActivity2", True, True)
        classes_list = classes_manager.get_classes()
        assert len(classes_list) == 2

    def test_add_method(self, classes_manager, sample_method):
        classes_manager.add_clazz("TestClass", True, False)
        assert classes_manager.add_method(sample_method) is True
        assert classes_manager.add_method(sample_method) is False  # Duplicate
        assert len(classes_manager.methods) == 1

    def test_classes_to_json(self, classes_manager, sample_method):
        classes_manager.add_clazz("TestClass", True, False)
        classes_manager.add_method(sample_method)
        json_data = classes_manager.to_json()
        assert len(json_data["classes"]) == 1
