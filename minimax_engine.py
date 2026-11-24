"""
Minimax Search Engine with Alpha-Beta Pruning and Tree Tracing.

Implements:
- Minimax with Alpha-Beta Pruning (required by Assignment 2)
- Plain Minimax without pruning (optional toggle for benchmark comparison)
- Structured Minimax Tree recording for both readable console printing
  (with explicit heuristic board values at every evaluated leaf) and
  JSON serialization for GUI tree visualization (bonus feature).
"""

from dataclasses import dataclass, field
import math
import time
from typing import Any, Dict, List, Optional, Tuple

from game_board import Connect4Board, HUMAN, AI
from heuristic import BoardEvaluator


@dataclass
class TreeNode:
    """Represents a single node in the Minimax / Alpha-Beta search tree."""

    node_type: str  # "MAX", "MIN", "LEAF", "TERMINAL", or "PRUNED"
    col: Optional[int]  # Column played to reach this node (None for root)
    depth: int  # Remaining search depth at this node
    value: Optional[float] = None  # Minimax backed-up value (or leaf score)
    heuristic_value: Optional[int] = None  # Explicit board heuristic value at leaves
    alpha: Optional[float] = None
    beta: Optional[float] = None
    pruned: bool = False
    children: List["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the node and its subtree into JSON-safe dictionaries."""
        def _fmt_bound(v: Optional[float]) -> Optional[Any]:
            if v is None:
                return None
            if v == math.inf:
                return "inf"
            if v == -math.inf:
                return "-inf"
            return v

        return {
            "node_type": self.node_type,
            "col": self.col,
            "depth": self.depth,
            "value": _fmt_bound(self.value),
            "heuristic_value": self.heuristic_value,
            "alpha": _fmt_bound(self.alpha),
            "beta": _fmt_bound(self.beta),
            "pruned": self.pruned,
            "children": [child.to_dict() for child in self.children],
        }


def format_minimax_tree(
    root: TreeNode,
    use_alpha_beta: bool = True,
    max_print_depth: Optional[int] = None,
) -> str:
    """
    Format a TreeNode hierarchy as a readable, traceable console tree.

    Explicitly displays:
    - Node role (MAX / MIN / LEAF / TERMINAL / PRUNED)
    - Column move
    - Evaluated score
    - Explicit Heuristic Board Value at every leaf / cutoff node
    - Alpha / Beta bounds (when alpha-beta pruning is enabled)
    """
    lines: List[str] = []

    def _fmt(v: Optional[float]) -> str:
        if v is None:
            return "-"
        if v == math.inf:
            return "+inf"
        if v == -math.inf:
            return "-inf"
        return str(int(v)) if isinstance(v, (int, float)) and float(v).is_integer() else f"{v:.1f}"

    def _walk(node: TreeNode, prefix: str, is_last: bool, level: int) -> None:
        connector = "" if level == 0 else ("`-- " if is_last else "|-- ")
        col_label = "ROOT" if node.col is None else f"Col {node.col}"

        if node.pruned:
            bounds = f" [alpha={_fmt(node.alpha)}, beta={_fmt(node.beta)}]" if use_alpha_beta else ""
            lines.append(f"{prefix}{connector}[PRUNED] {col_label}{bounds}")
            return

        if node.node_type == "TERMINAL":
            lines.append(
                f"{prefix}{connector}TERMINAL ({col_label}) -> "
                f"Board Value = {_fmt(node.value)}"
            )
            return

        if node.node_type == "LEAF":
            lines.append(
                f"{prefix}{connector}LEAF ({col_label}) -> "
                f"Heuristic Board Value = {node.heuristic_value}"
            )
            return

        bounds = (
            f" [alpha={_fmt(node.alpha)}, beta={_fmt(node.beta)}]"
            if use_alpha_beta
            else ""
        )
        lines.append(
            f"{prefix}{connector}{node.node_type} ({col_label}) -> "
            f"Val = {_fmt(node.value)}{bounds}"
        )

        if max_print_depth is not None and level >= max_print_depth:
            if node.children:
                child_prefix = prefix + ("    " if is_last else "|   ")
                lines.append(
                    f"{child_prefix}... ({len(node.children)} deeper branches omitted)"
                )
            return

        child_prefix = "" if level == 0 else prefix + ("    " if is_last else "|   ")
        for idx, child in enumerate(node.children):
            _walk(child, child_prefix, idx == len(node.children) - 1, level + 1)

    _walk(root, "", True, 0)
    return "\n".join(lines)


class MinimaxAgent:
    """
    Connect 4 AI Agent using depth-limited Minimax with Alpha-Beta Pruning.

    Attributes:
        k_depth (int): Maximum search depth K before heuristic cutoff.
        use_alpha_beta (bool): Enable alpha-beta pruning (True by default).
        nodes_expanded (int): Count of nodes expanded during the last search.
        pruned_branches (int): Count of pruned sibling branches in the last search.
        execution_time (float): Elapsed time in seconds for the last search.
        last_tree (Optional[TreeNode]): Root of the most recent search tree.
    """

    TERMINAL_SCORE_SCALE = 10000

    def __init__(
        self,
        k_depth: int = 4,
        evaluator: Optional[BoardEvaluator] = None,
        ai_player: int = AI,
        opp_player: int = HUMAN,
        use_alpha_beta: bool = True,
    ) -> None:
        if k_depth < 1:
            raise ValueError("Search depth K must be at least 1.")
        self.k_depth = k_depth
        self.ai_player = ai_player
        self.opp_player = opp_player
        self.evaluator = evaluator or BoardEvaluator(ai_player=ai_player, opp_player=opp_player)
        self.use_alpha_beta = use_alpha_beta

        # Per-turn telemetry
        self.nodes_expanded: int = 0
        self.pruned_branches: int = 0
        self.execution_time: float = 0.0
        self.last_tree: Optional[TreeNode] = None

    def choose_move(
        self,
        board: Connect4Board,
        print_tree: bool = True,
        record_tree: bool = True,
    ) -> Tuple[int, float]:
        """
        Run Minimax (with optional Alpha-Beta pruning) on a copy of `board`.

        Returns:
            (best_col, best_value)
        """
        self.nodes_expanded = 0
        self.pruned_branches = 0
        start_time = time.perf_counter()

        sim_board = board.clone()
        valid_cols = sim_board.get_available_cols(center_first=self.use_alpha_beta)
        if not valid_cols:
            raise ValueError("No valid moves available: board is already full.")

        root_node = TreeNode(
            node_type="MAX",
            col=None,
            depth=self.k_depth,
            alpha=-math.inf,
            beta=math.inf,
        )
        self.nodes_expanded += 1

        best_col = valid_cols[0]
        best_val = -math.inf
        alpha = -math.inf
        beta = math.inf

        for idx, col in enumerate(valid_cols):
            sim_board.drop_disc(col, self.ai_player)
            child_val, child_node = self._search(
                board=sim_board,
                depth=self.k_depth - 1,
                is_maximizing=False,
                alpha=alpha,
                beta=beta,
                move_col=col,
                record_tree=record_tree,
            )
            sim_board.undo_move()

            if record_tree and child_node is not None:
                root_node.children.append(child_node)

            if child_val > best_val:
                best_val = child_val
                best_col = col

            if self.use_alpha_beta:
                alpha = max(alpha, best_val)
                if beta <= alpha and idx < len(valid_cols) - 1:
                    self.pruned_branches += len(valid_cols) - 1 - idx
                    if record_tree:
                        for pruned_col in valid_cols[idx + 1 :]:
                            root_node.children.append(
                                TreeNode(
                                    node_type="PRUNED",
                                    col=pruned_col,
                                    depth=self.k_depth - 1,
                                    alpha=alpha,
                                    beta=beta,
                                    pruned=True,
                                )
                            )
                    break

        root_node.value = best_val
        root_node.alpha = alpha
        root_node.beta = beta
        self.execution_time = time.perf_counter() - start_time
        self.last_tree = root_node if record_tree else None

        if print_tree and record_tree:
            algo_name = "MINIMAX + ALPHA-BETA" if self.use_alpha_beta else "PLAIN MINIMAX"
            print(f"\n================ {algo_name} (K={self.k_depth}) ================")
            print(format_minimax_tree(root_node, use_alpha_beta=self.use_alpha_beta))
            print(
                f"Selected Move: Col {best_col} | Value: {best_val} | "
                f"Nodes Expanded: {self.nodes_expanded} | "
                f"Pruned: {self.pruned_branches} | "
                f"Time: {self.execution_time * 1000:.2f} ms"
            )
            print("================================================================\n")

        return best_col, best_val

    def _search(
        self,
        board: Connect4Board,
        depth: int,
        is_maximizing: bool,
        alpha: float,
        beta: float,
        move_col: int,
        record_tree: bool,
    ) -> Tuple[float, Optional[TreeNode]]:
        """Recursive Minimax with Alpha-Beta Pruning."""
        self.nodes_expanded += 1

        # 1. Terminal state (full board): exact score difference
        if board.is_full():
            ai_fours = board.count_fours(self.ai_player)
            opp_fours = board.count_fours(self.opp_player)
            terminal_val = (ai_fours - opp_fours) * self.TERMINAL_SCORE_SCALE
            node = (
                TreeNode(
                    node_type="TERMINAL",
                    col=move_col,
                    depth=depth,
                    value=terminal_val,
                    heuristic_value=terminal_val,
                    alpha=alpha,
                    beta=beta,
                )
                if record_tree
                else None
            )
            return terminal_val, node

        # 2. Depth cutoff (K levels reached): evaluate with heuristic
        if depth == 0:
            h_val = self.evaluator.evaluate(board)
            node = (
                TreeNode(
                    node_type="LEAF",
                    col=move_col,
                    depth=0,
                    value=h_val,
                    heuristic_value=h_val,
                    alpha=alpha,
                    beta=beta,
                )
                if record_tree
                else None
            )
            return h_val, node

        valid_cols = board.get_available_cols(center_first=self.use_alpha_beta)
        node = (
            TreeNode(
                node_type="MAX" if is_maximizing else "MIN",
                col=move_col,
                depth=depth,
                alpha=alpha,
                beta=beta,
            )
            if record_tree
            else None
        )

        if is_maximizing:
            best_val = -math.inf
            for idx, col in enumerate(valid_cols):
                board.drop_disc(col, self.ai_player)
                val, child = self._search(
                    board, depth - 1, False, alpha, beta, col, record_tree
                )
                board.undo_move()

                if record_tree and node is not None and child is not None:
                    node.children.append(child)

                if val > best_val:
                    best_val = val

                if self.use_alpha_beta:
                    alpha = max(alpha, best_val)
                    if beta <= alpha:
                        remaining = valid_cols[idx + 1 :]
                        self.pruned_branches += len(remaining)
                        if record_tree and node is not None:
                            for pruned_col in remaining:
                                node.children.append(
                                    TreeNode(
                                        node_type="PRUNED",
                                        col=pruned_col,
                                        depth=depth - 1,
                                        alpha=alpha,
                                        beta=beta,
                                        pruned=True,
                                    )
                                )
                        break

            if node is not None:
                node.value = best_val
                node.alpha = alpha
                node.beta = beta
            return best_val, node

        else:
            best_val = math.inf
            for idx, col in enumerate(valid_cols):
                board.drop_disc(col, self.opp_player)
                val, child = self._search(
                    board, depth - 1, True, alpha, beta, col, record_tree
                )
                board.undo_move()

                if record_tree and node is not None and child is not None:
                    node.children.append(child)

                if val < best_val:
                    best_val = val

                if self.use_alpha_beta:
                    beta = min(beta, best_val)
                    if beta <= alpha:
                        remaining = valid_cols[idx + 1 :]
                        self.pruned_branches += len(remaining)
                        if record_tree and node is not None:
                            for pruned_col in remaining:
                                node.children.append(
                                    TreeNode(
                                        node_type="PRUNED",
                                        col=pruned_col,
                                        depth=depth - 1,
                                        alpha=alpha,
                                        beta=beta,
                                        pruned=True,
                                    )
                                )
                        break

            if node is not None:
                node.value = best_val
                node.alpha = alpha
                node.beta = beta
            return best_val, node
