import io
import textwrap
from pathlib import Path

import pytest

from acidic.parser import Parser
from acidic.program import Interpreter


def easy_text(text: str) -> str:
    if "\n" in text:
        # Multi-line string: it's actual data.
        if text[0] == "\n":  # Remove a first newline
            text = text[1:]
        text = textwrap.dedent(text)
    else:
        # One-line string: it's a file name.
        text = Path(text).read_text()
    return text


def program(source: str, output: str) -> tuple[str, str]:
    return (easy_text(source), easy_text(output))


@pytest.mark.parametrize(
    "source, output",
    [
        # First program
        (
            """
            10 PRINT "hello": GOTO 30
            20 PRINT "boo"
            30 PRINT 1+2+3
            """,
            "hello\n6\n",
        ),
        # Spaces aren't needed
        (
            """
            10PRINT"hello":GOTO30
            20PRINT"boo"
            30PRINT1+2+3
            """,
            "hello\n6\n",
        ),
        # Lines are run in the order of their numbers.
        (
            """
            20 PRINT "boo"
            30 PRINT 1+2+3
            10 PRINT "hello": GOTO 30
            """,
            "hello\n6\n",
        ),
    ],
)
def test_program(source, output):
    outstream = io.StringIO()
    prog = Parser(source).parse()
    Interpreter().run(prog, instream=None, outstream=outstream)
    assert outstream.getvalue() == output
