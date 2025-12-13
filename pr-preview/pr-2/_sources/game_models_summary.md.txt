# Game Models Summary - Phase 9.1 Skribbl Mode

## File Locations

- **Models**: `/Users/coffee/git/public/JacobCoffee/scribbl-py/src/scribbl_py/game/models.py` (650 lines)
- **Package**: `/Users/coffee/git/public/JacobCoffee/scribbl-py/src/scribbl_py/game/__init__.py`
- **Documentation**: `/Users/coffee/git/public/JacobCoffee/scribbl-py/docs/game_models_design.md`

## Model Structure

```
┌─────────────────────────────────────────────────────────────┐
│                         GameRoom                            │
│  - room_code: str (auto-generated, e.g., "KHENU9")         │
│  - game_state: GameState (LOBBY → WORD_SELECTION → etc.)  │
│  - settings: GameSettings                                   │
│  - players: list[Player]                                    │
│  - current_round: Round | None                              │
│  - round_history: list[Round]                               │
└──────────┬──────────────────────────────────────────────────┘
           │
           ├──> GameSettings
           │    - round_duration_seconds: int (60-120)
           │    - rounds_per_game: int
           │    - max_players: int (2-12)
           │    - word_bank_ids: list[UUID]
           │    - custom_words: list[str]
           │    - hints_enabled: bool
           │    - drawer_points_multiplier: float
           │
           ├──> Player (multiple)
           │    - user_id: str
           │    - user_name: str
           │    - score: int
           │    - is_host: bool
           │    - connection_state: PlayerState
           │    - has_guessed: bool
           │
           └──> Round (current + history)
                - drawer_id: UUID
                - word: str (hidden from guessers)
                - word_hint: str (e.g., "_ _ _ ")
                - word_options: list[str] (3 choices)
                - guesses: list[Guess]
                - chat_messages: list[ChatMessage]
                - start_time / end_time: datetime
                │
                ├──> Guess
                │    - player_id: UUID
                │    - guess_text: str
                │    - result: GuessResult (CORRECT/CLOSE/WRONG)
                │    - points_awarded: int
                │    - time_elapsed: float
                │
                └──> ChatMessage
                     - message_type: ChatMessageType
                     - sender_id: UUID | None
                     - content: str
                     - metadata: dict | None

┌─────────────────────────────────────────────────────────────┐
│                       WordBank                               │
│  - category: WordCategory (ANIMALS/OBJECTS/etc.)            │
│  - words: list[str]                                          │
│  - difficulty: int (1-5)                                     │
│  - is_default: bool                                          │
└──────────────────────────────────────────────────────────────┘
```

## Enums (7 total)

| Enum | Values | Purpose |
|------|--------|---------|
| **GameState** | LOBBY, WORD_SELECTION, DRAWING, ROUND_END, GAME_OVER | Game flow state machine |
| **GameMode** | SKRIBBL, COLLABORATIVE | Game mode type |
| **PlayerState** | CONNECTED, DISCONNECTED, LEFT | Player connection status |
| **WordCategory** | ANIMALS, OBJECTS, ACTIONS, FOOD, PLACES, etc. | Word categorization |
| **ChatMessageType** | GUESS, SYSTEM, HINT, CORRECT, DRAWER | Chat message types |
| **GuessResult** | CORRECT, CLOSE, WRONG, ALREADY_GUESSED, DRAWER, INVALID | Guess evaluation |

## Dataclasses (7 total)

| Model | Key Attributes | Key Methods |
|-------|---------------|-------------|
| **Player** | user_name, score, is_host, has_guessed | reset_round_state(), award_points() |
| **WordBank** | category, words, difficulty | get_random_words(), add_word() |
| **Guess** | guess_text, result, points_awarded, time_elapsed | - |
| **ChatMessage** | message_type, sender_name, content | system(), hint() (class methods) |
| **Round** | drawer_id, word, word_hint, guesses, chat_messages | start(), end(), calculate_points(), reveal_hint() |
| **GameSettings** | round_duration, rounds_per_game, max_players, custom_words | add_custom_word() |
| **GameRoom** | room_code, game_state, players, current_round | add_player(), start_game(), next_round(), get_leaderboard() |

## Key Features Implemented

### 1. Game Room Management
- Auto-generated 6-character alphanumeric room codes
- Host assignment (first player becomes host)
- Player capacity limits (2-12 players)
- Connection state tracking

### 2. Round System
- Drawer rotation (round-robin)
- Word selection from 3 options
- Configurable timer (60-120 seconds)
- Automatic time tracking and expiration

### 3. Scoring System
- **Exponential decay**: faster guess = more points
- Formula: `points = 1000 * e^(-2 * time_ratio)`
- Range: 100-1000 points per correct guess
- Drawer gets 50% of total guesser points

