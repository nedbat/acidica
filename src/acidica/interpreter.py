import dataclasses
import math
import random
import time
from typing import Any, Callable, TextIO, Iterable, Never

from .exceptions import AcidicaError
from .inout import InOut
from .program import Ast, Program
from .tokens import parse_data


# Actually: `int | float | str`, but eval() is too dynamic, so punt.
type BasicVal = Any 
type BasicValOrArray = Any


def var_type(var: str) -> type[BasicVal]:
    """What Python type does this variable expect?"""
    if "%" in var:
        return int
    elif "$" in var:
        return str
    else:
        return float


def bool2float(bval: float) -> int:
    """BASIC bools are -1 for true, 0 for false. Convert Python to BASIC."""
    return -1 if bval else 0


def float2int(fval: float) -> int:
    """When an int is expected, a float is ok, and will be floor'ed."""
    return int(math.floor(fval))


def print_repr(value: float) -> str:
    """Create the string version of a number for printing."""
    if value >= 0:
        prepr = " "
    else:
        prepr = ""

    prepr += f"{value:.8g}"
    return prepr


class Array:
    """A multi-dimensional array."""

    def __init__(
        self, errfn: Callable[[str], None], dims: Iterable[int], default: BasicVal
    ) -> None:
        self.errfn = errfn
        self.dims = tuple(dims)
        if any(d < 1 for d in self.dims):
            self.errfn("Negative array dim")
        self.default = default
        self.data: dict[tuple[int, ...], BasicVal] = {}

    def __repr__(self) -> str:
        return f"Array({','.join(map(str, self.dims))})"

    def check_args(self, *args: int) -> None:
        if len(args) != len(self.dims):
            self.errfn("Mismatched array dimensions")
        if any(a < 0 for a in args):
            self.errfn("Negative array index")
        for a, d in zip(args, self.dims):
            if a > d:
                self.errfn("Out of array bounds")

    def get(self, *args: int) -> BasicVal:
        self.check_args(*args)
        return self.data.get(args, self.default)

    def set(self, val: BasicVal, *args: int) -> None:
        self.check_args(*args)
        self.data[args] = val


class StatementPointer:
    def __init__(self, program: Program, kind: str, label: int | None = None) -> None:
        self.program = program
        self.kind = kind
        self.jump(label or self.program.first)

    def stmt(self) -> Ast | None:
        while True:
            if self.line_num is None:
                return None
            # line_num, subline = self.line_num
            line = self.program.lines[self.line_num]
            if self.subline >= len(line):
                self.next_line()
                continue
            stmt = line[self.subline]
            self.subline += 1
            # if self.kind == "run":
            #     print(f"RUN {line_num}.{subline}: {stmt}")
            return stmt

    def next_line(self) -> None:
        assert self.line_num is not None
        self.jump(self.program.nexts.get(self.line_num))

    def jump(self, line_num: int | None) -> None:
        self.line_num = line_num
        self.subline = 0

    def copy(self) -> StatementPointer:
        sp = StatementPointer(self.program, self.kind)
        sp.line_num = self.line_num
        sp.subline = self.subline
        return sp


@dataclasses.dataclass
class Loop:
    """A FOR loop in progress."""

    var: str
    top_stmt: StatementPointer
    val: float
    step: float
    end: float


