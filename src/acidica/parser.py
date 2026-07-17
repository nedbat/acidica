from typing import Never

from .exceptions import AcidicaError
from .program import Program
from .tokens import Token, tokenize


class Parser:
    def __init__(self, text: str) -> None:
        self.toks = tokenize(text)
        self.tok = next(self.toks)
        self.line_num = None

    def error(self, line_num=True, token=True) -> Never:
        msg = "!Syntax error"
        if line_num:
            msg += f" on line {self.line_num}"
        if token:
            msg += f": '{self.tok.text}'"
        raise AcidicaError(msg)

    def eat(self, kind=None) -> None:
        if kind is None or self.tok.kind == kind:
            self.tok = next(self.toks)
        else:
            self.error()

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
                raise Exception(f"No line number, got {self.tok}!")
            self.line_num = self.tok.value()

            if self.line_num in lines:
                raise Exception(f"Duplicate line number: {self.line_num}")

            self.eat()
            lines[self.line_num] = line = []

            while True:
                match self.tok:
                    case Token("eol", _):
                        self.eat()
                        while line and not line[-1]:
                            line.pop()
                        break

                    case Token("colon", _):
                        self.eat()

                    case Token("key", "GO"):
                        self.eat()
                        match self.tok:
                            case Token("key", "TO"):
                                self.eat()
                                if self.tok.kind != "num":
                                    self.error()
                                line.append(("goto", self.tok.value()))
                                self.eat()
                            case Token("key", "SUB"):
                                pass
                            case _:
                                self.error()

                    case Token("key", "PRINT"):
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

                    case _:
                        line.append(self.tok)
                        self.eat()

        return Program(lines)

    def expr(self):
        node = self.term()

        while self.tok.kind == "op" and self.tok.text in {"+", "-"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.term())

        return node

    def term(self):
        node = self.factor()
        while self.tok.kind == "op" and self.tok.text in {"*", "/"}:
            op = self.tok.text
            self.eat()
            node = (op, node, self.factor())

        return node

    def factor(self):
        tok = self.tok
        match tok:
            case Token("num", _) | Token("str", _):
                self.eat()
                return ("value", tok.value())
            case Token("lparen", _):
                self.eat()
                node = self.expr()
                self.eat("rparen")
                return node
