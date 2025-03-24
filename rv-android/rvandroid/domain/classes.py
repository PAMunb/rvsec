# classes.py
from typing import Optional, Set, Dict, List

from rvandroid.util.logging.manager import LoggingManager


class Method:
    """
    Represents a method in a class with its properties and relationships.
    Used for tracking method reachability and MOP analysis.
    """

    def __init__(
            self,
            class_name: str,
            name: str,
            params: List[str],
            signature: str,
            reachable: bool,
            reaches_mop: bool,
            directly_reaches_mop: bool
    ):
        """
        Initialize a Method with its properties.

        Args:
            class_name: Name of the class containing this method
            name: Method name
            params: List of parameter types
            signature: Full method signature
            reachable: Whether the method is reachable
            reaches_mop: Whether the method reaches a MOP method
            directly_reaches_mop: Whether the method directly reaches a MOP method
        """
        self.class_name = class_name
        self.name = name
        self.params = params
        self.signature = signature
        self.reachable = reachable
        self.reaches_mop = reaches_mop
        self.directly_reaches_mop = directly_reaches_mop
        self.reached = False

    def to_json(self):
        """
        Convert the method to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "class": self.class_name,
            "name": self.name,
            "params": self.params,
            "signature": self.signature,
            "reachable": self.reachable,
            "reaches_mop": self.reaches_mop,
            "directly_reaches_mop": self.directly_reaches_mop
        }

    def __eq__(self, other: object) -> bool:
        """
        Compare this method with another for equality.

        Args:
            other: Object to compare with

        Returns:
            True if equal, False otherwise
        """
        if isinstance(other, Method):
            return self.signature == other.signature
        return False

    def __hash__(self) -> int:
        """
        Get hash value for this method.

        Returns:
            Hash value based on signature
        """
        return hash(self.signature)

    def __str__(self) -> str:
        """
        Get string representation of this method.

        Returns:
            String representation
        """
        return (f"Method=[name={self.name}, signature={self.signature}, "
                f"reachable={self.reachable}, reaches_mop={self.reaches_mop}, "
                f"directly_reaches_mop={self.directly_reaches_mop}]")

    def __repr__(self) -> str:
        """
        Get representation string for this method.

        Returns:
            Representation string
        """
        return self.signature


class Clazz:
    """
    Represents a class in the application, tracking its activities and methods.
    Manages the relationship between classes, methods, and fields.
    """

    def __init__(self, name: str, is_activity: bool, is_main_activity: bool):
        """
        Initialize a class.

        Args:
            name: Class name
            is_activity: Whether the class is an Android activity
            is_main_activity: Whether the class is the main activity
        """
        self.name = name
        self.is_activity = is_activity
        self.is_main_activity = is_main_activity
        self.methods: Set[Method] = set()
        self.fields: Set[str] = set()

    def add_method(self, method: Method) -> bool:
        """
        Add a method to the class if it doesn't already exist.

        Args:
            method: Method to add

        Returns:
            True if method was added, False if already exists
        """
        if method in self.methods:
            return False
        self.methods.add(method)
        return True

    def add_field(self, field: str) -> None:
        """
        Add a field to the class's field set.

        Args:
            field: Field name to add
        """
        self.fields.add(field)

    def to_json(self):
        """
        Convert class to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "name": self.name,
            "is_activity": self.is_activity,
            "is_main_activity": self.is_main_activity,
            "methods": [method.to_json() for method in self.methods],
            "fields": list(self.fields)
        }

    def __str__(self) -> str:
        """
        Get string representation of this class.

        Returns:
            String representation
        """
        return (f"Clazz=[name={self.name}, is_activity={self.is_activity}, "
                f"is_main={self.is_main_activity}, methods={self.methods}, "
                f"fields={self.fields}]")

    def __repr__(self) -> str:
        """
        Get representation string for this class.

        Returns:
            Representation string
        """
        return f"[{self.name},{self.is_activity},{self.is_main_activity}]"


class Classes:
    """
    Manages all classes and methods in the application.
    Provides functionality to add and retrieve classes and methods.
    """

    def __init__(self):
        """Initialize the Classes container with logging."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger("model.classes.Classes")
        self.classes: Dict[str, Clazz] = {}
        self.methods: Dict[str, Method] = {}

    def get_classes(self) -> List[Clazz]:
        """
        Returns a list of all classes.

        Returns:
            List of all class objects
        """
        return list(self.classes.values())

    def add_clazz(self, name: str, is_activity: bool, is_main_activity: bool) -> Clazz:
        """
        Add a new class or return an existing one.

        Args:
            name: Class name
            is_activity: Whether it's an activity
            is_main_activity: Whether it's the main activity

        Returns:
            The class object (either existing or newly created)
        """
        if name not in self.classes:
            self.logger.debug(f"Adding new class: {name}")
            self.classes[name] = Clazz(name, is_activity, is_main_activity)
        return self.classes[name]

    def get_clazz(self, name: str) -> Optional[Clazz]:
        """
        Retrieve a class by name if it exists.

        Args:
            name: Class name to look for

        Returns:
            Class object or None if not found
        """
        return self.classes.get(name)

    def add_method(self, method: Method) -> bool:
        """
        Add a method to both the class and methods dictionary.

        Args:
            method: Method to add

        Returns:
            True if method was added, False otherwise
        """
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                self.logger.debug(f"Added method: {method.signature}")
                return True
        return False

    def to_json(self):
        """
        Convert all classes to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "classes": [clazz.to_json() for clazz in self.classes.values()]
        }