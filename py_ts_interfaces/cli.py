import argparse
import os
import warnings
from collections import deque
from typing import Iterable, List, Set

from py_ts_interfaces import Interface, Parser


def main() -> None:
    args = get_args_namespace()
    if os.path.isdir(args.outpath):
        raise Exception(f"{args.outpath} is a directory! Aborting.")

    interface_parser = Parser(f"{Interface.__module__}.{Interface.__name__}")

    for code in read_code_from_files(get_paths_to_py_files(args.paths)):
        interface_parser.parse(code)

    result = interface_parser.flush()
    if not result:
        warnings.warn("Did not have anything to write to the file!", UserWarning)

    if not args.should_append or not os.path.isfile(args.outpath):
        with open(args.outpath, "w") as f:
            f.write(
                "// Generated using py-ts-interfaces.\n"
                "// See https://github.com/cs-cordero/py-ts-interfaces\n\n"
            )
            f.write(result)
        print(f"Created {args.outpath}!")
    else:
        with open(args.outpath, "a") as f:
            f.write(result)
        print(f"Appended to {args.outpath}!")


def get_args_namespace() -> argparse.Namespace:
    argparser = argparse.ArgumentParser(
        description="Generates TypeScript Interfaces from subclasses of"
        " py_ts_interfaces.Interface."
    )
    argparser.add_argument("paths", action="store", nargs="+")
    argparser.add_argument(
        "-o, --outpath", action="store", default="interface.ts", dest="outpath"
    )
    argparser.add_argument("-a, --append", action="store_true", dest="should_append")
    return argparser.parse_args()


def get_paths_to_py_files(raw_paths: List[str]) -> Set[str]:
    paths: Set[str] = set()
    queue = deque(raw_paths)
    while queue:
        path = queue.popleft()
        if os.path.isfile(path):
            if path.endswith(".py"):
                paths.add(path)
            continue

        if os.path.isdir(path):
            queue.extend(
                [os.path.join(path, next_path) for next_path in os.listdir(path)]
            )
            continue

        warnings.warn(f"Skipping {path}!", UserWarning)
    return paths


def read_code_from_files(paths: Iterable[str]) -> Iterable[str]:
    for path in paths:
        with open(path, "r") as f:
            yield f.read()


if __name__ == "__main__":
    main()
