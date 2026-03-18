const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { getRandomWord, getWords, obfuscateWord } = require('./words');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

app.use(express.static(path.join(__dirname, 'public')));

const rooms = new Map();
const ROUND_TIME = 80;
const MAX_PLAYERS = 12;

function generateRoomCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 4; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

function createRoom(code, hostId) {
  const room = {
    code,
    hostId,
    players: new Map(),
    state: 'lobby',
    currentRound: 0,
    totalRounds: 3,
    currentWord: null,
    currentDrawer: null,
    drawerIndex: 0,
    roundTimer: null,
    timeLeft: ROUND_TIME,
    canvasHistory: [],
    guessedPlayers: new Set(),
    wordHints: [],
    usedWords: new Set(),
  };
  rooms.set(code, room);
  return room;
}

function getPlayerList(room) {
  const players = [];
  room.players.forEach((player, socketId) => {
    players.push({
      id: socketId,
      nickname: player.nickname,
      score: player.score,
      isHost: socketId === room.hostId,
    });
  });
  return players;
}

function startRound(room) {
  if (room.drawerIndex >= room.players.size) {
    room.drawerIndex = 0;
    room.currentRound++;
  }

  if (room.currentRound > room.totalRounds) {
    endGame(room);
    return;
  }

  const playerIds = Array.from(room.players.keys());
  if (playerIds.length === 0) return;

  const drawerId = playerIds[room.drawerIndex % playerIds.length];
  room.currentDrawer = drawerId;
  room.guessedPlayers = new Set();
  room.wordHints = [];
  room.canvasHistory = [];
  room.timeLeft = ROUND_TIME;

  let word = getRandomWord();
  let attempts = 0;
  while (room.usedWords.has(word) && attempts < 20) {
    word = getRandomWord();
    attempts++;
  }
  room.currentWord = word;
  room.usedWords.add(word);

  const drawerSocket = io.sockets.sockets.get(drawerId);
  if (drawerSocket) {
    drawerSocket.emit('your-word', { word });
  }

  const wordDisplay = obfuscateWord(word);
  io.to(room.code).emit('round-start', {
    drawerId,
    drawerName: room.players.get(drawerId).nickname,
    round: room.currentRound,
    totalRounds: room.totalRounds,
    wordDisplay,
    timeLeft: ROUND_TIME,
    playerCount: room.players.size,
  });

  room.canvasHistory = [];
  io.to(room.code).emit('clear-canvas');

  if (room.roundTimer) clearInterval(room.roundTimer);
  room.roundTimer = setInterval(() => {
    room.timeLeft--;
    io.to(room.code).emit('timer', { timeLeft: room.timeLeft });

    if (room.timeLeft <= 0) {
      clearInterval(room.roundTimer);
      room.roundTimer = null;
      revealWord(room);
    }
  }, 1000);
}

function revealWord(room) {
  if (!room.currentWord) return;
  io.to(room.code).emit('round-end', {
    word: room.currentWord,
    players: getPlayerList(room),
  });
  room.drawerIndex++;
  setTimeout(() => {
    if (room.state === 'playing') {
      startRound(room);
    }
  }, 4000);
}

function endGame(room) {
  room.state = 'lobby';
  room.currentRound = 0;
  room.drawerIndex = 0;
  if (room.roundTimer) {
    clearInterval(room.roundTimer);
    room.roundTimer = null;
  }

  const leaderboard = getPlayerList(room).sort((a, b) => b.score - a.score);
  io.to(room.code).emit('game-end', { leaderboard });

  room.players.forEach(player => {
    player.score = 0;
  });
}

function resetRoom(room) {
  room.state = 'lobby';
  room.currentRound = 0;
  room.drawerIndex = 0;
  room.currentWord = null;
  room.currentDrawer = null;
  room.guessedPlayers = new Set();
  room.wordHints = [];
  room.canvasHistory = [];
  room.usedWords = new Set();
  room.players.forEach(player => {
    player.score = 0;
  });
  if (room.roundTimer) {
    clearInterval(room.roundTimer);
    room.roundTimer = null;
  }
  io.to(room.code).emit('back-to-lobby', { players: getPlayerList(room) });
}

