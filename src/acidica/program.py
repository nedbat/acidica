import itertools

class Program:
    def __init__(self, lines):
        self.lines: dict[int, list] = lines
        self.nexts = dict(itertools.pairwise(sorted(self.lines.keys())))
        self.first = min(self.lines.keys())