class Interpreter:
    def __init__(self, program: Program, instream: TextIO, outstream: TextIO) -> None:
        self.program = program
        self.io = InOut(instream, outstream)
        self.running = True
        self.stmt_ptr = StatementPointer(self.program, "run")
        self.call_stack: list[StatementPointer] = []
        self.variables: dict[str, BasicValOrArray] = {}
        self.loops: list[Loop] = []
        self.random = random.Random(314159)
        self.last_rnd = 0.0
        self.data_ptr = StatementPointer(self.program, "data")
        self.cur_data: list[tuple[str, ...]] = []

    def run(self) -> None:
        while self.running:
            stmt = self.stmt_ptr.stmt()
            if stmt is None:
                break
            self.exec(stmt)

    def error(self, msg: str) -> Never:
        msg += f" on line {self.stmt_ptr.line_num}"
        raise AcidicaError(msg)

    def get_var(self, var: str, *args: int) -> BasicVal:
        if args and not var.endswith("("):
            var += "("
        value = self.variables.get(var)
        if value is None:
            value = var_type(var)()
            if args:
                # Default array is indexed 0..10
                self.variables[var] = Array(self.error, [10], value)
            self.set_var(var, value, *args)
        else:
            if isinstance(value, Array):
                value = value.get(*args)
        # print(f"GET {var}{args}: {value!r}")
        return value

    def set_var(self, var: str, val: BasicVal, *args: int) -> None:
        if args and not var.endswith("("):
            var += "("
        # print(f"SET {var}{args} = {val!r}")
        vtype = var_type(var)
        if vtype is int and isinstance(val, float):
            val = float2int(val)
        elif vtype is float and isinstance(val, int):
            val = float(val)
        elif not isinstance(val, vtype):
            self.error(f"Incorrect type: can't assign {val!r} to {var}")
        if args:
            if var not in self.variables:
                self.variables[var] = Array(self.error, [10], vtype())
            self.variables[var].set(val, *args)
        else:
            self.variables[var] = val

    def exec(self, node: Ast) -> None:
        match node:
            case ("data", *vals):
                pass

            case ("def", ("var", var, *args), expr):
                self.variables[var + "@"] = (args, expr)

            case ("dim", ("var", var, *args)):
                assert args
                var += "("
                if var in self.variables:
                    self.error("Redim'd array")
                args = self.eval_var_args(args)
                self.variables[var] = Array(self.error, args, var_type(var)())

            case ("end",):
                self.running = False

            case ("for", var, start, end, step):
                if var_type(var) not in (int, float):
                    self.error("Type mismatch")
                val = self.eval(start)
                loop = Loop(
                    var=var,
                    top_stmt=self.stmt_ptr.copy(),
                    val=val,
                    step=self.eval(step),
                    end=self.eval(end),
                )
                self.loops.append(loop)
                self.set_var(var, val)

            case ("gosub", line_num):
                if line_num not in self.program.lines:
                    self.error(f"Bad GOSUB target {line_num}")
                self.call_stack.append(self.stmt_ptr)
                self.stmt_ptr = StatementPointer(self.program, "run", line_num)

            case ("goto", line_num):
                if line_num not in self.program.lines:
                    self.error(f"Bad GOTO target {line_num}")
                self.stmt_ptr.jump(line_num)

            case ("if", cond):
                cond = self.eval(cond)
                if isinstance(cond, str):
                    self.error("Type mismatch for IF")
                if not cond:
                    self.stmt_ptr.next_line()

            case ("input", msg, *vars):
                self.io.prompt(f"{msg}? ")
                while True:
                    vals = []
                    while True:
                        line = self.io.readline()
                        vals.extend(parse_data(line))
                        if len(vals) < len(vars):
                            self.io.prompt("?? ")
                        else:
                            break
                    if len(vals) > len(vars):
                        self.io.print("!Extra input ignored")
                    for (kind, var, *args), val in zip(vars, vals):
                        assert kind == "var"
                        try:
                            val = var_type(var)(val)
                        except ValueError:
                            # TODO: inputting "17 hello" should produce 17
                            self.io.print("!Number expected - retry input line")
                            self.io.prompt("? ")
                            break
                        self.set_var(var, val, *self.eval_var_args(args))
                    else:
                        break

            case ("let", ("var", var, *args), expr):
                self.set_var(var, self.eval(expr), *self.eval_var_args(args))

            case ("next", var):
                if var is not None:
                    while self.loops and self.loops[-1].var != var:
                        self.loops.pop()
                if not self.loops:
                    self.error("NEXT without FOR error")
                loop = self.loops[-1]
                loop.val += loop.step
                if loop.step > 0:
                    more = loop.val <= loop.end
                else:
                    more = loop.val >= loop.end
                if more:
                    self.set_var(loop.var, loop.val)
                    self.stmt_ptr = loop.top_stmt.copy()
                else:
                    self.loops.pop()

            case ("ongosub", expr, *labels):
                num = float2int(self.eval(expr))
                if 1 <= num <= len(labels):
                    line_num = labels[num - 1]
                    if line_num not in self.program.lines:
                        self.error(f"Bad ON GOSUB target {line_num}")
                    self.call_stack.append(self.stmt_ptr)
                    self.stmt_ptr = StatementPointer(self.program, "run", line_num)

            case ("ongoto", expr, *labels):
                num = float2int(self.eval(expr))
                if 1 <= num <= len(labels):
                    line_num = labels[num - 1]
                    if line_num not in self.program.lines:
                        self.error(f"Bad ON GOTO target {line_num}")
                    self.stmt_ptr.jump(line_num)

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

            case ("randomize",):
                self.random.seed(time.time())

            case ("read", *vars):
                for kind, var, *args in vars:
                    assert kind == "var"
                    if not self.cur_data:
                        while True:
                            stmt = self.data_ptr.stmt()
                            if stmt is None:
                                self.error("Out of data")
                            if stmt[0] == "data":
                                self.cur_data = list(stmt[1:])
                                break
                    val = var_type(var)(self.cur_data.pop(0))
                    self.set_var(var, val, *self.eval_var_args(args))

            case ("restore", label):
                label = label or self.program.first
                if label not in self.program.lines:
                    self.error(f"Bad RESTORE target {label}")
                self.data_ptr.jump(label)
                self.cur_data = []

            case ("return",):
                if not self.call_stack:
                    self.error("RETURN without GOSUB")
                self.stmt_ptr = self.call_stack.pop()

            case _NEVER:
                self.error(f"Unimplemented: {node}")

    def eval_var_args(self, args: list[Ast]) -> list[int]:
        return [float2int(self.eval(a)) for a in args]

    def eval(self, expr: Ast) -> BasicVal:
        try:
            match expr:
                case ("value", value):
                    return value
                case ("var", var, *args):
                    return self.get_var(var, *self.eval_var_args(args))
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
                case ("builtin", fn, *args):
                    args = [self.eval(a) for a in args]
                    return self.function(fn, *args)
                case ("fn", ("var", var, *args)):
                    fndef = self.variables.get(var + "@")
                    if fndef is None:
                        self.error(f"Undefined function {var}")
                    formals, expr = fndef
                    if len(formals) != len(args):
                        self.error(f"Wrong number of arguments for function {var}")
                    args = self.eval_var_args(args)
                    saved = {}
                    for (kind, var), val in zip(formals, args):
                        assert kind == "var"
                        saved[var] = self.variables.get(var)
                        self.set_var(var, val)
                    ret = self.eval(expr)
                    for _, var in formals:
                        oldval = saved[var]
                        if oldval is not None:
                            self.variables[var] = oldval
                    return ret
                case _NEVER:
                    self.error(f"Unimplemented: {expr}")
        except TypeError:
            self.error(f"Type mismatch for {expr[0]}")

    def expects(self, nargs: int, fn: str, args: tuple[BasicVal, ...]) -> None:
        if len(args) != nargs:
            self.error(f"Wrong number of arguments for {fn}")

    def function(self, fn: str, *args: BasicVal) -> BasicVal:
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
                    return chr(float2int(args[0]))
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
                    count: int | None = None
                    if len(args) == 3:
                        s, start, count = args
                        assert count is not None
                        count = float2int(count)
                    elif len(args) == 2:
                        s, start = args
                        count = None
                    else:
                        self.error("Wrong number of arguments for MID$")
                    start = float2int(start)
                    if start < 1:
                        self.error("Invalid argument for MID$")
                    s = s[start - 1 :]
                    if count is not None:
                        if count < 0:
                            self.error("Invalid argument for MID$")
                        s = s[:count]
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
                case "STR$":
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
                        return float(
                            args[0] + ""
                        )  # trick to force typeerror for floats
                    except ValueError:
                        return 0

                case _NEVER:
                    self.error(f"Unimplemented function: {fn}")
        except TypeError:
            self.error(f"Type mismatch for {fn}")
