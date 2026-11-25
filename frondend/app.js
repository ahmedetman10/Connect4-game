/* =========================================================
   Connect 4 AI Arena — Frontend Controller & Lazy Tree Viewer
   ========================================================= */

const API_BASE = "http://127.0.0.1:5000";
const EMPTY = 0;
const HUMAN = 1;
const AI = 2;

// Application State
const state = {
  rows: 6,
  cols: 7,
  depth: 4,
  humanColor: "red",
  aiColor: "yellow",
  useAlphaBeta: true,
  includeTree: true,
  printTree: true,
  grid: [],
  humanScore: 0,
  aiScore: 0,
  movesCount: 0,
  isThinking: false,
  gameOver: false,
  lastMove: null,      // { row, col }
  animateCoord: null,  // { row, col }
  lastTree: null,
};

// DOM References
const dom = {
  apiStatus: document.getElementById("api-status"),
  apiStatusText: document.getElementById("api-status-text"),
  btnToggleSettings: document.getElementById("btn-toggle-settings"),
  btnQuickRestart: document.getElementById("btn-quick-restart"),
  settingsPanel: document.getElementById("settings-panel"),

  inputDepth: document.getElementById("input-depth"),
  depthBadge: document.getElementById("depth-badge"),
  depthWarning: document.getElementById("depth-warning"),
  inputRows: document.getElementById("input-rows"),
  inputCols: document.getElementById("input-cols"),
  colorChoices: document.querySelectorAll(".color-choice"),
  toggleAlphaBeta: document.getElementById("toggle-alpha-beta"),
  toggleIncludeTree: document.getElementById("toggle-include-tree"),
  togglePrintTree: document.getElementById("toggle-print-tree"),
  btnStartGame: document.getElementById("btn-start-game"),

  cardHuman: document.getElementById("card-human"),
  cardAi: document.getElementById("card-ai"),
  avatarHuman: document.getElementById("avatar-human"),
  avatarAi: document.getElementById("avatar-ai"),
  scoreHuman: document.getElementById("score-human"),
  scoreAi: document.getElementById("score-ai"),
  turnBadge: document.getElementById("turn-badge"),
  movesCount: document.getElementById("moves-count"),
  maxMoves: document.getElementById("max-moves"),

  colIndicators: document.getElementById("col-indicators"),
  boardGrid: document.getElementById("board-grid"),
  colLabels: document.getElementById("col-labels"),
  thinkingOverlay: document.getElementById("thinking-overlay"),
  thinkingDepth: document.getElementById("thinking-depth"),
  gameoverOverlay: document.getElementById("gameover-overlay"),
  winnerIcon: document.getElementById("winner-icon"),
  winnerTitle: document.getElementById("winner-title"),
  winnerSubtitle: document.getElementById("winner-subtitle"),
  btnPlayAgain: document.getElementById("btn-play-again"),

  algoBadge: document.getElementById("algo-badge"),
  metricTime: document.getElementById("metric-time"),
  metricNodes: document.getElementById("metric-nodes"),
  metricPruned: document.getElementById("metric-pruned"),
  metricCol: document.getElementById("metric-col"),

  heuristicTotal: document.getElementById("heuristic-total"),
  hbCompleted: document.getElementById("hb-completed"),
  hbThreats: document.getElementById("hb-threats"),
  hbGravity: document.getElementById("hb-gravity"),
  hbPositional: document.getElementById("hb-positional"),

  btnExpandLvl2: document.getElementById("btn-expand-lvl2"),
  btnCollapseAll: document.getElementById("btn-collapse-all"),
  treeContainer: document.getElementById("tree-container"),
};

/* =========================================================
   Initialization & Event Listeners
   ========================================================= */
function init() {
  bindEvents();
  checkBackendHealth().then((online) => {
    if (online) {
      startNewGame();
    }
  });
}

