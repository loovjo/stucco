from __future__ import annotations
import random
from typing import List, Tuple, Optional, Union, Dict, Set
from enum import Enum

RESET = "\033[0m"
class MarkColor(Enum):
    ERROR_RED = 1
    INFO_BLUE = 4

    def into_escape_code(self) -> str:
        return f"\033[38;5;{self.value}m"

class DualSpan:
    def __init__(self, span_idx: int, start_col: int, end_col: int):
        self.span_idx = span_idx
        self.start_col = start_col
        self.end_col = end_col

class UpSpan:
    def __init__(self, span_idx: int, col: int):
        self.span_idx = span_idx
        self.col = col

class DownSpan:
    def __init__(self, span_idx: int, col: int):
        self.span_idx = span_idx
        self.col = col

class PseudoFilename(Enum):
    NULL = "Null file"
    PREDEFINED_MACROS = "Predefined macros"

class Source:
    def __init__(self, filename: Union[str, PseudoFilename], contents: str) -> None:
        self.filename = filename
        self.contents = contents
        self.lines = self.contents.split("\n")

    def __str__(self) -> str:
        linecount = len(self.lines)
        return f"Source(filename={self.filename!r}, {linecount} lines, {len(self.contents)} chars)"

    def __repr__(self) -> str:
        return str(self)

    def coords_for_offset(self, offset: int) -> Tuple[int, int]: # (line, col)
        line = self.contents[:offset].count("\n")
        col0 = sum(len(line_before) + 1 for line_before in self.lines[:line])
        col = offset - col0

        # assert(self.contents[offset] == self.lines[line][col])
        return line, col

    def print_spans(self, spans: List[Tuple[Span, MarkColor]], ctx_dist:int=2) -> None:
        lines: List[Union[str, UpSpan, DownSpan, DualSpan]] = list(self.lines)
        linenums: List[Optional[int]] = list(range(len(lines)))

        for i, (span, _) in enumerate(spans):
            start_line, start_col = self.coords_for_offset(span.start)
            end_line, end_col = self.coords_for_offset(span.end - 1)

            if start_line == end_line:
                idx = linenums.index(start_line) + 1
                lines.insert(idx, DualSpan(i, start_col, end_col))
                linenums.insert(idx, None)
            else:
                start_idx = linenums.index(start_line)
                lines.insert(start_idx, DownSpan(i, start_col))
                linenums.insert(start_idx, None)

                end_idx = linenums.index(end_line) + 1
                lines.insert(end_idx, UpSpan(i, end_col))
                linenums.insert(end_idx, None)

        dist_to_interesting = [float("inf") for _ in range(len(lines))]
        curr_dist_up = float("inf")
        for i in range(len(lines)):
            curr_dist_up += 1
            if not isinstance(lines[i], str):
                curr_dist_up = 0
            dist_to_interesting[i] = min(dist_to_interesting[i], curr_dist_up)

        curr_dist_down = float("inf")
        for i in range(len(lines) - 1, -1, -1):
            curr_dist_down += 1
            if not isinstance(lines[i], str):
                curr_dist_down = 0
            dist_to_interesting[i] = min(dist_to_interesting[i], curr_dist_down)


        open_spans: List[Set[int]] = [set() for _ in range(len(lines))]
        current_spans: Set[int] = set()

        xs: Dict[int, int] = {}

        for i in range(len(lines)):
            line = lines[i]
            if isinstance(line, DownSpan):
                max_x = max([-1] + [xs[j] for j in current_spans])
                xs[line.span_idx] = max_x + 1
                current_spans.add(line.span_idx)

            open_spans[i] = set(current_spans)
            if isinstance(line, UpSpan):
                current_spans.remove(line.span_idx)

        left_width = max([-1] + list(xs.values()))+1
        num_width = len(str(len(self.lines) - 1))
        num_pref = " ┃ "
        num_suff = " ┃ "
        last_uninteresting = False
        for i, line in enumerate(lines):
            own_x = left_width + 10

            lhs_lst: List[str] = [" " for _ in range(left_width)]
            if isinstance(line, (UpSpan, DownSpan)):
                for x in range(left_width):
                    if x > xs[line.span_idx]:
                        lhs_lst[x] = spans[line.span_idx][1].into_escape_code() + "─" + RESET

            for x in open_spans[i]:
                lhs_lst[xs[x]] = spans[x][1].into_escape_code() + "│" + RESET
                if isinstance(line, (UpSpan, DownSpan)):
                    if xs[x] >= xs[line.span_idx]:
                        if x == line.span_idx:
                            lhs_lst[xs[x]] = "┌" if isinstance(line, DownSpan) else "└"
                        else:
                            lhs_lst[xs[x]] = "┼"
                        lhs_lst[xs[x]] = spans[line.span_idx][1].into_escape_code() + lhs_lst[xs[x]] + RESET


            lhs: str = "".join(lhs_lst)

            if dist_to_interesting[i] > ctx_dist:
                if not last_uninteresting:
                    print(lhs + num_pref + "." * num_width + num_suff + " <...>")
                last_uninteresting = True
                continue
            last_uninteresting = False

            if isinstance(line, str):
                print(f"{lhs}{num_pref}{str(linenums[i]).ljust(num_width)}{num_suff}{line}")
            elif isinstance(line, DownSpan):
                print(f"{lhs}" + spans[line.span_idx][1].into_escape_code() + "─" * (len(num_pref + num_suff) + num_width + line.col) + "┐" + RESET)
            elif isinstance(line, UpSpan):
                print(f"{lhs}" + spans[line.span_idx][1].into_escape_code() + "─" * (len(num_pref + num_suff) + num_width + line.col) + "┘" + RESET)
            elif isinstance(line, DualSpan):
                if line.start_col == line.end_col:
                    print(f"{lhs}" + spans[line.span_idx][1].into_escape_code() + num_pref + " " * num_width + num_suff + " " * (line.start_col) + "↑" + RESET)
                else:
                    print(f"{lhs}" + spans[line.span_idx][1].into_escape_code() + num_pref + " " * num_width + num_suff + " " * (line.start_col) + "└" + "─" * (line.end_col - line.start_col- 1) + "┘" + RESET)
            else:
                print("death")