io.on('connection', (socket) => {
  let currentRoom = null;

  socket.on('create-room', ({ nickname }) => {
    let code = generateRoomCode();
    while (rooms.has(code)) {
      code = generateRoomCode();
    }

    const room = createRoom(code, socket.id);
    room.players.set(socket.id, { nickname, score: 0 });
    socket.join(code);
    currentRoom = code;

    socket.emit('room-created', { code });
    io.to(code).emit('player-list', { players: getPlayerList(room) });
  });

  socket.on('join-room', ({ code, nickname }) => {
    code = code.toUpperCase().trim();
    const room = rooms.get(code);

    if (!room) {
      socket.emit('error', { message: 'Room not found' });
      return;
    }

    if (room.state !== 'lobby') {
      socket.emit('error', { message: 'Game already in progress' });
      return;
    }

    if (room.players.size >= MAX_PLAYERS) {
      socket.emit('error', { message: 'Room is full' });
      return;
    }

    room.players.set(socket.id, { nickname, score: 0 });
    socket.join(code);
    currentRoom = code;

    socket.emit('room-joined', { code });
    io.to(code).emit('player-list', { players: getPlayerList(room) });

    if (room.players.size === 1) {
      room.hostId = socket.id;
      io.to(code).emit('player-list', { players: getPlayerList(room) });
    }
  });

  socket.on('start-game', () => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.hostId !== socket.id) return;
    if (room.players.size < 2) {
      socket.emit('error', { message: 'Need at least 2 players' });
      return;
    }

    room.state = 'playing';
    room.currentRound = 1;
    room.drawerIndex = 0;
    room.usedWords = new Set();
    io.to(currentRoom).emit('game-start', { totalRounds: room.totalRounds });
    setTimeout(() => startRound(room), 1500);
  });

  socket.on('draw-event', (data) => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.currentDrawer !== socket.id) return;

    socket.to(currentRoom).emit('draw-event', data);
  });

  socket.on('draw-sync', (data) => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.currentDrawer !== socket.id) return;
    socket.to(currentRoom).emit('draw-sync', data);
  });

  socket.on('guess', ({ text }) => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.state !== 'playing') return;
    if (room.currentDrawer === socket.id) return;
    if (room.guessedPlayers.has(socket.id)) return;

    const player = room.players.get(socket.id);
    if (!player) return;

    const guess = text.trim().toLowerCase();
    const word = room.currentWord.toLowerCase();

    if (guess === word) {
      room.guessedPlayers.add(socket.id);
      const guessOrder = room.guessedPlayers.size;
      const basePoints = Math.max(100 - (guessOrder - 1) * 25, 20);
      const timeBonus = Math.floor(room.timeLeft / 10) * 5;
      player.score += basePoints + timeBonus;

      io.to(currentRoom).emit('correct-guess', {
        playerId: socket.id,
        nickname: player.nickname,
        points: basePoints + timeBonus,
        players: getPlayerList(room),
      });

      if (room.guessedPlayers.size === room.players.size - 1) {
        clearInterval(room.roundTimer);
        room.roundTimer = null;
        revealWord(room);
      }
    } else {
      const closeMatch = checkCloseGuess(guess, word);
      if (closeMatch) {
        socket.emit('close-guess', { message: 'Almost!' });
      } else {
        socket.to(currentRoom).emit('chat-message', {
          id: socket.id,
          nickname: player.nickname,
          text: guess,
          isGuess: true,
        });
      }
    }
  });

  socket.on('chat-message', ({ text }) => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room) return;

    const player = room.players.get(socket.id);
    if (!player) return;

    io.to(currentRoom).emit('chat-message', {
      id: socket.id,
      nickname: player.nickname,
      text: text.substring(0, 200),
    });
  });

  socket.on('skip-word', () => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.hostId !== socket.id) return;

    if (room.roundTimer) {
      clearInterval(room.roundTimer);
      room.roundTimer = null;
    }
    revealWord(room);
  });

  socket.on('hint', () => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.currentDrawer !== socket.id) return;

    const word = room.currentWord;
    const revealed = room.wordHints;

    for (let i = 0; i < word.length; i++) {
      if (!revealed.includes(i) && word[i] !== ' ') {
        revealed.push(i);
        break;
      }
    }

    io.to(currentRoom).emit('hint-update', {
      wordDisplay: obfuscateWord(word, revealed),
    });
  });

  socket.on('back-to-lobby', () => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room || room.hostId !== socket.id) return;
    resetRoom(room);
  });

  socket.on('disconnect', () => {
    if (!currentRoom) return;
    const room = rooms.get(currentRoom);
    if (!room) return;

    room.players.delete(socket.id);
    io.to(currentRoom).emit('player-list', { players: getPlayerList(room) });

    if (room.players.size === 0) {
      if (room.roundTimer) clearInterval(room.roundTimer);
      rooms.delete(currentRoom);
    } else {
      if (room.currentDrawer === socket.id) {
        if (room.roundTimer) {
          clearInterval(room.roundTimer);
          room.roundTimer = null;
        }
        io.to(currentRoom).emit('drawer-left');
        room.drawerIndex++;
        if (room.state === 'playing') {
          setTimeout(() => {
            if (room.state === 'playing') startRound(room);
          }, 2000);
        }
      }

      if (room.hostId === socket.id) {
        const newHost = Array.from(room.players.keys())[0];
        room.hostId = newHost;
        io.to(currentRoom).emit('player-list', { players: getPlayerList(room) });
        io.to(currentRoom).emit('new-host', { hostId: newHost });
      }
    }
  });
});

function checkCloseGuess(guess, word) {
  if (guess.length < 3) return false;
  let matches = 0;
  for (let i = 0; i < Math.min(guess.length, word.length); i++) {
    if (guess[i] === word[i]) matches++;
  }
  const ratio = matches / word.length;
  return ratio >= 0.75 && ratio < 1.0;
}

const PORT = process.env.PORT || 5002;
server.listen(PORT, '127.0.0.1', () => {
  console.log(`Skribbl server running on port ${PORT}`);
});
