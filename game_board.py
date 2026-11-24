"""
Connect 4 Board Representation and Game Mechanics.

Implements a configurable Connect 4 grid (minimum 6 rows x 7 columns) where
players take turns dropping discs until the board is completely full.
The winner is determined by who has the greater total number of connected-fours
(horizontal, vertical, 


and both diagonals).
"""

from typing import List, Optional, Tuple


EMPTY = 0
HUMAN = 1
AI = 2

# instead naming the cells we number them as it is lighter


class Connect4Board:
    """
    take care here:
    >> grid state with O(1) move/undo operations

    >> row 0 is the bottom row (where the first disc drops)
    and row (rows - 1) is the top row
    """

    def __init__(self, rows: int = 6, cols: int = 7) -> None:
        # the minimum dimensions are (6, 7)
        if rows < 6 or cols < 7:
            raise ValueError("Board dimensions must be at least 6 rows x 7 columns.")

        self.rows: int = rows
        self.cols: int = cols
        self.grid: List[List[int]] = [[EMPTY] * cols for _ in range(rows)]
        # we start with an empty grid
        self.col_heights: List[int] = [0] * cols
        # tracks the next open row index for each column
        # helps in making insert operation O(1) instead of O(rows)
        self.move_history: List[Tuple[int, int]] = []
        # history stack of (col, player) moves to support fast O(1)
        self.total_moves: int = 0 #detemines whether the board is full
        center = cols // 2
        # center column first to improve alpha-beta pruning efficiency
        # like starting with the smaller values in branches in trivial tree
    
        self._center_order: List[int] = sorted(
            range(cols), key=lambda c: (abs(c - center), c)
        )
       


    def is_valid_col(self, col: int) -> bool:
        # detects whether the col is available or not
        return (0 <= col < self.cols) and (self.col_heights[col] < self.rows)
        # you see the benefit of col_heights

    def get_available_cols(self, center_first: bool = True) -> List[int]:

        order = self._center_order if center_first else range(self.cols)
        return [c for c in order if self.col_heights[c] < self.rows]
        # the difference between the center first and the ordinary order

    def drop_disc(self, col: int, player: int) -> Optional[int]:
        # drops the discs in the board

        if not self.is_valid_col(col):
            return None

        row = self.col_heights[col]
        # finds the row at the top of this col
        self.grid[row][col] = player
        # marks that row with the player
        self.col_heights[col] += 1
        # moves the col upward
        self.total_moves += 1
        self.move_history.append((col, player))
        # record the move for the history
        return row

        ## the previous function does not require searching for the empty rows
        ## and runs in O(1) due to col_heights

    def undo_move(self) -> Optional[Tuple[int, int]]:
        # removes the last move in O(1) using the move_history
        # it is typically the reverse of the previous function
    
        if not self.move_history:
            return None

        col, player = self.move_history.pop()
        self.col_heights[col] -= 1
        row = self.col_heights[col]
        self.grid[row][col] = EMPTY
        self.total_moves -= 1
        return col, player

    ## using the previous 2 functions 
    

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
