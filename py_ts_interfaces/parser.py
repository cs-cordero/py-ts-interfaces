import warnings
from collections import deque
from typing import Dict, List, NamedTuple, Optional, Union

import astroid


class Interface:
    pass


class PossibleInterfaceReference(str):
    pass


TYPE_MAP: Dict[str, str] = {
    "bool": "boolean",
    "str": "string",
    "int": "number",
    "float": "number",
    "complex": "number",
    "Any": "any",
    "Dict": "Record<any, any>",
    "List": "Array<any>",
    "Tuple": "[any]",
    "Union": "any",
}

SUBSCRIPT_FORMAT_MAP: Dict[str, str] = {
    "Dict": "Record<%s>",
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

            if current.name in self.prepared:
                warnings.warn(
                    f"Found duplicate interface with name {current.name}."
                    "All interfaces after the first will be ignored",
                    UserWarning,
                )
                continue

            self.prepared[current.name] = get_types_from_classdef(current)
        ensure_possible_interface_references_valid(self.prepared)

    def flush(self) -> str:
        serialized: List[str] = []

        for interface, attributes in self.prepared.items():
            s = f"interface {interface} {{\n"
            for attribute_name, attribute_type in attributes.items():
                s += f"    {attribute_name}: {attribute_type};\n"
            s += "}"
            serialized.append(s)

        self.prepared.clear()
        return "\n\n".join(serialized).strip() + "\n"


def get_types_from_classdef(node: astroid.ClassDef) -> Dict[str, str]:
    serialized_types: Dict[str, str] = {}
    for child in node.body:
        if not isinstance(child, astroid.AnnAssign):
            continue
        child_name, child_type = parse_annassign_node(child)
        serialized_types[child_name] = child_type
    return serialized_types


class ParsedAnnAssign(NamedTuple):
    attr_name: str
    attr_type: str


def parse_annassign_node(node: astroid.AnnAssign) -> ParsedAnnAssign:
    def helper(
        node: astroid.node_classes.NodeNG,
    ) -> Union[str, PossibleInterfaceReference]:
        type_value = "UNKNOWN"

        if isinstance(node, astroid.Name):
            # When the node is of an astroid.Name type, it could have a
            # name that exists in our TYPE_MAP, it could have a name that
            # refers to another class previously defined in the source, or
            # it could be a forward reference to a class that has yet to
            # be parsed.
            # We will have to assume it is a valid forward reference now and
            # then just double check that it does indeed reference another
            # Interface class as a post-parse step.
            type_value = TYPE_MAP.get(node.name, PossibleInterfaceReference(node.name))
            if node.name == "Union":
                warnings.warn(
                    "Came across an annotation for Union without any indexed types!"
                    " Coercing the annotation to any.",
                    UserWarning,
                )

        elif isinstance(node, astroid.Const) and node.name == "str":
            # When the node is of an astroid.Const type, it could be one of
            # num, str, bool, None, or bytes.
            # If it is Const.str, then it is possible that the value is a
            # reference to a class previously defined in the source or it could
            # be a forward reference to a class that has yet to be parsed.
            type_value = PossibleInterfaceReference(node.value)

        elif isinstance(node, astroid.Subscript):
            subscript_value = node.value
            type_format = SUBSCRIPT_FORMAT_MAP[subscript_value.name]
            type_value = type_format % helper(node.slice)

        elif isinstance(node, astroid.Tuple):
            inner_types = get_inner_tuple_types(node)
            delimiter = get_inner_tuple_delimiter(node)

            if delimiter == " | ":
                inner_types_deduplicated = []

                # Deduplicate inner types using a list to preserve order
                for inner_type in inner_types:
                    if inner_type not in inner_types_deduplicated:
                        inner_types_deduplicated.append(inner_type)

                inner_types = inner_types_deduplicated

            if delimiter != "UNKNOWN":
                type_value = delimiter.join(inner_types)

        return type_value

    def get_inner_tuple_types(tuple_node: astroid.Tuple) -> List[str]:
        # avoid using Set to keep order. We also want repetitions
        # to avoid problems with tuples where repeated types do have
        # a meaning (e.g., Dict[int, int]).
        inner_types: List[str] = []
        for child in tuple_node.get_children():
            inner_types.append(helper(child))

        return inner_types

    def get_inner_tuple_delimiter(tuple_node: astroid.Tuple) -> str:
        parent_subscript_name = tuple_node.parent.value.name
        delimiter = "UNKNOWN"
        if parent_subscript_name in {"Dict", "Tuple"}:
            delimiter = ", "
        elif parent_subscript_name == "Union":
            delimiter = " | "
        return delimiter

    return ParsedAnnAssign(node.target.name, helper(node.annotation))


def has_dataclass_decorator(decorators: Optional[astroid.Decorators]) -> bool:
    if not decorators:
        return False

    return any(
        (getattr(decorator.func, "name", None) == "dataclass")
        if isinstance(decorator, astroid.Call)
        else decorator.name == "dataclass"
        for decorator in decorators.nodes
    )


def ensure_possible_interface_references_valid(interfaces: PreparedInterfaces) -> None:
    interface_names = set(interfaces.keys())

    for interface, attributes in interfaces.items():
        for attribute_name, attribute_type in attributes.items():
            if not isinstance(attribute_type, PossibleInterfaceReference):
                continue

            if attribute_type not in interface_names:
                raise RuntimeError(
                    f"Invalid nested Interface reference '{attribute_type}'"
                    f" found for interface {interface}!\n"
                    f"Does '{attribute_type}' exist and is it an Interface?"
                )
