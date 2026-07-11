from textwrap import dedent

import pytest

from acidic.tokens import Token, tokenize


@pytest.mark.parametrize(
    "text, toks",
    [
        (
            dedent("""\
                GOSUB 120
                REM A comment
                X = Y + 2
                """),
            [
                Token(kind="key", text="GO"),
                Token(kind="key", text="SUB"),
                Token(kind="num", text="120"),
                Token(kind="eol", text=""),
                Token(kind="eol", text=""),
                Token(kind="var", text="X"),
                Token(kind="op", text="="),
                Token(kind="var", text="Y"),
                Token(kind="op", text="+"),
                Token(kind="num", text="2"),
                Token(kind="eol", text=""),
                Token(kind="eol", text=""),
            ],
        ),
    ],
)
def test_tokenize(text, toks):
    assert list(tokenize(text)) == toks
