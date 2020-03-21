from copy import deepcopy
from itertools import count
from unittest.mock import patch

import pytest
from astroid import extract_node

from py_ts_interfaces import Interface, Parser
from py_ts_interfaces.parser import (
    PossibleInterfaceReference,
    ensure_possible_interface_references_valid,
    get_types_from_classdef,
    parse_annassign_node,
)
from py_ts_interfaces.tests import utils


@pytest.fixture(scope="module")
def interface_qualname():
    return f"{Interface.__module__}.{Interface.__qualname__}"


PYTHON_VERSION = utils.get_version()


TEST_ONE = """
    class Foo:
        pass
"""
TEST_TWO = """
    from py_ts_interfaces import Interface

    class Foo(Interface):
        pass
"""
TEST_THREE = """
    from dataclasses import dataclass
    from py_ts_interfaces import Interface

    @dataclass
    class Foo(Interface):
        pass
"""
TEST_FOUR = """
    from dataclasses import dataclass
    from py_ts_interfaces import Interface

    @dataclass
    class Foo(Interface):
        pass

    @dataclass
    class Bar(Interface):
        pass

    class Baz(Interface):
        pass

    class Parent:
        class Child1(Interface):
            pass

        @dataclass
        class Child2(Interface):
            pass
"""
TEST_FIVE = """
    from dataclasses import dataclass

    class Interface:
        pass

    class Foo(Interface):
        pass

    @dataclass
    class Bar(Interface):
        pass
"""

if PYTHON_VERSION < 3.8:
    TEST_SIX = """
        from dataclasses import dataclass
        from py_ts_interfaces import Interface

        @dataclass  #@
        class Foo(Interface):
            aaa: str
            bbb: int
            ccc: bool
            ddd = 100

            def foo(self) -> None:
                pass
    """
    TEST_SEVEN = """
        from dataclasses import dataclass
        from py_ts_interfaces import Interface

        @dataclass  #@
        class Foo(Interface):
            def foo(self) -> None:
                pass

            aaa: str = 'hello'
            bbb: int = 5
            ccc: bool = True
    """
else:
    TEST_SIX = """
        from dataclasses import dataclass
        from py_ts_interfaces import Interface

        @dataclass
        class Foo(Interface):  #@
            aaa: str
            bbb: int
            ccc: bool
            ddd = 100

            def foo(self) -> None:
                pass
    """
    TEST_SEVEN = """
        from dataclasses import dataclass
        from py_ts_interfaces import Interface

        @dataclass
        class Foo(Interface):  #@
            def foo(self) -> None:
                pass

            aaa: str = 'hello'
            bbb: int = 5
            ccc: bool = True
    """

TEST_EIGHT = """
    from dataclasses import dataclass
    from py_ts_interfaces import Interface

    @dataclass
    class Foo(Interface):
        aaa: str

    @dataclass
    class Foo(Interface):
        bbb: int
"""

TEST_NINE = """
    from dataclasses import dataclass
    from py_ts_interfaces import Interface

    @dataclass
    class Foo(Interface):
        aaa: str

    @dataclass
    class Bar(Interface):
        bbb: int
        foo: Foo
"""

TEST_TEN = """
    from dataclasses import dataclass
    from py_ts_interfaces import Interface

    @dataclass
    class One(Interface):
        aaa: str

    @dataclass
    class Two(Interface):
        bbb: int
        one: One

    @dataclass
    class Three(Interface):
        bbb: int
        two: Two

    @dataclass
    class All(Interface):
        bbb: int
        one: One
        two: Two
        three: Three
"""


@pytest.mark.filterwarnings("ignore::UserWarning")
@pytest.mark.parametrize(
    "code, expected_call_count",
    [
        (TEST_ONE, 0),
        (TEST_TWO, 0),
        (TEST_THREE, 1),
        (TEST_FOUR, 3),
        (TEST_FIVE, 0),
        (TEST_EIGHT, 1),
        (TEST_NINE, 2),
        (TEST_TEN, 4),
    ],
)
def test_parser_parse(code, expected_call_count, interface_qualname):
    parser = Parser(interface_qualname)
    with patch("py_ts_interfaces.parser.get_types_from_classdef") as mock_writer:
        parser.parse(code=code)
        assert mock_writer.call_count == expected_call_count


