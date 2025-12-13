# Skribbl Mode Game Models Design

This document describes the data models for Phase 9.1 Skribbl Mode game system.

## Overview

The game models are located in `/Users/coffee/git/public/JacobCoffee/scribbl-py/src/scribbl_py/game/models.py` and follow the existing codebase patterns using dataclasses with full type annotations.

## Model Architecture

### 1. Enums

#### GameState
Represents the state machine for game flow:
- `LOBBY` - Waiting for players to join
- `WORD_SELECTION` - Drawer choosing a word
- `DRAWING` - Active round with players guessing
- `ROUND_END` - Round complete, showing results
- `GAME_OVER` - All rounds finished

#### GameMode
- `SKRIBBL` - Drawing guessing game
- `COLLABORATIVE` - Free-form whiteboard (future)

#### PlayerState
- `CONNECTED` - Active player
- `DISCONNECTED` - Temporarily disconnected
- `LEFT` - Permanently left

#### WordCategory
- `ANIMALS`, `OBJECTS`, `ACTIONS`, `FOOD`, `PLACES`, `PEOPLE`, `NATURE`, `TECHNOLOGY`, `SPORTS`, `ENTERTAINMENT`, `CUSTOM`

#### ChatMessageType
- `GUESS` - Player guess attempt
- `SYSTEM` - System notifications
- `HINT` - Close guess hints
- `CORRECT` - Correct guess notification
- `DRAWER` - Drawer messages (shown after round)

#### GuessResult
- `CORRECT` - Exact match
- `CLOSE` - Close to the word (Levenshtein distance)
- `WRONG` - Not close
- `ALREADY_GUESSED` - Player already guessed
- `DRAWER` - Drawer cannot guess
- `INVALID` - Invalid guess

### 2. Core Models

#### Player
Represents a player in the game room.

**Attributes:**
- `id: UUID` - Unique identifier
- `user_id: str` - User ID from auth system
- `user_name: str` - Display name
- `avatar_url: str | None` - Avatar image URL
- `score: int` - Total score across all rounds
- `is_host: bool` - Room host flag
- `connection_state: PlayerState` - Connection status
- `has_guessed: bool` - Guessed correctly this round
- `guess_time: float | None` - Time taken to guess
- `joined_at: datetime` - Join timestamp
- `last_seen: datetime` - Last activity timestamp

**Methods:**
- `reset_round_state()` - Reset per-round state
- `award_points(points: int)` - Add points to score
- `mark_active()` - Update last_seen timestamp

#### WordBank
Collection of words organized by category.

**Attributes:**
- `id: UUID` - Unique identifier
- `name: str` - Display name
- `category: WordCategory` - Category
- `words: list[str]` - Available words
- `difficulty: int` - Difficulty level (1-5)
- `is_default: bool` - Built-in flag
- `created_by: str | None` - Creator user ID
- `created_at: datetime` - Creation timestamp

**Methods:**
- `get_random_words(count: int = 3) -> list[str]` - Get random words for selection
- `add_word(word: str)` - Add word to bank
- `remove_word(word: str)` - Remove word from bank

#### Guess
Represents a player's guess attempt.

**Attributes:**
- `id: UUID` - Unique identifier
- `player_id: UUID` - Player who guessed
- `player_name: str` - Player display name
- `guess_text: str` - The guessed word/phrase
- `result: GuessResult` - Guess result
- `points_awarded: int` - Points awarded
- `time_elapsed: float` - Seconds since round start
- `timestamp: datetime` - Guess timestamp

#### ChatMessage
Chat message for guessing and communication.

**Attributes:**
- `id: UUID` - Unique identifier
- `message_type: ChatMessageType` - Message type
- `sender_id: UUID | None` - Sender player ID
- `sender_name: str` - Sender display name
- `content: str` - Message text
- `metadata: dict[str, str | int | float | bool] | None` - Additional data
- `timestamp: datetime` - Message timestamp

**Class Methods:**
- `system(content: str, **metadata) -> ChatMessage` - Create system message
- `hint(player_name: str, **metadata) -> ChatMessage` - Create hint message

