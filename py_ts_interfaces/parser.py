from collections import deque
from typing import Optional
import astroid
import warnings


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


class Interface:
    pass


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

            self.write_ast_node_to_interface(current)

    def write_ast_node_to_interface(self, node: astroid.ClassDef) -> None:
        pass