function bindEvents() {
    dom.inputRows.addEventListener("change", () => startNewGame());
dom.inputCols.addEventListener("change", () => startNewGame());
  dom.btnToggleSettings.addEventListener("click", () => {
    dom.settingsPanel.classList.toggle("hidden");
  });

  dom.btnQuickRestart.addEventListener("click", () => startNewGame());
  dom.btnStartGame.addEventListener("click", () => startNewGame());
  dom.btnPlayAgain.addEventListener("click", () => startNewGame());

  dom.inputDepth.addEventListener("input", () => {
    const k = parseInt(dom.inputDepth.value, 10);
    dom.depthBadge.textContent = `K = ${k}`;
    dom.depthWarning.classList.toggle("hidden", k < 7);
  });

  dom.colorChoices.forEach((btn) => {
  btn.addEventListener("click", () => {
    dom.colorChoices.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.humanColor = btn.dataset.color;
    state.aiColor = state.humanColor === "red" ? "yellow" : "red";
    dom.avatarHuman.className = `player-avatar ${state.humanColor}`;
    dom.avatarAi.className = `player-avatar ${state.aiColor}`;
    renderBoardDiscs();
  });
});

  dom.toggleIncludeTree.addEventListener("change", () => {
    state.includeTree = dom.toggleIncludeTree.checked;
  });

  dom.btnExpandLvl2.addEventListener("click", () => {
    if (state.lastTree) renderMinimaxTree(state.lastTree, 2);
  });

  dom.btnCollapseAll.addEventListener("click", () => {
    if (state.lastTree) renderMinimaxTree(state.lastTree, 0);
  });
}

/* =========================================================
   Backend API Communication
   ========================================================= */
async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("Unhealthy");
    dom.apiStatus.className = "status-pill online";
    dom.apiStatusText.textContent = "Backend Online (:5000)";
    return true;
  } catch (err) {
    dom.apiStatus.className = "status-pill offline";
    dom.apiStatusText.textContent = "Backend Offline — Run app.py";
    return false;
  }
}

