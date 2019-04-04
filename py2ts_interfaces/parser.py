from collections import deque
import astroid


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


class Interface:
    pass


class Parser:
    def __init__(self, interface_qualname: str, outpath: str = "interfaces.ts") -> None:
        self.interface = interface_qualname
        self.outpath = outpath

    def parse(self, *, code: str) -> None:
        queue = deque([astroid.parse(code)])
        while queue:
            current = queue.popleft()
            children = current.get_children()
            if not isinstance(current, astroid.node_classes.ClassDef):
                queue.extend(children)
                continue

            if not current.is_subtype_of(self.interface):
                queue.extend(children)
                continue

            self.write_ast_node_to_interface(current)

    def write_ast_node_to_interface(self, node: astroid.node_classes.ClassDef) -> None:
        pass
