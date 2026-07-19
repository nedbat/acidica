ZONE_WIDTH = 14


class InOut:
    def __init__(self, outstream, instream):
        self.outstream = outstream
        self.instream = instream

        self.cur_col = 0
        self.next_col = 0

    def print(self, text="", end="\n", flush=False):
        print(text, end=end, flush=flush, file=self.outstream)
        if end == "\n":
            self.cur_col = 0
            self.next_col = 0

    def prompt(self, text):
        self.print(text, end="", flush=True)

    def next_zone(self):
        self.next_col = (
            (max(self.cur_col, self.next_col) + ZONE_WIDTH) // ZONE_WIDTH * ZONE_WIDTH
        )

    def print_value(self, svalue):
        nspaces = self.next_col - self.cur_col
        self.print(" " * nspaces + svalue, end="")
        self.cur_col += nspaces + len(svalue)

    def readline(self):
        line = self.instream.readline()
        if not self.instream.isatty():
            self.print()
        return line
