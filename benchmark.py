"""
Benchmark Script for Assignment 2 Report.

Measures execution time and nodes expanded across different search depths K,
comparing Plain Minimax against Minimax with Alpha-Beta Pruning on a realistic
mid-game Connect 4 board state.

Run directly with:
    python benchmark.py
"""

from typing import List
from game_board import Connect4Board, HUMAN, AI
from heuristic import BoardEvaluator
from minimax_engine import MinimaxAgent


def create_midgame_board() -> Connect4Board:
    """Create a repeatable mid-game 6x7 board position for fair benchmarking."""
    board = Connect4Board(rows=6, cols=7)
    opening_moves = [
        (3, HUMAN),
        (3, AI),
        (2, HUMAN),
        (4, AI),
        (2, HUMAN),
        (2, AI),
        (4, HUMAN),
        (3, AI),
    ]
    for col, player in opening_moves:
        board.drop_disc(col, player)
    return board


def run_benchmark(depths: List[int]) -> None:
    board = create_midgame_board()
    evaluator = BoardEvaluator(ai_player=AI, opp_player=HUMAN)

    print("=== Connect 4 Benchmark: Minimax vs. Alpha-Beta Pruning ===")
    print(board.render_ascii())
    print(f"Initial Board Heuristic Value: {evaluator.evaluate(board)}\n")

    header = (
        f"{'K':>2} | {'AB Move':>7} | {'AB Nodes':>10} | {'AB Time (ms)':>12} | "
        f"{'AB Pruned':>9} | {'Plain Nodes':>11} | {'Plain Time (ms)':>15} | {'Node Reduction':>14}"
    )
    print(header)
    print("-" * len(header))

    for k in depths:
        ab_agent = MinimaxAgent(k_depth=k, evaluator=evaluator, use_alpha_beta=True)
        ab_col, _ = ab_agent.choose_move(board, print_tree=False, record_tree=False)

        # Plain Minimax grows O(7^K), so skip plain minimax above K=5 by default
        if k <= 5:
            plain_agent = MinimaxAgent(k_depth=k, evaluator=evaluator, use_alpha_beta=False)
            plain_agent.choose_move(board, print_tree=False, record_tree=False)
            reduction = (1.0 - (ab_agent.nodes_expanded / plain_agent.nodes_expanded)) * 100.0
            plain_nodes_str = f"{plain_agent.nodes_expanded:>11}"
            plain_time_str = f"{plain_agent.execution_time * 1000:>15.2f}"
            reduction_str = f"{reduction:>13.1f}%"
        else:
            plain_nodes_str = f"{'skipped':>11}"
            plain_time_str = f"{'skipped':>15}"
            reduction_str = f"{'-':>14}"

        print(
            f"{k:>2} | {ab_col:>7} | {ab_agent.nodes_expanded:>10} | "
            f"{ab_agent.execution_time * 1000:>12.2f} | {ab_agent.pruned_branches:>9} | "
            f"{plain_nodes_str} | {plain_time_str} | {reduction_str}"
        )


if __name__ == "__main__":
    run_benchmark(depths=[1, 2, 3, 4, 5, 6])
