# Connect 4 AI Backend (Minimax with Alpha-Beta Pruning)

Backend implementation for **Assignment 2 — Using Minimax Algorithm to Make Connect 4 AI Agent** (Artificial Intelligence Course).

## Features

- **Full-Board Connect 4 Rules**: Human vs. Computer on any board with `rows >= 6` and `cols >= 7` (default `6x7`). Players keep playing until the board is full, and the winner is the player with the greater number of connected-fours.
- **Minimax with Alpha-Beta Pruning**: Uses center-first move ordering and root-level alpha updates for strong branch pruning.
- **Multi-Factor Heuristic**: Evaluates completed connected-fours, 3-in-a-row / 2-in-a-row unblocked windows, immediate gravity-playable threats, and a dynamic window-participation positional matrix.
- **Traceable Tree Printing + Heuristic Values**: Prints the Minimax search tree to the console on every AI turn, explicitly showing each leaf's `Heuristic Board Value`, `[alpha, beta]` bounds, and `[PRUNED]` branches.
- **GUI-Ready REST API**: Returns board state, scores, heuristic breakdown, performance metrics, and the full JSON `minimax_tree` so a frontend can render the tree visually.
- **Built-in Console Mode & Benchmark Script**: Play directly in the terminal (`cli_game.py`) or generate K-depth timing and node-expansion tables (`benchmark.py`) for the report.

## Project Structure

```text
connect4-ai-backend/
├── app.py                # Flask REST API (/health, /start, /move, /state)
├── game_board.py         # Connect4Board class (O(1) move/undo, connect-4 counting)
├── heuristic.py          # Multi-factor BoardEvaluator heuristic
├── minimax_engine.py     # Minimax + Alpha-Beta engine, tree printer & JSON serializer
├── cli_game.py           # Playable Human vs. Computer console mode
├── benchmark.py          # Performance comparison across K = 1..6 for the report
├── tests/
│   └── test_backend.py   # Automated unit tests
├── requirements.txt
└── .gitignore
```

## Quick Start

### 1. Create a virtual environment and install dependencies

```bash
python -m venv venv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Flask API server (for Frontend integration)

```bash
python app.py
```

The server runs on `http://127.0.0.1:5000`.

#### API Endpoints

- `GET /health` — Health check.
- `POST /start` — Start a new game:
  ```json
  {
    "depth": 4,
    "rows": 6,
    "cols": 7,
    "human_color": "red",
    "use_alpha_beta": true,
    "print_tree": true
  }
  ```
- `POST /move` — Play a human column and get the AI response + tree:
  ```json
  {
    "col": 3,
    "include_tree": true
  }
  ```
- `GET /state` — Fetch current grid, scores, and heuristic breakdown.

### 3. Play in Console Mode (no extra packages required)

```bash
python cli_game.py
```

### 4. Run the K-Depth Benchmark (for your report)

```bash
python benchmark.py
```

### 5. Run Unit Tests

```bash
python -m unittest discover -s tests -v
```
