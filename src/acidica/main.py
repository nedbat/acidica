import argparse
import pprint
import sys
from pathlib import Path

from .exceptions import AcidicaError
from .parser import Parser
from .interpreter import Interpreter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", help="Trace the execution", action="store_true")
    parser.add_argument("file")
    args = parser.parse_args()

    source = Path(args.file).read_text()
    try:
        prog = Parser(source).parse()
        if 0:
            pprint.pprint(prog.lines)
            print("-" * 40)
        tracefn = print if args.trace else None
        Interpreter(prog, sys.stdin, sys.stdout, tracefn=tracefn).run()
    except AcidicaError as e:
        print(e)
