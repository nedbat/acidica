from typing import Never

from .exceptions import AcidicaError


def types(var: str):
    if var.endswith("%"):
        return (int,)
    elif var.endswith("$"):
        return (str,)
    else:
        return (int, float)


class Interpreter:
    def run(self, program, instream, outstream):
        self.instream = instream
        self.outstream = outstream

        self.cur_line = program.first
        self.next_line = None
        self.cur_col = 0
        self.next_col = 0
        self.variables = {}

        while True:
            for stmt in program.lines[self.cur_line]:
                self.exec(stmt)
                if self.next_line:
                    break
            if self.next_line:
                self.cur_line = self.next_line
                self.next_line = None
            else:
                self.cur_line = program.nexts.get(self.cur_line)
                if self.cur_line is None:
                    break

    def error(self, msg: str) -> Never:
        msg += f" on line {self.cur_line}"
        raise AcidicaError(msg)

    def exec(self, node):
        match node:
            case ("goto", line_num):
                self.next_line = line_num

            case ("let", var, expr):
                val = self.eval(expr)
                ok_types = types(var)
                if not isinstance(val, ok_types):
                    self.error(f"Incorrect type: can't assign {val!r} to {var}")
                self.variables[var] = val

            case ("print", *exprs):
                newline = True
                for expr in exprs:
                    match expr:
                        case ("comma",):
                            newline = False
                            self.next_col = (
                                (max(self.cur_col, self.next_col) + 14) // 14 * 14
                            )
                        case ("semicolon",):
                            newline = False
                        case _:
                            self.print(self.eval(expr))
                            newline = True
                if newline:
                    print(file=self.outstream)
                    self.cur_col = 0
                    self.next_col = 0

            case NEVER:
                self.error(f"Unimplemented: {node}")

    def eval(self, expr):
        match expr:
            case ("value", value):
                return value
            case ("var", var):
                value = self.variables.get(var)
                if value is None:
                    value = types(var)[0]()
                return value
            case ("+", e1, e2):
                return self.eval(e1) + self.eval(e2)
            case ("-", e1, e2):
                return self.eval(e1) - self.eval(e2)
            case ("*", e1, e2):
                return self.eval(e1) * self.eval(e2)
            case ("/", e1, e2):
                v1 = self.eval(e1)
                v2 = self.eval(e2)
                if v2 == 0:
                    self.error("Division by zero")
                return v1 / v2
            case NEVER:
                self.error(f"Unimplemented: {expr}")

    def print(self, value):
        if isinstance(value, str):
            out = value
        else:
            out = ""
            if value >= 0:
                out += " "

            out += f"{value:.7f}".rstrip("0").rstrip(".")
            out += " "

        nspaces = self.next_col - self.cur_col
        print(" " * nspaces + out, end="", file=self.outstream)
        self.cur_col += nspaces + len(out)
