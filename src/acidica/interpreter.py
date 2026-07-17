import dataclasses
from typing import Never

from .exceptions import AcidicaError


def types(var: str):
    if var.endswith("%"):
        return (int,)
    elif var.endswith("$"):
        return (str,)
    else:
        return (int, float)


@dataclasses.dataclass
class Loop:
    var: str
    line: int
    subline: int
    val: float
    step: float
    end: float


class Interpreter:
    def run(self, program, instream, outstream):
        self.instream = instream
        self.outstream = outstream

        self.cur_line = program.first
        self.cur_subline = 0
        self.cur_col = 0
        self.next_col = 0
        self.variables = {}
        self.loops = []

        while True:
            line = program.lines[self.cur_line]
            if self.cur_subline >= len(line):
                self.cur_line = program.nexts.get(self.cur_line)
                if self.cur_line is None:
                    break
                self.cur_subline = 0
                continue

            self.exec(program.lines[self.cur_line][self.cur_subline])
            self.cur_subline += 1

    def error(self, msg: str) -> Never:
        msg += f" on line {self.cur_line}"
        raise AcidicaError(msg)

    def exec(self, node):
        match node:
            case ("for", var, start, end, step):
                val = self.eval(start)
                loop = Loop(
                    var=var,
                    line=self.cur_line,
                    subline=self.cur_subline,
                    val=val,
                    step=self.eval(step),
                    end=self.eval(end),
                )
                self.loops.append(loop)
                self.variables[var] = val

            case ("goto", line_num):
                self.cur_line = line_num
                self.cur_subline = -1  # the main loop will increment it

            case ("let", var, expr):
                val = self.eval(expr)
                ok_types = types(var)
                if not isinstance(val, ok_types):
                    self.error(f"Incorrect type: can't assign {val!r} to {var}")
                self.variables[var] = val

            case ("next", var):
                if var is not None:
                    while self.loops and self.loops[-1].var != var:
                        self.loops.pop()
                if not self.loops:
                    self.error("No matching loop found")
                loop = self.loops[-1]
                loop.val += loop.step
                if loop.step > 0:
                    more = loop.val <= loop.end
                else:
                    more = loop.val >= loop.end
                if more:
                    self.variables[loop.var] = loop.val
                    self.cur_line = loop.line
                    self.cur_subline = loop.subline
                else:
                    self.loops.pop()

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
