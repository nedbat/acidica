class Interpreter:
    def run(self, program, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.cur_line = program.first
        self.next_line = None
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

    def exec(self, node):
        match node:
            case ("print", *exprs):
                for expr in exprs:
                    self.print(self.eval(expr))
                print(file=self.outstream)

            case ("goto", line_num):
                self.next_line = line_num

    def eval(self, expr):
        match expr:
            case ("value", value):
                return value
            case ("+", e1, e2):
                return self.eval(e1) + self.eval(e2)
            case ("-", e1, e2):
                return self.eval(e1) - self.eval(e2)
            case ("*", e1, e2):
                return self.eval(e1) * self.eval(e2)
            case ("/", e1, e2):
                return self.eval(e1) / self.eval(e2)

    def print(self, value):
        if isinstance(value, str):
            print(value, end="", file=self.outstream)
        else:
            if value >= 0:
                pad = " "
            else:
                pad = ""

            if value == int(value):
                digits = 0
            else:
                digits = 7

            print(f"{pad}{value:.{digits}f} ", end="", file=self.outstream)
