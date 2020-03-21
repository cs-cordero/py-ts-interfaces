import warnings
from collections import deque
from typing import Dict, List, NamedTuple, Optional

import astroid


class Interface:
    pass


TYPE_MAP: Dict[str, str] = {
    "bool": "boolean",
    "str": "string",
    "int": "number",
    "float": "number",
    "complex": "number",
    "Any": "any",
    "List": "Array<any>",
    "Tuple": "[any]",
    "Union": "any",
}

SUBSCRIPT_FORMAT_MAP: Dict[str, str] = {
    "List": "Array<%s>",
    "Optional": "%s | null",
    "Tuple": "[%s]",
    "Union": "%s",
}


InterfaceAttributes = Dict[str, str]
PreparedInterfaces = Dict[str, InterfaceAttributes]


class Parser:
    def __init__(self, interface_qualname: str) -> None:
        self.interface_qualname = interface_qualname
        self.prepared: PreparedInterfaces = {}
        self._classdefs: Dict[str, astroid.ClassDef] = {}

    def parse(self, code: str) -> None:
        queue = deque([astroid.parse(code)])
        while queue:
            current = queue.popleft()
            children = current.get_children()
            if not isinstance(current, astroid.ClassDef):
                queue.extend(children)
                continue

            if not current.is_subtype_of(self.interface_qualname):
                queue.extend(children)
                continue

            if not has_dataclass_decorator(current.decorators):
                warnings.warn(
                    "Non-dataclasses are not supported, see documentation.", UserWarning
                )
                continue

            self._classdefs.update({current.name: current})

            if current.name in self.prepared:
                warnings.warn(
                    f"Found duplicate interface with name {current.name}."
                    "All interfaces after the first will be ignored",
                    UserWarning,
                )
                continue

            self.prepared[current.name] = get_types_from_classdef(
                current, self._classdefs
            )

    def flush(self) -> str:
        serialized: List[str] = []

        for interface, attributes in self.prepared.items():
            s = f"interface {interface} {{\n"
            for attribute_name, attribute_type in attributes.items():
                s += f"    {attribute_name}: {attribute_type};\n"
            s += "}"
            serialized.append(s)

        self.prepared.clear()
        return "\n\n".join(serialized).strip()


def get_types_from_classdef(
    node: astroid.ClassDef, classdefs: Optional[Dict[str, astroid.ClassDef]] = None
) -> Dict[str, str]:
    if classdefs is None:
        classdefs = {}
    assert classdefs is not None

    serialized_types: Dict[str, str] = {}
    for child in node.body:
        if not isinstance(child, astroid.AnnAssign):
            continue
        child_name, child_type = parse_annassign_node(child, classdefs)
        serialized_types[child_name] = child_type
    return serialized_types


class ParsedAnnAssign(NamedTuple):
    attr_name: str
    attr_type: str


def parse_annassign_node(
    node: astroid.AnnAssign, classdefs: Optional[Dict[str, astroid.ClassDef]] = None
) -> ParsedAnnAssign:
    if classdefs is None:
        classdefs = {}
    assert classdefs is not None

    def helper(
        node: astroid.node_classes.NodeNG,
        classdefs: Optional[Dict[str, astroid.ClassDef]] = None,
    ) -> str:
        if classdefs is None:
            # This shouldn't be None since it is called from within
            # parse_annassign_node(...) which checks the value of classdefs,
            # but check just in case.
            classdefs = {}
        assert classdefs is not None
        type_value = "UNKNOWN"

        if isinstance(node, astroid.Name):
            type_value = TYPE_MAP.get(node.name, "")
            if not type_value:
                classref = classdefs.get(node.name)
                if not classref:
                    warnings.warn(
                        UserWarning(
                            f"Couldn't map {str(node.name)} to a type or class-type."
                            f" Existing class-defs: {str(classdefs.keys())}"
                        )
                    )
                    type_value = "UNKNOWN"
                else:
                    assert classref is not None
                    type_value = classref.name

            if node.name == "Union":
                warnings.warn(
                    UserWarning(
                        "Came across an annotation for Union without any indexed types!"
                        " Coercing the annotation to any."
                    )
                )
        elif isinstance(node, astroid.Subscript):
            subscript_value = node.value
            type_format = SUBSCRIPT_FORMAT_MAP[subscript_value.name]
            type_value = type_format % helper(node.slice.value, classdefs)
        elif isinstance(node, astroid.Tuple):
            inner_types = get_inner_tuple_types(node, classdefs)
            delimiter = get_inner_tuple_delimiter(node)
            if delimiter != "UNKNOWN":
                type_value = delimiter.join(inner_types)

        return type_value

    def get_inner_tuple_types(
        tuple_node: astroid.Tuple,
        classdefs: Optional[Dict[str, astroid.ClassDef]] = None,
    ) -> List[str]:
        if classdefs is None:
            # This shouldn't be None since it is called from within
            # parse_annassign_node(...) which checks the value of classdefs,
            # but check just in case.
            classdefs = {}
        assert classdefs is not None

        # avoid using Set to keep order
        inner_types: List[str] = []
        for child in tuple_node.get_children():
            child_type = helper(child, classdefs)
            if child_type not in inner_types:
                inner_types.append(child_type)
        return inner_types

    def get_inner_tuple_delimiter(tuple_node: astroid.Tuple) -> str:
        parent_subscript_name = tuple_node.parent.parent.value.name
        delimiter = "UNKNOWN"
        if parent_subscript_name == "Tuple":
            delimiter = ", "
        elif parent_subscript_name == "Union":
            delimiter = " | "
        return delimiter

    return ParsedAnnAssign(node.target.name, helper(node.annotation, classdefs))


def has_dataclass_decorator(decorators: Optional[astroid.Decorators]) -> bool:
    if not decorators:
        return False

    return any(
        (getattr(decorator.func, "name", None) == "dataclass")
        if isinstance(decorator, astroid.Call)
        else decorator.name == "dataclass"
        for decorator in decorators.nodes
    )
