"""
Connect 4 Board Representation and Game Mechanics.

Implements a configurable Connect 4 grid (minimum 6 rows x 7 columns) where
players take turns dropping discs until the board is completely full.
The winner is determined by who has the greater total number of connected-fours
(horizontal, vertical, and both diagonals).
"""

from typing import List, Optional, Tuple


EMPTY = 0
HUMAN = 1
AI = 2


class Connect4Board:
    """
    Represents the Connect 4 grid state with O(1) move/undo operations.

    Row 0 is the bottom row (where the first disc in a column lands),
    and row (rows - 1) is the top row.
    """

    def __init__(self, rows: int = 6, cols: int = 7) -> None:
        if rows < 6 or cols < 7:
            raise ValueError("Board dimensions must be at least 6 rows x 7 columns.")

        self.rows: int = rows
        self.cols: int = cols
        # 2D integer grid: 0 = empty, 1 = human, 2 = AI
        self.grid: List[List[int]] = [[EMPTY] * cols for _ in range(rows)]
        # Tracks the next open row index for each column (0..rows)
        self.col_heights: List[int] = [0] * cols
        # History stack of (col, player) moves to support fast O(1) undo during search
        self.move_history: List[Tuple[int, int]] = []
        self.total_moves: int = 0
        # Precomputed center-first column order to improve alpha-beta pruning efficiency
        center = cols // 2
        self._center_order: List[int] = sorted(
            range(cols), key=lambda c: (abs(c - center), c)
        )

    def is_valid_col(self, col: int) -> bool:
        """Return True if a disc can be dropped into `col`."""
        return 0 <= col < self.cols and self.col_heights[col] < self.rows

    def get_available_cols(self, center_first: bool = True) -> List[int]:
        """
        Return all non-full column indices.

        When `center_first=True`, columns closer to the center are ordered first,
        which helps Alpha-Beta pruning find stronger cutoffs earlier.
        """
        order = self._center_order if center_first else range(self.cols)
        return [c for c in order if self.col_heights[c] < self.rows]

    def drop_disc(self, col: int, player: int) -> Optional[int]:
        """
        Drop a disc for `player` into `col`.

        Returns the landing row index if valid, or None if the column is invalid/full.
        """
        if not self.is_valid_col(col):
            return None

        row = self.col_heights[col]
        self.grid[row][col] = player
        self.col_heights[col] += 1
        self.total_moves += 1
        self.move_history.append((col, player))
        return row

    def undo_move(self) -> Optional[Tuple[int, int]]:
        """Revert the most recent move in O(1) time. Returns (col, player) or None."""
        if not self.move_history:
            return None

        col, player = self.move_history.pop()
        self.col_heights[col] -= 1
        row = self.col_heights[col]
        self.grid[row][col] = EMPTY
        self.total_moves -= 1
        return col, player

    def is_full(self) -> bool:
        """Return True when every cell on the board is occupied (terminal state)."""
        return self.total_moves >= self.rows * self.cols

    def count_fours(self, player: int) -> int:
        """
        Count all overlapping 4-in-a-row segments owned by `player`
        across horizontal, vertical, ascending diagonal (/), and descending diagonal (\\).
        """
        grid = self.grid
        rows, cols = self.rows, self.cols
        count = 0

        # 1. Horizontal windows
        for r in range(rows):
            row_cells = grid[r]
            for c in range(cols - 3):
                if (
                    row_cells[c] == player
                    and row_cells[c + 1] == player
                    and row_cells[c + 2] == player
                    and row_cells[c + 3] == player
                ):
                    count += 1

        # 2. Vertical windows
        for c in range(cols):
            for r in range(rows - 3):
                if (
                    grid[r][c] == player
                    and grid[r + 1][c] == player
                    and grid[r + 2][c] == player
                    and grid[r + 3][c] == player
                ):
                    count += 1

        # 3. Positive-slope diagonal (/)
        for r in range(rows - 3):
            for c in range(cols - 3):
                if (
                    grid[r][c] == player
                    and grid[r + 1][c + 1] == player
                    and grid[r + 2][c + 2] == player
                    and grid[r + 3][c + 3] == player
                ):
                    count += 1

        # 4. Negative-slope diagonal (\)
        for r in range(3, rows):
            for c in range(cols - 3):
                if (
                    grid[r][c] == player
                    and grid[r - 1][c + 1] == player
                    and grid[r - 2][c + 2] == player
                    and grid[r - 3][c + 3] == player
                ):
                    count += 1

        return count

    def get_scores(self) -> Tuple[int, int]:
        """Return (human_score, ai_score) as counts of connected-fours."""
        return self.count_fours(HUMAN), self.count_fours(AI)

    def get_winner(self) -> Optional[str]:
        """
        Determine the winner once the board is full.

        Returns 'Human', 'AI', 'Draw', or None if the game is still ongoing.
        """
        if not self.is_full():
            return None
        human_score, ai_score = self.get_scores()
        if human_score > ai_score:
            return "Human"
        if ai_score > human_score:
            return "AI"
        return "Draw"

    def clone(self) -> "Connect4Board":
        """Create a fast independent copy of the board for search simulation."""
        copy_board = Connect4Board(self.rows, self.cols)
        copy_board.grid = [row[:] for row in self.grid]
        copy_board.col_heights = self.col_heights[:]
        copy_board.total_moves = self.total_moves
        copy_board.move_history = self.move_history[:]
        return copy_board

    def to_matrix(self) -> List[List[int]]:
        """
        Return a copy of the 2D grid (row 0 = bottom, row rows-1 = top)
        suitable for JSON serialization.
        """
        return [row[:] for row in self.grid]

    def render_ascii(self, human_symbol: str = "X", ai_symbol: str = "O") -> str:
        """Render the board top-to-bottom as a clean ASCII string for the console."""
        symbols = {EMPTY: ".", HUMAN: human_symbol, AI: ai_symbol}
        lines = []
        for r in range(self.rows - 1, -1, -1):
            row_str = " ".join(symbols[cell] for cell in self.grid[r])
            lines.append(f"| {row_str} |")
        lines.append("+" + "-" * (2 * self.cols + 1) + "+")
        col_labels = " ".join(str(c) for c in range(self.cols))
        lines.append(f"  {col_labels}")
        return "\n".join(lines)