class Span:
    def __init__(self, source: Source, start: int, end: int) -> None:
        assert(end >= start)

        self.source = source
        self.start = start
        self.end = end

    def combine(self, other: Span) -> Span:
        assert(other.source == self.source)
        assert(other.end > self.start)
        return Span(self.source, self.start, other.end)

    def contents(self) -> str:
        return self.source.contents[self.start:self.end]

class NullSpan(Span):
    def __init__(self, source: Source) -> None:
        self.source = source
        self.start = 0
        self.end = 0

    def combine(self, other: Span) -> Span:
        return other

class SourceCtx:
    def __init__(self, source: Source, idx: int) -> None:
        self.source = source
        self.idx = idx

    def point_span(self) -> Span:
        return Span(self.source, self.idx, self.idx + 1)

    def pop(self, tok_len:int=1) -> Tuple[Optional[str], Span]:
        if self.idx + tok_len > len(self.source.contents):
            return None, Span(self.source, self.idx, len(self.source.contents))
        else:
            res = self.source.contents[self.idx:][:tok_len]
            start = self.idx
            self.idx += tok_len
            return res, Span(self.source, start, self.idx)

    def peek(self, tok_len:int=1) -> Optional[str]:
        if self.idx + tok_len > len(self.source.contents):
            return None
        else:
            return self.source.contents[self.idx:][:tok_len]

    def peek_exact(self, wanted: str) -> bool:
        return self.peek(len(wanted)) == wanted

    def pop_exact(self, wanted: str) -> Optional[Tuple[Optional[str], Span]]:
        if self.peek(len(wanted)) == wanted:
            return self.pop(len(wanted))
        return None

if __name__ == "__main__":
    f = "parse.py"
    source = Source(f, open(f, "r").read())
    print(source)

    spans: List[Tuple[Span, MarkColor]] = []
    for i in range(5):
        start = random.randrange(len(source.contents))
        end = random.randrange(start + 1, start + 100) # len(source.contents))
        spans.append((Span(source, start, end), random.choice([MarkColor.INFO_BLUE, MarkColor.ERROR_RED])))

    for i, (span, _) in enumerate(spans):
        start_line, start_col = source.coords_for_offset(span.start)
        end_line, end_col = source.coords_for_offset(span.end)

        start_aa = source.lines[start_line-1]
        start_a = source.lines[start_line][:start_col]
        start_mid = source.lines[start_line][start_col]
        start_b = source.lines[start_line][start_col+1:]
        start_bb = source.lines[start_line+1]

        end_a = source.lines[end_line][:end_col]
        end_mid = source.lines[end_line][end_col]
        end_b = source.lines[end_line][end_col+1:]

        print(f"Span {i}:")
        print(f"{start_line-1:5} | {start_aa}")
        print(f"{start_line:5} | {start_a}\033[48;5;5m{start_mid}\033[0m{start_b}")
        print(f"{start_line+1:5} | {start_bb}")
        print(f"{end_line:5} | {end_a}\033[48;5;5m{end_mid}\033[0m{end_b}")
        print()


    source.print_spans(spans)
