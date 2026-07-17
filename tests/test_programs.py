import io
import re
import textwrap
from pathlib import Path

import pytest

from acidica.exceptions import AcidicaError
from acidica.parser import Parser
from acidica.interpreter import Interpreter


def easy_text(text: str) -> str:
    if text:
        if re.search(r"\s", text):
            # White space in string: it's the data.
            if text[0] == "\n":  # Remove a first newline
                text = text[1:]
            text = textwrap.dedent(text)
        else:
            # One-line string: it's a file name.
            text = Path(text).read_text()
    return text


def program(
    source: str,
    output: str,
    *,
    error: str | None = None,
) -> tuple[str, str, str | None]:
    return (easy_text(source), easy_text(output), error)


TEST_PROGRAMS = [
    # First program
    program(
        """
        10 PRINT "hello": GOTO 30
        20 PRINT "boo"
        30 PRINT 1+2+3
        """,
        "hello\n 6 \n",
    ),
    # Spaces aren't needed
    program(
        """
        10PRINT"hello":GOTO30
        20PRINT"boo"
        30PRINT1+2+3
        """,
        "hello\n 6 \n",
    ),
    # Keywords are case-insensitive
    program(
        """
        10print"hello":GoTo30
        20Print"boo"
        30pRiNt1+2+3
        """,
        "hello\n 6 \n",
    ),
    # Lines are run in the order of their numbers.
    program(
        """
        20 PRINT "boo"
        30 PRINT 1+2+3
        10 PRINT "hello": GOTO 30
        """,
        "hello\n 6 \n",
    ),
    # Arithmetic
    program(
        """
        1 PRINT "look:"
        2 PRINT (3*(1+2) - 1) / 2
        3 PRINT 6-10
        4 PRINT (3*(1+2) - 1) / 3
        5 PRINT "bye"
        """,
        "look:\n 4 \n-4 \n 2.6666667 \nbye\n",
    ),
    # Semicolons control spacing
    program(
        """
        3 PRINT;;
        4 PRINT"hi";
        5 PRINT"there"
        6 PRINT1;2;;3;"X"
        """,
        "hithere\n 1  2  3 X\n",
    ),
    # Commas jump to the next 14-space zone
    program(
        """
        10 PRINT "X", "Y", "Z"
        20 PRINT "XX", "YY", "ZZ"
        30 PRINT "AAAAAAAAAAAAAAHAA", "YY", "ZZ"
        32 PRINT "AAAAAAAAAAAAA", "YY", "ZZ"
        35 PRINT "AAAAAAAAAAAAAA", "YY", "ZZ"
        40 PRINT ,"ZZZ"
        50 PRINT ,,"AA",
        60 PRINT "XYZ"
        """,
        """
        X             Y             Z
        XX            YY            ZZ
        AAAAAAAAAAAAAAHAA           YY            ZZ
        AAAAAAAAAAAAA YY            ZZ
        AAAAAAAAAAAAAA              YY            ZZ
                      ZZZ
                                    AA            XYZ
        """,
    ),
    # Error handling
    program(
        "17 PRINT LET",
        "",
        error="!Syntax error on line 17: 'LET'",
    ),
    program(
        "PRINT 10",
        "",
        error="!No line number: 'PRINT'",
    ),
    program(
        """
        10 PRINT 10
        10 PRINT 20
        """,
        "",
        error="!Duplicate line number 10",
    ),
    program(
        "999 GO TO PRINT",
        "",
        error="!Syntax error on line 999: 'PRINT'",
    ),
    program(
        "999 GO 123",
        "",
        error="!Syntax error on line 999: '123'",
    ),
    program(
        "9999 1234",
        "",
        error="!Syntax error on line 9999: '1234'",
    ),
    program(
        """
        100 print "hello"
        101 print 1/0
        """,
        "hello\n",
        error="!Division by zero on line 101",
    ),
]


@pytest.mark.parametrize(
    "source, output, error",
    TEST_PROGRAMS,
)
def test_program(source, output, error):
    outstream = io.StringIO()
    try:
        prog = Parser(source).parse()
        Interpreter().run(prog, instream=None, outstream=outstream)
    except AcidicaError as e:
        assert str(e) == error
    else:
        assert error is None
    assert outstream.getvalue() == output
