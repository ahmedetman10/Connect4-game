/* =========================================================
   Connect 4 AI Arena — Frontend Controller & New-Tab Tree Viewer
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
  lastMove: null,
  animateCoord: null,
  lastTree: null,
  lastTelemetry: null,
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
  // Hide old inline tree buttons since the tree now opens in a dedicated tab
  if (dom.btnExpandLvl2) dom.btnExpandLvl2.style.display = "none";
  if (dom.btnCollapseAll) dom.btnCollapseAll.style.display = "none";

  bindEvents();
  setupTreeModalAndTopbarButton();
  syncDepthBadges();

  checkBackendHealth().then((online) => {
    if (online) {
      startNewGame();
    }
  });
}

function syncDepthBadges() {
  const k = Math.max(1, parseInt(dom.inputDepth.value, 10) || 1);
  if (dom.depthBadge) dom.depthBadge.textContent = `K = ${k}`;
  if (dom.depthWarning) dom.depthWarning.classList.toggle("hidden", k < 7);
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
    syncDepthBadges();
  });

  dom.inputDepth.addEventListener("change", () => {
    syncDepthBadges();
    // Auto-apply immediately if match hasn't started yet
    if (state.movesCount === 0 && !state.isThinking) {
      startNewGame();
    }
  });

  dom.toggleAlphaBeta.addEventListener("change", () => {
    // Auto-apply immediately if match hasn't started yet
    if (state.movesCount === 0 && !state.isThinking) {
      startNewGame();
    }
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
  dom.inputDepth.value = depth;
  dom.inputRows.value = rows;
  dom.inputCols.value = cols;
  syncDepthBadges();

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
  state.lastTelemetry = null;

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

    // Update UI badges
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

  const targetRow = getLowestEmptyRow(col);
  if (targetRow === -1) return;

  // 1. Optimistic Human Move
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

    // 2. Sync with backend state
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

    state.lastTree = data.minimax_tree || null;
    state.lastTelemetry = {
      col: data.ai_move,
      timeMs: ((data.execution_time || 0) * 1000).toFixed(2),
      nodes: data.nodes_expanded || 0,
      pruned: data.pruned_branches || 0,
      algo: state.useAlphaBeta ? `Alpha-Beta (K=${state.depth})` : `Plain Minimax (K=${state.depth})`,
      useAlphaBeta: state.useAlphaBeta,
    };

    renderTreeLauncherUI();

    if (state.gameOver) {
      setTurnUI("over");
      showGameOverBanner(data.winner, data.human_score, data.ai_score, data.winning_lines);
    } else {
      setTurnUI("human");
    }
  } catch (err) {
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
   Board Rendering
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

  const indicators = dom.colIndicators.querySelectorAll(".col-indicator");
  indicators.forEach((ind) => {
    const c = parseInt(ind.dataset.col, 10);
    const colFull = getLowestEmptyRow(c) === -1;
    ind.classList.toggle("disabled", colFull || state.isThinking || state.gameOver);
  });

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

  renderTreeLauncherUI();
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

/* =========================================================
   Game Over Banner & Winning Lines Inspector
   ========================================================= */
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
   Same-Screen Minimax Tree Modal + Top Bar Button
   ========================================================= */
let treeModalZoom = 1.0;

