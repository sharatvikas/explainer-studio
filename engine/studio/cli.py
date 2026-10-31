import argparse
import sys
from typing import Callable

from . import __version__

COMMANDS: dict[str, Callable[[argparse.Namespace], int]] = {}


def command(name):
    # handlers may set `fn.configure = <fn(parser)>` after decoration; read lazily in main()
    def deco(fn):
        COMMANDS[name] = fn
        return fn

    return deco


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="studio")
    ap.add_argument("--version", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    from . import commands  # noqa: F401  registers subcommands

    for name, fn in COMMANDS.items():
        getattr(fn, "configure", lambda p: None)(sub.add_parser(name))
    a = ap.parse_args(argv)
    if a.version:
        print(f"studio {__version__}")
        return 0
    if not a.cmd:
        ap.print_help()
        return 1
    return COMMANDS[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
