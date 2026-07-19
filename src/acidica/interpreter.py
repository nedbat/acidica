import dataclasses
import math
import random
import re
from typing import Never

from .exceptions import AcidicaError
from .inout import InOut


def var_type(var: str):
    if var.endswith("%"):
        return int
    elif var.endswith("$"):
        return str
    else:
        return float


def bool2float(bval):
    return -1 if bval else 0


def float2int(fval):
    return int(math.floor(fval))


def print_repr(value):
    prepr = ""
    if value >= 0:
        prepr += " "

    prepr += f"{value:.8g}"
    if "." in prepr:
        prepr = prepr.rstrip("0").rstrip(".")
    return prepr


@dataclasses.dataclass
class Loop:
    var: str
    line: int
    subline: int
    val: float
    step: float
    end: float


class Interpreter:
    def __init__(self, program, instream, outstream):
        self.program = program
        self.io = InOut(outstream, instream)
        self.cur_line = self.program.first
        self.cur_subline = 0
        self.variables = {}
        self.loops = []
        self.random = random.Random(314159)
        self.last_rnd = 0

    def run(self):
        while True:
            line = self.program.lines[self.cur_line]
            if self.cur_subline >= len(line):
                self.cur_line = self.program.nexts.get(self.cur_line)
                if self.cur_line is None:
                    break
                self.cur_subline = 0
                continue

            self.exec(self.program.lines[self.cur_line][self.cur_subline])
            self.cur_subline += 1

    def error(self, msg: str) -> Never:
        msg += f" on line {self.cur_line}"
        raise AcidicaError(msg)

    def get_var(self, var):
        value = self.variables.get(var)
        if value is None:
            value = var_type(var)()
        return value

    def set_var(self, var, val):
        vtype = var_type(var)
        if vtype is int and isinstance(val, float):
            val = float2int(val)
        elif vtype is float and isinstance(val, int):
            val = float(val)
        elif not isinstance(val, vtype):
            self.error(f"Incorrect type: can't assign {val!r} to {var}")
        self.variables[var] = val

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
                self.set_var(var, val)

            case ("goto", line_num):
                self.cur_line = line_num
                self.cur_subline = -1  # the main loop will increment it

            case ("input", msg, *vars):
                VAL_TOKENS = r'(\s*"[^"]*")|(\s*[^",][^,]+)'
                self.io.prompt(f"{msg}? ")
                while True:
                    vals = []
                    while True:
                        line = self.io.readline()
                        vals.extend(
                            v.group(0).strip().strip('"')
                            for v in re.finditer(VAL_TOKENS, line)
                        )
                        if len(vals) < len(vars):
                            self.io.prompt("?? ")
                        else:
                            break
                    if len(vals) > len(vars):
                        self.io.print("!Extra input ignored")
                    for var, val in zip(vars, vals):
                        try:
                            val = var_type(var)(val)
                        except ValueError:
                            self.io.print("!Number expected - retry input line")
                            self.io.prompt("? ")
                            break
                        self.set_var(var, val)
                    else:
                        break

            case ("let", var, expr):
                self.set_var(var, self.eval(expr))

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
                    self.set_var(loop.var, loop.val)
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
                            self.io.next_zone()
                        case ("semicolon",):
                            newline = False
                        case _:
                            val = self.eval(expr)
                            if isinstance(val, (float, int)):
                                val = print_repr(val) + " "
                            self.io.print_value(val)
                            newline = True
                if newline:
                    self.io.print()

            case NEVER:
                self.error(f"Unimplemented: {node}")

    def eval(self, expr):
        try:
            match expr:
                case ("value", value):
                    return value
                case ("var", var):
                    return self.get_var(var)
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
                case ("^", e1, e2):
                    return self.eval(e1) ** self.eval(e2)
                case ("negate", e1):
                    return -self.eval(e1)
                case ("=", e1, e2):
                    return bool2float(self.eval(e1) == self.eval(e2))
                case ("<>", e1, e2):
                    return bool2float(self.eval(e1) != self.eval(e2))
                case ("<", e1, e2):
                    return bool2float(self.eval(e1) < self.eval(e2))
                case ("<=", e1, e2):
                    return bool2float(self.eval(e1) <= self.eval(e2))
                case (">", e1, e2):
                    return bool2float(self.eval(e1) > self.eval(e2))
                case (">=", e1, e2):
                    return bool2float(self.eval(e1) >= self.eval(e2))
                case ("not", e1):
                    return bool2float(not self.eval(e1))
                case ("and", e1, e2):
                    return bool2float(self.eval(e1) and self.eval(e2))
                case ("or", e1, e2):
                    return bool2float(self.eval(e1) or self.eval(e2))
                case ("fn", fn, *args):
                    args = [self.eval(a) for a in args]
                    return self.function(fn, *args)
                case NEVER:
                    self.error(f"Unimplemented: {expr}")
        except TypeError:
            self.error(f"Type mismatch for {expr[0]}")

    def expects(self, nargs, fn, args):
        if len(args) != nargs:
            self.error(f"Wrong number of arguments for {fn}")

    def function(self, fn, *args):
        try:
            match fn:
                case "ABS":
                    self.expects(1, fn, args)
                    return abs(args[0])
                case "ASC":
                    self.expects(1, fn, args)
                    if not args[0]:
                        self.error("Invalid argument for ASC")
                    return ord(args[0][0])
                case "ATN":
                    self.expects(1, fn, args)
                    return math.atan(args[0])
                case "CHR$":
                    self.expects(1, fn, args)
                    return chr(args[0])
                case "COS":
                    self.expects(1, fn, args)
                    return math.cos(args[0])
                case "EXP":
                    self.expects(1, fn, args)
                    return math.exp(args[0])
                case "INT":
                    self.expects(1, fn, args)
                    return float2int(args[0])
                case "LEFT$":
                    self.expects(2, fn, args)
                    num = float2int(args[1])
                    if num < 0:
                        self.error("Invalid argument for LEFT$")
                    return args[0][:num]
                case "LEN":
                    self.expects(1, fn, args)
                    return len(args[0])
                case "LOG":
                    self.expects(1, fn, args)
                    return math.log(args[0])
                case "MID$":
                    if len(args) == 3:
                        s, start, num = args
                    elif len(args) == 2:
                        s, start = args
                        num = None
                    else:
                        self.error("Wrong number of arguments for MID$")
                    if start < 1:
                        self.error("Invalid argument for MID$")
                    s = s[start - 1 :]
                    if num is not None:
                        if num < 0:
                            self.error("Invalid argument for MID$")
                        s = s[:num]
                    return s
                case "RIGHT$":
                    self.expects(2, fn, args)
                    num = float2int(args[1])
                    if num < 0:
                        self.error("Invalid argument for RIGHT$")
                    if num == 0:
                        return ""
                    return args[0][-num:]
                case "RND":
                    self.expects(1, fn, args)
                    num = float2int(args[0])
                    if num < 0:
                        self.random.seed(num)
                    if num != 0:
                        self.last_rnd = self.random.random()
                    return self.last_rnd
                case "SGN":
                    self.expects(1, fn, args)
                    if args[0] < 0:
                        return -1
                    elif args[0] > 0:
                        return 1
                    else:
                        return 0
                case "SIN":
                    self.expects(1, fn, args)
                    return math.sin(args[0])
                case "SPC":
                    self.expects(1, fn, args)
                    num = float2int(args[0])
                    if num < 0:
                        self.error("Invalid argument for SPC")
                    return " " * num
                case "SQR":
                    self.expects(1, fn, args)
                    num = args[0]
                    if num < 0:
                        self.error("Invalid argument for SQR")
                    return math.sqrt(num)
                case "STR":  # not implemented by vintage-basic?
                    self.expects(1, fn, args)
                    return print_repr(args[0])
                case "TAB":
                    self.expects(1, fn, args)
                    return self.io.tab(float2int(args[0]))
                case "TAN":
                    self.expects(1, fn, args)
                    return math.tan(args[0])
                case "VAL":
                    self.expects(1, fn, args)
                    try:
                        return float(args[0] + "")  # trick to force typeerror for floats
                    except ValueError:
                        return 0

                case NEVER:
                    self.error(f"Unimplemented function: {fn}")
        except TypeError:
            self.error(f"Type mismatch for {fn}")
