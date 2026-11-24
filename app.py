"""
Flask REST API Backend for the Connect 4 AI Agent.

Exposes clean JSON endpoints so any frontend (React, Vue, HTML/JS, etc.)
can start games, drop discs, display scores/heuristic values, and render
the Minimax Alpha-Beta search tree in the GUI.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

from game_board import Connect4Board, HUMAN, AI
from heuristic import BoardEvaluator
from minimax_engine import MinimaxAgent

app = Flask(__name__)
CORS(app)

# Active game session state
game_state = {
    "board": None,
    "evaluator": None,
    "agent": None,
    "human_color": "red",
    "ai_color": "yellow",
    "print_tree": True,
}


@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/start", methods=["POST"])
def start_game():
    """
    Initialize a new Human vs. Computer Connect 4 session.

    Expected JSON body (all fields optional with safe defaults):
    {
        "depth": 4,               # Search depth K (>= 1)
        "rows": 6,                # Board height (>= 6)
        "cols": 7,                # Board width (>= 7)
        "human_color": "red",     # "red" or "yellow"
        "use_alpha_beta": true,   # true = Alpha-Beta, false = Plain Minimax
        "print_tree": true        # Print traceable Minimax tree to console
    }
    """
    data = request.get_json(silent=True) or {}

    try:
        k_depth = int(data.get("depth", 4))
        rows = int(data.get("rows", 6))
        cols = int(data.get("cols", 7))
        use_alpha_beta = bool(data.get("use_alpha_beta", True))
        print_tree = bool(data.get("print_tree", True))
        human_color = str(data.get("human_color", "red")).lower()
        ai_color = "yellow" if human_color == "red" else "red"

        board = Connect4Board(rows=rows, cols=cols)
        evaluator = BoardEvaluator(ai_player=AI, opp_player=HUMAN)
        agent = MinimaxAgent(
            k_depth=k_depth,
            evaluator=evaluator,
            ai_player=AI,
            opp_player=HUMAN,
            use_alpha_beta=use_alpha_beta,
        )
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

    game_state["board"] = board
    game_state["evaluator"] = evaluator
    game_state["agent"] = agent
    game_state["human_color"] = human_color
    game_state["ai_color"] = ai_color
    game_state["print_tree"] = print_tree

    return jsonify(
        {
            "message": "Game started",
            "rows": rows,
            "cols": cols,
            "depth": k_depth,
            "human_color": human_color,
            "ai_color": ai_color,
            "use_alpha_beta": use_alpha_beta,
            "grid": board.to_matrix(),
            "human_score": 0,
            "ai_score": 0,
            "board_heuristic_value": 0,
        }
    )


@app.route("/state", methods=["GET"])
def get_state():
    """Return the current board state, scores, and heuristic evaluation."""
    board: Connect4Board = game_state["board"]
    evaluator: BoardEvaluator = game_state["evaluator"]
    if board is None:
        return jsonify({"error": "Game not started. Call POST /start first."}), 400

    human_score, ai_score = board.get_scores()
    breakdown = evaluator.evaluate_detailed(board)
    return jsonify(
        {
            "grid": board.to_matrix(),
            "rows": board.rows,
            "cols": board.cols,
            "human_color": game_state["human_color"],
            "ai_color": game_state["ai_color"],
            "human_score": human_score,
            "ai_score": ai_score,
            "game_over": board.is_full(),
            "winner": board.get_winner(),
            "board_heuristic_value": breakdown["total"],
            "heuristic_breakdown": breakdown,
        }
    )


@app.route("/move", methods=["POST"])
def make_move():
    """
    Apply the human player's move, then compute and apply the AI's response.

    Expected JSON body:
    {
        "col": 3,
        "include_tree": true   # Optional: return serialized minimax tree for GUI
    }
    """
    board: Connect4Board = game_state["board"]
    evaluator: BoardEvaluator = game_state["evaluator"]
    agent: MinimaxAgent = game_state["agent"]

    if board is None or agent is None:
        return jsonify({"error": "Game not started. Call POST /start first."}), 400

    if board.is_full():
        human_score, ai_score = board.get_scores()
        return jsonify(
            {
                "error": "Game is already over.",
                "grid": board.to_matrix(),
                "game_over": True,
                "winner": board.get_winner(),
                "human_score": human_score,
                "ai_score": ai_score,
            }
        ), 400

    data = request.get_json(silent=True) or {}
    col = data.get("col")
    include_tree = bool(data.get("include_tree", True))

    if not isinstance(col, int) or not board.is_valid_col(col):
        return jsonify({"error": f"Invalid column: {col}"}), 400

    # 1. Apply Human move
    human_row = board.drop_disc(col, HUMAN)

    # Check if Human's move filled the board
    if board.is_full():
        human_score, ai_score = board.get_scores()
        breakdown = evaluator.evaluate_detailed(board)
        return jsonify(
            {
                "grid": board.to_matrix(),
                "human_move": {"row": human_row, "col": col},
                "ai_move": None,
                "game_over": True,
                "winner": board.get_winner(),
                "human_score": human_score,
                "ai_score": ai_score,
                "board_heuristic_value": breakdown["total"],
                "heuristic_breakdown": breakdown,
                "execution_time": 0.0,
                "nodes_expanded": 0,
                "pruned_branches": 0,
                "minimax_tree": None,
            }
        )

    # 2. Run AI Minimax with Alpha-Beta Pruning (prints tree to console)
    best_col, best_eval = agent.choose_move(
        board,
        print_tree=game_state["print_tree"],
        record_tree=include_tree or game_state["print_tree"],
    )
    ai_row = board.drop_disc(best_col, AI)

    # 3. Compute updated scores and board heuristic value
    human_score, ai_score = board.get_scores()
    breakdown = evaluator.evaluate_detailed(board)
    print(
        f"Board Heuristic Value after AI move (Col {best_col}): "
        f"{breakdown['total']} | Breakdown: {breakdown}"
    )

    return jsonify(
        {
            "grid": board.to_matrix(),
            "human_move": {"row": human_row, "col": col},
            "ai_move": best_col,
            "ai_move_coords": {"row": ai_row, "col": best_col},
            "ai_eval": best_eval,
            "game_over": board.is_full(),
            "winner": board.get_winner(),
            "human_score": human_score,
            "ai_score": ai_score,
            "board_heuristic_value": breakdown["total"],
            "heuristic_breakdown": breakdown,
            "execution_time": round(agent.execution_time, 6),
            "nodes_expanded": agent.nodes_expanded,
            "pruned_branches": agent.pruned_branches,
            "minimax_tree": agent.last_tree.to_dict() if (include_tree and agent.last_tree) else None,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
