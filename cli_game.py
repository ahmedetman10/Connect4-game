"""
Playable Console Mode for Connect 4 (Human vs. Computer).

Run directly with:
    python cli_game.py

Satisfies Assignment 2 requirements:
- Player chooses disc color before starting
- Configurable board dimensions (rows >= 6, cols >= 7) and search depth K
- Plays until the board is completely full; winner has more connected-fours
- Prints the traceable Minimax + Alpha-Beta tree and heuristic board values
  on every AI turn
"""

from game_board import Connect4Board, HUMAN, AI
from heuristic import BoardEvaluator
from minimax_engine import MinimaxAgent


def prompt_int(label: str, default: int, min_val: int) -> int:
    """Prompt the user for an integer >= min_val with a default fallback."""
    while True:
        raw = input(f"{label} [default={default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if val >= min_val:
                return val
            print(f"Please enter an integer >= {min_val}.")
        except ValueError:
            print("Invalid integer. Try again.")


def main() -> None:
    print("=== Connect 4 AI (Minimax with Alpha-Beta Pruning) ===")
    color_choice = input("Choose your color (R for Red / Y for Yellow) [default=R]: ").strip().upper()
    if color_choice == "Y":
        human_symbol, ai_symbol = "Y", "R"
        human_color, ai_color = "Yellow", "Red"
    else:
        human_symbol, ai_symbol = "R", "Y"
        human_color, ai_color = "Red", "Yellow"

    rows = prompt_int("Board rows (>= 6)", default=6, min_val=6)
    cols = prompt_int("Board columns (>= 7)", default=7, min_val=7)
    k_depth = prompt_int("Search depth K (>= 1)", default=3, min_val=1)

    board = Connect4Board(rows=rows, cols=cols)
    evaluator = BoardEvaluator(ai_player=AI, opp_player=HUMAN)
    agent = MinimaxAgent(
        k_depth=k_depth,
        evaluator=evaluator,
        ai_player=AI,
        opp_player=HUMAN,
        use_alpha_beta=True,
    )

    print(f"\nYou are {human_color} ({human_symbol}); AI is {ai_color} ({ai_symbol}).")
    print(f"Playing on a {rows}x{cols} board with depth K={k_depth} until full.\n")

    while not board.is_full():
        print(board.render_ascii(human_symbol=human_symbol, ai_symbol=ai_symbol))
        human_score, ai_score = board.get_scores()
        current_h = evaluator.evaluate(board)
        print(
            f"Scores -> Human ({human_symbol}): {human_score} | "
            f"AI ({ai_symbol}): {ai_score} | Current Board Heuristic: {current_h}\n"
        )

        # Human turn
        while True:
            raw_col = input(f"Your move (0..{cols - 1}): ").strip()
            try:
                col = int(raw_col)
                if board.is_valid_col(col):
                    break
                print("Column is full or out of range. Pick another column.")
            except ValueError:
                print("Please enter a valid column number.")

        board.drop_disc(col, HUMAN)
        if board.is_full():
            break

        # AI turn (prints full traceable minimax tree + heuristic board values)
        best_col, _ = agent.choose_move(board, print_tree=True, record_tree=True)
        board.drop_disc(best_col, AI)
        post_h = evaluator.evaluate_detailed(board)
        print(
            f"AI dropped in column {best_col}. "
            f"Board Heuristic Value = {post_h['total']} {post_h}\n"
        )

    # Final board and winner announcement
    print("\n=== FINAL BOARD ===")
    print(board.render_ascii(human_symbol=human_symbol, ai_symbol=ai_symbol))
    human_score, ai_score = board.get_scores()
    print(f"Final Connected-Fours -> Human: {human_score} | AI: {ai_score}")
    print(f"Winner: {board.get_winner()}")


if __name__ == "__main__":
    main()
