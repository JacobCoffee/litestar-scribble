"""Game service for managing CanvasClash mode game rooms."""

from __future__ import annotations

import random
import string
from uuid import UUID

import structlog

from scribbl_py.game.models import (
    ChatMessage,
    ChatMessageType,
    GameRoom,
    GameSettings,
    GameState,
    Guess,
    GuessResult,
    Player,
    PlayerState,
    Round,
)
from scribbl_py.game.wordbank import WordBank

logger = structlog.get_logger(__name__)


class GameNotFoundError(Exception):
    """Raised when a game room is not found."""

    def __init__(self, room_id: UUID | str) -> None:
        self.room_id = room_id
        super().__init__(f"Game room not found: {room_id}")


class PlayerNotFoundError(Exception):
    """Raised when a player is not found in a game."""

    def __init__(self, player_id: UUID | str) -> None:
        self.player_id = player_id
        super().__init__(f"Player not found: {player_id}")


class GameStateError(Exception):
    """Raised when a game action is invalid for current state."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class GameService:
    """Service for managing game rooms and gameplay logic.

    Provides business logic for:
    - Creating and managing game rooms
    - Player join/leave operations
    - Game lifecycle (start, rounds, scoring)
    - Guess validation and scoring
    - Word selection and hints
    """

    def __init__(self, word_bank: WordBank | None = None) -> None:
        """Initialize the game service.

        Args:
            word_bank: Word bank for word selection. Uses default if None.
        """
        self._rooms: dict[UUID, GameRoom] = {}
        self._room_codes: dict[str, UUID] = {}  # code -> room_id mapping
        self._word_bank = word_bank or WordBank()

    # Room Management

    def create_room(
        self,
        host_user_id: str,
        host_name: str,
        room_name: str = "Untitled Game",
        settings: GameSettings | None = None,
    ) -> GameRoom:
        """Create a new game room.

        Args:
            host_user_id: User ID of the room creator.
            host_name: Display name of the host.
            room_name: Name for the room.
            settings: Game settings (uses defaults if None).

        Returns:
            The created game room.
        """
        # Generate unique room code
        room_code = self._generate_room_code()

        # Create host player
        host = Player(
            user_id=host_user_id,
            user_name=host_name,
            is_host=True,
        )

        # Create room
        room = GameRoom(
            room_code=room_code,
            name=room_name,
            settings=settings or GameSettings(),
            host_id=host.id,
        )
        room.players.append(host)

        # Store room
        self._rooms[room.id] = room
        self._room_codes[room_code] = room.id

        logger.info(
            "Game room created",
            room_id=str(room.id),
            room_code=room_code,
            host_name=host_name,
        )

        return room

    def get_room(self, room_id: UUID) -> GameRoom:
        """Get a game room by ID.

        Args:
            room_id: The room UUID.

        Returns:
            The game room.

        Raises:
            GameNotFoundError: If room doesn't exist.
        """
        room = self._rooms.get(room_id)
        if not room:
            raise GameNotFoundError(room_id)
        return room

    def get_room_by_code(self, code: str) -> GameRoom:
        """Get a game room by join code.

        Args:
            code: The room join code.

        Returns:
            The game room.

        Raises:
            GameNotFoundError: If room doesn't exist.
        """
        room_id = self._room_codes.get(code.upper())
        if not room_id:
            raise GameNotFoundError(code)
        return self.get_room(room_id)

    def delete_room(self, room_id: UUID) -> None:
        """Delete a game room.

        Args:
            room_id: The room to delete.
        """
        room = self._rooms.pop(room_id, None)
        if room:
            self._room_codes.pop(room.room_code, None)
            logger.info("Game room deleted", room_id=str(room_id))

    # Player Management

    def join_room(
        self,
        room_id: UUID,
        user_id: str,
        user_name: str,
        avatar_url: str | None = None,
        as_spectator: bool = False,
    ) -> Player:
        """Add a player to a game room.

        Args:
            room_id: The room to join.
            user_id: User's identifier.
            user_name: Display name.
            avatar_url: Optional avatar URL.
            as_spectator: If True, join as spectator (can watch but not play).

        Returns:
            The created Player instance.

        Raises:
            GameNotFoundError: If room doesn't exist.
            GameStateError: If room is full or game already started (non-spectators only).
        """
        room = self.get_room(room_id)

        # Check if player already in room (reconnect case)
        existing = next((p for p in room.players if p.user_id == user_id), None)
        if existing:
            existing.connection_state = PlayerState.CONNECTED
            existing.mark_active()
            logger.info(
                "Player reconnected",
                room_id=str(room_id),
                player_id=str(existing.id),
                user_name=user_name,
                is_spectator=existing.is_spectator,
            )
            return existing

        # Create new player
        player = Player(
            user_id=user_id,
            user_name=user_name,
            avatar_url=avatar_url,
            is_spectator=as_spectator,
        )

        try:
            room.add_player(player)
        except ValueError as e:
            raise GameStateError(str(e)) from e

        logger.info(
            "Player joined room",
            room_id=str(room_id),
            player_id=str(player.id),
            user_name=user_name,
            is_spectator=as_spectator,
        )

        return player

    def leave_room(self, room_id: UUID, player_id: UUID) -> bool:
        """Remove a player from a game room.

        Args:
            room_id: The room ID.
            player_id: The player to remove.

        Returns:
            True if player was removed, False if not found.
        """
        room = self.get_room(room_id)
        player = room.get_player(player_id)

        if not player:
            return False

        room.remove_player(player_id)

        logger.info(
            "Player left room",
            room_id=str(room_id),
            player_id=str(player_id),
            user_name=player.user_name,
        )

        # Delete room if empty
        if not room.active_players():
            self.delete_room(room_id)

        return True

    def get_player(self, room_id: UUID, player_id: UUID) -> Player:
        """Get a player from a room.

        Args:
            room_id: The room ID.
            player_id: The player ID.

        Returns:
            The player instance.

        Raises:
            GameNotFoundError: If room doesn't exist.
            PlayerNotFoundError: If player doesn't exist.
        """
        room = self.get_room(room_id)
        player = room.get_player(player_id)
        if not player:
            raise PlayerNotFoundError(player_id)
        return player

    # Game Flow

    def start_game(self, room_id: UUID, player_id: UUID) -> Round:
        """Start the game (host only).

        Args:
            room_id: The room to start.
            player_id: Player requesting start (must be host).

        Returns:
            The first round.

        Raises:
            GameNotFoundError: If room doesn't exist.
            GameStateError: If not host or invalid state.
        """
        room = self.get_room(room_id)
        player = room.get_player(player_id)

        if not player or not player.is_host:
            raise GameStateError("Only the host can start the game")

        try:
            room.start_game()
        except ValueError as e:
            raise GameStateError(str(e)) from e

        # Create first round
        new_round = room.next_round()

        # Generate word options for drawer (including custom words from host)
        logger.info(
            "Generating word options",
            room_id=str(room_id),
            custom_words=room.settings.custom_words,
            custom_words_only=room.settings.custom_words_only,
        )
        new_round.word_options = self._word_bank.get_word_options(
            game_id=room.id,
            count=3,
            custom_words=room.settings.custom_words if room.settings.custom_words else None,
            custom_words_only=room.settings.custom_words_only,
        )

        logger.info(
            "Game started",
            room_id=str(room_id),
            total_rounds=room.settings.rounds_per_game,
            word_options=new_round.word_options,
        )

        return new_round

    def select_word(self, room_id: UUID, player_id: UUID, word: str) -> Round:
        """Select word for drawing (drawer only).

        Args:
            room_id: The room ID.
            player_id: Player selecting (must be drawer).
            word: The selected word.

        Returns:
            The updated round.

        Raises:
            GameStateError: If not drawer or invalid state.
        """
        room = self.get_room(room_id)

        if room.game_state != GameState.WORD_SELECTION:
            raise GameStateError("Not in word selection phase")

        if not room.current_round:
            raise GameStateError("No active round")

        if room.current_round.drawer_id != player_id:
            raise GameStateError("Only the drawer can select the word")

        # Validate word is one of the options
        if word.lower() not in [w.lower() for w in room.current_round.word_options]:
            raise GameStateError("Invalid word selection")

        # Mark the selected word as used (so it won't appear in future rounds)
        self._word_bank.mark_word_used(room.id, word)

        # Start the round
        room.current_round.start(word)
        room.game_state = GameState.DRAWING

        logger.info(
            "Word selected, round started",
            room_id=str(room_id),
            round=room.current_round.round_number,
        )

        return room.current_round

    def submit_guess(
        self,
        room_id: UUID,
        player_id: UUID,
        guess_text: str,
    ) -> tuple[Guess, ChatMessage]:
        """Submit a guess for the current word.

        Args:
            room_id: The room ID.
            player_id: Player guessing.
            guess_text: The guess attempt.

        Returns:
            Tuple of (Guess result, ChatMessage to broadcast).

        Raises:
            GameStateError: If not in drawing phase or invalid player.
        """
        room = self.get_room(room_id)
        player = room.get_player(player_id)

        if not player:
            raise PlayerNotFoundError(player_id)

        if room.game_state != GameState.DRAWING:
            raise GameStateError("Not in drawing phase")

        if not room.current_round:
            raise GameStateError("No active round")

        # Spectators cannot guess
        if player.is_spectator:
            guess = Guess(
                player_id=player_id,
                player_name=player.user_name,
                guess_text=guess_text,
                result=GuessResult.INVALID,
            )
            msg = ChatMessage(
                message_type=ChatMessageType.SYSTEM,
                sender_id=player_id,
                sender_name=player.user_name,
                content="Spectators cannot guess!",
            )
            return guess, msg

        # Drawer cannot guess
        if room.current_round.drawer_id == player_id:
            guess = Guess(
                player_id=player_id,
                player_name=player.user_name,
                guess_text=guess_text,
                result=GuessResult.DRAWER,
            )
            msg = ChatMessage(
                message_type=ChatMessageType.SYSTEM,
                sender_id=player_id,
                sender_name=player.user_name,
                content="Drawer cannot guess!",
            )
            return guess, msg

        # Already guessed correctly
        if player.has_guessed:
            guess = Guess(
                player_id=player_id,
                player_name=player.user_name,
                guess_text=guess_text,
                result=GuessResult.ALREADY_GUESSED,
            )
            msg = ChatMessage(
                message_type=ChatMessageType.SYSTEM,
                sender_id=player_id,
                sender_name=player.user_name,
                content=f"{player.user_name} has already guessed!",
            )
            return guess, msg

        # Calculate time elapsed
        time_elapsed = 0.0
        if room.current_round.start_time:
            from datetime import UTC, datetime

            time_elapsed = (datetime.now(UTC) - room.current_round.start_time).total_seconds()

        # Check the guess (returns GuessResult.CORRECT, .CLOSE, or .WRONG)
        result = self._word_bank.check_guess(
            room.current_round.word,
            guess_text,
        )

        points = 0
        if result == GuessResult.CORRECT:
            points = room.current_round.calculate_points(time_elapsed)
            player.has_guessed = True
            player.guess_time = time_elapsed
            player.award_points(points)

            # Award drawer points
            drawer = room.get_player(room.current_round.drawer_id)
            if drawer:
                drawer_points = int(points * room.settings.drawer_points_multiplier)
                drawer.award_points(drawer_points)

        # Create guess record
        guess = Guess(
            player_id=player_id,
            player_name=player.user_name,
            guess_text=guess_text,
            result=result,
            points_awarded=points,
            time_elapsed=time_elapsed,
        )
        room.current_round.add_guess(guess)

        # Create chat message
        if result == GuessResult.CORRECT:
            msg = ChatMessage(
                message_type=ChatMessageType.CORRECT,
                sender_id=player_id,
                sender_name=player.user_name,
                content=f"{player.user_name} guessed the word! (+{points} points)",
                metadata={"points": points, "time": time_elapsed},
            )
        elif result == GuessResult.CLOSE:
            msg = ChatMessage.hint(player.user_name)
        else:
            # Regular guess shown to everyone
            msg = ChatMessage(
                message_type=ChatMessageType.GUESS,
                sender_id=player_id,
                sender_name=player.user_name,
                content=guess_text,
            )

        room.current_round.add_chat_message(msg)

        logger.debug(
            "Guess submitted",
            room_id=str(room_id),
            player=player.user_name,
            result=result.value,
            points=points,
        )

        return guess, msg

    def end_round(self, room_id: UUID) -> dict:
        """End the current round and prepare results.

        Args:
            room_id: The room ID.

        Returns:
            Round results including word, scores, drawer info, and next state.
        """
        room = self.get_room(room_id)

        if not room.current_round:
            raise GameStateError("No active round")

        word = room.current_round.word
        round_number = room.current_round.round_number
        drawer_id = room.current_round.drawer_id

        # Get drawer name before moving round to history
        drawer = room.get_player(drawer_id)
        drawer_name = drawer.user_name if drawer else "Unknown"

        room.end_round()

        # Check if game is over
        is_game_over = room.is_game_over()
        if is_game_over:
            room.game_state = GameState.GAME_OVER

        logger.info(
            "Round ended",
            room_id=str(room_id),
            round=round_number,
            word=word,
            game_over=is_game_over,
        )

        return {
            "word": word,
            "round_number": round_number,
            "drawer_id": drawer_id,
            "drawer_name": drawer_name,
            "leaderboard": room.get_leaderboard(),
            "is_game_over": is_game_over,
        }

    def next_round(self, room_id: UUID) -> Round:
        """Start the next round.

        Args:
            room_id: The room ID.

        Returns:
            The new round.

        Raises:
            GameStateError: If game is over or invalid state.
        """
        room = self.get_room(room_id)

        if room.game_state == GameState.GAME_OVER:
            raise GameStateError("Game is already over")

        try:
            new_round = room.next_round()
        except ValueError as e:
            raise GameStateError(str(e)) from e

        # Generate word options (including custom words from host)
        new_round.word_options = self._word_bank.get_word_options(
            game_id=room.id,
            count=3,
            custom_words=room.settings.custom_words if room.settings.custom_words else None,
            custom_words_only=room.settings.custom_words_only,
        )

        logger.info(
            "Next round started",
            room_id=str(room_id),
            round=new_round.round_number,
        )

        return new_round

    def reveal_hint(self, room_id: UUID) -> str | None:
        """Reveal a letter in the word hint.

        Args:
            room_id: The room ID.

        Returns:
            Updated hint string, or None if no active round.
        """
        room = self.get_room(room_id)

        if not room.current_round or room.game_state != GameState.DRAWING:
            return None

        return room.current_round.reveal_hint()

    def reset_game(self, room_id: UUID) -> GameRoom:
        """Reset game to lobby state for replay.

        Args:
            room_id: The room ID.

        Returns:
            The reset game room.
        """
        room = self.get_room(room_id)

        room.game_state = GameState.LOBBY
        room.current_round = None
        room.round_history = []
        room.current_round_number = 0
        room.started_at = None
        room.ended_at = None

        # Reset player scores
        for player in room.players:
            player.score = 0
            player.reset_round_state()

        # Reset word bank used words
        self._word_bank.reset_game_words(room.id)

        logger.info("Game reset to lobby", room_id=str(room_id))

        return room

    # Utility Methods

    def _generate_room_code(self, length: int = 6) -> str:
        """Generate a unique room join code.

        Args:
            length: Code length.

        Returns:
            Unique alphanumeric code.
        """
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
            if code not in self._room_codes:
                return code

    def get_all_rooms(self) -> list[GameRoom]:
        """Get all active game rooms.

        Returns:
            List of all rooms.
        """
        return list(self._rooms.values())

    def get_lobby_rooms(self, *, public_only: bool = True) -> list[GameRoom]:
        """Get rooms that are in lobby state (joinable).

        Args:
            public_only: If True, only return public rooms visible in lobby list.
                         If False, return all lobby rooms regardless of visibility.

        Returns:
            List of rooms in LOBBY state.
        """
        rooms = [r for r in self._rooms.values() if r.game_state == GameState.LOBBY]
        if public_only:
            rooms = [r for r in rooms if r.settings.is_public]
        return rooms

    def get_active_games(self, *, public_only: bool = True) -> list[GameRoom]:
        """Get rooms with games in progress (available for spectating).

        Args:
            public_only: If True, only return public rooms.

        Returns:
            List of rooms in DRAWING, WORD_SELECTION, or ROUND_END state.
        """
        active_states = {GameState.DRAWING, GameState.WORD_SELECTION, GameState.ROUND_END}
        rooms = [r for r in self._rooms.values() if r.game_state in active_states]
        if public_only:
            rooms = [r for r in rooms if r.settings.is_public]
        return rooms
