"""

returns larger positive numbers when the AI is in a stronger position and
smaller (more negative) numbers when the human player is nearer to winning.
"""

from typing import Dict, List, Tuple
from game_board import Connect4Board, EMPTY, HUMAN, AI


class BoardEvaluator:
    """
    Evaluates non-terminal Connect 4 board states using four weighted factors:

    1. Completed Connect-4 Differential:
       Directly reflects the actual game objective (total connected-fours)
    2. Four-Cell Window Threat Analysis:
       Scores every horizontal, vertical, and diagonal 4-cell window that is
       unblocked by the opponent (3-in-a-row threats and 2-in-a-row setups)
       Opponent 3-in-a-row threats receive slightly higher defensive weight so
       the AI prioritizes blocking imminent opponent points
    3. Immediate Playability (Gravity) Bonus:
       A 3-in-a-row window whose missing cell is immediately playable
       is significantly more urgent than one floating above empty cells
    4. Dynamic Positional Weight Matrix:
       Every cell (r, c) is weighted by the exact number of 4-cell windows that
       pass through it (center cells participate in up to 13 windows on a 6x7
       board, whereas corners participate in only 3)
       Works for any rows >= 6, cols >= 7
    """

    # weights (larger = better for AI)
    WEIGHT_COMPLETED_FOUR = 1000
    WEIGHT_AI_THREE = 55
    WEIGHT_AI_THREE_IMMEDIATE = 35
    WEIGHT_OPP_THREE = -65
    WEIGHT_OPP_THREE_IMMEDIATE = -45
    WEIGHT_AI_TWO = 12
    WEIGHT_OPP_TWO = -14
    WEIGHT_POSITIONAL = 2
    # here we are making the human threats larger 
    # to make the AI more defensive which means preventig the heman from connecting
    # the 4 is more imp than hading for the four

    def __init__(self, ai_player: int = AI, opp_player: int = HUMAN) -> None:
        self.ai_player = ai_player
        self.opp_player = opp_player
        self._pos_matrix_cache: Dict[Tuple[int, int], List[List[int]]] = {}
        # cahce for recording the position evaluations

    def _get_positional_weights(self, rows: int, cols: int) -> List[List[int]]:
  
        key = (rows, cols)
        if key in self._pos_matrix_cache:
            return self._pos_matrix_cache[key]

        weights = [[0] * cols for _ in range(rows)]

        # the idea here that we compute the number of possible connected
        # four lines that include this cell , and we save the weights for
        # every dimension we compute to not need to recompute
        # the corners>> 3 , the midlle>> 13

        # horizontal
        for r in range(rows):
            for c in range(cols - 3):
                for k in range(4):
                    weights[r][c + k] += 1

        # vertical
        for c in range(cols):
            for r in range(rows - 3):
                for k in range(4):
                    weights[r + k][c] += 1

        # diagonal (/)
        for r in range(rows - 3):
            for c in range(cols - 3):
                for k in range(4):
                    weights[r + k][c + k] += 1

        # diagonal (\)
        for r in range(3, rows):
            for c in range(cols - 3):
                for k in range(4):
                    weights[r - k][c + k] += 1

        self._pos_matrix_cache[key] = weights
        return weights

    def _score_window(
        self,
        cells: Tuple[int, int, int, int],
        coords: Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]],
        col_heights: List[int],
    ) -> Tuple[int, int, int]:
        """
        Evaluate a single 4-cell window

        Returns (completed_four_score, threat_score, gravity_bonus)
        """
        ai_count = 0
        opp_count = 0
        empty_idx = -1

        for idx, val in enumerate(cells):
            if val == self.ai_player:
                ai_count += 1
            elif val == self.opp_player:
                opp_count += 1
            else:
                empty_idx = idx

        # Mixed windows containing both players cannot form a connect-4
        if ai_count > 0 and opp_count > 0:
            return 0, 0, 0

        if ai_count == 4:
            return self.WEIGHT_COMPLETED_FOUR, 0, 0
        if opp_count == 4:
            return -self.WEIGHT_COMPLETED_FOUR, 0, 0

        if ai_count == 3:
            r, c = coords[empty_idx]
            gravity = self.WEIGHT_AI_THREE_IMMEDIATE if col_heights[c] == r else 0
            return 0, self.WEIGHT_AI_THREE, gravity

        if opp_count == 3:
            r, c = coords[empty_idx]
            gravity = self.WEIGHT_OPP_THREE_IMMEDIATE if col_heights[c] == r else 0
            return 0, self.WEIGHT_OPP_THREE, gravity

            # gravity here tells us whether we can play in the cell or 
            # we should fille the under cells first

        if ai_count == 2:
            return 0, self.WEIGHT_AI_TWO, 0
        if opp_count == 2:
            return 0, self.WEIGHT_OPP_TWO, 0

        return 0, 0, 0

    def evaluate_detailed(self, board: Connect4Board) -> Dict[str, int]:
        """
        Compute the heuristic score along
        """
        grid = board.grid
        rows, cols = board.rows, board.cols
        col_heights = board.col_heights

        completed_score = 0
        threat_score = 0
        gravity_score = 0

        #Horizontall
        for r in range(rows):
            row_cells = grid[r]
            for c in range(cols - 3):
                c4, th, gr = self._score_window(
                    (row_cells[c], row_cells[c + 1], row_cells[c + 2], row_cells[c + 3]),
                    ((r, c), (r, c + 1), (r, c + 2), (r, c + 3)),
                    col_heights,
                )
                completed_score += c4
                threat_score += th
                gravity_score += gr

        #vertical
        for c in range(cols):
            for r in range(rows - 3):
                c4, th, gr = self._score_window(
                    (grid[r][c], grid[r + 1][c], grid[r + 2][c], grid[r + 3][c]),
                    ((r, c), (r + 1, c), (r + 2, c), (r + 3, c)),
                    col_heights,
                )
                completed_score += c4
                threat_score += th
                gravity_score += gr

        #diagonal(/)
        for r in range(rows - 3):
            for c in range(cols - 3):
                c4, th, gr = self._score_window(
                    (
                        grid[r][c],
                        grid[r + 1][c + 1],
                        grid[r + 2][c + 2],
                        grid[r + 3][c + 3],
                    ),
                    ((r, c), (r + 1, c + 1), (r + 2, c + 2), (r + 3, c + 3)),
                    col_heights,
                )
                completed_score += c4
                threat_score += th
                gravity_score += gr

        # diagonal(\)
        for r in range(3, rows):
            for c in range(cols - 3):
                c4, th, gr = self._score_window(
                    (
                        grid[r][c],
                        grid[r - 1][c + 1],
                        grid[r - 2][c + 2],
                        grid[r - 3][c + 3],
                    ),
                    ((r, c), (r - 1, c + 1), (r - 2, c + 2), (r - 3, c + 3)),
                    col_heights,
                )
                completed_score += c4
                threat_score += th
                gravity_score += gr

        # center
        pos_weights = self._get_positional_weights(rows, cols)
        positional_score = 0
        for r in range(rows):
            for c in range(cols):
                cell = grid[r][c]
                if cell == self.ai_player:
                    positional_score += pos_weights[r][c] * self.WEIGHT_POSITIONAL
                elif cell == self.opp_player:
                    positional_score -= pos_weights[r][c] * self.WEIGHT_POSITIONAL

        total = completed_score + threat_score + gravity_score + positional_score
        return {
            "total": total,
            "completed_fours": completed_score,
            "window_threats": threat_score,
            "immediate_threats": gravity_score,
            "positional_control": positional_score,
        }

    def evaluate(self, board: Connect4Board) -> int:
        """Return the scalar heuristic value of `board` for Minimax."""
        return self.evaluate_detailed(board)["total"]
