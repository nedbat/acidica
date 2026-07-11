import dataclasses
import re
from typing import Iterator


@dataclasses.dataclass
class Token:
    kind: str
    text: str


KEYWORDS = "|".join("""
    DATA DEF FN DIM END FOR TO STEP GO SUB IF THEN INPUT LET NEXT ON PRINT 
    RANDOMIZE READ RESTORE RETURN STOP

    ABS ASC ATN CHR$ COS EXP INT LEFT$ LEN LOG MID$ RIGHT$ RND SGN SIN SPC SQR
    STR TAB TAN VAL

    NOT AND OR
    """.split())

TOKENS = rf"""(?xm)
    (?:
        (REM.*$)                                            |
        (?P<lparen>\()                                      |
        (?P<rparen>\))                                      |
        (?P<comma>,)                                        |
        (?P<colon>:)                                        |
        (?P<semicolon>;)                                    |
        (?P<key>{KEYWORDS})                                 |
        (?P<var>[A-Z]+[0-9]*[$%]?)                          |
        (?P<num>[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)     |
        (?P<str>"[^"]*")                                    |
        (?P<op>-|\+|\^|\*|/|=|<>|<=|>=|<|>)                 |
        (?P<eol>$)                                          |
        [ ]                                                 |
        (?P<err>.)
    )
    """


def tokenize(text: str) -> Iterator[Token]:
    matches = re.finditer(TOKENS, text)
    toks = (Token(m.lastgroup, m.group()) for m in matches if m.lastgroup)
    return toks
