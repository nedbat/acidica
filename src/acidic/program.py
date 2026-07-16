import itertools

class Program:
    def __init__(self, lines):
        self.lines: dict[int, list] = lines
        self.nexts = dict(itertools.pairwise(sorted(self.lines.keys())))
        self.first = min(self.lines.keys())


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
                    print(self.eval(expr), file=self.outstream)

            case ("goto", line_num):
                self.next_line = line_num

    def eval(self, expr):
        match expr:
            case ("literal", value):
                return value
            case ("+", e1, e2):
                return self.eval(e1) + self.eval(e2)