function setupTreeModalAndTopbarButton() {
  // 1. Add "Minimax Tree" button to the Top Bar next to Settings
  if (!document.getElementById("btn-open-tree-topbar") && dom.btnToggleSettings) {
    const topBtn = document.createElement("button");
    topBtn.id = "btn-open-tree-topbar";
    topBtn.className = dom.btnToggleSettings.className;
    topBtn.textContent = "🌳 Minimax Tree";
    topBtn.addEventListener("click", openTreeModal);
    dom.btnToggleSettings.insertAdjacentElement("beforebegin", topBtn);
  }

  // 2. Inject Visual Tree CSS + Modal styles once
  if (!document.getElementById("vtree-modal-styles")) {
    const style = document.createElement("style");
    style.id = "vtree-modal-styles";
    style.textContent = `
      .tm-backdrop {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(6, 10, 26, 0.82); backdrop-filter: blur(6px);
        display: flex; align-items: center; justify-content: center; padding: 20px;
      }
      .tm-backdrop.hidden { display: none; }
      .tm-dialog {
        width: 95vw; height: 90vh; border-radius: 16px;
        background: #0e142d; border: 1px solid rgba(255,255,255,0.14);
        display: flex; flex-direction: column; overflow: hidden;
        box-shadow: 0 24px 60px rgba(0,0,0,0.6);
      }
      .tm-header {
        display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
        gap: 10px; padding: 14px 18px; background: #151d40;
        border-bottom: 1px solid rgba(255,255,255,0.1);
      }
      .tm-title { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 4px; }
      .tm-stats { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #b8c4eb; }
      .tm-pill {
        padding: 3px 9px; border-radius: 999px;
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
      }
      .tm-controls { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
      .tm-btn {
        padding: 6px 11px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.18);
        background: #1f2a5c; color: #fff; font-weight: 600; font-size: 12px; cursor: pointer;
      }
      .tm-btn:hover { background: #2c3b7e; }
      .tm-btn.close-btn { background: rgba(239,68,68,0.22); border-color: rgba(239,68,68,0.45); color: #fca5a5; }
      .tm-btn.close-btn:hover { background: rgba(239,68,68,0.38); }
      .tm-canvas { flex: 1; overflow: auto; padding: 24px 16px 50px; }
      .tm-stage { display: inline-block; min-width: 100%; text-align: center; transform-origin: top center; transition: transform 0.15s ease; }

      .vtree ul { padding-top: 24px; padding-left: 0; margin: 0; position: relative; display: flex; justify-content: center; }
      .vtree > ul { padding-top: 0; }
      .vtree li { list-style: none; text-align: center; position: relative; padding: 24px 8px 0; display: flex; flex-direction: column; align-items: center; }
      .vtree > ul > li { padding-top: 0; }
      .vtree li::before, .vtree li::after { content: ""; position: absolute; top: 0; right: 50%; border-top: 2px solid rgba(148,163,184,0.35); width: 50%; height: 24px; }
      .vtree li::after { right: auto; left: 50%; border-left: 2px solid rgba(148,163,184,0.35); }
      .vtree li:only-child::before, .vtree li:only-child::after { display: none; }
      .vtree li:only-child { padding-top: 0; }
      .vtree li:first-child::before, .vtree li:last-child::after { border: 0 none; }
      .vtree li:last-child::before { border-right: 2px solid rgba(148,163,184,0.35); border-radius: 0 6px 0 0; }
      .vtree li:first-child::after { border-radius: 6px 0 0 0; }
      .vtree ul ul::before { content: ""; position: absolute; top: 0; left: 50%; border-left: 2px solid rgba(148,163,184,0.35); width: 0; height: 24px; }

      .node-card {
        display: inline-flex; flex-direction: column; align-items: center; gap: 3px;
        min-width: 108px; padding: 8px 11px; border-radius: 11px;
        background: #182147; border: 2px solid rgba(255,255,255,0.14);
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px;
        user-select: none; box-shadow: 0 6px 16px rgba(0,0,0,0.28);
      }
      .node-card.clickable { cursor: pointer; }
      .node-card.clickable:hover { border-color: rgba(255,255,255,0.5); transform: translateY(-2px); }
      .node-card.max { border-color: #3b82f6; background: linear-gradient(180deg, rgba(59,130,246,0.18), #172045); }
      .node-card.min { border-color: #a855f7; background: linear-gradient(180deg, rgba(168,85,247,0.18), #172045); }
      .node-card.leaf { border-color: #10b981; background: linear-gradient(180deg, rgba(16,185,129,0.18), #14263a); }
      .node-card.terminal { border-color: #f59e0b; background: linear-gradient(180deg, rgba(245,158,11,0.2), #252038); }
      .node-card.pruned { border-color: rgba(239,68,68,0.55); border-style: dashed; background: rgba(239,68,68,0.1); opacity: 0.72; }
      .n-type { font-size: 10px; font-weight: 800; text-transform: uppercase; }
      .node-card.max .n-type { color: #60a5fa; }
      .node-card.min .n-type { color: #c084fc; }
      .node-card.leaf .n-type { color: #34d399; }
      .node-card.terminal .n-type { color: #fbbf24; }
      .node-card.pruned .n-type { color: #f87171; }
      .n-col { font-size: 13px; font-weight: 700; color: #fff; }
      .n-val { font-size: 12px; color: #dbeafe; font-weight: 600; }
      .n-bounds { font-size: 10px; color: #94a3b8; }
      .n-toggle { margin-top: 2px; font-size: 10px; padding: 1px 7px; border-radius: 999px; background: rgba(255,255,255,0.1); color: #cbd5e1; }
    `;
    document.head.appendChild(style);
  }

  // 3. Create Modal DOM once
  if (!document.getElementById("tree-modal-backdrop")) {
    const backdrop = document.createElement("div");
    backdrop.id = "tree-modal-backdrop";
    backdrop.className = "tm-backdrop hidden";
    backdrop.innerHTML = `
      <div class="tm-dialog">
        <div class="tm-header">
          <div>
            <div class="tm-title">🌳 Minimax Visual Search Tree (Latest Move)</div>
            <div class="tm-stats" id="tm-stats"></div>
          </div>
          <div class="tm-controls">
            <button class="tm-btn" id="tm-lvl1">Depth 1</button>
            <button class="tm-btn" id="tm-lvl2">Depth 2</button>
            <button class="tm-btn" id="tm-all">Expand All</button>
            <button class="tm-btn" id="tm-zout">−</button>
            <button class="tm-btn" id="tm-zreset">100%</button>
            <button class="tm-btn" id="tm-zin">+</button>
            <button class="tm-btn close-btn" id="tm-close">✕ Close</button>
          </div>
        </div>
        <div class="tm-canvas">
          <div class="tm-stage" id="tm-stage">
            <div class="vtree" id="tm-root"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(backdrop);

    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) closeTreeModal();
    });
    document.getElementById("tm-close").onclick = closeTreeModal;
    document.getElementById("tm-lvl1").onclick = () => renderVisualTreeInModal(1);
    document.getElementById("tm-lvl2").onclick = () => renderVisualTreeInModal(2);
    document.getElementById("tm-all").onclick = () => renderVisualTreeInModal(99);
    document.getElementById("tm-zin").onclick = () => { treeModalZoom = Math.min(1.6, treeModalZoom + 0.15); applyModalZoom(); };
    document.getElementById("tm-zout").onclick = () => { treeModalZoom = Math.max(0.35, treeModalZoom - 0.15); applyModalZoom(); };
    document.getElementById("tm-zreset").onclick = () => { treeModalZoom = 1.0; applyModalZoom(); };

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeTreeModal();
    });
  }
}

function applyModalZoom() {
  const stage = document.getElementById("tm-stage");
  const btn = document.getElementById("tm-zreset");
  if (stage) stage.style.transform = `scale(${treeModalZoom})`;
  if (btn) btn.textContent = `${Math.round(treeModalZoom * 100)}%`;
}

function openTreeModal() {
  if (!state.lastTree) {
    alert("Make a move first so the AI generates a search tree.");
    return;
  }
  treeModalZoom = 1.0;
  applyModalZoom();
  renderVisualTreeInModal(2);
  document.getElementById("tree-modal-backdrop").classList.remove("hidden");
}

function closeTreeModal() {
  const el = document.getElementById("tree-modal-backdrop");
  if (el) el.classList.add("hidden");
}

function formatTreeVal(v) {
  if (v === null || v === undefined) return "-";
  if (v === "inf" || v === Infinity) return "+∞";
  if (v === "-inf" || v === -Infinity) return "-∞";
  return String(v);
}

function buildVisualTreeLi(node, level, expandDepth, useAlphaBeta) {
  const li = document.createElement("li");
  const typeLower = String(node.node_type || "leaf").toLowerCase();
  const hasKids = Array.isArray(node.children) && node.children.length > 0 && !node.pruned;
  let expanded = hasKids && level < expandDepth;
  let mounted = false;

  const card = document.createElement("div");
  card.className = `node-card ${typeLower}${hasKids ? " clickable" : ""}`;

  const t = document.createElement("div");
  t.className = "n-type";
  t.textContent = node.node_type;
  card.appendChild(t);

  const c = document.createElement("div");
  c.className = "n-col";
  c.textContent = node.col === null || node.col === undefined ? "ROOT" : `Col ${node.col}`;
  card.appendChild(c);

  if (!node.pruned) {
    const v = document.createElement("div");
    v.className = "n-val";
    if (node.node_type === "LEAF") v.textContent = `h = ${formatTreeVal(node.heuristic_value)}`;
    else if (node.node_type === "TERMINAL") v.textContent = `Board = ${formatTreeVal(node.value)}`;
    else v.textContent = `Val = ${formatTreeVal(node.value)}`;
    card.appendChild(v);
  }

  if (useAlphaBeta && (node.alpha !== null || node.beta !== null)) {
    const b = document.createElement("div");
    b.className = "n-bounds";
    b.textContent = `α:${formatTreeVal(node.alpha)} | β:${formatTreeVal(node.beta)}`;
    card.appendChild(b);
  }

  let tog = null;
  if (hasKids) {
    tog = document.createElement("div");
    tog.className = "n-toggle";
    tog.textContent = expanded ? "− hide" : `+ ${node.children.length} branches`;
    card.appendChild(tog);
  }

  li.appendChild(card);

  if (hasKids) {
    const ul = document.createElement("ul");
    if (!expanded) ul.classList.add("hidden");
    li.appendChild(ul);

    const mountKids = () => {
      if (mounted) return;
      const frag = document.createDocumentFragment();
      for (const ch of node.children) {
        frag.appendChild(buildVisualTreeLi(ch, level + 1, expandDepth, useAlphaBeta));
      }
      ul.appendChild(frag);
      mounted = true;
    };

    if (expanded) mountKids();

    card.addEventListener("click", () => {
      expanded = !expanded;
      if (expanded && !mounted) mountKids();
      ul.classList.toggle("hidden", !expanded);
      tog.textContent = expanded ? "− hide" : `+ ${node.children.length} branches`;
    });
  }

  return li;
}

function renderVisualTreeInModal(depth) {
  const rootEl = document.getElementById("tm-root");
  const statsEl = document.getElementById("tm-stats");
  const meta = state.lastTelemetry || {};

  statsEl.innerHTML = [
    meta.algo ? `<span class="tm-pill">${meta.algo}</span>` : "",
    meta.col !== undefined && meta.col !== null ? `<span class="tm-pill">Selected: Col ${meta.col}</span>` : "",
    `<span class="tm-pill">Time: ${meta.timeMs || "0.00"} ms</span>`,
    `<span class="tm-pill">Nodes: ${Number(meta.nodes || 0).toLocaleString()}</span>`,
    `<span class="tm-pill">Pruned: ${Number(meta.pruned || 0).toLocaleString()}</span>`,
  ].join("");

  rootEl.innerHTML = "";
  const topUl = document.createElement("ul");
  topUl.appendChild(buildVisualTreeLi(state.lastTree, 0, depth, Boolean(meta.useAlphaBeta)));
  rootEl.appendChild(topUl);
}

function renderTreeLauncherUI() {
  dom.treeContainer.innerHTML = "";
  if (!state.includeTree) {
    dom.treeContainer.innerHTML = `<div class="tree-empty">GUI Tree is disabled in Settings.</div>`;
    return;
  }
  if (!state.lastTree) {
    dom.treeContainer.innerHTML = `<div class="tree-empty">Make a move, then click "🌳 Minimax Tree" in the top bar to inspect it.</div>`;
    return;
  }
  dom.treeContainer.innerHTML = `<div class="tree-empty">Latest tree ready (Col ${state.lastTelemetry?.col ?? "—"}). Click <strong>🌳 Minimax Tree</strong> in the top bar to view.</div>`;
}

/* =========================================================
   Formatting Helpers
   ========================================================= */
function formatSigned(num) {
  if (num > 0) return `+${num}`;
  return String(num);
}

// Boot the Arena
init();