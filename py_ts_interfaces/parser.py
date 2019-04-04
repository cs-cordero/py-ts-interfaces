from collections import deque
from typing import Dict, Optional
import astroid
import warnings


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


class Interface:
    pass


TYPE_MAP: Dict[str, str] = {
    "bool": "boolean",
    "str": "string",
    "int": "number",
    "float": "number",
    "complex": "number",
}


def has_dataclass_decorator(decorators: Optional[astroid.Decorators]) -> bool:
    if not decorators:
        return False

    return any(
        (getattr(decorator.func, "name", None) == "dataclass")
        if isinstance(decorator, astroid.Call)
        else decorator.name == "dataclass"
        for decorator in decorators.nodes
    )


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
