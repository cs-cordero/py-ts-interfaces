import sys


def get_version() -> float:
    if sys.version_info.major < 3 or sys.version_info.minor < 7:
        raise Exception("py-ts-interfaces only supports Python 3.7 or above.")

    return float(sys.version_info.major) + (sys.version_info.minor / 10)
