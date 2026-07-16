import dataclasses
import re
from typing import Iterator


@dataclasses.dataclass
class Token:
    kind: str
    text: str

    def value(self):
        match self.kind:
            case "num":
                try:
                    return int(self.text)
                except ValueError:
                    return float(self.text)

            case "str":
                return self.text[1:-1]

            case _:
                return self.text


KEYWORDS = "|".join("""
    DATA DEF FN DIM END FOR TO STEP GO SUB IF THEN INPUT LET NEXT ON PRINT 
    RANDOMIZE READ RESTORE RETURN STOP
    """.split())

FUNCTIONS = "|".join("""
    ABS ASC ATN CHR$ COS EXP INT LEFT$ LEN LOG MID$ RIGHT$ RND SGN SIN SPC SQR
    STR TAB TAN VAL
    """.split())

OPWORDS = "|".join("NOT AND OR".split())

TOKENS = rf"""(?xm)
    (?:
        (REM.*$)                                            |
        (?P<lparen>\()                                      |
        (?P<rparen>\))                                      |
        (?P<comma>,)                                        |
        (?P<colon>:)                                        |
        (?P<semicolon>;)                                    |
        (?P<key>{KEYWORDS})                                 |
        (?P<fn>{FUNCTIONS})                                 |
        (?P<var>[A-Z]+[0-9]*[$%]?)                          |
        (?P<num>[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)          |
        (?P<str>"[^"]*")                                    |
        (?P<op>-|\+|\^|\*|/|=|<>|<=|>=|<|>|{OPWORDS})       |
        (?P<eol>$)                                          |
        [ ]                                                 |
        (?P<err>.)
    )
    """


def tokenize(text: str) -> Iterator[Token]:
    matches = re.finditer(TOKENS, text)
    return (Token(m.lastgroup, m.group()) for m in matches if m.lastgroup)
