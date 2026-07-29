from typing import TextIO


ZONE_WIDTH = 14


class InOut:
    def __init__(self, instream: TextIO, outstream: TextIO) -> None:
        self.instream = instream
        self.outstream = outstream

        self.cur_col: int = 0
        self.next_col: int = 0

    def print(self, text: str = "", end: str = "\n", flush: bool = False) -> None:
        print(text, end=end, flush=flush, file=self.outstream)
        if end == "\n":
            self.cur_col = 0
            self.next_col = 0

    def prompt(self, text: str) -> None:
        self.print(text, end="", flush=True)

    def next_zone(self) -> None:
        self.next_col = (
            (max(self.cur_col, self.next_col) + ZONE_WIDTH) // ZONE_WIDTH * ZONE_WIDTH
        )

    def tab(self, n: int) -> str:
        cur = max(self.cur_col, self.next_col)
        if cur < n:
            return " " * (n - cur)
        else:
            return ""

    def print_value(self, svalue: str) -> None:
        nspaces = max(0, self.next_col - self.cur_col)
        self.print(" " * nspaces + svalue, end="")
        self.cur_col += nspaces + len(svalue)

    def readline(self) -> str:
        line = self.instream.readline()
        if not self.instream.isatty():
            self.print()
        return line
