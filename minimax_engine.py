import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from game_board import AI, HUMAN, Connect4Board
from heuristic import BoardEvaluator

# Transposition Table Bound Flags
TT_EXACT = 0
TT_LOWERBOUND = 1
TT_UPPERBOUND = 2


def _serialize_num(val: Optional[float]) -> Any:
    """Converts Python inf/-inf into JSON-safe strings for the frontend."""
    if val is None:
        return None
    if val == math.inf:
        return "inf"
    if val == -math.inf:
        return "-inf"
    return val


@dataclass
class TreeNode:
    node_type: str  # "MAX", "MIN", "LEAF", "TERMINAL", "PRUNED"
    col: Optional[int] = None
    depth: int = 0
    value: Optional[float] = None
    heuristic_value: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    pruned: bool = False
    children: List["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "col": self.col,
            "depth": self.depth,
            "value": _serialize_num(self.value),
            "heuristic_value": _serialize_num(self.heuristic_value),
            "alpha": _serialize_num(self.alpha),
            "beta": _serialize_num(self.beta),
            "pruned": self.pruned,
            "children": [child.to_dict() for child in self.children],
        }

    def format_tree(self, indent: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        col_str = "ROOT" if self.col is None else f"Col {self.col}"

        if self.pruned:
            line = f"{indent}{connector}[PRUNED] {col_str}"
        elif self.node_type == "LEAF":
            line = f"{indent}{connector}[LEAF] {col_str} -> h={self.heuristic_value}"
        elif self.node_type == "TERMINAL":
            line = f"{indent}{connector}[TERMINAL] {col_str} -> Val={self.value}"
        else:
            bounds = ""
            if self.alpha is not None or self.beta is not None:
                a_s = _serialize_num(self.alpha)
                b_s = _serialize_num(self.beta)
                bounds = f" [α={a_s}, β={b_s}]"
            line = f"{indent}{connector}[{self.node_type}] {col_str} -> Val={self.value}{bounds}"

        lines = [line]
        child_indent = indent + ("    " if is_last else "│   ")
        for idx, child in enumerate(self.children):
            lines.append(child.format_tree(child_indent, idx == len(self.children) - 1))
        return "\n".join(lines)


class MinimaxEngine:
    """
    Optimized Connect 4 Minimax Engine featuring:
      - Bitboard-powered fast search & evaluation
      - Transposition Table (Exact / Lower / Upper bounds)
      - Iterative Deepening with PV/TT Move Ordering
      - Constrained Tree Recording for lag-free UI inspection at high K
    """

    MAX_TT_ENTRIES = 500_000

    def __init__(
        self,
        k_depth: int = 4,
        evaluator: Optional[BoardEvaluator] = None,
        use_alpha_beta: bool = True,
        ai_player: int = AI,
        opp_player: int = HUMAN,
        depth: Optional[int] = None,
    ) -> None:
        self.k_depth: int = depth if depth is not None else k_depth
        self.use_alpha_beta: bool = use_alpha_beta
        self.ai_player: int = ai_player
        self.opp_player: int = opp_player
        self.evaluator = evaluator or BoardEvaluator(
            ai_player=ai_player, opp_player=opp_player
        )
        # key: (human_mask, ai_mask, maximizing)
        # val: (depth, flag, score, best_col)
        self.tt: Dict[Tuple[int, int, bool], Tuple[int, int, float, Optional[int]]] = {}
        self.nodes_expanded: int = 0
        self.pruned_branches: int = 0
        self.tt_hits: int = 0
        self.execution_time: float = 0.0
        self.best_score: float = 0.0
        self.last_tree: Optional[TreeNode] = None

    def clear_cache(self) -> None:
        self.tt.clear()

    def choose_move(
        self,
        board: Connect4Board,
        depth: Optional[int] = None,
        use_alpha_beta: Optional[bool] = None,
        print_tree: bool = False,
        record_tree: bool = True,
        max_tree_depth: Optional[int] = None,
    ) -> Tuple[Optional[int], float]:
        start_time = time.perf_counter()

        search_depth = self.k_depth if depth is None else depth
        alpha_beta = (
            self.use_alpha_beta if use_alpha_beta is None else use_alpha_beta
        )

        if board.is_full():
            final_score = float(
                BoardEvaluator.W_FOUR
                * (board.count_fours(self.ai_player) - board.count_fours(self.opp_player))
            )
            self.nodes_expanded = 0
            self.pruned_branches = 0
            self.execution_time = time.perf_counter() - start_time
            self.best_score = final_score
            self.last_tree = None
            return None, final_score

        # Prevent unbounded RAM growth across long matches
        if len(self.tt) > self.MAX_TT_ENTRIES:
            self.tt.clear()

        self.nodes_expanded = 0
        self.pruned_branches = 0
        self.tt_hits = 0

        # Cap recorded GUI tree depth at high K so the engine searches full K
        # without allocating hundreds of thousands of TreeNode objects.
        if max_tree_depth is None:
            tree_limit = search_depth if search_depth <= 4 else 3
        else:
            tree_limit = max_tree_depth

        need_tree = record_tree or print_tree
        best_col: Optional[int] = None
        best_score: float = -math.inf
        root_tree: Optional[TreeNode] = None

        if alpha_beta:
            # Iterative Deepening warm-up for K >= 5 to populate TT move ordering
            if search_depth >= 5:
                for d in range(1, search_depth):
                    self._alphabeta(
                        board=board,
                        depth=d,
                        alpha=-math.inf,
                        beta=math.inf,
                        maximizing=True,
                        record_tree=False,
                        tree_depth_left=0,
                    )

            if need_tree:
                root_tree = TreeNode(
                    node_type="MAX",
                    col=None,
                    depth=0,
                    alpha=-math.inf,
                    beta=math.inf,
                )

            best_score, best_col = self._alphabeta(
                board=board,
                depth=search_depth,
                alpha=-math.inf,
                beta=math.inf,
                maximizing=True,
                record_tree=need_tree,
                tree_depth_left=tree_limit,
                tree_node=root_tree,
            )
        else:
            # Plain Minimax (no Alpha-Beta, no TT) for fair benchmark comparison
            if need_tree:
                root_tree = TreeNode(node_type="MAX", col=None, depth=0)

            best_score, best_col = self._minimax_plain(
                board=board,
                depth=search_depth,
                maximizing=True,
                record_tree=need_tree,
                tree_depth_left=tree_limit,
                tree_node=root_tree,
            )

        if root_tree is not None:
            root_tree.value = best_score

        self.execution_time = time.perf_counter() - start_time
        self.best_score = best_score
        self.last_tree = root_tree

        if print_tree and root_tree is not None:
            print(root_tree.format_tree())

        return best_col, best_score

    def _alphabeta(
        self,
        board: Connect4Board,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        record_tree: bool,
        tree_depth_left: int,
        tree_node: Optional[TreeNode] = None,
    ) -> Tuple[float, Optional[int]]:
        self.nodes_expanded += 1
        orig_alpha = alpha
        orig_beta = beta

        # 1. Terminal check (board completely full)
        if board.is_full():
            score = BoardEvaluator.W_FOUR * (
                board.count_fours(self.ai_player) - board.count_fours(self.opp_player)
            )
            if tree_node is not None:
                tree_node.node_type = "TERMINAL"
                tree_node.value = score
            return score, None

        # 2. Depth limit reached -> Bitboard Heuristic Evaluation
        if depth == 0:
            score = self.evaluator.evaluate(board)
            if tree_node is not None:
                tree_node.node_type = "LEAF"
                tree_node.heuristic_value = score
                tree_node.value = score
            return score, None

        # 3. Transposition Table Lookup
        tt_key = (board.human_mask, board.ai_mask, maximizing)
        tt_entry = self.tt.get(tt_key)
        tt_best_col: Optional[int] = None

        if tt_entry is not None:
            entry_depth, entry_flag, entry_val, tt_best_col = tt_entry
            can_cutoff = not (record_tree and tree_node is not None and tree_node.col is None)
            if can_cutoff and entry_depth >= depth:
                self.tt_hits += 1
                if entry_flag == TT_EXACT:
                    if tree_node is not None:
                        tree_node.value = entry_val
                        tree_node.alpha = alpha
                        tree_node.beta = beta
                    return entry_val, tt_best_col
                elif entry_flag == TT_LOWERBOUND:
                    if entry_val > alpha:
                        alpha = entry_val
                elif entry_flag == TT_UPPERBOUND:
                    if entry_val < beta:
                        beta = entry_val

                if alpha >= beta:
                    self.pruned_branches += 1
                    if tree_node is not None:
                        tree_node.value = entry_val
                        tree_node.alpha = alpha
                        tree_node.beta = beta
                    return entry_val, tt_best_col

        # 4. Move Ordering: TT best move first, then center-first
        cols = board.get_available_cols(center_first=True)
        if tt_best_col is not None and tt_best_col in cols:
            cols.remove(tt_best_col)
            cols.insert(0, tt_best_col)

        best_col = cols[0]
        record_children = record_tree and tree_node is not None and tree_depth_left > 0

        if maximizing:
            value = -math.inf
            for idx, col in enumerate(cols):
                board.drop_disc(col, self.ai_player)

                child_node: Optional[TreeNode] = None
                if record_children:
                    child_node = TreeNode(
                        node_type="MIN",
                        col=col,
                        depth=tree_node.depth + 1,
                        alpha=alpha,
                        beta=beta,
                    )
                    tree_node.children.append(child_node)

                child_val, _ = self._alphabeta(
                    board=board,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    maximizing=False,
                    record_tree=record_children,
                    tree_depth_left=tree_depth_left - 1,
                    tree_node=child_node,
                )
                board.undo_move()

                if child_val > value:
                    value = child_val
                    best_col = col
                if value > alpha:
                    alpha = value

                if alpha >= beta:
                    remaining = len(cols) - idx - 1
                    if remaining > 0:
                        self.pruned_branches += remaining
                        if record_children:
                            for p_col in cols[idx + 1 :]:
                                tree_node.children.append(
                                    TreeNode(
                                        node_type="PRUNED",
                                        col=p_col,
                                        depth=tree_node.depth + 1,
                                        alpha=alpha,
                                        beta=beta,
                                        pruned=True,
                                    )
                                )
                    break
        else:
            value = math.inf
            for idx, col in enumerate(cols):
                board.drop_disc(col, self.opp_player)

                child_node = None
                if record_children:
                    child_node = TreeNode(
                        node_type="MAX",
                        col=col,
                        depth=tree_node.depth + 1,
                        alpha=alpha,
                        beta=beta,
                    )
                    tree_node.children.append(child_node)

                child_val, _ = self._alphabeta(
                    board=board,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    maximizing=True,
                    record_tree=record_children,
                    tree_depth_left=tree_depth_left - 1,
                    tree_node=child_node,
                )
                board.undo_move()

                if child_val < value:
                    value = child_val
                    best_col = col
                if value < beta:
                    beta = value

                if alpha >= beta:
                    remaining = len(cols) - idx - 1
                    if remaining > 0:
                        self.pruned_branches += remaining
                        if record_children:
                            for p_col in cols[idx + 1 :]:
                                tree_node.children.append(
                                    TreeNode(
                                        node_type="PRUNED",
                                        col=p_col,
                                        depth=tree_node.depth + 1,
                                        alpha=alpha,
                                        beta=beta,
                                        pruned=True,
                                    )
                                )
                    break

        # 5. Store in Transposition Table
        if value <= orig_alpha:
            flag = TT_UPPERBOUND
        elif value >= orig_beta:
            flag = TT_LOWERBOUND
        else:
            flag = TT_EXACT

        if tt_entry is None or depth >= tt_entry[0]:
            self.tt[tt_key] = (depth, flag, value, best_col)

        if tree_node is not None:
            tree_node.value = value
            tree_node.alpha = alpha
            tree_node.beta = beta

        return value, best_col

    def _minimax_plain(
        self,
        board: Connect4Board,
        depth: int,
        maximizing: bool,
        record_tree: bool,
        tree_depth_left: int,
        tree_node: Optional[TreeNode] = None,
    ) -> Tuple[float, Optional[int]]:
        self.nodes_expanded += 1

        if board.is_full():
            score = BoardEvaluator.W_FOUR * (
                board.count_fours(self.ai_player) - board.count_fours(self.opp_player)
            )
            if tree_node is not None:
                tree_node.node_type = "TERMINAL"
                tree_node.value = score
            return score, None

        if depth == 0:
            score = self.evaluator.evaluate(board)
            if tree_node is not None:
                tree_node.node_type = "LEAF"
                tree_node.heuristic_value = score
                tree_node.value = score
            return score, None

        cols = board.get_available_cols(center_first=False)
        best_col = cols[0]
        record_children = record_tree and tree_node is not None and tree_depth_left > 0

        if maximizing:
            value = -math.inf
            for col in cols:
                board.drop_disc(col, self.ai_player)
                child_node = None
                if record_children:
                    child_node = TreeNode(
                        node_type="MIN", col=col, depth=tree_node.depth + 1
                    )
                    tree_node.children.append(child_node)

                child_val, _ = self._minimax_plain(
                    board=board,
                    depth=depth - 1,
                    maximizing=False,
                    record_tree=record_children,
                    tree_depth_left=tree_depth_left - 1,
                    tree_node=child_node,
                )
                board.undo_move()

                if child_val > value:
                    value = child_val
                    best_col = col
        else:
            value = math.inf
            for col in cols:
                board.drop_disc(col, self.opp_player)
                child_node = None
                if record_children:
                    child_node = TreeNode(
                        node_type="MAX", col=col, depth=tree_node.depth + 1
                    )
                    tree_node.children.append(child_node)

                child_val, _ = self._minimax_plain(
                    board=board,
                    depth=depth - 1,
                    maximizing=True,
                    record_tree=record_children,
                    tree_depth_left=tree_depth_left - 1,
                    tree_node=child_node,
                )
                board.undo_move()

                if child_val < value:
                    value = child_val
                    best_col = col

        if tree_node is not None:
            tree_node.value = value

        return value, best_col


MinimaxAgent = MinimaxEngine