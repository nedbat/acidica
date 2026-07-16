import pytest

from acidic.tokens import Token, tokenize


@pytest.mark.parametrize(
    "text, toks",
    [
        (
            """\
            10 GOSUB 120
            20 REM A comment
            30 X = Y + 2
            """,
            [
                Token(kind="num", text="10"),
                Token(kind="key", text="GO"),
                Token(kind="key", text="SUB"),
                Token(kind="num", text="120"),
                Token(kind="eol", text=""),
                Token(kind="num", text="20"),
                Token(kind="eol", text=""),
                Token(kind="num", text="30"),
                Token(kind="var", text="X"),
                Token(kind="op", text="="),
                Token(kind="var", text="Y"),
                Token(kind="op", text="+"),
                Token(kind="num", text="2"),
                Token(kind="eol", text=""),
                Token(kind="eol", text=""),
            ],
        ),
        (
            """\
            10LETX$="Hello, world!"
            20F=-.1234e10
            30FORX=1TO10
            """,
            [
                Token(kind="num", text="10"),
                Token(kind="key", text="LET"),
                Token(kind="var", text="X$"),
                Token(kind="op", text="="),
                Token(kind="str", text='"Hello, world!"'),
                Token(kind="eol", text=""),
                Token(kind="num", text="20"),
                Token(kind="var", text="F"),
                Token(kind="op", text="="),
                Token(kind="op", text="-"),
                Token(kind="num", text=".1234e10"),
                Token(kind="eol", text=""),
                Token(kind="num", text="30"),
                Token(kind="key", text="FOR"),
                Token(kind="var", text="X"),
                Token(kind="op", text="="),
                Token(kind="num", text="1"),
                Token(kind="key", text="TO"),
                Token(kind="num", text="10"),
                Token(kind="eol", text=""),
                Token(kind="eol", text=""),
            ],
        ),
    ],
)
def test_tokenize(text, toks):
    assert list(tokenize(text)) == toks
