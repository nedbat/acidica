import itertools
from typing import Any

type Ast = tuple[Any, ...]

class Program:
    def __init__(self, lines: dict[int, list[Ast]]) -> None:
        self.lines: dict[int, list[Ast]] = lines
        self.nexts = dict(itertools.pairwise(sorted(self.lines.keys())))
        self.first = min(self.lines.keys())
