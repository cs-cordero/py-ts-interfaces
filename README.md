# py-ts-interfaces
### Python to TypeScript Interfaces

![MIT License](https://img.shields.io/github/license/cs-cordero/py-ts-interfaces)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/cs-cordero/py-ts-interfaces/Continuous%20Integration)
![PyPI](https://img.shields.io/pypi/v/py-ts-interfaces)

## What is this?

This library provides utilities that convert Python dataclasses with type
annotations to a TypeScript `interface` and serializes them to a file.

## Installation

```
python --version  # requires 3.7+
pip install py-ts-interfaces
```

## Motivation

In web applications where Python is used in the backend and TypeScript is used
in the frontend, it is often the case that the client will make calls to the
backend to request some data with some specific pre-defined "shape".  On the
client-side, an `interface` for this data is usually defined and if the Python
backend authors use typechecking, like with [mypy](http://mypy-lang.org/), the
project authors may be typing the JSON response values as well.

This results in a duplication of code.  If the shape changes in the backend,
the related interface must also be reflect its changes in the frontend.  At
best, this is annoying to maintain.  At worst, over time the interfaces may
diverge and cause bugs.

This library aims to have a single source of truth that describes the shape of
the payload between the backend and the frontend.

## Usage

In Python, `py-ts-interfaces` exposes a new class object called `Interface`.
By subclassing this object, you identify to the also-packaged script that you
want it to be serialized to an interface file.

1. First, hook up your dataclasses:

```python
# views.py
from dataclasses import dataclass
from py_ts_interfaces import Interface

@dataclass
class MyComponentProps(Interface):
    name: str
    show: bool
    value: float

@dataclass
class WillNotGetPickedUp:  # this doesn't subclass Interface, so it won't be included
    name: str
    value: float
```

2. In your shell, run the included command and pass in the name of the file or
   directory you want to use.  By default it will output to a file in your
   directory called interface.ts
```
$ py-ts-interfaces views.py
Created interface.ts!
```

You may also use the following arguments:
* `-o, --output [filepath]`:  where the file will be saved. default is `interface.ts`.
* `-a, --append`:  by default each run will overwrite the output file. this flag
allows only appends.  Be warned, duplicate interfaces are not tested.


3. The resulting file will look like this:
```typescript
// interface.ts
interface MyComponentProps {
    name: string;
    show: boolean;
    value: number;
}
```

## Why @dataclass?

`Dataclass`es were introduced in Python 3.7 and they are great.  Some
alternatives that I have seen other codebases using are `NamedTuple` and
`TypedDict`.  All of these objects attempt to do the same thing: group together
pieces of data that belong close together like a struct.

However, `dataclass` won out over the other two for the following reasons:
1. dataclasses are built-in to Python.  As of writing, `NamedTuple` is also
   built-in to the `typing` module, but `TypedDict` is still considered
   experimental.
2. dataclasses cannot be declared and defined inline like you can do with
   `NamedTuple` and `TypedDict`, e.g., `NamedTuple` can be defined using class
   inheritance like `class MyNamedTuple(NamedTuple): ...`, but also like
   `MyNamedTuple = NamedTuple('MyNamedTuple', [('name', str), ('id', int)])`.
   This is a good thing.  Dataclasses require you to use a class style
   declaration, which not only looks closer to a TypeScript interface
   declaration, but it avoids the complex metaclass machinery that NamedTuples
   and TypedDicts use to gain all its features.  Since this library uses the
   AST and static analysis of the code to determine what data to serialize,
   this makes the choice a no-brainer.
3. dataclasses can be made to be immutable (mostly) by setting `frozen=True`.
   This library does not require it but in later versions we may provide a
   `partial`ed dataclass decorator that guarantees immutability.
4. Because we avoid the metaclass machinery of NamedTuples and TypedDicts, it
   opens up the possibility of writing custom classes that allows `mypy` to
   typecheck it one way, but gives the AST parser some clues in order to
   generate TypeScript types that cannot easily be expressed in Python.

## Why define the types in Python instead of TypeScript?

TypeScript is significantly more mature for typing syntax than Python.
Generally speaking, you can express any type that Python can do in TypeScript,
but _not_ vice versa.

So defining the types in Python guarantee that you can also express the whole
interface in both languages.

## Supported Type Mappings
Please note that usage of `T` `U` and `V` in the table below represent
stand-ins for actual types.  They do not represent actually using generic typed
variables.

| Python                          | Typescript                    |
|:-------------------------------:|:-----------------------------:|
| None                            | null                          |
| str                             | string                        |
| int                             | number                        |
| float                           | number                        |
| complex                         | number                        |
| bool                            | boolean                       |
| List                            | Array\<any\>                  |
| Tuple                           | [any]                         |
| Dict                            | Record<any, any>              |
| List[T]                         | Array[T]                      |
| Tuple[T, U]                     | [T, U]                        |
| Dict[T, U]                      | Record<T, U>                  |
| Optional[T]                     | T \| null                     |
| Union[T, U, V]                  | T \| U \| V                   |

## Planned Supported Mappings

* String literals
* Undefined type
* isNaN type
* ReadOnly types
* Excess Properties

## Unsupported/Rejected Mappings

The primary purpose of this library is to help type, first and foremost, _data_
moving back and forth from client to server.  Many of these features, whether they be specific to TypeScript or Python, would be overkill to support.

* void
* callables/functions
* enums
* Dates, datetime, dates, times (send these over as strings and convert them to richer objects on the client)
* extends
* generics, TypeVars
* intersection types
* mapped types
* conditional types
* classes

## Contributing

Interested in contributing?  You're awesome!  It's not much, but here's some notes to get you started [CONTRIBUTING.md](CONTRIBUTING.md).

## Author

[Christopher Sabater Cordero](https://chrisdoescoding.com)