#### Round
Represents a single game round.

**Attributes:**
- `id: UUID` - Unique identifier
- `round_number: int` - Sequential round number (1-indexed)
- `drawer_id: UUID` - Player drawing this round
- `word: str` - The word being drawn (hidden)
- `word_hint: str` - Partially revealed word
- `word_options: list[str]` - Three word choices
- `canvas_id: UUID` - Canvas for this round
- `start_time: datetime | None` - Round start time
- `end_time: datetime | None` - Round end time
- `duration_seconds: int` - Total round duration
- `guesses: list[Guess]` - All guess attempts
- `chat_messages: list[ChatMessage]` - Round chat messages
- `scores: dict[str, int]` - Player scores this round
- `is_active: bool` - Active round flag

**Methods:**
- `start(word: str)` - Start round with selected word
- `end()` - End the round
- `add_guess(guess: Guess)` - Add guess attempt
- `add_chat_message(message: ChatMessage)` - Add chat message
- `calculate_points(time_elapsed: float, max_points: int = 1000) -> int` - Calculate points based on time
- `reveal_hint(reveal_count: int = 1) -> str` - Reveal letters in hint
- `is_expired() -> bool` - Check if time expired
- `time_remaining() -> float` - Get remaining seconds

#### GameSettings
Configurable game settings.

**Attributes:**
- `id: UUID` - Unique identifier
- `round_duration_seconds: int` - Time limit per round (60-120)
- `rounds_per_game: int` - Total rounds
- `max_players: int` - Max players (2-12)
- `word_bank_ids: list[UUID]` - Word banks to use
- `allow_custom_words: bool` - Custom words allowed
- `custom_words: list[str]` - Custom word list
- `hints_enabled: bool` - Show hints during rounds
- `hint_intervals: list[int]` - Seconds when to show hints
- `drawer_points_multiplier: float` - Drawer points multiplier
- `close_guess_threshold: int` - Max edit distance for "close"
- `require_exact_match: bool` - Exact spelling required

**Methods:**
- `add_custom_word(word: str)` - Add custom word
- `remove_custom_word(word: str)` - Remove custom word

#### GameRoom
Game lobby/room for Skribbl mode.

**Attributes:**
- `id: UUID` - Unique identifier
- `room_code: str` - Short join code (e.g., "ABCD1234")
- `name: str` - Display name
- `game_mode: GameMode` - Game mode type
- `game_state: GameState` - Current state
- `settings: GameSettings` - Game settings
- `host_id: UUID | None` - Host player ID
- `players: list[Player]` - All players
- `current_round: Round | None` - Active round
- `round_history: list[Round]` - Completed rounds
- `current_round_number: int` - Current round index
- `canvas_id: UUID | None` - Active canvas ID
- `created_at: datetime` - Creation timestamp
- `started_at: datetime | None` - Game start time
- `ended_at: datetime | None` - Game end time

**Methods:**
- `add_player(player: Player)` - Add player to room
- `remove_player(player_id: UUID)` - Remove player
- `get_player(player_id: UUID) -> Player | None` - Get player by ID
- `active_players() -> list[Player]` - Get connected players
- `start_game()` - Start game from lobby
- `next_round() -> Round` - Create next round
- `end_round()` - End current round
- `get_leaderboard() -> list[tuple[Player, int]]` - Get sorted leaderboard
- `is_game_over() -> bool` - Check if game finished

**Post Init:**
- Automatically generates 6-character alphanumeric room code if not provided

## Example Usage

### Creating a Game Room

```python
from scribbl_py.game import GameRoom, GameSettings, Player, WordBank, WordCategory

# Create game settings
settings = GameSettings(
    round_duration_seconds=80,
    rounds_per_game=8,
    max_players=8,
    hints_enabled=True,
)

# Create game room (auto-generates room code)
room = GameRoom(
    name="Epic Drawing Game",
    settings=settings,
)

print(f"Room code: {room.room_code}")  # e.g., "A3X7K9"
```

### Adding Players

