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
) -> tuple[str, str, str, str | None]:
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
        2 PRINT "simple"; (3*(1+2) - 1) / 2; "."
        3 PRINT "negative "; 6-10; "."
        4 PRINT "float"; (3*(1+2) - 1) / 3; "."
        5 PRINT "unary "; -1; +3.14; "."
        6 print "exp"; 2^3^2; (2^3)^2; 2^(3^2); "."
        """,
        """
        simple 4 .
        negative -4 .
        float 2.6666667 .
        unary -1  3.14 .
        exp 512  64  512 .
        """,
    ),
    # Comparisons
    program(
        """
        1 PRINT "eq "; 0 =  0; 0 =  1; 1 =  0; "X" =  "X"; "X" =  "Y"; "Y" =  "X"; "."
        2 PRINT "ne "; 0 <> 0; 0 <> 1; 1 <> 0; "X" <> "X"; "X" <> "Y"; "Y" <> "X"; "."
        3 PRINT "lt "; 0 <  0; 0 <  1; 1 <  0; "X" <  "X"; "X" <  "Y"; "Y" <  "X"; "."
        4 PRINT "le "; 0 <= 0; 0 <= 1; 1 <= 0; "X" <= "X"; "X" <= "Y"; "Y" <= "X"; "."
        5 PRINT "gt "; 0 >  0; 0 >  1; 1 >  0; "X" >  "X"; "X" >  "Y"; "Y" >  "X"; "."
        6 PRINT "ge "; 0 >= 0; 0 >= 1; 1 >= 0; "X" >= "X"; "X" >= "Y"; "Y" >= "X"; "."
        """,
        """
        eq -1  0  0 -1  0  0 .
        ne  0 -1 -1  0 -1 -1 .
        lt  0 -1  0  0 -1  0 .
        le -1 -1  0 -1 -1  0 .
        gt  0  0 -1  0  0 -1 .
        ge -1  0 -1 -1  0 -1 .
        """,
    ),
    program(
        """
        10 X = 1: Y = 2
        20 Print "not " NOT X = Y; "."
        30 Print "and " X = X and X = Y; "."
        40 Print "or  " X = X or X = Y; "."
        """,
        """
        not -1 .
        and  0 .
        or  -1 .
        """,
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
    # No separator is the same as a semicolon
    program(
        """
        6 PRINT "Z" 1 "A" 3 "X"
        """,
        "Z 1 A 3 X\n",
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
        20 For I = 5 to 1 step -1
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
        error="!Expected TO, saw 10 on line 10: '10'",
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
        "What? \nHello there    12            3.14159 \n",
        input="""
        "Hello there",  12, 3.14159
        """,
    ),
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        "What? \n?? \nHello          12            3.14159 \n",
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
        "What? \n!Extra input ignored\nHello          12            3.14159 \n",
        input="""
        Hello, 12, 3.14159, 1, 2, 3, 4
        """,
    ),
    program(
        """
        10 INPUT "What"; x$, y%, z
        20 PRINT x$, y%, z
        """,
        "What? \n!Number expected - retry input line\n? \nGoodbye        34            2.71828 \n",
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
    # Type mismatches
    program(
        '10 print "Hi" + 1',
        error="!Type mismatch for + on line 10",
    ),
    program(
        '10 print 10 * (4 - 3 * ("Hi" + 1))',
        error="!Type mismatch for + on line 10",
    ),
    # Functions
    program(
        """
        10 print "abs"; abs(10.1); abs(-10.1); abs(10); "."
        20 print "asc"; asc("Hello"); "."
        30 print "atn"; atn(10.5); "."
        40 print "chr$ "; chr$(72); chr$(73.4); "."
        50 print "cos "; cos(10.5); "."
        60 print "exp"; exp(10.5); "."
        70 print "int"; int(10); int(10.4); int(-10.4); "."
        80 print "left$ "; left$("Hello", 3); "x"; left$("Hello", 99); "x"; left$("Hello", 0); "."
        90 print "left$ "; left$("Hello", 3.14); "."
        100 print "len"; len("Hello"); len(""); "."
        110 print "log"; log(10.5); "."
        120 print "mid$ "; mid$("Abcdef", 3); "x"; mid$("Abcdef", 3, 2); "x"; mid$("Abcdef", 3, 0); "."
        130 print "right$ "; right$("Abcdef", 3); "x"; right$("Abcdef", 999); "x"; right$("Abcdef", 0); "."
        140 print "right$ "; right$("Abcdef", 3.14); "."
        150 print "sgn"; sgn(10.5); sgn(0); sgn(-10.5); "."
        160 print "sin "; sin(10.5); "."
        170 print "spc "; "x"; spc(10); "x"; spc(0); "x"; spc(2.3); "."
        180 print "sqr"; sqr(10.5); "."
        190 print "str$"; str$(10); str$(10.543); str$(-10.5); "."
        200 print "tab"; tab(10); "x"; tab(15); "x"; tab(5); "x"
        210 print "tan"; tan(10.5); "."
        220 print "val"; val("3.14159"); val("Hello"); "."
        """,
        """
        abs 10.1  10.1  10 .
        asc 72 .
        atn 1.4758446 .
        chr$ HI.
        cos -0.47553693 .
        exp 36315.503 .
        int 10  10 -11 .
        left$ HelxHellox.
        left$ Hel.
        len 5  0 .
        log 2.3513753 .
        mid$ cdefxcdx.
        right$ defxAbcdefx.
        right$ def.
        sgn 1  0 -1 .
        sin -0.87969576 .
        spc x          xx  .
        sqr 3.2403703 .
        str$ 10 10.543-10.5.
        tab       x    xx
        tan 1.8499 .
        val 3.14159  0 .
        """,
    ),
    program(
        """
        10 print "rnd(0):"; rnd(0); "."
        20 print "rnd(1):"; rnd(1); rnd(0); "."
        30 print "rnd(-1):"; rnd(-1); rnd(1); rnd(0); "."
        """,
        """
        rnd(0): 0 .
        rnd(1): 0.19236379  0.19236379 .
        rnd(-1): 0.13436424  0.84743374  0.84743374 .
        """,
    ),
    program(
        """
        10 print abs("Hello")
        """,
        error="!Type mismatch for ABS on line 10",
    ),
    program(
        """
        10 print abs(10, 20)
        """,
        error="!Wrong number of arguments for ABS on line 10",
    ),
    program(
        """
        10 print asc("")
        """,
        error="!Invalid argument for ASC on line 10",
    ),
    program(
        """
        10 print asc(10)
        """,
        error="!Type mismatch for ASC on line 10",
    ),
    program(
        """
        10 print left$("Hello", -1)
        """,
        error="!Invalid argument for LEFT$ on line 10",
    ),
    program(
        """
        10 print mid$("Hello", -1)
        """,
        error="!Invalid argument for MID$ on line 10",
    ),
    program(
        """
        10 print mid$("Hello", 0)
        """,
        error="!Invalid argument for MID$ on line 10",
    ),
    program(
        """
        10 print mid$("Hello", 1, -1)
        """,
        error="!Invalid argument for MID$ on line 10",
    ),
    program(
        """
        10 print mid$("Hello")
        """,
        error="!Wrong number of arguments for MID$ on line 10",
    ),
    program(
        """
        10 print mid$("Hello", 1, 2, 3)
        """,
        error="!Wrong number of arguments for MID$ on line 10",
    ),
    program(
        """
        10 print mid$(123, 1, 2)
        """,
        error="!Type mismatch for MID$ on line 10",
    ),
    program(
        """
        10 print right$("Hello", -1)
        """,
        error="!Invalid argument for RIGHT$ on line 10",
    ),
    program(
        """
        10 print spc(-1)
        """,
        error="!Invalid argument for SPC on line 10",
    ),
    program(
        """
        10 print sqr(-1)
        """,
        error="!Invalid argument for SQR on line 10",
    ),
    program(
        """
        10 print str$("Hello")
        """,
        error="!Type mismatch for STR$ on line 10",
    ),
    program(
        """
        10 print val(3.14159)
        """,
        error="!Type mismatch for VAL on line 10",
    ),
    # If
    program(
        """
        10 if 1 = 1 then print "equal": print "nice"
        20 print "done part 1"
        30 if 1 <> 1 then print "wrong!"
        40 print "done part 2"
        50 if 1 = 1 then 70
        60 print "weird"
        70 print "done part 3"
        """,
        """
        equal
        nice
        done part 1
        done part 2
        done part 3
        """,
    ),
    program(
        """
        10 if chr$(72) then print "What!?"
        """,
        error="!Type mismatch for IF on line 10",
    ),
    # Stop/End
    program(
        """
        10 print "Hello"
        20 end
        30 print "more"
        """,
        "Hello\n",
    ),
    program(
        """
        10 print "Hello"
        20 stop
        30 print "more"
        """,
        "Hello\n",
    ),
    program(
        """
        10 print "Hello": stop: print "more"
        """,
        "Hello\n",
    ),
]

EXAMPLES = [
    # Vintage-basic examples
    program(
        "./tests/examples/diamond.bas",
        "./tests/examples/diamond.out",
    ),
    program(
        "./tests/examples/name.bas",
        "./tests/examples/ned.out",
        input="./tests/examples/ned.in",
    ),
    program(
        "./tests/examples/math.bas",
        "./tests/examples/math.out",
        input="./tests/examples/math.in",
    ),
    program(
        "./tests/examples/strings.bas",
        "./tests/examples/strings.out",
        input="./tests/examples/strings.in",
    ),
    program(
        "./tests/examples/stars.bas",
        "./tests/examples/stars.out",
        input="./tests/examples/stars.in",
    ),
]


@pytest.mark.parametrize(
    "source, output, input, error",
    TEST_PROGRAMS + EXAMPLES,
)
def test_program(source, output, input, error):
    outstream = io.StringIO()
    instream = io.StringIO(input)
    try:
        prog = Parser(source).parse()
        Interpreter(prog, instream=instream, outstream=outstream).run()
    except AcidicaError as e:
        assert str(e) == error
    else:
        assert error is None
    assert outstream.getvalue() == output