async function startNewGame() {
  const depth = Math.max(1, parseInt(dom.inputDepth.value, 10) || 4);
  const rows = Math.max(6, Math.min(10, parseInt(dom.inputRows.value, 10) || 6));
  const cols = Math.max(7, Math.min(11, parseInt(dom.inputCols.value, 10) || 7));
  dom.inputRows.value = rows;
  dom.inputCols.value = cols;

  state.depth = depth;
  state.rows = rows;
  state.cols = cols;
  state.useAlphaBeta = dom.toggleAlphaBeta.checked;
  state.includeTree = dom.toggleIncludeTree.checked;
  state.printTree = dom.togglePrintTree.checked;
  state.isThinking = false;
  state.gameOver = false;
  state.lastMove = null;
  state.animateCoord = null;
  state.lastTree = null;

  try {
    const res = await fetch(`${API_BASE}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        depth: state.depth,
        rows: state.rows,
        cols: state.cols,
        human_color: state.humanColor,
        use_alpha_beta: state.useAlphaBeta,
        print_tree: state.printTree,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.error || "Failed to start game.");
      return;
    }

    dom.apiStatus.className = "status-pill online";
    dom.apiStatusText.textContent = "Backend Online (:5000)";

    state.grid = data.grid;
    state.humanColor = data.human_color;
    state.aiColor = data.ai_color;
    state.humanScore = 0;
    state.aiScore = 0;
    state.movesCount = 0;

    // Update static UI
    dom.avatarHuman.className = `player-avatar ${state.humanColor}`;
    dom.avatarAi.className = `player-avatar ${state.aiColor}`;
    dom.maxMoves.textContent = state.rows * state.cols;
    dom.algoBadge.textContent = state.useAlphaBeta
      ? `Alpha-Beta (K=${state.depth})`
      : `Plain Minimax (K=${state.depth})`;
    dom.thinkingDepth.textContent = `K=${state.depth}`;

    dom.gameoverOverlay.classList.add("hidden");
    dom.thinkingOverlay.classList.add("hidden");

    resetAnalyticsUI();
    updateScoreboardUI();
    setTurnUI("human");
    buildBoardStructure();
    renderBoardDiscs();
  } catch (err) {
    dom.apiStatus.className = "status-pill offline";
    dom.apiStatusText.textContent = "Backend Offline — Run app.py";
    alert("Cannot reach Flask backend at http://127.0.0.1:5000. Make sure `python app.py` is running.");
  }
}

async function handleColumnClick(col) {
  if (state.isThinking || state.gameOver) return;

  // Find lowest empty row (row 0 = bottom) for Optimistic UI update
  const targetRow = getLowestEmptyRow(col);
  if (targetRow === -1) return; // Column is full

  // 1. Optimistic Human Move (instant visual feedback)
  state.grid[targetRow][col] = HUMAN;
  state.movesCount += 1;
  state.lastMove = { row: targetRow, col };
  state.animateCoord = { row: targetRow, col };
  state.isThinking = true;

  renderBoardDiscs();
  updateScoreboardUI();
  setTurnUI("ai");
  dom.thinkingOverlay.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        col,
        include_tree: state.includeTree,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Move rejected by server.");
    }

    // 2. Sync with authoritative backend state + animate AI disc
    state.grid = data.grid;
    state.humanScore = data.human_score;
    state.aiScore = data.ai_score;
    state.gameOver = Boolean(data.game_over);

    if (data.ai_move_coords) {
      state.movesCount += 1;
      state.lastMove = data.ai_move_coords;
      state.animateCoord = data.ai_move_coords;
    } else {
      state.animateCoord = null;
    }

    state.isThinking = false;
    dom.thinkingOverlay.classList.add("hidden");

    renderBoardDiscs();
    updateScoreboardUI();
    updateTelemetryUI(data);
    updateHeuristicUI(data.heuristic_breakdown);

    if (data.minimax_tree) {
      state.lastTree = data.minimax_tree;
      renderMinimaxTree(data.minimax_tree, 2);
    } else if (!state.includeTree && data.ai_move !== null) {
      state.lastTree = null;
      dom.treeContainer.innerHTML =
        `<div class="tree-empty">GUI Tree is disabled for maximum speed at K=${state.depth}. Enable "GUI Tree" in Settings to inspect nodes.</div>`;
    }

    if (state.gameOver) {
      setTurnUI("over");
      showGameOverBanner(data.winner, data.human_score, data.ai_score, data.winning_lines);
    } else {
      setTurnUI("human");
    }
  } catch (err) {
    // Revert optimistic move on error
    state.grid[targetRow][col] = EMPTY;
    state.movesCount = Math.max(0, state.movesCount - 1);
    state.isThinking = false;
    state.animateCoord = null;
    dom.thinkingOverlay.classList.add("hidden");
    renderBoardDiscs();
    updateScoreboardUI();
    setTurnUI("human");
    alert(`Error: ${err.message}`);
  }
}

/* =========================================================
   Board Rendering (Flipped: row rows-1 at top, row 0 at bottom)
   ========================================================= */
function getLowestEmptyRow(col) {
  for (let r = 0; r < state.rows; r++) {
    if (state.grid[r] && state.grid[r][col] === EMPTY) {
      return r;
    }
  }
  return -1;
}

function buildBoardStructure() {
  const colTemplate = `repeat(${state.cols}, 1fr)`;
  dom.colIndicators.style.gridTemplateColumns = colTemplate;
  dom.boardGrid.style.gridTemplateColumns = colTemplate;
  dom.colLabels.style.gridTemplateColumns = colTemplate;

  // Top drop arrows
  dom.colIndicators.innerHTML = "";
  for (let c = 0; c < state.cols; c++) {
    const ind = document.createElement("div");
    ind.className = "col-indicator";
    ind.dataset.col = c;
    ind.textContent = "▼";
    ind.addEventListener("mouseenter", () => highlightColumn(c, true));
    ind.addEventListener("mouseleave", () => highlightColumn(c, false));
    ind.addEventListener("click", () => handleColumnClick(c));
    dom.colIndicators.appendChild(ind);
  }

  // Cells: loop TOP (rows - 1) down to BOTTOM (0)
  dom.boardGrid.innerHTML = "";
  for (let r = state.rows - 1; r >= 0; r--) {
    for (let c = 0; c < state.cols; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = r;
      cell.dataset.col = c;
      cell.addEventListener("mouseenter", () => highlightColumn(c, true));
      cell.addEventListener("mouseleave", () => highlightColumn(c, false));
      cell.addEventListener("click", () => handleColumnClick(c));
      dom.boardGrid.appendChild(cell);
    }
  }

  // Bottom column indices
  dom.colLabels.innerHTML = "";
  for (let c = 0; c < state.cols; c++) {
    const lbl = document.createElement("div");
    lbl.className = "col-label";
    lbl.textContent = c;
    dom.colLabels.appendChild(lbl);
  }
}

function renderBoardDiscs() {
  const cells = dom.boardGrid.querySelectorAll(".cell");
  cells.forEach((cell) => {
    const r = parseInt(cell.dataset.row, 10);
    const c = parseInt(cell.dataset.col, 10);
    const val = state.grid[r] ? state.grid[r][c] : EMPTY;
    const colFull = getLowestEmptyRow(c) === -1;

    cell.classList.toggle("disabled", colFull || state.isThinking || state.gameOver);
    cell.innerHTML = "";

    if (val !== EMPTY) {
      const disc = document.createElement("div");
      const color = val === HUMAN ? state.humanColor : state.aiColor;
      disc.className = `disc ${color}`;

      if (state.lastMove && state.lastMove.row === r && state.lastMove.col === c) {
        disc.classList.add("last-move");
      }
      if (state.animateCoord && state.animateCoord.row === r && state.animateCoord.col === c) {
        disc.classList.add("drop-anim");
      }

      cell.appendChild(disc);
    }
  });

  // Update top indicators disabled state
  const indicators = dom.colIndicators.querySelectorAll(".col-indicator");
  indicators.forEach((ind) => {
    const c = parseInt(ind.dataset.col, 10);
    const colFull = getLowestEmptyRow(c) === -1;
    ind.classList.toggle("disabled", colFull || state.isThinking || state.gameOver);
  });

  // Clear one-shot animation flag
  state.animateCoord = null;
}

function highlightColumn(col, active) {
  if (state.isThinking || state.gameOver) return;
  const colFull = getLowestEmptyRow(col) === -1;
  if (colFull && active) return;

  const ind = dom.colIndicators.querySelector(`.col-indicator[data-col="${col}"]`);
  if (ind) ind.classList.toggle("hover-active", active);

  const cells = dom.boardGrid.querySelectorAll(`.cell[data-col="${col}"]`);
  cells.forEach((cell) => cell.classList.toggle("col-hover", active));
}

/* =========================================================
   Scoreboard, Telemetry & Heuristic Breakdown UI
   ========================================================= */
function updateScoreboardUI() {
  dom.scoreHuman.textContent = state.humanScore;
  dom.scoreAi.textContent = state.aiScore;
  dom.movesCount.textContent = state.movesCount;
}

function setTurnUI(turn) {
  dom.cardHuman.classList.toggle("active-turn", turn === "human");
  dom.cardAi.classList.toggle("active-turn", turn === "ai");

  if (turn === "human") {
    dom.turnBadge.className = "turn-badge your-turn";
    dom.turnBadge.textContent = "Your Turn";
  } else if (turn === "ai") {
    dom.turnBadge.className = "turn-badge ai-turn";
    dom.turnBadge.textContent = "AI Thinking...";
  } else {
    dom.turnBadge.className = "turn-badge game-ended";
    dom.turnBadge.textContent = "Board Full";
  }
}

function resetAnalyticsUI() {
  dom.metricTime.textContent = "0.00 ms";
  dom.metricNodes.textContent = "0";
  dom.metricPruned.textContent = "0";
  dom.metricCol.textContent = "—";

  updateHeuristicUI({
    total: 0,
    completed_fours: 0,
    window_threats: 0,
    immediate_threats: 0,
    positional_control: 0,
  });

  dom.treeContainer.innerHTML =
    `<div class="tree-empty">Make your first move to inspect the AI's Minimax Alpha-Beta search tree.</div>`;
}

function updateTelemetryUI(data) {
  const ms = ((data.execution_time || 0) * 1000).toFixed(2);
  dom.metricTime.textContent = `${ms} ms`;
  dom.metricNodes.textContent = (data.nodes_expanded || 0).toLocaleString();
  dom.metricPruned.textContent = (data.pruned_branches || 0).toLocaleString();
  dom.metricCol.textContent = data.ai_move !== null && data.ai_move !== undefined ? `Col ${data.ai_move}` : "—";
}

function updateHeuristicUI(breakdown) {
  if (!breakdown) return;
  const total = breakdown.total ?? 0;
  dom.heuristicTotal.textContent = formatSigned(total);

  if (total > 0) dom.heuristicTotal.className = "heuristic-pill positive";
  else if (total < 0) dom.heuristicTotal.className = "heuristic-pill negative";
  else dom.heuristicTotal.className = "heuristic-pill neutral";

  dom.hbCompleted.textContent = formatSigned(breakdown.completed_fours ?? 0);
  dom.hbThreats.textContent = formatSigned(breakdown.window_threats ?? 0);
  dom.hbGravity.textContent = formatSigned(breakdown.immediate_threats ?? 0);
  dom.hbPositional.textContent = formatSigned(breakdown.positional_control ?? 0);
}

function showGameOverBanner(winner, humanScore, aiScore, winningLines) {
  const w = String(winner || "").toLowerCase();
  if (w === "human") {
    dom.winnerIcon.textContent = "🏆";
    dom.winnerTitle.textContent = "You Beat the AI!";
  } else if (w === "ai") {
    dom.winnerIcon.textContent = "🤖";
    dom.winnerTitle.textContent = "AI Agent Wins!";
  } else {
    dom.winnerIcon.textContent = "🤝";
    dom.winnerTitle.textContent = "It's a Draw!";
  }
  dom.winnerSubtitle.textContent = `Final Connected-Fours — You: ${humanScore} | AI: ${aiScore}`;

  // Add "Inspect Board" button once next to "Play Again"
  if (!document.getElementById("btn-inspect-board")) {
    const inspectBtn = document.createElement("button");
    inspectBtn.id = "btn-inspect-board";
    inspectBtn.textContent = "Inspect Board";
    inspectBtn.style.cssText =
      "margin-left: 10px; padding: 10px 18px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.1); color: #fff; cursor: pointer; font-weight: 600;";
    inspectBtn.addEventListener("click", () => {
      dom.gameoverOverlay.classList.add("hidden");
    });
    dom.btnPlayAgain.insertAdjacentElement("afterend", inspectBtn);
  }

  if (winningLines) {
    renderWinningLinesInspector(winningLines);
  }

  dom.gameoverOverlay.classList.remove("hidden");
}

function highlightCells(cells, color) {
  const allCells = dom.boardGrid.querySelectorAll(".cell");
  if (!cells) {
    allCells.forEach((el) => {
      el.style.outline = "";
      el.style.boxShadow = "";
      el.style.opacity = "";
      el.style.transform = "";
    });
    return;
  }

  const keySet = new Set(cells.map((c) => `${c.row},${c.col}`));
  allCells.forEach((el) => {
    const key = `${el.dataset.row},${el.dataset.col}`;
    if (keySet.has(key)) {
      el.style.outline = `3px solid ${color}`;
      el.style.boxShadow = `0 0 14px ${color}`;
      el.style.opacity = "1";
      el.style.transform = "scale(1.06)";
    } else {
      el.style.outline = "";
      el.style.boxShadow = "";
      el.style.opacity = "0.35";
      el.style.transform = "";
    }
  });
}

function renderWinningLinesInspector(winningLines) {
  const box = document.createElement("div");
  box.style.cssText =
    "padding: 12px; margin-bottom: 12px; border-radius: 10px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.12);";

  const title = document.createElement("div");
  title.textContent = "Final Connect-4 Breakdown (Hover any line to highlight on board)";
  title.style.cssText = "font-weight: 700; margin-bottom: 8px; font-size: 13px; color: #fff;";
  box.appendChild(title);

  const buildGroup = (label, list, color) => {
    const header = document.createElement("div");
    header.textContent = `${label} (${list.length})`;
    header.style.cssText = `font-weight: 600; font-size: 12px; margin: 6px 0 4px; color: ${color};`;
    box.appendChild(header);

    if (list.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "None";
      empty.style.cssText = "font-size: 12px; opacity: 0.6; margin-bottom: 4px;";
      box.appendChild(empty);
      return;
    }

    list.forEach((item, idx) => {
      const row = document.createElement("div");
      const coordsText = item.cells.map((c) => `(${c.row},${c.col})`).join(" → ");
      row.textContent = `#${idx + 1} [${item.direction}]: ${coordsText}`;
      row.style.cssText =
        "font-size: 12px; padding: 5px 8px; border-radius: 6px; cursor: pointer; margin-bottom: 3px; background: rgba(255,255,255,0.04);";
      row.addEventListener("mouseenter", () => {
        row.style.background = "rgba(255,255,255,0.14)";
        highlightCells(item.cells, color);
      });
      row.addEventListener("mouseleave", () => {
        row.style.background = "rgba(255,255,255,0.04)";
        highlightCells(null);
      });
      box.appendChild(row);
    });
  };

  buildGroup("YOU (Human)", winningLines.human || [], "#ff4d6d");
  buildGroup("AI AGENT", winningLines.ai || [], "#ffd166");

  dom.treeContainer.prepend(box);
}
/* =========================================================
   Lazy / Collapsible Minimax Tree Renderer (Zero-Lag at High K)
   ========================================================= */
function renderMinimaxTree(rootNode, autoExpandDepth = 2) {
  dom.treeContainer.innerHTML = "";
  if (!rootNode) {
    dom.treeContainer.innerHTML = `<div class="tree-empty">No search tree available.</div>`;
    return;
  }
  const rootEl = createTreeNodeElement(rootNode, 0, autoExpandDepth);
  dom.treeContainer.appendChild(rootEl);
}

function createTreeNodeElement(node, level, autoExpandDepth) {
  const wrapper = document.createElement("div");
  wrapper.className = level === 0 ? "tree-node is-root" : "tree-node";

  const hasChildren = Array.isArray(node.children) && node.children.length > 0 && !node.pruned;
  let isExpanded = hasChildren && level < autoExpandDepth;
  let childrenRendered = false;

  const row = document.createElement("div");
  row.className = node.pruned ? "tree-row pruned-row" : "tree-row";

  // Expand / collapse toggle icon
  const toggle = document.createElement("span");
  toggle.className = hasChildren ? "tree-toggle" : "tree-toggle empty";
  toggle.textContent = isExpanded ? "▾" : "▸";
  row.appendChild(toggle);

  // Node Type Badge
  const badge = document.createElement("span");
  const typeLower = (node.node_type || "leaf").toLowerCase();
  badge.className = `tree-badge ${typeLower}`;
  badge.textContent = node.node_type;
  row.appendChild(badge);

  // Column label
  const colSpan = document.createElement("span");
  colSpan.className = "tree-col";
  colSpan.textContent = node.col === null || node.col === undefined ? "ROOT" : `Col ${node.col}`;
  row.appendChild(colSpan);

  // Value / Heuristic Display
  if (!node.pruned) {
    const valSpan = document.createElement("span");
    valSpan.className = "tree-val";
    if (node.node_type === "LEAF") {
      valSpan.textContent = `→ h = ${formatTreeNum(node.heuristic_value)}`;
    } else if (node.node_type === "TERMINAL") {
      valSpan.textContent = `→ Board = ${formatTreeNum(node.value)}`;
    } else {
      valSpan.textContent = `→ Val = ${formatTreeNum(node.value)}`;
    }
    row.appendChild(valSpan);
  }

  // Alpha-Beta bounds
  if (state.useAlphaBeta && (node.alpha !== null || node.beta !== null)) {
    const boundsSpan = document.createElement("span");
    boundsSpan.className = "tree-bounds";
    boundsSpan.textContent = `[α=${formatTreeNum(node.alpha)}, β=${formatTreeNum(node.beta)}]`;
    row.appendChild(boundsSpan);
  }

  // Child count hint when collapsed
  if (hasChildren) {
    const countSpan = document.createElement("span");
    countSpan.className = "tree-bounds";
    countSpan.textContent = `(${node.children.length})`;
    row.appendChild(countSpan);
  }

  wrapper.appendChild(row);

  // Lazy Children Container
  if (hasChildren) {
    const childrenBox = document.createElement("div");
    childrenBox.className = isExpanded ? "tree-children" : "tree-children hidden";
    wrapper.appendChild(childrenBox);

    const mountChildren = () => {
      if (childrenRendered) return;
      const frag = document.createDocumentFragment();
      for (const child of node.children) {
        frag.appendChild(createTreeNodeElement(child, level + 1, autoExpandDepth));
      }
      childrenBox.appendChild(frag);
      childrenRendered = true;
    };

    if (isExpanded) {
      mountChildren();
    }

    row.addEventListener("click", () => {
      isExpanded = !isExpanded;
      toggle.textContent = isExpanded ? "▾" : "▸";
      if (isExpanded && !childrenRendered) {
        mountChildren();
      }
      childrenBox.classList.toggle("hidden", !isExpanded);
    });
  }

  return wrapper;
}

/* =========================================================
   Formatting Helpers
   ========================================================= */
function formatSigned(num) {
  if (num > 0) return `+${num}`;
  return String(num);
}

function formatTreeNum(val) {
  if (val === null || val === undefined) return "-";
  if (val === "inf" || val === Infinity) return "+∞";
  if (val === "-inf" || val === -Infinity) return "-∞";
  return String(val);
}

// Boot the Arena
init();