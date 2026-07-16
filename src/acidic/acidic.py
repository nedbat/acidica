import textwrap

from .parser import Parser
from .program import Interpreter

def main():
    import pprint

    prog = Parser(
        textwrap.dedent("""\
            10 PRINT "hello": GOTO 30
            20 PRINT "boo"
            30 PRINT 1+2+3
        """)
    ).parse()
    pprint.pprint(prog.lines)
    print("first: ", prog.first)
    print(prog.nexts)
    print("-" * 40)
    Interpreter().run(prog)
