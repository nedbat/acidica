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
            10 PRINT "hello": GOTO 30
            20 PRINT "boo"
            30 PRINT 1+2+3
            40 PRINT 1;2
            50 LET X = 1 +1
            60 PRINT X
        """)
    try:
        prog = Parser(source).parse()
        pprint.pprint(prog.lines)
        print("-" * 40)
        Interpreter().run(prog, None, sys.stdout)
    except AcidicaError as e:
        print(str(e))
