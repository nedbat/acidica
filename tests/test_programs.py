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
    output: str = "",
    *,
    input: str = "",
    error: str | None = None,
) -> tuple[str, str, str | None]:
    return (easy_text(source), easy_text(output), easy_text(input), error)


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
        error="!Syntax error on line 17: 'LET'",
    ),
    program(
        "PRINT 10",
        error="!No line number: 'PRINT'",
    ),
    program(
        """
        10 PRINT 10
        10 PRINT 20
        """,
        error="!Duplicate line number 10",
    ),
    program(
        "999 GO TO PRINT",
        error="!Syntax error on line 999: 'PRINT'",
    ),
    program(
        "999 GO 123",
        error="!Syntax error on line 999: '123'",
    ),
    program(
        "9999 1234",
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
    program(
        "10 PRINT (X+",
        error="!Expected rparen, saw eol on line 10",
    ),
    # Variables
    program(
        """
        10 LET X = 10 * (2 + 3)
        20 PRINT "fifty ="; X
        """,
        "fifty = 50 \n",
    ),
    program(
        "10 LET 12 = 10 + 2",
        error="!Syntax error on line 10: '12'",
    ),
    program(
        "10 LET X 24",
        error="!Syntax error on line 10: '24'",
    ),
    program(
        """
        10 REM undefined variables start as zero or empty string
        20 PRINT "empty:"; X; "and empty:"; X$; "."
        """,
        "empty: 0 and empty:.\n",
    ),
    # Types of values have to match type of variable
    program(
        """
        10 LET PI = 3.1416: LET PI$ = "pi": LET PI% = 3
        20 PRINT "PI ="; PI; "; PI$ = "; PI$; "; PI% ="; PI%
        """,
        "PI = 3.1416 ; PI$ = pi; PI% = 3 \n",
    ),
    program(
        """
        10 PI% = 3.14159: LOW% = 0-3.14159: PRINT "Nums:";PI%;LOW%
        """,
        "Nums: 3 -4 \n",
    ),
    program(
        '10 LET X = "hello"',
        error="!Incorrect type: can't assign 'hello' to X on line 10",
    ),
    program(
        '10 LET X% = "hello"',
        error="!Incorrect type: can't assign 'hello' to X% on line 10",
    ),
    program(
        "10 LET X$ = 12",
        error="!Incorrect type: can't assign 12 to X$ on line 10",
    ),
    # LET is implicit, and ? is the same as PRINT
    program(
        """
        10 PI = 3.1416: PI$ = "pi": PI% = 3
        20 ? "PI ="; PI; "; PI$ = "; PI$; "; PI% ="; PI%
        """,
        "PI = 3.1416 ; PI$ = pi; PI% = 3 \n",
    ),
    # In variable names, only the first two letters and the first digit are
    # significant
    program(
        """
        10 LINES12 = 13
        20 PRINT "lines12 ="; LIB100
        """,
        "lines12 = 13 \n",
    ),
    # For loops
    program(
        """
        20 print"numbers:";: For I = 1 to 5: print i;: next: print
        """,
        "numbers: 1  2  3  4  5 \n",
    ),
    program(
        """
        10 print "countdown:";
        20 For I = 5 to 1 step 1-2
        30 print i;
        40 next
        50 print
        """,
        "countdown: 5  4  3  2  1 \n",
    ),
    program(
        """
        5 print "numbers:";
        10 for i = 1 to 5
        20 for j = 1 to i
        30 print j;
        40 next
        50 print "."
        60 next
        """,
        """
        numbers: 1 .
         1  2 .
         1  2  3 .
         1  2  3  4 .
         1  2  3  4  5 .
        """,
    ),
    program(
        """
        10 print "Look:";
        20 for i% = 1.1 to 5.5 step 1.1
        30 print i%;
        40 next i%
        50 print "."
        """,
        "Look: 1  2  3  4  5 .\n",
    ),
    # Loop errors
    program(
        "10 for 12",
        error="!Syntax error on line 10: '12'",
    ),
    program(
        "10 for i 1 10",
        error="!Syntax error on line 10: '1'",
    ),
    program(
        "10 for i = 1 10",
        error="!Syntax error on line 10: '10'",
    ),
    program(
        "10 for i = 1 to 10 Step LET",
        error="!Syntax error on line 10: 'LET'",
    ),
    program(
        """
        10 next 3.14159
        """,
        error="!Syntax error on line 10: '3.14159'",
    ),
    # Named NEXT
    program(
        """
        5 print "LOOK:";
        10 for i = 1 to 5
        20 for j = 1 to 5
        30 print j;
        40 next i
        50 print
        """,
        "LOOK: 1  1  1  1  1 \n",
    ),
    program(
        """
        10 next i
        """,
        error="!No matching loop found on line 10",
    ),
    program(
        """
        10 for i = 1 to 10
        20 next j
        """,
        error="!No matching loop found on line 20",
    ),
    program(
        "10 for x$ = 1 to 10",
        error="!Incorrect type: can't assign 1 to X$ on line 10",
    ),
    # Input
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        """What? \nHello there    12            3.14159 \n""",
        input="""
        "Hello there",  12, 3.14159
        """,
    ),
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        """What? \n?? \nHello          12            3.14159 \n""",
        input="""
        Hello
        12, 3.14159
        """,
    ),
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        """What? \n!Extra input ignored\nHello          12            3.14159 \n""",
        input="""
        Hello, 12, 3.14159, 1, 2, 3, 4
        """,
    ),
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        """What? \n!Number expected - retry input line\n? \nGoodbye        34            2.71828 \n""",
        input="""
        Hello, 12.234, 3.14159
        Goodbye, 34, 2.71828
        """,
    ),
    # Input errors
    program(
        "10 INPUT",
        error="!Syntax error on line 10",
    ),
    program(
        '10 INPUT "What"',
        error="!Expected semicolon, saw eol on line 10",
    ),
    program(
        '10 INPUT "What";',
        error="!Syntax error on line 10",
    ),
    program(
        '10 INPUT "What";x,',
        error="!Syntax error on line 10",
    ),
    program(
        '10 INPUT "What";x 12.34',
        error="!Syntax error on line 10: '12.34'",
    ),
]


@pytest.mark.parametrize(
    "source, output, input, error",
    TEST_PROGRAMS,
)
def test_program(source, output, input, error):
    outstream = io.StringIO()
    instream = io.StringIO(input)
    try:
        prog = Parser(source).parse()
        Interpreter().run(prog, instream=instream, outstream=outstream)
    except AcidicaError as e:
        assert str(e) == error
    else:
        assert error is None
    assert outstream.getvalue() == output
