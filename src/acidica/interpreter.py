from .exceptions import AcidicaError


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
                self.variables[var] = self.eval(expr)

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
                return self.variables[var]
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
            if value >= 0:
                pad = " "
            else:
                pad = ""

            if value == int(value):
                digits = 0
            else:
                digits = 7

            out = f"{pad}{value:.{digits}f} "

        nspaces = self.next_col - self.cur_col
        print(" " * nspaces + out, end="", file=self.outstream)
        self.cur_col += nspaces + len(out)
