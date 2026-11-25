from typing import Any, Dict, List, Optional, Tuple

EMPTY = 0
HUMAN = 1
AI = 2


class Connect4Board:
    """
    High-performance Row-Major Bitboard representation of Connect 4
    supporting arbitrary board dimensions (rows >= 6, cols >= 7).

    Bit layout:
      Bit index of cell (r, c) where r=0 is the bottom row: `r * cols + c`.
      Wrap-around across row boundaries is prevented using `not_last_col`
      and `not_first_col` bitmasks.
    """

    __slots__ = (
        "rows",
        "cols",
        "human_mask",
        "ai_mask",
        "not_last_col",
        "not_first_col",
        "col_heights",
        "moves_count",
        "max_moves",
        "_history",
        "_center_order",
        "_left_order",
    )

    def __init__(self, rows: int = 6, cols: int = 7) -> None:
        if rows < 6 or cols < 7:
            raise ValueError("Board dimensions must be at least 6 rows x 7 cols.")

        self.rows: int = rows
        self.cols: int = cols

        self.human_mask: int = 0
        self.ai_mask: int = 0
        self.col_heights: List[int] = [0] * cols
        self.moves_count: int = 0
        self.max_moves: int = rows * cols
        self._history: List[Tuple[int, int, int]] = []  # (row, col, player)

        # Precompute boundary masks once to prevent horizontal/diagonal wrap-around
        not_last = 0
        not_first = 0
        for r in range(rows):
            row_base = r * cols
            for c in range(cols):
                bit = 1 << (row_base + c)
                if c != cols - 1:
                    not_last |= bit
                if c != 0:
                    not_first |= bit
        self.not_last_col: int = not_last
        self.not_first_col: int = not_first

        # Precompute column orders once (avoids sorting on every search node)
        center = cols // 2
        self._left_order: Tuple[int, ...] = tuple(range(cols))
        self._center_order: Tuple[int, ...] = tuple(
            sorted(range(cols), key=lambda c: (abs(c - center), c))
        )

    @property
    def grid(self) -> List[List[int]]:
        """Reconstructs the 2D list (row 0 = bottom) on demand for API/CLI compatibility."""
        h_mask = self.human_mask
        a_mask = self.ai_mask
        rows = self.rows
        cols = self.cols

        board_grid = [[EMPTY] * cols for _ in range(rows)]
        for c in range(cols):
            col_h = self.col_heights[c]
            for r in range(col_h):
                bit = 1 << (r * cols + c)
                if h_mask & bit:
                    board_grid[r][c] = HUMAN
                elif a_mask & bit:
                    board_grid[r][c] = AI
        return board_grid

    def is_valid_col(self, col: int) -> bool:
        return 0 <= col < self.cols and self.col_heights[col] < self.rows

    def drop_disc(self, col: int, player: int) -> int:
        row = self.col_heights[col]
        if row >= self.rows:
            raise ValueError(f"Column {col} is full.")

        bit = 1 << (row * self.cols + col)
        if player == HUMAN:
            self.human_mask |= bit
        else:
            self.ai_mask |= bit

        self.col_heights[col] = row + 1
        self.moves_count += 1
        self._history.append((row, col, player))
        return row

    def undo_move(self) -> Tuple[int, int]:
        if not self._history:
            raise ValueError("No moves to undo.")

        row, col, player = self._history.pop()
        bit = 1 << (row * self.cols + col)
        if player == HUMAN:
            self.human_mask ^= bit
        else:
            self.ai_mask ^= bit

        self.col_heights[col] = row
        self.moves_count -= 1
        return row, col

    def is_full(self) -> bool:
        return self.moves_count >= self.max_moves

    def get_available_cols(self, center_first: bool = True) -> List[int]:
        heights = self.col_heights
        rows = self.rows
        order = self._center_order if center_first else self._left_order
        return [c for c in order if heights[c] < rows]

    def count_fours(self, player: int) -> int:
        """Counts all overlapping 4-in-a-row sequences in O(1) using bitwise shifts."""
        bb = self.human_mask if player == HUMAN else self.ai_mask
        if bb == 0:
            return 0

        c = self.cols
        not_last = self.not_last_col
        not_first = self.not_first_col

        # 1. Vertical (|): step = cols
        v1 = bb >> c
        v2 = v1 >> c
        v3 = v2 >> c
        total = (bb & v1 & v2 & v3).bit_count()

        # 2. Horizontal (-): step = 1
        h1 = (bb >> 1) & not_last
        h2 = (h1 >> 1) & not_last
        h3 = (h2 >> 1) & not_last
        total += (bb & h1 & h2 & h3).bit_count()

        # 3. Diagonal Up-Right (/): step = cols + 1
        d1 = c + 1
        u1 = (bb >> d1) & not_last
        u2 = (u1 >> d1) & not_last
        u3 = (u2 >> d1) & not_last
        total += (bb & u1 & u2 & u3).bit_count()

        # 4. Diagonal Up-Left (\): step = cols - 1
        d2 = c - 1
        l1 = (bb >> d2) & not_first
        l2 = (l1 >> d2) & not_first
        l3 = (l2 >> d2) & not_first
        total += (bb & l1 & l2 & l3).bit_count()

        return total

    def state_key(self) -> Tuple[int, int]:
        """O(1) hashable key representing the exact board state for Transposition Tables."""
        return (self.human_mask, self.ai_mask)

    def clone(self) -> "Connect4Board":
        new_board = Connect4Board.__new__(Connect4Board)
        new_board.rows = self.rows
        new_board.cols = self.cols
        new_board.human_mask = self.human_mask
        new_board.ai_mask = self.ai_mask
        new_board.not_last_col = self.not_last_col
        new_board.not_first_col = self.not_first_col
        new_board.col_heights = self.col_heights.copy()
        new_board.moves_count = self.moves_count
        new_board.max_moves = self.max_moves
        new_board._history = self._history.copy()
        new_board._center_order = self._center_order
        new_board._left_order = self._left_order
        return new_board

    def __str__(self) -> str:
        symbols = {EMPTY: ".", HUMAN: "X", AI: "O"}
        g = self.grid
        lines = []
        for r in range(self.rows - 1, -1, -1):
            lines.append(" ".join(symbols[g[r][c]] for c in range(self.cols)))
        lines.append(" ".join(str(c) for c in range(self.cols)))
        return "\n".join(lines)
    def render_ascii(self) -> str:
        return self.__str__()

    def to_matrix(self) -> List[List[int]]:
        return self.grid

    def get_scores(self) -> Tuple[int, int]:
        return self.count_fours(HUMAN), self.count_fours(AI)

    def get_winner(self) -> Optional[str]:
        if not self.is_full():
            return None
        human_score, ai_score = self.get_scores()
        if ai_score > human_score:
            return "AI"
        if human_score > ai_score:
            return "Human"
        return "Draw"

    def get_fours_coords(self, player: int) -> List[Dict[str, Any]]:
        """Returns exact coordinates and direction of every 4-in-a-row for visual verification."""
        bb = self.human_mask if player == HUMAN else self.ai_mask
        if bb == 0:
            return []

        lines: List[Dict[str, Any]] = []
        rows, cols = self.rows, self.cols
        directions = (
            (0, 1, "Horizontal —"),
            (1, 0, "Vertical |"),
            (1, 1, "Diagonal /"),
            (1, -1, "Diagonal \\"),
        )

        for r in range(rows):
            for c in range(cols):
                for dr, dc, label in directions:
                    end_r = r + 3 * dr
                    end_c = c + 3 * dc
                    if 0 <= end_r < rows and 0 <= end_c < cols:
                        coords = []
                        ok = True
                        for k in range(4):
                            rr, cc = r + k * dr, c + k * dc
                            if not (bb & (1 << (rr * cols + cc))):
                                ok = False
                                break
                            coords.append({"row": rr, "col": cc})
                        if ok:
                            lines.append({"direction": label, "cells": coords})
        return lines