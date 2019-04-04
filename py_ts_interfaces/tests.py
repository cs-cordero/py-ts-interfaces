from astroid import extract_node
from itertools import count
from py_ts_interfaces import Interface, Parser
from py_ts_interfaces.parser import parse_annassign_node, get_types_from_classdef
from unittest.mock import patch
import pytest


@pytest.fixture(scope="module")
def interface_qualname():
    return f"{Interface.__module__}.{Interface.__qualname__}"


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
    ],
)
def test_parse_annassign_node(node, expected):
    assert parse_annassign_node(node) == expected


@pytest.mark.parametrize("code, expected_call_count", [(TEST_SIX, 0)])
def test_get_types_from_classdef(code, expected_call_count):
    classdef = extract_node(code)
    with patch("py_ts_interfaces.parser.parse_annassign_node") as annassign_parser:
        k, v = count(0, 2), count(1, 2)
        annassign_parser.side_effect = lambda x: (str(next(k)), str(next(v)))
        result = get_types_from_classdef(classdef)
        assert result == {"0": "1", "2": "3", "4": "5"}
        assert annassign_parser.call_count == 3