### 4. Word System
- Categorized word banks
- Custom word lists
- Random word selection (3 options)
- Progressive hint reveals

### 5. Chat & Guessing
- Guess attempts tracked
- System messages
- Close guess hints (Levenshtein distance)
- Correct guess notifications
- Round chat history

### 6. State Management
- State machine: LOBBY → WORD_SELECTION → DRAWING → ROUND_END → GAME_OVER
- Round history preservation
- Leaderboard calculation
- Game completion detection

## Type Safety

All models use:
- **Full type annotations** (PEP 484)
- **dataclasses** for structure
- **StrEnum** for type-safe enums
- **UUID** for unique identifiers
- **datetime** with UTC timezone
- **Optional types** (`| None` syntax)

## Code Quality

- **Linting**: Passes `ruff check` with all rules
- **Imports**: All at top-level (no lazy imports)
- **Docstrings**: Google-style for all classes/methods
- **Line count**: 650 lines in models.py
- **Pattern consistency**: Follows existing codebase patterns

## Example Usage

```python
from scribbl_py.game import GameRoom, Player, GameSettings, WordBank, WordCategory

# Create game
settings = GameSettings(round_duration_seconds=80, rounds_per_game=8)
room = GameRoom(name="Epic Game", settings=settings)
# room.room_code auto-generated (e.g., "KHENU9")

# Add players
alice = Player(user_id="user1", user_name="Alice")
bob = Player(user_id="user2", user_name="Bob")
room.add_player(alice)  # Alice becomes host
room.add_player(bob)

# Start game
room.start_game()  # GameState.WORD_SELECTION

# Create round
round = room.next_round()
round.word_options = ["cat", "dog", "elephant"]
round.start("cat")  # GameState.DRAWING

# Handle guess
from scribbl_py.game import Guess, GuessResult

points = round.calculate_points(time_elapsed=5.2)
guess = Guess(
    player_id=bob.id,
    player_name=bob.user_name,
    guess_text="cat",
    result=GuessResult.CORRECT,
    points_awarded=points,
    time_elapsed=5.2,
)
round.add_guess(guess)
bob.award_points(points)

# End round
round.end()
room.end_round()  # GameState.ROUND_END

# Leaderboard
for player, score in room.get_leaderboard():
    print(f"{player.user_name}: {score} points")
```

## Integration Points

### With Existing Canvas System
```python
from scribbl_py.core import Canvas

# Each round has its own canvas
canvas = Canvas(
    id=round.canvas_id,
    name=f"Round {round.round_number}",
)
```

### With WebSocket System
```python
# Broadcast game events
await connection_manager.broadcast(
    room_id=str(room.id),
    message={
        "type": "game_state_changed",
        "state": room.game_state.value,
        "round": room.current_round_number,
    }
)
```

## Next Implementation Steps

1. **Game Service** - Business logic for game flow
2. **WebSocket Handlers** - Real-time game synchronization
3. **REST API Endpoints** - HTTP interface for game operations
4. **Frontend Components** - Lobby, game board, scoreboard UIs
5. **Word Bank Data** - Default word lists with categories
6. **Database Models** - Persistence layer (optional)

## Testing Strategy

Key test scenarios:
- Room creation and player management
- State transitions (LOBBY → WORD_SELECTION → DRAWING → etc.)
- Round progression and drawer rotation
- Scoring calculation with various time values
- Word hint reveals
- Guess evaluation (correct/close/wrong)
- Close guess detection (Levenshtein distance)
- Leaderboard sorting
- Game completion detection

## Performance Considerations

- **In-memory** models (no DB overhead)
- **Efficient lookups**: UUID-based player/round access
- **Minimal copying**: Lists stored directly on objects
- **Lazy computation**: Points calculated on-demand
- **State caching**: game_state field avoids recomputation

## Design Decisions

1. **Dataclasses over msgspec**: Follows existing codebase patterns
2. **StrEnum**: Type-safe string enums for JSON serialization
3. **Auto room codes**: Generated in `__post_init__` for convenience
4. **Exponential decay scoring**: Rewards early guesses more than linear
5. **Round-robin drawer**: Fair rotation through all players
6. **Minimum 100 points**: Ensures participation value
7. **Close guess threshold**: Configurable edit distance (default=2)
8. **Drawer points**: 50% multiplier of total guesser points

## Validation Rules

- Min 2 players to start game
- Max players configurable (2-12)
- Round duration: 60-120 seconds
- Word hint: spaces between letters (e.g., "_ _ _ ")
- Room codes: 6 uppercase alphanumeric characters
- Guess evaluation: Case-insensitive by default