@pytest.mark.parametrize(
    "prepared_mocks, expected",
    [
        ({"abc": {"def": "ghi"}}, """interface abc {\n    def: ghi;\n}"""),
        (
            {"abc": {"def": "ghi", "jkl": "mno"}},
            """interface abc {\n    def: ghi;\n    jkl: mno;\n}""",
        ),
        ({"abc": {}}, """interface abc {\n}"""),
        (
            {"abc": {"def": PossibleInterfaceReference("ghi")}, "ghi": {"jkl": "mno"}},
            """interface abc {\n    def: ghi;\n}\n\n"""
            """interface ghi {\n    jkl: mno;\n}""",
        ),
    ],
)
def test_parser_flush(prepared_mocks, expected, interface_qualname):
    parser = Parser(interface_qualname)
    parser.prepared = prepared_mocks
    assert parser.flush() == expected


@pytest.mark.filterwarnings("ignore::UserWarning")
@pytest.mark.parametrize(
    "node, expected",
    [
        (extract_node("baz: str"), ("baz", "string")),
        (extract_node("ace: int"), ("ace", "number")),
        (extract_node("ace: float"), ("ace", "number")),
        (extract_node("ace: complex"), ("ace", "number")),
        (extract_node("ace: bool"), ("ace", "boolean")),
        (extract_node("ace: Any"), ("ace", "any")),
        (extract_node("foo: List"), ("foo", "Array<any>")),
        (extract_node("bar: Tuple"), ("bar", "[any]")),
        (extract_node("foo: List[str]"), ("foo", "Array<string>")),
        (extract_node("bar: Tuple[str, int]"), ("bar", "[string, number]")),
        (extract_node("baz: Optional[str]"), ("baz", "string | null")),
        (extract_node("ace: Optional[int]"), ("ace", "number | null")),
        (extract_node("ace: Optional[float]"), ("ace", "number | null")),
        (extract_node("ace: Optional[complex]"), ("ace", "number | null")),
        (extract_node("ace: Optional[bool]"), ("ace", "boolean | null")),
        (extract_node("ace: Optional[Any]"), ("ace", "any | null")),
        (
            extract_node("bar: Optional[Tuple[str, int]]"),
            ("bar", "[string, number] | null"),
        ),
        (
            extract_node("bar: Tuple[List[Optional[Tuple[str, int]]], str, int]"),
            ("bar", "[Array<[string, number] | null>, string, number]"),
        ),
        (extract_node("lol: Union[str, int, float]"), ("lol", "string | number")),
        (extract_node("lol: Union"), ("lol", "any")),
        (
            extract_node("whatever: 'StringForward'"),
            ("whatever", PossibleInterfaceReference("StringForward")),
        ),
        (
            extract_node("whatever: NakedReference"),
            ("whatever", PossibleInterfaceReference("NakedReference")),
        ),
        (extract_node("whatever: 1234"), ("whatever", "UNKNOWN")),
    ],
)
def test_parse_annassign_node(node, expected):
    assert parse_annassign_node(node) == expected


@pytest.mark.parametrize("code, expected_call_count", [(TEST_SIX, 0), (TEST_SEVEN, 0)])
def test_get_types_from_classdef(code, expected_call_count):
    classdef = extract_node(code)
    with patch("py_ts_interfaces.parser.parse_annassign_node") as annassign_parser:
        k, v = count(0, 2), count(1, 2)
        annassign_parser.side_effect = lambda x: (str(next(k)), str(next(v)))
        result = get_types_from_classdef(classdef)
        assert result == {"0": "1", "2": "3", "4": "5"}
        assert annassign_parser.call_count == 3


@pytest.mark.parametrize(
    "interfaces",
    [
        {"interfaceA": {"name": "str"}, "interfaceB": {"another_name": "int"}},
        {
            "interfaceA": {"name": PossibleInterfaceReference("interfaceB")},
            "interfaceB": {"another_name": "int"},
        },
        {"interfaceA": {"name": PossibleInterfaceReference("interfaceA")}},
    ],
)
def test_ensure_possible_interface_references_valid__succeeds(interfaces):
    copied_interfaces = deepcopy(interfaces)
    ensure_possible_interface_references_valid(interfaces)
    assert copied_interfaces == interfaces  # Make sure no mutations occurred


@pytest.mark.parametrize(
    "interfaces",
    [
        {
            "interfaceA": {"name": PossibleInterfaceReference("interfaceB")},
            "interfaceB": {"another_name": PossibleInterfaceReference("interfaceC")},
        },
        {"interfaceA": {"name": PossibleInterfaceReference("interfaceB")}},
    ],
)
def test_ensure_possible_interface_references_valid__fails(interfaces):
    with pytest.raises(RuntimeError):
        ensure_possible_interface_references_valid(interfaces)
