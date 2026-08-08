from typing import Never

from .exceptions import AcidicaError
from .program import Ast, Program
from .tokens import Token, parse_data, tokenize


class Parser:
    def __init__(self, text: str) -> None:
        self.toks = tokenize(text)
        self.tok = next(self.toks)
        self.line_num: int | None = None

    def error(
        self,
        msg: str = "Syntax error",
        *,
        show_line_num: bool = True,
        show_token: bool = True,
    ) -> Never:
        """Raise an error exception.

        Args:
            msg: the text of the error message.
            show_line_num: whether to include the current line number in the
                message.
            show_token: whether to include the current token in the message.

        Always raises.

        """
        if show_line_num:
            msg += f" on line {self.line_num}"
        if show_token:
            if self.tok.text:
                msg += f": '{self.tok.text}'"
            else:
                msg += f": {self.tok.kind}"
        raise AcidicaError(msg)

    def eat(self, kind: str | None = None, text: str | None = None) -> str:
        if kind is not None and self.tok.kind != kind:
            self.error(
                f"Expected {text or kind}, saw {self.tok.text or self.tok.kind}",
                show_token=False,
            )
        elif text is not None and self.tok.text != text:
            self.error(
                f"Expected {text}, saw {self.tok.text or self.tok.kind}",
                show_token=False,
            )
        text = self.tok.text
        self.tok = next(self.toks)
        return text

    def parse(self) -> Program:
        lines: dict[int, list[Ast]] = {}
        while True:
            # Start of a line: need a line number
            if self.tok.kind == "eol":
                try:
                    self.eat()
                except StopIteration:
                    break
                continue
            if self.tok.kind != "num":
                self.error("No line number", show_line_num=False)
            self.line_num = self.label(show_line_num=False)

            if self.line_num in lines:
                self.error(
                    f"Duplicate line number {self.line_num}",
                    show_token=False,
                    show_line_num=False,
                )

            line: list[Ast] = []
            lines[self.line_num] = line

            while True:
                match self.tok:
                    case Token("eol", _):
                        break

                    case Token("colon", _):
                        self.eat()

                    case Token("data", data):
                        line.append(("data", *parse_data(data)))
                        self.eat()

                    case Token("key", "DEF"):
                        self.eat()
                        self.eat("key", "FN")
                        var = self.one_var()
                        self.eat("op", "=")
                        line.append(("def", var, self.expr()))

                    case Token("key", "DIM"):
                        self.eat()
                        while True:
                            line.append(("dim", self.one_var()))
                            if self.tok.kind != "comma":
                                break
                            self.eat()

                    case Token("key", "END"):
                        self.eat()
                        line.append(("end",))

                    case Token("key", "FOR"):
                        self.eat()
                        for_var = self.eat("var")
                        self.eat("op", "=")
                        start = self.expr()
                        self.eat("key", "TO")
                        end = self.expr()
                        if self.tok == Token("key", "STEP"):
                            self.eat()
                            step = self.expr()
                        else:
                            step = ("value", 1)
                        line.append(("for", for_var, start, end, step))

                    case Token("key", "GO"):
                        self.eat()
                        match self.tok:
                            case Token("key", "TO"):
                                self.eat()
                                line.append(("goto", self.label()))
                            case Token("key", "SUB"):
                                self.eat()
                                line.append(("gosub", self.label()))
                            case _:
                                self.error()

                    case Token("key", "IF"):
                        self.eat()
                        cond = self.expr()
                        self.eat("key", "THEN")
                        line.append(("if", cond))
                        if self.tok.kind == "num":
                            line.append(("goto", self.label()))

                    case Token("key", "INPUT"):
                        self.eat()
                        if self.tok.kind == "str":
                            msg = self.tok.value()
                            self.eat()
                            self.eat("semicolon")
                        else:
                            msg = ""
                        line.append(("input", msg, *self.var_list()))

                    case Token("key", "LET"):
                        self.eat()
                        match self.tok:
                            case Token("var", _):
                                line.append(self.parse_let())
                            case _:
                                self.error()

                    case Token("key", "NEXT"):
                        self.eat()
                        next_var: str | None = None
                        if self.tok.kind == "var":
                            next_var = self.tok.text
                            self.eat()
                        line.append(("next", next_var))

                    case Token("key", "ON"):
                        self.eat()
                        expr = self.expr()
                        self.eat("key", "GO")
                        if self.tok == Token("key", "TO"):
                            self.eat()
                            op = "ongoto"
                        elif self.tok == Token("key", "SUB"):
                            self.eat()
                            op = "ongosub"
                        else:
                            self.error()
                        labels = []
                        while True:
                            labels.append(self.label())
                            if self.tok.kind != "comma":
                                break
                            self.eat()
                        line.append((op, expr, *labels))

                    case Token("key", "PRINT") | Token("key", "?"):
                        self.eat()
                        items = []
                        while True:
                            match self.tok:
                                case Token("comma", _) | Token("semicolon", _):
                                    items.append((self.tok.kind,))
                                    self.eat()
                                case Token("colon", _) | Token("eol", _):
                                    break
                                case _:
                                    items.append(self.expr())
                        line.append(("print", *items))

                    case Token("key", "RANDOMIZE"):
                        self.eat()
                        line.append(("randomize",))

                    case Token("key", "READ"):
                        self.eat()
                        line.append(("read", *self.var_list()))

                    case Token("key", "RESTORE"):
                        self.eat()
                        if self.tok.kind == "num":
                            label = self.label()
                        else:
                            label = 0
                        line.append(("restore", label))

                    case Token("key", "RETURN"):
                        self.eat()
                        line.append(("return",))

                    case Token("key", "STOP"):
                        self.eat()
                        line.append(("end",))

                    case Token("var", _):
                        line.append(self.parse_let())

                    case _:
                        self.error()

        return Program(lines)

    def label(
        self,
        *,
        show_line_num: bool = True,
    ) -> int:
        if self.tok.kind != "num":
            self.error()
        label = self.tok.value()
        if not isinstance(label, int) or label < 0:
            self.error("Bad label", show_line_num=show_line_num)
        self.eat()
        return label

    def parse_let(self) -> Ast:
        var = self.tok.text
        self.eat()
        args = self.arg_list()
        self.eat("op", "=")
        return ("let", ("var", var, *args), self.expr())

    def var_list(self) -> list[Ast]:
        vars = []
        while True:
            vars.append(self.one_var())
            if self.tok.kind != "comma":
                break
            self.eat()
        return vars

    def one_var(self) -> Ast:
        var = self.eat("var")
        return ("var", var, *self.arg_list())

    def arg_list(self) -> list[Ast]:
        args = []
        if self.tok.kind == "lparen":
            self.eat()
            while True:
                args.append(self.expr())
                if self.tok.kind == "rparen":
                    break
                self.eat("comma")
            self.eat("rparen")
        return args

    def prec9(self) -> Ast:
        tok = self.tok
        match tok:
            case Token("num", _) | Token("str", _):
                self.eat()
                return ("value", tok.value())
            case Token("var", var):
                self.eat()
                return ("var", var, *self.arg_list())
            case Token("lparen", _):
                self.eat()
                node = self.expr()
                self.eat("rparen")
                return node
            case Token("builtin", fn):
                self.eat()
                if self.tok.kind != "lparen":
                    self.error()
                return ("builtin", fn, *self.arg_list())
            case Token("key", "FN"):
                self.eat()
                return ("fn", self.one_var())
            case _NEVER:
                self.error()

    def prec8(self) -> Ast:
        match self.tok:
            case Token("op", "-"):
                self.eat()
                return ("negate", self.prec9())
            case Token("op", "+"):
                self.eat()
                return self.prec9()
            case _:
                return self.prec9()

    def prec7(self) -> Ast:
        # ^ associates to the right
        node = self.prec8()
        more = [node]
        while self.tok.kind == "op" and self.tok.text == "^":
            self.eat()
            more.append(self.prec8())
        while len(more) >= 2:
            e2 = more.pop()
            e1 = more.pop()
            node = ("^", e1, e2)
            more.append(node)
        return more[0]

    def prec6(self) -> Ast:
        node = self.prec7()
        while self.tok.kind == "op" and self.tok.text in {"*", "/"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.prec7())
        return node

    def prec5(self) -> Ast:
        node = self.prec6()
        while self.tok.kind == "op" and self.tok.text in {"+", "-"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.prec6())
        return node

    def prec4(self) -> Ast:
        node = self.prec5()
        while self.tok.kind == "op" and self.tok.text in {
            "=",
            "<>",
            "<",
            "<=",
            ">",
            ">=",
        }:
            op = self.tok.text
            self.eat()
            node = (op, node, self.prec5())
        return node

    def prec3(self) -> Ast:
        match self.tok:
            case Token("op", "NOT"):
                self.eat()
                return ("not", self.prec4())
            case _:
                return self.prec4()

    def prec2(self) -> Ast:
        node = self.prec3()
        while self.tok.kind == "op" and self.tok.text == "AND":
            self.eat()
            node = ("and", node, self.prec3())
        return node

    def prec1(self) -> Ast:
        node = self.prec2()
        while self.tok.kind == "op" and self.tok.text == "OR":
            self.eat()
            node = ("or", node, self.prec2())
        return node

    expr = prec1