```python
# Create host player
host = Player(
    user_id="user123",
    user_name="Alice",
    is_host=True,
)

room.add_player(host)

# Add more players
player2 = Player(user_id="user456", user_name="Bob")
player3 = Player(user_id="user789", user_name="Charlie")

room.add_player(player2)
room.add_player(player3)

# Check active players
print(f"Players: {len(room.active_players())}")  # 3
```

### Starting a Game

```python
# Start the game
room.start_game()
print(room.game_state)  # GameState.WORD_SELECTION

# Create next round
current_round = room.next_round()
print(f"Round {current_round.round_number}")
print(f"Drawer: {room.get_player(current_round.drawer_id).user_name}")
```

### Word Selection and Round Start

```python
# Create word bank
word_bank = WordBank(
    name="Animals",
    category=WordCategory.ANIMALS,
    words=["cat", "dog", "elephant", "giraffe", "penguin"],
)

# Get word options for drawer
word_options = word_bank.get_random_words(count=3)
current_round.word_options = word_options

# Drawer selects word
selected_word = word_options[0]
current_round.start(selected_word)

room.game_state = GameState.DRAWING
print(f"Word: {current_round.word}")  # Hidden from guessers
print(f"Hint: {current_round.word_hint}")  # "_ _ _ "
print(f"Time remaining: {current_round.time_remaining()}s")
```

### Handling Guesses

```python
from scribbl_py.game import Guess, GuessResult, ChatMessage

# Player makes a guess
time_elapsed = 5.2  # seconds since round start
guess_text = "cat"

# Calculate points
is_correct = guess_text.lower() == current_round.word.lower()
points = 0

if is_correct:
    points = current_round.calculate_points(time_elapsed)
    result = GuessResult.CORRECT

    # Update player
    player2.has_guessed = True
    player2.guess_time = time_elapsed
    player2.award_points(points)
else:
    result = GuessResult.WRONG

# Record guess
guess = Guess(
    player_id=player2.id,
    player_name=player2.user_name,
    guess_text=guess_text,
    result=result,
    points_awarded=points,
    time_elapsed=time_elapsed,
)
current_round.add_guess(guess)

# Add chat message
if is_correct:
    msg = ChatMessage(
        message_type=ChatMessageType.CORRECT,
        sender_id=player2.id,
        sender_name=player2.user_name,
        content=f"{player2.user_name} guessed correctly! (+{points} points)",
        metadata={"points": points},
    )
else:
    msg = ChatMessage(
        message_type=ChatMessageType.GUESS,
        sender_id=player2.id,
        sender_name=player2.user_name,
        content=guess_text,
    )

current_round.add_chat_message(msg)
```

### Revealing Hints

```python
# Reveal 1 letter
current_round.reveal_hint(reveal_count=1)
print(f"Updated hint: {current_round.word_hint}")  # "c _ _ "

# System message for hint
hint_msg = ChatMessage.system(
    f"Hint: {current_round.word_hint}",
    hint_type="letter_reveal",
)
current_round.add_chat_message(hint_msg)
```

### Ending a Round

```python
# End the round
current_round.end()
room.end_round()

room.game_state = GameState.ROUND_END

# Get leaderboard
leaderboard = room.get_leaderboard()
for player, score in leaderboard:
    print(f"{player.user_name}: {score} points")

# Check if game over
if room.is_game_over():
    room.game_state = GameState.GAME_OVER
    print("Game finished!")
else:
    # Start next round
    room.game_state = GameState.WORD_SELECTION
    next_round = room.next_round()
```

### Close Guess Hints

```python
from Levenshtein import distance

# Check if guess is close
def is_close_guess(guess: str, word: str, threshold: int = 2) -> bool:
    return distance(guess.lower(), word.lower()) <= threshold

# Player guesses "cta" (close to "cat")
guess_text = "cta"
time_elapsed = 8.5

if is_close_guess(guess_text, current_round.word, threshold=2):
    # Send hint
    hint_msg = ChatMessage.hint(
        player_name=player3.user_name,
        guess_text=guess_text,
    )
    current_round.add_chat_message(hint_msg)

    guess = Guess(
        player_id=player3.id,
        player_name=player3.user_name,
        guess_text=guess_text,
        result=GuessResult.CLOSE,
        points_awarded=0,
        time_elapsed=time_elapsed,
    )
    current_round.add_guess(guess)
```

