(function () {
  const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

  const boardEl = document.getElementById("board");
  const statusText = document.getElementById("status-text");
  const checkBadge = document.getElementById("check-badge");
  const coordsFiles = document.querySelector(".board-coords-files");
  const coordsRanks = document.querySelector(".board-coords-ranks");
  const moveList = document.getElementById("move-list");
  const capturedWhite = document.getElementById("captured-white");
  const capturedBlack = document.getElementById("captured-black");
  const playerColorText = document.getElementById("player-color-text");
  const depthSlider = document.getElementById("depth-slider");
  const depthValue = document.getElementById("depth-value");
  const promotionModal = document.getElementById("promotion-modal");
  const promotionPieces = document.getElementById("promotion-pieces");
  const timerBot = document.getElementById("timer-bot");
  const timerPlayer = document.getElementById("timer-player");
  const timeButtons = document.querySelectorAll(".time-btn");

  const playWhiteBtn = document.getElementById("play-white");
  const playBlackBtn = document.getElementById("play-black");
  const flipBtn = document.getElementById("flip");
  const undoBtn = document.getElementById("undo");
  const newGameBtn = document.getElementById("new-game");

  const socket = io();

  let state = {
    fen: START_FEN,
    moves: [],
    player_color: null,
    turn: "white",
    is_check: false,
    is_game_over: false,
    outcome: null,
    move_stack: [],
    depth: 2,
  };
  let orientation = "white";
  let selectedSquare = null;
  let lastMove = null;
  let draggedFromSquare = null;
  let draggedPiece = null;
  let pendingPromotion = null;
  
  let playerTime = 180;
  let botTime = 180;
  let selectedGameTime = 180;
  let timerInterval = null;

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
      if (from === fromSq) targets.set(to, uci);
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

  function formatTime(seconds) {
    if (seconds < 0) seconds = 0;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins + ":" + (secs < 10 ? "0" : "") + secs;
  }

  function updateTimers() {
    if (timerPlayer) {
      timerPlayer.textContent = formatTime(playerTime);
      timerPlayer.classList.remove("active", "low-time");
      if (isOurTurn() && state.player_color && !state.is_game_over) {
        timerPlayer.classList.add("active");
        if (playerTime <= 30) timerPlayer.classList.add("low-time");
      }
    }
    
    if (timerBot) {
      timerBot.textContent = formatTime(botTime);
      timerBot.classList.remove("active", "low-time");
      if (!isOurTurn() && state.player_color && !state.is_game_over) {
        timerBot.classList.add("active");
        if (botTime <= 30) timerBot.classList.add("low-time");
      }
    }
  }

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(function () {
      if (state.is_game_over) {
        clearInterval(timerInterval);
        return;
      }
      if (!state.player_color) return;
      
      if (isOurTurn()) {
        playerTime--;
        if (playerTime <= 0) {
          playerTime = 0;
          stopTimer();
          state.is_game_over = true;
          state.outcome = "timeout";
          statusText.textContent = "Time out! You lose";
        }
      } else {
        botTime--;
        if (botTime <= 0) {
          botTime = 0;
          stopTimer();
          state.is_game_over = true;
          state.outcome = "timeout";
          showConfetti();
          statusText.textContent = "Time out! You win!";
        }
      }
      updateTimers();
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function showConfetti() {
    const duration = 3000;
    const animationEnd = Date.now() + duration;
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff'];
    
    (function frame() {
      confetti({
        particleCount: 5,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: colors
      });
      confetti({
        particleCount: 5,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: colors
      });
      
      if (Date.now() < animationEnd) {
        requestAnimationFrame(frame);
      }
    }());
    
    setTimeout(function() {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: colors
      });
    }, 500);
  }

  function updateCapturedPieces() {
    capturedWhite.innerHTML = "";
    capturedBlack.innerHTML = "";
    
    const fenPart = state.fen.split(" ")[0];
    const pieces = parseFenBoard(fenPart);
    
    const currentCount = { white: {}, black: {} };
    for (const [sq, piece] of pieces) {
      const isWhite = piece === piece.toUpperCase();
      const color = isWhite ? "white" : "black";
      currentCount[color][piece] = (currentCount[color][piece] || 0) + 1;
    }
    
    for (const color of ["white", "black"]) {
      const container = color === "white" ? capturedBlack : capturedWhite;
      const pieceset = color === "white" ? { P: 8, N: 2, B: 2, R: 2, Q: 1 } : { p: 8, n: 2, b: 2, r: 2, q: 1 };
      
      for (const [piece, expected] of Object.entries(pieceset)) {
        const current = currentCount[color][piece] || 0;
        const captured = expected - current;
        for (let i = 0; i < captured; i++) {
          const img = document.createElement("img");
          img.src = pieceImage(piece);
          img.alt = piece;
          container.appendChild(img);
        }
      }
    }
  }

  function getMoveNotation(uci, fenBefore) {
    if (!uci) return "";
    
    const from = uci.slice(0, 2);
    const to = uci.slice(2, 4);
    const promo = uci.length > 4 ? uci[4] : "";
    
    const pieces = parseFenBoard(fenBefore.split(" ")[0]);
    const piece = pieces.get(from);
    if (!piece) return uci;
    
    const captured = pieces.get(to);
    const pieceChar = piece.toUpperCase();
    
    let notation = "";
    
    if (pieceChar === "K" && Math.abs(files.indexOf(from[0]) - files.indexOf(to[0])) === 2) {
      notation = to[0] === "g" ? "O-O" : "O-O-O";
    }
    else if (pieceChar === "P") {
      if (captured) {
        notation = from[0] + "x" + to;
      } else {
        notation = to;
      }
      if (promo) {
        notation += "=" + promo.toUpperCase();
      }
    }
    else {
      notation = pieceChar;
      if (captured) notation += "x";
      notation += to;
    }
    
    return notation;
  }

  function updateMoveList() {
    moveList.innerHTML = "";
    
    for (let i = 0; i < state.move_stack.length; i += 2) {
      const moveNum = Math.floor(i / 2) + 1;
      const whiteMove = state.move_stack[i];
      const blackMove = state.move_stack[i + 1];
      
      const row = document.createElement("div");
      row.className = "move-row";
      
      const numEl = document.createElement("span");
      numEl.className = "move-number";
      numEl.textContent = moveNum + ".";
      row.appendChild(numEl);
      
      if (whiteMove) {
        const whiteEl = document.createElement("span");
        whiteEl.className = "move-notation" + (whiteMove.isEngine ? " engine-move" : "");
        whiteEl.textContent = whiteMove.notation || "";
        row.appendChild(whiteEl);
      }
      
      if (blackMove) {
        const blackEl = document.createElement("span");
        blackEl.className = "move-notation" + (blackMove.isEngine ? " engine-move" : "");
        blackEl.textContent = blackMove.notation || "";
        row.appendChild(blackEl);
      }
      
      moveList.appendChild(row);
    }
    
    moveList.scrollTop = moveList.scrollHeight;
  }

  function updateStatusText() {
    if (state.is_game_over && state.outcome) {
      if (state.outcome === "checkmate") {
        const winner = state.turn === "white" ? "Black" : "White";
        const playerWon = (winner === "White" && state.player_color === "white") || 
                          (winner === "Black" && state.player_color === "black");
        if (playerWon) {
          statusText.textContent = "Checkmate! You win!";
          showConfetti();
        } else {
          statusText.textContent = "Checkmate! " + winner + " wins";
        }
      } else if (state.outcome === "stalemate") {
        statusText.textContent = "Draw by stalemate";
      } else if (state.outcome === "timeout") {
        // Already set
      } else {
        statusText.textContent = "Draw";
      }
      stopTimer();
      return;
    }
    if (!state.player_color) {
      statusText.textContent = "Choose a side to play";
      return;
    }
    if (state.is_check) {
      statusText.textContent = isOurTurn() ? "Your turn - You are in check!" : "Engine thinking...";
      return;
    }
    statusText.textContent = isOurTurn() ? "Your turn - make a move" : "Engine thinking...";
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

  function showPromotionModal(from, to, color) {
    pendingPromotion = { from, to };
    promotionPieces.innerHTML = "";
    
    const pieces = ["q", "r", "b", "n"];
    const prefix = color === "white" ? "w" : "b";
    
    for (const p of pieces) {
      const div = document.createElement("div");
      div.className = "promotion-piece";
      const img = document.createElement("img");
      img.src = "/assets/pieces/" + prefix + p + ".png";
      img.alt = p.toUpperCase();
      div.appendChild(img);
      div.addEventListener("click", function () {
        hidePromotionModal();
        const uci = from + to + p;
        socket.emit("move", { move: uci });
      });
      promotionPieces.appendChild(div);
    }
    
    promotionModal.style.display = "flex";
  }

  function hidePromotionModal() {
    promotionModal.style.display = "none";
    pendingPromotion = null;
  }

  function buildUci(from, to, piece) {
    const toRank = to[1];
    const isPawnPromotion = (piece === "P" && toRank === "8") || (piece === "p" && toRank === "1");
    
    if (isPawnPromotion) {
      showPromotionModal(from, to, state.player_color);
      return null;
    }
    
    return from + to;
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

        if (lastMove && (lastMove.from === sq || lastMove.to === sq)) {
          cell.classList.add("last-move");
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
          img.draggable = false;
          cell.appendChild(img);
        }

        const canDrag = piece && isOurTurn() && isOurPiece(piece);
        if (canDrag) {
          cell.draggable = true;
          cell.addEventListener("dragstart", function (e) {
            onDragStart(e, sq, cell, piece);
          });
        }
        cell.addEventListener("dragover", function (e) {
          onDragOver(e, sq, cell);
        });
        cell.addEventListener("dragleave", function () {
          cell.classList.remove("drag-over");
        });
        cell.addEventListener("drop", function (e) {
          onDrop(e, sq, cell);
        });
        cell.addEventListener("dragend", onDragEnd);

        cell.addEventListener("click", function () {
          onSquareClick(sq, pieces.get(sq));
        });
        boardEl.appendChild(cell);
      }
    }

    updateStatusText();
    updateCapturedPieces();
    updateTimers();
    checkBadge.hidden = !state.is_check;
  }

  function onDragStart(e, fromSq, cell, piece) {
    if (state.is_game_over || !isOurTurn() || !state.player_color) {
      e.preventDefault();
      return;
    }
    draggedFromSquare = fromSq;
    draggedPiece = piece;
    e.dataTransfer.setData("text/plain", fromSq);
    e.dataTransfer.effectAllowed = "move";
    
    const img = cell.querySelector(".piece");
    if (img) {
      e.dataTransfer.setDragImage(img, img.offsetWidth / 2, img.offsetHeight / 2);
    }
    
    setTimeout(function () {
      cell.classList.add("dragging");
      selectedSquare = fromSq;
      render();
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
    
    const fromSq = e.dataTransfer.getData("text/plain") || draggedFromSquare;
    draggedFromSquare = null;
    draggedPiece = null;
    
    if (!fromSq || fromSq === toSq) return;
    
    const targets = legalTargetsFrom(fromSq);
    if (!targets.has(toSq)) return;
    
    const piece = parseFenBoard(state.fen.split(" ")[0]).get(fromSq);
    const uci = buildUci(fromSq, toSq, piece);
    
    if (uci) {
      socket.emit("move", { move: uci });
    }
    
    selectedSquare = null;
    render();
  }

  function onDragEnd() {
    draggedFromSquare = null;
    draggedPiece = null;
    clearDragOver();
  }

  function clearDragOver() {
    document.querySelectorAll(".sq.drag-over").forEach(function (el) {
      el.classList.remove("drag-over");
    });
    document.querySelectorAll(".sq.dragging").forEach(function (el) {
      el.classList.remove("dragging");
    });
  }

  function onSquareClick(sq, piece) {
    if (!state.fen) return;
    if (state.is_game_over) return;

    if (!state.player_color) {
      statusText.textContent = "Choose White or Black first";
      return;
    }

    if (!isOurTurn()) return;

    if (!selectedSquare) {
      if (!piece || !isOurPiece(piece)) return;
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
      if (piece && isOurPiece(piece)) {
        const newTargets = legalTargetsFrom(sq);
        if (newTargets.size > 0) {
          selectedSquare = sq;
          render();
          return;
        }
      }
      selectedSquare = null;
      render();
      return;
    }

    const fromPiece = parseFenBoard(state.fen.split(" ")[0]).get(selectedSquare);
    const uci = buildUci(selectedSquare, sq, fromPiece);
    
    if (uci) {
      socket.emit("move", { move: uci });
    }
    
    selectedSquare = null;
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
        updateMoveList();
      })
      .catch(function () {
        render();
      });
  }

  function resetGame() {
    state.fen = START_FEN;
    state.moves = [];
    state.move_stack = [];
    state.is_check = false;
    state.is_game_over = false;
    state.outcome = null;
    lastMove = null;
    selectedSquare = null;
    playerTime = selectedGameTime;
    botTime = selectedGameTime;
    stopTimer();
    render();
    updateMoveList();
    updateTimers();
  }

  // Time button handlers
  timeButtons.forEach(function(btn) {
    btn.addEventListener("click", function() {
      timeButtons.forEach(function(b) { b.classList.remove("active"); });
      btn.classList.add("active");
      selectedGameTime = parseInt(btn.dataset.time, 10);
      playerTime = selectedGameTime;
      botTime = selectedGameTime;
      updateTimers();
    });
  });

  playWhiteBtn.addEventListener("click", function () {
    socket.emit("select_color", { color: "white" });
    state.player_color = "white";
    playWhiteBtn.classList.add("active");
    playBlackBtn.classList.remove("active");
    playerColorText.textContent = "White";
    resetGame();
    startTimer();
    refreshStatus();
  });

  playBlackBtn.addEventListener("click", function () {
    socket.emit("select_color", { color: "black" });
    state.player_color = "black";
    playBlackBtn.classList.add("active");
    playWhiteBtn.classList.remove("active");
    playerColorText.textContent = "Black";
    resetGame();
    startTimer();
    refreshStatus();
  });

  flipBtn.addEventListener("click", function () {
    orientation = orientation === "white" ? "black" : "white";
    renderCoords();
    render();
  });

  undoBtn.addEventListener("click", function () {
    if (state.move_stack.length >= 2) {
      state.move_stack.pop();
      state.move_stack.pop();
    }
    socket.emit("game_action", { action: "undo" });
  });

  newGameBtn.addEventListener("click", function () {
    state.player_color = null;
    playWhiteBtn.classList.remove("active");
    playBlackBtn.classList.remove("active");
    playerColorText.textContent = "Choose a side";
    resetGame();
    socket.emit("game_action", { action: "new_game" });
  });

  depthSlider.addEventListener("input", function () {
    state.depth = parseInt(depthSlider.value, 10);
    depthValue.textContent = state.depth;
    socket.emit("set_depth", { depth: state.depth });
  });

  socket.on("move_made", function (data) {
    if (data.fen) state.fen = data.fen;
    lastMove = data.move ? { from: data.move.slice(0, 2), to: data.move.slice(2, 4) } : null;
    refreshStatus();
  });

  socket.on("player_move", function (data) {
    if (!data.valid) {
      statusText.textContent = data.message || "Invalid move";
      selectedSquare = null;
      render();
      return;
    }
    
    const fenBefore = state.fen;
    
    // Show player's move immediately
    if (data.last_move) {
      const notation = getMoveNotation(data.last_move, fenBefore);
      state.move_stack.push({ uci: data.last_move, notation: notation, isEngine: false });
      lastMove = { from: data.last_move.slice(0, 2), to: data.last_move.slice(2, 4) };
    }
    
    if (data.fen) state.fen = data.fen;
    if (data.moves) state.moves = data.moves;
    if (data.check != null) state.is_check = data.check;
    
    // If game over, update status
    if (data.game_over) {
      state.is_game_over = true;
      if (data.outcome != null) state.outcome = data.outcome;
    }
    
    render();
    updateMoveList();
    
    // Show thinking status if game not over
    if (!data.game_over) {
      statusText.textContent = "Engine thinking...";
    }
  });

  socket.on("engine_move", function (data) {
    // Add engine move to stack
    if (data.engine_move) {
      const notation = getMoveNotation(data.engine_move, state.fen);
      state.move_stack.push({ uci: data.engine_move, notation: notation, isEngine: true });
      lastMove = { from: data.engine_move.slice(0, 2), to: data.engine_move.slice(2, 4) };
    }
    
    if (data.fen) state.fen = data.fen;
    if (data.moves) state.moves = data.moves;
    if (data.check != null) state.is_check = data.check;
    if (data.game_over != null) state.is_game_over = data.game_over;
    if (data.outcome != null) state.outcome = data.outcome;
    
    render();
    updateMoveList();
  });

  socket.on("board_update", function (data) {
    if (data.action === "undo" && data.fen) {
      state.fen = data.fen;
      lastMove = null;
      refreshStatus();
    } else if (data.action === "new_game" && data.fen) {
      state.fen = data.fen;
      resetGame();
      render();
    }
  });

  promotionModal.addEventListener("click", function (e) {
    if (e.target === promotionModal) {
      hidePromotionModal();
    }
  });

  renderCoords();
  render();
  updateTimers();
  refreshStatus();
})();
