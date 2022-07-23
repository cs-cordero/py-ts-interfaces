# Contributing

If you're here, that means you're either me in the future, or you're actually someone who wants to help improve this project!  I'm so glad you're here.

## Getting Setup

This project relies on [pyenv](https://github.com/pyenv/pyenv) for managing Python versions and [Poetry](https://python-poetry.org/) for managing dependencies (and publishing).

Check out their documentation respectively to get set up for your system.  Once they're set up, pull down this respository and you can get started right away.

```shell
$ cd /path/to/where/you/want/this/project
$ git clone https://github.com/cs-cordero/py-ts-interfaces
$ cd py-ts-interfaces
$
$ pyenv local [at least 3.7.2]
$ poetry install
```

From here, you're good to go!

## Running tests

### Unit tests for your current Python package

There is a helpful shell script called [run_tests.sh](./run_tests.sh) that will execute all tests: code quality, type checking, and pytests.

```shell
$ poetry run ./run_tests.sh
```

This will only run the test suite for your current Python package.  It's a quick way to check that you're on the right track, though.

Poetry has [facilities for switching Python versions if you've got them installed on your computer](https://python-poetry.org/docs/managing-environments/#switching-between-environments).  See their documentation for how that works.  Once you swap environments, you can just re-run the shell script.

### Nox tests

This package uses [nox](https://nox.thea.codes/en/stable/index.html) for executing the test suite against all supported python versions.  Its configuration is found in the [noxfile.py](./noxfile.py).

```shell
$ poetry run nox
```

There are some setup details you'll need to remember to do before `nox` can run successfully.  Specifically, your computer needs to have the supported Python minor versions installed.  See the [noxfile.py](./noxfile.py) for the full list of supported python versions.

```shell
$ pyenv install 3.7.x  # replace x with the latest patch version
$ pyenv install 3.8.x
$ # ...rest of the supported versions...
$
$ pyenv local 3.9.x 3.8.x 3.7.x
$ poetry run nox
```

### Continuous Integration

This project leverages GitHub Actions for continuous integration tests, meaning once you make a pull request, it'll run the test suite for supported python versions right there in the PR.  The configuration for the github action is at [./.github/workflows/pythonpackage.yml](./.github/workflows/pythonpackage.yml).
