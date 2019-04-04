from collections import deque
from typing import Dict, List, NamedTuple, Optional
import astroid
import warnings


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
}

SUBSCRIPT_FORMAT_MAP: Dict[str, str] = {
    "List": "Array<%s>",
    "Optional": "%s | null",
    "Tuple": "[%s]",
    "Union": "%s"
}


class ParsedAnnAssign(NamedTuple):
    attr_name: str
    attr_type: str


def has_dataclass_decorator(decorators: Optional[astroid.Decorators]) -> bool:
    if not decorators:
        return False

    return any(
        (getattr(decorator.func, "name", None) == "dataclass")
        if isinstance(decorator, astroid.Call)
        else decorator.name == "dataclass"
        for decorator in decorators.nodes
    )


def parse_annassign_node(node: astroid.AnnAssign) -> ParsedAnnAssign:
    def helper(node: astroid.node_classes.NodeNG) -> str:
        type_value = "UNKNOWN"
        if isinstance(node, astroid.Name):
            type_value = TYPE_MAP[node.name]
        elif isinstance(node, astroid.Subscript):
            subscript_value = node.value
            type_format = SUBSCRIPT_FORMAT_MAP[subscript_value.name]
            type_value = type_format % helper(node.slice.value)
        elif isinstance(node, astroid.Tuple):
            inner_types = get_inner_tuple_types(node)
            delimiter = get_inner_tuple_delimiter(node)
            if delimiter != "UNKNOWN":
                type_value = delimiter.join(inner_types)

        return type_value

    def get_inner_tuple_types(tuple_node: astroid.Tuple) -> List[str]:
        # avoid using Set to keep order
        inner_types: List[str] = []
        for child in tuple_node.get_children():
            child_type = helper(child)
            if child_type not in inner_types:
                inner_types.append(child_type)
        return inner_types

    def get_inner_tuple_delimiter(tuple_node: astroid.Tuple) -> str:
        parent_subscript_name = tuple_node.parent.parent.value.name
        delimiter = "UNKNOWN"
        if parent_subscript_name == 'Tuple':
            delimiter = ", "
        elif parent_subscript_name == 'Union':
            delimiter = " | "
        return delimiter

    return ParsedAnnAssign(node.target.name, helper(node.annotation))


class Parser:
    def __init__(self, interface_qualname: str, outpath: str = "interfaces.ts") -> None:
        self.interface_qualname = interface_qualname
        self.outpath = outpath

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
                    UserWarning("Non-dataclasses are not supported, see documentation.")
                )
                continue

            serialized_types = self.serialize_ast_node_annassigns(current)
            # TODO: Test code
            if serialized_types:
                print()
                print(f"interface {current.name} {{")
                print("\n".join(f"    {k}: {v};" for k, v in serialized_types.items()))
                print(f"}}\n")

    def serialize_ast_node_annassigns(self, node: astroid.ClassDef) -> Dict[str, str]:
        # TODO: Clean this up
        serialized_types: Dict[str, str] = {}
        for child in node.body:
            if not isinstance(child, astroid.AnnAssign):
                continue

            # TODO: This deserves to be a standalone, well-tested function.
            is_optional = (
                isinstance(child.annotation, astroid.Subscript)
                and child.annotation.value.name == "Optional"
            )
            name = child.target.name
            if is_optional:
                name += "?"

            if isinstance(child.annotation, astroid.Subscript):
                if isinstance(child.annotation.slice, astroid.Index):
                    annotation = TYPE_MAP[child.annotation.slice.value.name]
                if child.annotation.value.name == "List":
                    annotation += "[]"
            else:
                annotation = child.annotation.name
            serialized_types[name] = TYPE_MAP.get(annotation, annotation)
        return serialized_types
