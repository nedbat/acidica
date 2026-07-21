from typing import Never

from .exceptions import AcidicaError
from .program import Program
from .tokens import Token, tokenize


class Parser:
    def __init__(self, text: str) -> None:
        self.toks = tokenize(text)
        self.tok = next(self.toks)
        self.line_num = None

    def error(self, msg="Syntax error", line_num=True, token=True) -> Never:
        if line_num:
            msg += f" on line {self.line_num}"
        if token:
            if self.tok.text:
                msg += f": '{self.tok.text}'"
            else:
                msg += f": saw {self.tok.kind}"
        raise AcidicaError(msg)

    def eat(self, kind=None) -> None:
        if kind is None or self.tok.kind == kind:
            self.tok = next(self.toks)
        else:
            self.error(f"Expected {kind}, saw {self.tok.kind}", token=False)

    def eat_key(self, text):
        if self.tok.kind == "key" and self.tok.text == text:
            self.tok = next(self.toks)
        else:
            self.error(f"Expected {text}, saw {self.tok.text}", token=False)

    def parse(self) -> Program:
        lines = {}
        while True:
            # Start of a line: need a line number
            if self.tok.kind == "eol":
                try:
                    self.eat()
                except StopIteration:
                    break
                continue
            if self.tok.kind != "num":
                self.error("No line number", line_num=False)
            self.line_num = self.tok.value()

            if self.line_num in lines:
                self.error(
                    f"Duplicate line number {self.line_num}",
                    token=False,
                    line_num=False,
                )

            self.eat()
            lines[self.line_num] = line = []

            while True:
                match self.tok:
                    case Token("eol", _):
                        break

                    case Token("colon", _):
                        self.eat()

                    case Token("key", "DIM"):
                        self.eat()
                        while True:
                            if self.tok.kind != "var":
                                self.error()
                            var = self.tok.text
                            self.eat()
                            self.eat("lparen")
                            dims = []
                            while True:
                                dims.append(self.expr())
                                if self.tok.kind == "rparen":
                                    self.eat()
                                    break
                                self.eat("comma")
                            line.append(("dim", var, *dims))
                            if self.tok.kind != "comma":
                                break
                            self.eat()

                    case Token("key", "END"):
                        self.eat()
                        line.append(("end",))

                    case Token("key", "FOR"):
                        self.eat()
                        if self.tok.kind != "var":
                            self.error()
                        var = self.tok.text
                        self.eat()
                        if self.tok != Token("op", "="):
                            self.error()
                        self.eat()
                        start = self.expr()
                        self.eat_key("TO")
                        end = self.expr()
                        if self.tok == Token("key", "STEP"):
                            self.eat()
                            step = self.expr()
                            if step is None:
                                self.error()
                        else:
                            step = ("value", 1)
                        line.append(("for", var, start, end, step))

                    case Token("key", "GO"):
                        self.eat()
                        match self.tok:
                            case Token("key", "TO"):
                                self.eat()
                                if self.tok.kind != "num":
                                    self.error()
                                line.append(("goto", self.tok.value()))
                                self.eat()
                            case _:
                                self.error()

                    case Token("key", "IF"):
                        self.eat()
                        cond = self.expr()
                        self.eat_key("THEN")
                        line.append(("if", cond))
                        if self.tok.kind == "num":
                            line.append(("goto", self.tok.value()))
                            self.eat()

                    case Token("key", "INPUT"):
                        self.eat()
                        if self.tok.kind == "str":
                            msg = self.tok.value()
                            self.eat()
                            self.eat("semicolon")
                        else:
                            msg = ""
                        vars = []
                        while True:
                            if self.tok.kind != "var":
                                self.error()
                            vars.append(self.tok.text)
                            self.eat()
                            if self.tok.kind != "comma":
                                break
                            self.eat()
                        line.append(("input", msg, *vars))

                    case Token("key", "LET"):
                        self.eat()
                        match self.tok:
                            case Token("var", _):
                                line.append(self.parse_let())
                            case _:
                                self.error()

                    case Token("key", "NEXT"):
                        self.eat()
                        if self.tok.kind == "var":
                            var = self.tok.text
                            self.eat()
                        else:
                            var = None
                        line.append(("next", var))

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
                                    item = self.expr()
                                    if item is None:
                                        self.error()
                                    items.append(item)
                        line.append(("print", *items))

                    case Token("key", "STOP"):
                        self.eat()
                        line.append(("end",))

                    case Token("var", _):
                        line.append(self.parse_let())

                    case _:
                        self.error()

        return Program(lines)

    def parse_let(self):
        var = self.tok.text
        self.eat()
        if self.tok.kind == "lparen":
            self.eat()
            args = self.arg_list()
        else:
            args = []
        if self.tok != Token("op", "="):
            self.error()
        self.eat()
        return ("let", var, *args, self.expr())

    def arg_list(self):
        args = []
        while True:
            args.append(self.expr())
            if self.tok.kind == "rparen":
                break
            self.eat("comma")
        self.eat("rparen")
        return args

    def prec9(self):
        tok = self.tok
        match tok:
            case Token("num", _) | Token("str", _):
                self.eat()
                return ("value", tok.value())
            case Token("var", var):
                self.eat()
                if self.tok.kind == "lparen":
                    self.eat()
                    args = self.arg_list()
                else:
                    args = []
                return ("var", var, *args)
            case Token("lparen", _):
                self.eat()
                node = self.expr()
                self.eat("rparen")
                return node
            case Token("fn", fn):
                self.eat()
                self.eat("lparen")
                args = self.arg_list()
                return ("fn", fn, *args)

    def prec8(self):
        match self.tok:
            case Token("op", "-"):
                self.eat()
                return ("negate", self.prec9())
            case Token("op", "+"):
                self.eat()
                return self.prec9()
            case _:
                return self.prec9()

    def prec7(self):
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

    def prec6(self):
        node = self.prec7()
        while self.tok.kind == "op" and self.tok.text in {"*", "/"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.prec7())
        return node

    def prec5(self):
        node = self.prec6()
        while self.tok.kind == "op" and self.tok.text in {"+", "-"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.prec6())
        return node

    def prec4(self):
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

    def prec3(self):
        match self.tok:
            case Token("op", "NOT"):
                self.eat()
                return ("not", self.prec4())
            case _:
                return self.prec4()

    def prec2(self):
        node = self.prec3()
        while self.tok.kind == "op" and self.tok.text == "AND":
            self.eat()
            node = ("and", node, self.prec3())
        return node

    def prec1(self):
        node = self.prec2()
        while self.tok.kind == "op" and self.tok.text == "OR":
            self.eat()
            node = ("or", node, self.prec2())
        return node

    expr = prec1
