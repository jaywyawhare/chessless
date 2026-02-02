(function () {
  const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

  const boardEl = document.getElementById("board");
  const statusText = document.getElementById("status-text");
  const checkBadge = document.getElementById("check-badge");
  const overBadge = document.getElementById("over-badge");
  const coordsFiles = document.querySelector(".board-coords-files");
  const coordsRanks = document.querySelector(".board-coords-ranks");

  const playWhiteBtn = document.getElementById("play-white");
  const playBlackBtn = document.getElementById("play-black");
  const flipBtn = document.getElementById("flip");
  const undoBtn = document.getElementById("undo");

  const socket = io();

  let state = {
    fen: START_FEN,
    moves: [],
    player_color: null,
    turn: "white",
    is_check: false,
    is_game_over: false,
    outcome: null,
  };
  let orientation = "white";
  let selectedSquare = null;
  let lastMove = null;
  let draggedFromSquare = null;

  const files = "abcdefgh";
  const ranks = "12345678";

  function pieceImage(pieceChar) {
    const lower = pieceChar.toLowerCase();
    const color = pieceChar === pieceChar.toUpperCase() ? "w" : "b";
    return "/assets/pieces/" + color + lower + ".png";
  }

  function squareName(fileIdx, rankIdxFromTop) {
    return files[fileIdx] + ranks[7 - rankIdxFromTop];
  }

  function parseFenBoard(fenPart) {
    const rows = fenPart.split("/");
    const squares = new Map();
    for (let r = 0; r < 8; r++) {
      let f = 0;
      for (const ch of rows[r]) {
        if (/\d/.test(ch)) {
          f += Number(ch);
        } else {
          squares.set(squareName(f, r), ch);
          f += 1;
        }
      }
    }
    return squares;
  }

  function legalTargetsFrom(fromSq) {
    const targets = new Map();
    for (const uci of state.moves || []) {
      const from = uci.slice(0, 2);
      const to = uci.slice(2, 4);
      if (from === fromSq) targets.set(to, uci.length > 4);
    }
    return targets;
  }

  function hasPiece(squares, sq) {
    return squares.has(sq);
  }

  function isOurPiece(piece) {
    if (!state.player_color || !piece) return false;
    return state.player_color === "white" ? piece === piece.toUpperCase() : piece === piece.toLowerCase();
  }

  function isOurTurn() {
    if (!state.player_color) return false;
    return state.turn === state.player_color;
  }

  var OUTCOME_LABELS = {
    checkmate: "Checkmate",
    stalemate: "Stalemate",
    draw: "Draw",
    draw_insufficient_material: "Draw (insufficient material)",
    draw_50_moves: "Draw (50-move rule)",
    draw_repetition: "Draw (repetition)",
  };

  function updateStatusText() {
    if (state.is_game_over && state.outcome) {
      statusText.textContent = OUTCOME_LABELS[state.outcome] || "Game over";
      return;
    }
    if (!state.player_color) {
      statusText.textContent = "Choose a side to play";
      return;
    }
    if (state.is_check) {
      statusText.textContent = isOurTurn() ? "Your turn (check)" : "Engine thinking…";
      return;
    }
    statusText.textContent = isOurTurn() ? "Your turn" : "Engine thinking…";
  }

  function renderCoords() {
    const fileOrder = orientation === "white" ? files : files.split("").reverse().join("");
    const rankOrder = orientation === "white" ? "87654321" : "12345678";
    coordsFiles.innerHTML = "";
    coordsRanks.innerHTML = "";
    for (let i = 0; i < 8; i++) {
      const f = document.createElement("span");
      f.textContent = fileOrder[i];
      coordsFiles.appendChild(f);
      const r = document.createElement("span");
      r.textContent = rankOrder[i];
      coordsRanks.appendChild(r);
    }
  }

  function buildUci(from, to) {
    const piece = parseFenBoard((state.fen || START_FEN).split(" ")[0]).get(from);
    const toRank = to[1];
    const isPawnPromotion =
      (piece === "P" && toRank === "8") || (piece === "p" && toRank === "1");
    return from + to + (isPawnPromotion ? "q" : "");
  }

  function render() {
    const fenPart = state.fen ? state.fen.split(" ")[0] : START_FEN.split(" ")[0];
    const pieces = parseFenBoard(fenPart);
    const targets = selectedSquare ? legalTargetsFrom(selectedSquare) : new Map();

    const fileOrder = orientation === "white" ? files : files.split("").reverse().join("");
    const rankOrderTop = orientation === "white" ? "87654321" : "12345678";

    boardEl.innerHTML = "";

    for (let ri = 0; ri < 8; ri++) {
      for (let fi = 0; fi < 8; fi++) {
        const file = fileOrder[fi];
        const rank = rankOrderTop[ri];
        const sq = file + rank;

        const fileIdx = files.indexOf(file);
        const rankNum = parseInt(rank, 10);
        const isLight = (fileIdx + rankNum) % 2 === 0;

        const cell = document.createElement("div");
        cell.className = "sq " + (isLight ? "light" : "dark");
        cell.dataset.square = sq;
        cell.setAttribute("aria-label", sq);

        if (lastMove && (lastMove.from === sq || lastMove.to === sq)) {
          cell.classList.add(lastMove.from === sq ? "last-from" : "last-to");
        }
        if (sq === selectedSquare) cell.classList.add("selected");
        if (targets.has(sq)) {
          cell.classList.add("hint");
          if (hasPiece(pieces, sq)) cell.classList.add("capture");
        }

        const piece = pieces.get(sq);
        if (piece) {
          const img = document.createElement("img");
          img.className = "piece";
          img.alt = piece;
          img.src = pieceImage(piece);
          img.loading = "lazy";
          img.draggable = false;
          cell.appendChild(img);
        }

        const canDrag = piece && isOurTurn() && isOurPiece(piece);
        if (canDrag) {
          cell.draggable = true;
          cell.setAttribute("draggable", "true");
          cell.addEventListener("dragstart", function (e) {
            onDragStart(e, sq, cell);
          });
        }
        cell.addEventListener("dragover", function (e) {
          onDragOver(e, sq, cell);
        });
        cell.addEventListener("dragleave", function (e) {
          cell.classList.remove("drag-over");
        });
        cell.addEventListener("drop", function (e) {
          onDrop(e, sq, cell);
        });
        cell.addEventListener("dragend", function () {
          draggedFromSquare = null;
          clearDragOver();
        });

        cell.addEventListener("click", function () {
          onSquareClick(sq);
        });
        boardEl.appendChild(cell);
      }
    }

    updateStatusText();
    checkBadge.hidden = !state.is_check;
    overBadge.hidden = !state.is_game_over;
  }

  function onDragStart(e, fromSq, cell) {
    if (state.is_game_over || !isOurTurn() || !state.player_color) {
      e.preventDefault();
      return;
    }
    draggedFromSquare = fromSq;
    e.dataTransfer.setData("text/plain", fromSq);
    e.dataTransfer.effectAllowed = "move";
    const img = cell.querySelector(".piece");
    if (img) {
      e.dataTransfer.setDragImage(img, img.offsetWidth / 2, img.offsetHeight / 2);
    }
    setTimeout(function () {
      cell.classList.add("dragging");
    }, 0);
  }

  function onDragOver(e, toSq, cell) {
    if (!draggedFromSquare) return;
    const targets = legalTargetsFrom(draggedFromSquare);
    if (targets.has(toSq)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      cell.classList.add("drag-over");
    }
  }

  function onDrop(e, toSq, cell) {
    e.preventDefault();
    cell.classList.remove("drag-over");
    clearDragOver();
    if (state.is_game_over) return;
    const fromSq = e.dataTransfer.getData("text/plain");
    draggedFromSquare = null;
    if (!fromSq || fromSq === toSq) return;
    const targets = legalTargetsFrom(fromSq);
    if (!targets.has(toSq)) return;
    const uci = buildUci(fromSq, toSq);
    socket.emit("move", { move: uci });
    render();
  }

  function clearDragOver() {
    draggedFromSquare = null;
    document.querySelectorAll(".sq.drag-over").forEach(function (el) {
      el.classList.remove("drag-over");
    });
    document.querySelectorAll(".sq.dragging").forEach(function (el) {
      el.classList.remove("dragging");
    });
  }

  function onSquareClick(sq) {
    if (!state.fen) return;
    if (state.is_game_over) return;

    if (!state.player_color) {
      statusText.textContent = "Choose White or Black first";
      return;
    }

    if (!isOurTurn()) return;

    if (!selectedSquare) {
      const targets = legalTargetsFrom(sq);
      if (targets.size === 0) return;
      selectedSquare = sq;
      render();
      return;
    }

    if (sq === selectedSquare) {
      selectedSquare = null;
      render();
      return;
    }

    const targets = legalTargetsFrom(selectedSquare);
    if (!targets.has(sq)) {
      selectedSquare = null;
      render();
      return;
    }

    const uci = buildUci(selectedSquare, sq);
    selectedSquare = null;
    socket.emit("move", { move: uci });
    render();
  }

  function refreshStatus() {
    return fetch("/api/game/status")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        state.fen = data.fen;
        state.moves = data.moves || [];
        state.turn = data.turn || "white";
        state.player_color = data.player_color || null;
        state.is_check = data.is_check || false;
        state.is_game_over = data.is_game_over || false;
        state.outcome = data.outcome || null;
        render();
      })
      .catch(function () {
        render();
      });
  }

  playWhiteBtn.addEventListener("click", function () {
    socket.emit("select_color", { color: "white" });
    state.player_color = "white";
    playWhiteBtn.classList.add("active");
    playBlackBtn.classList.remove("active");
    refreshStatus();
  });

  playBlackBtn.addEventListener("click", function () {
    socket.emit("select_color", { color: "black" });
    state.player_color = "black";
    playBlackBtn.classList.add("active");
    playWhiteBtn.classList.remove("active");
    refreshStatus();
  });

  flipBtn.addEventListener("click", function () {
    orientation = orientation === "white" ? "black" : "white";
    socket.emit("game_action", { action: "flip" });
    renderCoords();
    render();
  });

  undoBtn.addEventListener("click", function () {
    socket.emit("game_action", { action: "undo" });
  });

  socket.on("move_made", function (data) {
    if (data.fen) state.fen = data.fen;
    lastMove = data.move ? { from: data.move.slice(0, 2), to: data.move.slice(2, 4) } : null;
    refreshStatus();
  });

  socket.on("move_response", function (data) {
    if (!data.valid) {
      statusText.textContent = data.message || "Invalid move";
      selectedSquare = null;
      render();
      return;
    }
    if (data.fen) state.fen = data.fen;
    if (data.outcome != null) state.outcome = data.outcome;
    if (data.game_over != null) state.is_game_over = data.game_over;
    lastMove = data.last_move
      ? { from: data.last_move.slice(0, 2), to: data.last_move.slice(2, 4) }
      : null;
    if (data.engine_move) {
      lastMove = { from: data.engine_move.slice(0, 2), to: data.engine_move.slice(2, 4) };
    }
    refreshStatus();
  });

  socket.on("board_update", function (data) {
    if (data.action === "undo" && data.fen) {
      state.fen = data.fen;
      lastMove = null;
      refreshStatus();
    }
  });

  renderCoords();
  render();
  refreshStatus();
})();
