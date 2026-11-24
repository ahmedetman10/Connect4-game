"""
Automated unit tests for the Connect 4 AI backend.

Run with:
    python -m unittest discover -s tests -v
"""

import unittest

from game_board import Connect4Board, HUMAN, AI
from heuristic import BoardEvaluator
from minimax_engine import MinimaxAgent, format_minimax_tree


class TestConnect4Board(unittest.TestCase):
    def test_minimum_dimensions_enforced(self):
        with self.assertRaises(ValueError):
            Connect4Board(rows=5, cols=7)
        with self.assertRaises(ValueError):
            Connect4Board(rows=6, cols=6)
        b = Connect4Board(rows=7, cols=8)
        self.assertEqual((b.rows, b.cols), (7, 8))

    def test_drop_and_undo(self):
        b = Connect4Board()
        r0 = b.drop_disc(3, HUMAN)
        r1 = b.drop_disc(3, AI)
        self.assertEqual((r0, r1), (0, 1))
        self.assertEqual(b.total_moves, 2)
        b.undo_move()
        self.assertEqual(b.col_heights[3], 1)
        self.assertEqual(b.grid[1][3], 0)
        self.assertEqual(b.total_moves, 1)

    def test_count_fours_all_directions(self):
        # Horizontal
        b = Connect4Board()
        for c in range(4):
            b.drop_disc(c, HUMAN)
        self.assertEqual(b.count_fours(HUMAN), 1)
        # Adding a 5th in a row yields 2 overlapping connect-fours
        b.drop_disc(4, HUMAN)
        self.assertEqual(b.count_fours(HUMAN), 2)

        # Vertical
        bv = Connect4Board()
        for _ in range(4):
            bv.drop_disc(0, AI)
        self.assertEqual(bv.count_fours(AI), 1)

        # Ascending diagonal (/)
        bd = Connect4Board()
        # Build staircase so AI lands on (0,0), (1,1), (2,2), (3,3)
        bd.drop_disc(0, AI)
        bd.drop_disc(1, HUMAN)
        bd.drop_disc(1, AI)
        for _ in range(2):
            bd.drop_disc(2, HUMAN)
        bd.drop_disc(2, AI)
        for _ in range(3):
            bd.drop_disc(3, HUMAN)
        bd.drop_disc(3, AI)
        self.assertEqual(bd.count_fours(AI), 1)

    def test_full_board_winner_by_ai_even_on_human_last_move(self):
        b = Connect4Board()
        # Fill board with AI getting more connect-4s, human playing the final disc
        for c in range(b.cols):
            for r in range(b.rows):
                if c == b.cols - 1 and r == b.rows - 1:
                    b.drop_disc(c, HUMAN)
                else:
                    player = AI if c < 4 else HUMAN
                    b.drop_disc(c, player)
        self.assertTrue(b.is_full())
        self.assertEqual(b.get_winner(), "AI")


class TestHeuristicAndMinimax(unittest.TestCase):
    def test_heuristic_prefers_ai_advantage(self):
        ev = BoardEvaluator(ai_player=AI, opp_player=HUMAN)
        b_ai = Connect4Board()
        for c in range(3):
            b_ai.drop_disc(c, AI)

        b_human = Connect4Board()
        for c in range(3):
            b_human.drop_disc(c, HUMAN)

        self.assertGreater(ev.evaluate(b_ai), 0)
        self.assertLess(ev.evaluate(b_human), 0)

    def test_alpha_beta_matches_plain_minimax_value_and_prunes(self):
        b = Connect4Board()
        for col, player in [(3, HUMAN), (3, AI), (2, HUMAN), (4, AI)]:
            b.drop_disc(col, player)

        ev = BoardEvaluator()
        plain = MinimaxAgent(k_depth=3, evaluator=ev, use_alpha_beta=False)
        ab = MinimaxAgent(k_depth=3, evaluator=ev, use_alpha_beta=True)

        _, plain_val = plain.choose_move(b, print_tree=False, record_tree=False)
        _, ab_val = ab.choose_move(b, print_tree=False, record_tree=True)

        self.assertEqual(plain_val, ab_val)
        self.assertLess(ab.nodes_expanded, plain.nodes_expanded)
        self.assertGreater(ab.pruned_branches, 0)

    def test_ai_blocks_immediate_human_connect_four(self):
        b = Connect4Board()
        # Human has 3 in a row at bottom: cols 0, 1, 2 -> col 3 completes 4
        b.drop_disc(0, HUMAN)
        b.drop_disc(1, HUMAN)
        b.drop_disc(2, HUMAN)
        b.drop_disc(6, AI)
        b.drop_disc(6, AI)

        ab = MinimaxAgent(k_depth=3, use_alpha_beta=True)
        best_col, _ = ab.choose_move(b, print_tree=False, record_tree=False)
        self.assertEqual(best_col, 3)

    def test_tree_formatting_contains_heuristic_values_and_json_serializable(self):
        b = Connect4Board()
        b.drop_disc(3, HUMAN)

        ab = MinimaxAgent(k_depth=2, use_alpha_beta=True)
        ab.choose_move(b, print_tree=False, record_tree=True)

        self.assertIsNotNone(ab.last_tree)
        tree_text = format_minimax_tree(ab.last_tree, use_alpha_beta=True)
        self.assertIn("Heuristic Board Value =", tree_text)
        self.assertIn("MAX (ROOT)", tree_text)

        tree_json = ab.last_tree.to_dict()
        self.assertEqual(tree_json["node_type"], "MAX")
        self.assertTrue(len(tree_json["children"]) > 0)


if __name__ == "__main__":
    unittest.main()
