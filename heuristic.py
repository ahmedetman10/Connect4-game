from typing import Dict, Tuple
from game_board import AI, HUMAN, Connect4Board


class BoardEvaluator:
    """
    Bitboard-accelerated heuristic evaluator for Full-Board Connect 4.
    Never touches `board.grid` during search; operates purely on
    `human_mask`, `ai_mask`, `empty_mask`, and `playable_mask`.
    """

    # Heuristic weights (positive favors AI, negative favors Human)
    W_FOUR: int = 1000
    W_THREE: int = 50
    W_TWO: int = 10
    W_IMMEDIATE: int = 120
    W_POSITIONAL: int = 1

    def __init__(self, ai_player: int = AI, opp_player: int = HUMAN) -> None:
        self.ai_player: int = ai_player
        self.opp_player: int = opp_player
        # Cache per (rows, cols): (full_mask, weight_masks)
        # weight_masks is a tuple of (weight, bitmask) pairs
        self._dim_cache: Dict[Tuple[int, int], Tuple[int, Tuple[Tuple[int, int], ...]]] = {}

    def _get_dim_data(
        self, rows: int, cols: int
    ) -> Tuple[int, Tuple[Tuple[int, int], ...]]:
        key = (rows, cols)
        cached = self._dim_cache.get(key)
        if cached is not None:
            return cached

        full_mask = (1 << (rows * cols)) - 1

        # Count how many 4-in-a-row windows pass through each cell (r, c)
        counts = [[0] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(cols):
                # Horizontal
                if c + 3 < cols:
                    for k in range(4):
                        counts[r][c + k] += 1
                # Vertical
                if r + 3 < rows:
                    for k in range(4):
                        counts[r + k][c] += 1
                # Diagonal Up-Right (/)
                if r + 3 < rows and c + 3 < cols:
                    for k in range(4):
                        counts[r + k][c + k] += 1
                # Diagonal Up-Left (\)
                if r + 3 < rows and c - 3 >= 0:
                    for k in range(4):
                        counts[r + k][c - k] += 1

        # Group cells by scaled weight into bitmasks (typically ~6 masks total)
        by_weight: Dict[int, int] = {}
        for r in range(rows):
            row_base = r * cols
            for c in range(cols):
                w = (counts[r][c] + 1) // 2
                if w > 0:
                    by_weight[w] = by_weight.get(w, 0) | (1 << (row_base + c))

        weight_masks = tuple(by_weight.items())
        data = (full_mask, weight_masks)
        self._dim_cache[key] = data
        return data

    @staticmethod
    def _build_playable_mask(board: Connect4Board) -> int:
        """Bitmask of cells where a disc would land immediately due to gravity."""
        mask = 0
        cols = board.cols
        rows = board.rows
        heights = board.col_heights
        for c in range(cols):
            h = heights[c]
            if h < rows:
                mask |= 1 << (h * cols + c)
        return mask

    @staticmethod
    def _count_window_threats(
        bb: int,
        empty_mask: int,
        playable_mask: int,
        cols: int,
        not_last: int,
        not_first: int,
    ) -> Tuple[int, int, int]:
        """
        Counts (threes, twos, immediate_gravity_threes) across all 4 directions
        simultaneously using bitwise shifts.
        """
        if bb == 0:
            return 0, 0, 0

        threes = 0
        twos = 0
        immediate = 0

        directions = (
            (cols, None),
            (1, not_last),
            (cols + 1, not_last),
            (cols - 1, not_first),
        )

        for step, mask in directions:
            if mask is None:
                s1 = bb >> step
                s2 = s1 >> step
                s3 = s2 >> step

                e1 = empty_mask >> step
                e2 = e1 >> step
                e3 = e2 >> step

                g1 = playable_mask >> step
                g2 = g1 >> step
                g3 = g2 >> step
            else:
                s1 = (bb >> step) & mask
                s2 = (s1 >> step) & mask
                s3 = (s2 >> step) & mask

                e1 = (empty_mask >> step) & mask
                e2 = (e1 >> step) & mask
                e3 = (e2 >> step) & mask

                g1 = (playable_mask >> step) & mask
                g2 = (g1 >> step) & mask
                g3 = (g2 >> step) & mask

            # 3 discs + 1 empty (4 patterns: 1110, 1101, 1011, 0111)
            threes += (
                (bb & s1 & s2 & e3)
                | (bb & s1 & e2 & s3)
                | (bb & e1 & s2 & s3)
                | (empty_mask & s1 & s2 & s3)
            ).bit_count()

            # Immediate gravity threats: 3 discs + 1 playable cell
            immediate += (
                (bb & s1 & s2 & g3)
                | (bb & s1 & g2 & s3)
                | (bb & g1 & s2 & s3)
                | (playable_mask & s1 & s2 & s3)
            ).bit_count()

            # 2 discs + 2 empty (6 patterns: 1100, 1010, 1001, 0110, 0101, 0011)
            twos += (
                (bb & s1 & e2 & e3)
                | (bb & e1 & s2 & e3)
                | (bb & e1 & e2 & s3)
                | (empty_mask & s1 & s2 & e3)
                | (empty_mask & s1 & e2 & s3)
                | (empty_mask & e1 & s2 & s3)
            ).bit_count()

        return threes, twos, immediate

    def _get_player_masks(self, board: Connect4Board) -> Tuple[int, int]:
        ai_mask = board.ai_mask if self.ai_player == AI else board.human_mask
        opp_mask = board.human_mask if self.opp_player == HUMAN else board.ai_mask
        return ai_mask, opp_mask

    def evaluate(self, board: Connect4Board) -> int:
        """Fast scalar evaluation called at every leaf node during Minimax search."""
        ai_mask, opp_mask = self._get_player_masks(board)
        cols = board.cols
        full_mask, weight_masks = self._get_dim_data(board.rows, cols)

        # 1. Completed Connect-4s
        completed_score = self.W_FOUR * (
            board.count_fours(self.ai_player) - board.count_fours(self.opp_player)
        )

        # 2 & 3. Window threats (3s & 2s) + Immediate Gravity Threats
        empty_mask = full_mask ^ (ai_mask | opp_mask)
        playable_mask = self._build_playable_mask(board)

        ai_3, ai_2, ai_imm = self._count_window_threats(
            ai_mask, empty_mask, playable_mask, cols, board.not_last_col, board.not_first_col
        )
        opp_3, opp_2, opp_imm = self._count_window_threats(
            opp_mask, empty_mask, playable_mask, cols, board.not_last_col, board.not_first_col
        )

        window_score = self.W_THREE * (ai_3 - opp_3) + self.W_TWO * (ai_2 - opp_2)
        immediate_score = self.W_IMMEDIATE * (ai_imm - opp_imm)

        # 4. Positional Center Control
        pos_score = 0
        for w, mask in weight_masks:
            pos_score += w * (
                (ai_mask & mask).bit_count() - (opp_mask & mask).bit_count()
            )
        pos_score *= self.W_POSITIONAL

        return completed_score + window_score + immediate_score + pos_score

    def evaluate_detailed(self, board: Connect4Board) -> Dict[str, int]:
        """Detailed heuristic breakdown called once per move for the UI & API."""
        ai_mask, opp_mask = self._get_player_masks(board)
        cols = board.cols
        full_mask, weight_masks = self._get_dim_data(board.rows, cols)

        completed_score = self.W_FOUR * (
            board.count_fours(self.ai_player) - board.count_fours(self.opp_player)
        )

        empty_mask = full_mask ^ (ai_mask | opp_mask)
        playable_mask = self._build_playable_mask(board)

        ai_3, ai_2, ai_imm = self._count_window_threats(
            ai_mask, empty_mask, playable_mask, cols, board.not_last_col, board.not_first_col
        )
        opp_3, opp_2, opp_imm = self._count_window_threats(
            opp_mask, empty_mask, playable_mask, cols, board.not_last_col, board.not_first_col
        )

        window_score = self.W_THREE * (ai_3 - opp_3) + self.W_TWO * (ai_2 - opp_2)
        immediate_score = self.W_IMMEDIATE * (ai_imm - opp_imm)

        pos_score = 0
        for w, mask in weight_masks:
            pos_score += w * (
                (ai_mask & mask).bit_count() - (opp_mask & mask).bit_count()
            )
        pos_score *= self.W_POSITIONAL

        total = completed_score + window_score + immediate_score + pos_score
        return {
            "total": total,
            "completed_fours": completed_score,
            "window_threats": window_score,
            "immediate_threats": immediate_score,
            "positional_control": pos_score,
        }