### Custom Words

```python
# Add custom words to settings
room.settings.add_custom_word("skateboard")
room.settings.add_custom_word("headphones")

# Create custom word bank
custom_bank = WordBank(
    name="My Words",
    category=WordCategory.CUSTOM,
    words=room.settings.custom_words,
    is_default=False,
    created_by=host.user_id,
)
```

### Drawer Points

```python
# At round end, award drawer points based on guesser scores
drawer = room.get_player(current_round.drawer_id)
total_guesser_points = sum(g.points_awarded for g in current_round.guesses)
drawer_points = int(total_guesser_points * room.settings.drawer_points_multiplier)

drawer.award_points(drawer_points)

current_round.scores[str(drawer.id)] = drawer_points
```

## Integration Points

### With Existing Canvas System

Each round creates a new canvas for drawing:

```python
from scribbl_py.core import Canvas

# When starting a round
canvas = Canvas(
    id=current_round.canvas_id,
    name=f"Round {current_round.round_number} - {current_round.word}",
)

# Only drawer can draw, guessers see read-only view
```

### With WebSocket System

Game events can be broadcast via existing WebSocket infrastructure:

```python
from scribbl_py.realtime.messages import MessageType

# Broadcast game state changes
await connection_manager.broadcast(
    room_id=str(room.id),
    message={
        "type": "game_state_changed",
        "state": room.game_state.value,
        "round_number": room.current_round_number,
    }
)

# Broadcast guess results
await connection_manager.broadcast(
    room_id=str(room.id),
    message={
        "type": "player_guessed",
        "player_name": player.user_name,
        "result": guess.result.value,
        "points": guess.points_awarded,
    }
)
```

## Scoring Algorithm

Points are calculated using exponential decay:

```
points = max_points * e^(-2 * (time_elapsed / duration))
minimum = 100 points for correct guess
```

Examples:
- Instant guess (0s): 1000 points
- 10s (1/8 duration): ~779 points
- 20s (1/4 duration): ~607 points
- 40s (1/2 duration): ~368 points
- 60s (3/4 duration): ~223 points
- 80s (full duration): ~135 points (clamped to 100)

## State Machine

```
LOBBY
  ├─> [start_game()] -> WORD_SELECTION

WORD_SELECTION
  ├─> [drawer selects word] -> DRAWING

DRAWING
  ├─> [time expires or all guessed] -> ROUND_END

ROUND_END
  ├─> [is_game_over() = False] -> WORD_SELECTION (next round)
  └─> [is_game_over() = True] -> GAME_OVER

GAME_OVER
  └─> [final scores displayed]
```

## File Locations

- Models: `/Users/coffee/git/public/JacobCoffee/scribbl-py/src/scribbl_py/game/models.py`
- Package Init: `/Users/coffee/git/public/JacobCoffee/scribbl-py/src/scribbl_py/game/__init__.py`

## Next Steps

To implement Phase 9.1 Skribbl Mode:

1. **Create game service** (`src/scribbl_py/services/game.py`)
   - Game room management
   - Player join/leave handling
   - Round progression logic
   - Guess evaluation with Levenshtein distance
   - Word bank loading

2. **Create WebSocket handlers** (`src/scribbl_py/realtime/game_handler.py`)
   - Game state synchronization
   - Real-time guess broadcasts
   - Chat message distribution
   - Hint reveals
   - Timer synchronization

3. **Create REST API endpoints** (`src/scribbl_py/web/game_controllers.py`)
   - Create/join/leave game rooms
   - Get room state
   - Update settings
   - Manage word banks

4. **Create frontend components** (`frontend/src/game/`)
   - Lobby UI
   - Word selection modal
   - Game board with canvas + chat
   - Round end overlay
   - Scoreboard

5. **Database persistence** (optional)
   - Game room storage
   - Word bank management
   - Game history
   - Statistics

6. **Default word banks**
   - Create JSON files with categorized words
   - Seed database with default banks
   - Word difficulty ratings
