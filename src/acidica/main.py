import pprint
import sys
import textwrap
from pathlib import Path

from .exceptions import AcidicaError
from .parser import Parser
from .interpreter import Interpreter


def main():
    if len(sys.argv) > 1:
        source = Path(sys.argv[1]).read_text()
    else:
        source = textwrap.dedent("""\
            60 input "Hello"; x
        """)
    try:
        prog = Parser(source).parse()
        pprint.pprint(prog.lines)
        print("-" * 40)
        Interpreter(prog, sys.stdin, sys.stdout).run()
    except AcidicaError as e:
        print(str(e))
