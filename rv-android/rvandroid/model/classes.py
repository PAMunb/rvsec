import logging as logging_api
from typing import Optional, Set, Dict, List


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
        self.class_name = class_name
        self.name = name
        self.params = params
        self.signature = signature
        self.reachable = reachable
        self.reaches_mop = reaches_mop
        self.directly_reaches_mop = directly_reaches_mop
        self.reached = False

    def to_json(self):
        print(f"METHOD to json: {self.signature}")
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
        if isinstance(other, Method):
            return self.signature == other.signature
        return False

    def __hash__(self) -> int:
        return hash(self.signature)

    def __str__(self) -> str:
        return (f"Method=[name={self.name}, signature={self.signature}, "
                f"reachable={self.reachable}, reaches_mop={self.reaches_mop}, "
                f"directly_reaches_mop={self.directly_reaches_mop}]")

    def __repr__(self) -> str:
        return self.signature


class Clazz:
    """
    Represents a class in the application, tracking its activities and methods.
    Manages the relationship between classes, methods, and fields.
    """

    def __init__(self, name: str, is_activity: bool, is_main_activity: bool):
        self.name = name
        self.is_activity = is_activity
        self.is_main_activity = is_main_activity
        self.methods: Set[Method] = set()
        self.fields: Set[str] = set()

    def add_method(self, method: Method) -> bool:
        """Adds a method to the class if it doesn't already exist."""
        if method in self.methods:
            return False
        self.methods.add(method)
        return True

    def add_field(self, field: str) -> None:
        """Adds a field to the class's field set."""
        self.fields.add(field)

    def to_json(self):
        print(f"CLASS to json: {self.name}")
        return {
            "name": self.name,
            "is_activity": self.is_activity,
            "is_main_activity": self.is_main_activity,
            "methods": [method.to_json() for method in self.methods],
            "fields": list(self.fields)
        }

    def __str__(self) -> str:
        return (f"Clazz=[name={self.name}, is_activity={self.is_activity}, "
                f"is_main={self.is_main_activity}, methods={self.methods}, "
                f"fields={self.fields}]")

    def __repr__(self) -> str:
        return f"[{self.name},{self.is_activity},{self.is_main_activity}]"


class Classes:
    """
    Manages all classes and methods in the application.
    Provides functionality to add and retrieve classes and methods.
    """

    def __init__(self):
        self.logging = logging_api.getLogger("rvandroid.model.classes.Classes")
        self.classes: Dict[str, Clazz] = {}
        self.methods: Dict[str, Method] = {}

    def get_classes(self) -> List[Clazz]:
        """Returns a list of all classes."""
        return list(self.classes.values())

    def add_clazz(self, name: str, is_activity: bool, is_main_activity: bool) -> Clazz:
        """Adds a new class or returns existing one."""
        if name not in self.classes:
            self.logging.debug(f"Class {name} not found, adding")
            self.classes[name] = Clazz(name, is_activity, is_main_activity)
        return self.classes[name]

    def get_clazz(self, name: str) -> Optional[Clazz]:
        """Retrieves a class by name if it exists."""
        return self.classes.get(name)

    def add_method(self, method: Method) -> bool:
        """Adds a method to both the class and the method's dictionary."""
        if method.signature not in self.methods:
            clazz = self.get_clazz(method.class_name)
            if clazz and clazz.add_method(method):
                self.methods[method.signature] = method
                self.logging.debug(f"Added method {method.signature}")
                return True
        return False

    def to_json(self):
        return {
            "classes": [clazz.to_json() for clazz in self.classes.values()]
        }
