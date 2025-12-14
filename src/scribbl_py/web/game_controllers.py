"""Litestar controllers for Skribbl game mode API endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

import structlog
from litestar import Controller, delete, get, patch, post
from litestar.response import Redirect, Response, Template
from litestar.status_codes import HTTP_204_NO_CONTENT

from scribbl_py.auth.db_service import DatabaseAuthService  # noqa: TC001
from scribbl_py.game.moderation import validate_custom_words
from scribbl_py.services.game import (
    GameService,
    PlayerNotFoundError,
)
from scribbl_py.services.telemetry import get_telemetry

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from litestar.connection import Request


# DTOs for Game API


@dataclass
class CreateRoomDTO:
    """Data for creating a new game room."""

    name: str = "Untitled Game"
    host_name: str = "Anonymous"
    round_duration: int = 80
    rounds_per_game: int = 8
    max_players: int = 8
    is_public: bool = False  # Private by default


@dataclass
class JoinRoomDTO:
    """Data for joining a game room."""

    user_name: str = "Anonymous"
    as_spectator: bool = False


@dataclass
class UpdateSettingsDTO:
    """Data for updating game settings."""

    round_duration: int | None = None
    rounds_per_game: int | None = None
    custom_words: list[str] | None = None
    custom_words_only: bool | None = None


@dataclass
class SelectWordDTO:
    """Data for selecting a word to draw."""

    word: str


@dataclass
class RoomResponseDTO:
    """Response data for a game room."""

    id: str
    code: str
    name: str
    state: str
    host_id: str | None
    player_count: int
    max_players: int
    current_round: int
    total_rounds: int


@dataclass
class PlayerResponseDTO:
    """Response data for a player."""

    id: str
    user_id: str
    name: str
    score: int
    is_host: bool
    is_spectator: bool = False


@dataclass
class RoomDetailDTO:
    """Detailed response for a game room."""

    id: str
    code: str
    name: str
    state: str
    host_id: str | None
    players: list[PlayerResponseDTO]
    settings: dict[str, Any]
    current_round: int
    total_rounds: int


def room_to_response(room: Any) -> RoomResponseDTO:
    """Convert GameRoom to response DTO."""
    return RoomResponseDTO(
        id=str(room.id),
        code=room.room_code,
        name=room.name,
        state=room.game_state.value,
        host_id=str(room.host_id) if room.host_id else None,
        player_count=len(room.active_players()),
        max_players=room.settings.max_players,
        current_round=room.current_round_number,
        total_rounds=room.settings.rounds_per_game,
    )


def room_to_detail(room: Any) -> RoomDetailDTO:
    """Convert GameRoom to detailed DTO."""
    return RoomDetailDTO(
        id=str(room.id),
        code=room.room_code,
        name=room.name,
        state=room.game_state.value,
        host_id=str(room.host_id) if room.host_id else None,
        players=[
            PlayerResponseDTO(
                id=str(p.id),
                user_id=p.user_id,
                name=p.user_name,
                score=p.score,
                is_host=p.is_host,
            )
            for p in room.active_players()
        ],
        settings={
            "round_duration": room.settings.round_duration_seconds,
            "rounds_per_game": room.settings.rounds_per_game,
            "max_players": room.settings.max_players,
            "hints_enabled": room.settings.hints_enabled,
            "custom_words": room.settings.custom_words,
            "custom_words_only": room.settings.custom_words_only,
        },
        current_round=room.current_round_number,
        total_rounds=room.settings.rounds_per_game,
    )


def player_to_response(player: Any) -> PlayerResponseDTO:
    """Convert Player to response DTO."""
    return PlayerResponseDTO(
        id=str(player.id),
        user_id=player.user_id,
        name=player.user_name,
        score=player.score,
        is_host=player.is_host,
        is_spectator=player.is_spectator,
    )


class GameRoomController(Controller):
    """Controller for game room operations.

    Handles creation, joining, and management of Skribbl game rooms.
    """

    path = "/canvas-clash/rooms"
    tags: ClassVar[list[str]] = ["Skribbl Game"]

    @post("/")
    async def create_room(
        self,
        data: CreateRoomDTO,
        game_service: GameService,
        game_ws_handler: Any,
        request: Request,
    ) -> RoomDetailDTO:
        """Create a new game room.

        Args:
            data: Room creation data.
            game_service: Game service instance (injected).
            game_ws_handler: WebSocket handler for broadcasting (injected).
            request: The request object.

        Returns:
            The created game room details.
        """
        # Get or generate user ID from session/cookie
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        # Create settings
        from scribbl_py.game.models import GameSettings

        settings = GameSettings(
            is_public=data.is_public,
            round_duration_seconds=data.round_duration,
            rounds_per_game=data.rounds_per_game,
            max_players=data.max_players,
        )

        room = game_service.create_room(
            host_user_id=user_id,
            host_name=data.host_name,
            room_name=data.name,
            settings=settings,
        )

        # Track room creation telemetry
        telemetry = get_telemetry()
        telemetry.track_room_created(room.id, is_public=data.is_public)

        # Notify lobby browsers about the new room (only if public)
        if game_ws_handler is not None and settings.is_public:
            await game_ws_handler._broadcast_to_lobby_browsers(
                {
                    "type": "room_created",
                    "room": game_ws_handler._serialize_lobby(room),
                }
            )

        return room_to_detail(room)

    @get("/")
    async def list_rooms(self, game_service: GameService) -> list[RoomResponseDTO]:
        """List all available game rooms in lobby state.

        Args:
            game_service: Game service instance (injected).

        Returns:
            List of joinable game rooms.
        """
        rooms = game_service.get_lobby_rooms()
        return [room_to_response(r) for r in rooms]

    @get("/{room_id:uuid}")
    async def get_room(self, room_id: UUID, game_service: GameService) -> RoomDetailDTO:
        """Get a game room by ID.

        Args:
            room_id: The room UUID.
            game_service: Game service instance (injected).

        Returns:
            The game room details.

        Raises:
            GameNotFoundError: If room doesn't exist.
        """
        room = game_service.get_room(room_id)
        return room_to_detail(room)

    @get("/code/{code:str}")
    async def get_room_by_code(self, code: str, game_service: GameService) -> RoomDetailDTO:
        """Get a game room by join code.

        Args:
            code: The room join code (6 characters).
            game_service: Game service instance (injected).

        Returns:
            The game room details.

        Raises:
            GameNotFoundError: If room doesn't exist.
        """
        room = game_service.get_room_by_code(code)
        return room_to_detail(room)

    @post("/{room_id:uuid}/join")
    async def join_room(
        self,
        room_id: UUID,
        data: JoinRoomDTO,
        game_service: GameService,
        request: Request,
    ) -> PlayerResponseDTO:
        """Join a game room.

        Args:
            room_id: The room UUID.
            data: Join data with user name and spectator flag.
            game_service: Game service instance (injected).
            request: The request object.

        Returns:
            The player's details.

        Raises:
            GameNotFoundError: If room doesn't exist.
            GameStateError: If room is full or game started (non-spectators only).
        """
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        player = game_service.join_room(
            room_id=room_id,
            user_id=user_id,
            user_name=data.user_name,
            as_spectator=data.as_spectator,
        )

        return player_to_response(player)

    @post("/{room_id:uuid}/leave")
    async def leave_room(
        self,
        room_id: UUID,
        game_service: GameService,
        request: Request,
    ) -> Redirect:
        """Leave a game room.

        Args:
            room_id: The room UUID.
            game_service: Game service instance (injected).
            request: The request object.

        Returns:
            Redirect to Canvas Clash home.
        """
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        # Find player by user_id
        room = game_service.get_room(room_id)
        player = next((p for p in room.players if p.user_id == user_id), None)

        if player:
            game_service.leave_room(room_id, player.id)

        return Redirect(path="/canvas-clash/")

    @patch("/{room_id:uuid}/settings")
    async def update_settings(
        self,
        room_id: UUID,
        data: UpdateSettingsDTO,
        game_service: GameService,
    ) -> dict[str, Any]:
        """Update game room settings (host only).

        Args:
            room_id: The room UUID.
            data: Settings to update.
            game_service: Game service instance (injected).

        Returns:
            Updated room details with moderation info.
        """
        room = game_service.get_room(room_id)
        rejected_count = 0

        if data.round_duration is not None:
            room.settings.round_duration_seconds = data.round_duration
        if data.rounds_per_game is not None:
            room.settings.rounds_per_game = data.rounds_per_game
        if data.custom_words is not None:
            # Filter custom words for hate speech
            raw_words = [w.strip() for w in data.custom_words if w.strip()]
            valid_words, rejected_words = validate_custom_words(raw_words)
            room.settings.custom_words = valid_words
            rejected_count = len(rejected_words)
            if rejected_words:
                logger.warning(
                    "Some custom words were rejected (hate speech filter)",
                    room_id=str(room_id),
                    rejected_count=rejected_count,
                    rejected_words=rejected_words,  # Log the actual words for moderation review
                )
            logger.info(
                "Custom words updated",
                room_id=str(room_id),
                custom_words=room.settings.custom_words,
                accepted_count=len(valid_words),
            )
        if data.custom_words_only is not None:
            room.settings.custom_words_only = data.custom_words_only
            logger.info(
                "Custom words only setting updated",
                room_id=str(room_id),
                custom_words_only=room.settings.custom_words_only,
            )

        # Return room details plus moderation info
        detail = room_to_detail(room)
        return {
            "id": detail.id,
            "code": detail.code,
            "name": detail.name,
            "state": detail.state,
            "host_id": detail.host_id,
            "players": [
                {
                    "id": p.id,
                    "user_id": p.user_id,
                    "name": p.name,
                    "score": p.score,
                    "is_host": p.is_host,
                    "is_spectator": p.is_spectator,
                }
                for p in detail.players
            ],
            "settings": detail.settings,
            "current_round": detail.current_round,
            "total_rounds": detail.total_rounds,
            "rejected_words_count": rejected_count,
        }

    @post("/{room_id:uuid}/start")
    async def start_game(
        self,
        room_id: UUID,
        game_service: GameService,
        request: Request,
    ) -> dict[str, Any]:
        """Start the game (host only).

        Args:
            room_id: The room UUID.
            game_service: Game service instance (injected).
            request: The request object.

        Returns:
            First round information.

        Raises:
            GameStateError: If not host or not enough players.
        """
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        room = game_service.get_room(room_id)
        player = next((p for p in room.players if p.user_id == user_id), None)

        if not player:
            raise PlayerNotFoundError(user_id)

        first_round = game_service.start_game(room_id, player.id)

        return {
            "round_number": first_round.round_number,
            "drawer_id": str(first_round.drawer_id),
            "word_options": first_round.word_options,
            "duration": first_round.duration_seconds,
        }

    @post("/{room_id:uuid}/select-word")
    async def select_word(
        self,
        room_id: UUID,
        data: SelectWordDTO,
        game_service: GameService,
        request: Request,
    ) -> dict[str, Any]:
        """Select a word to draw (drawer only).

        Args:
            room_id: The room UUID.
            data: Word selection data.
            game_service: Game service instance (injected).
            request: The request object.

        Returns:
            Round start information.

        Raises:
            GameStateError: If not drawer or invalid word.
        """
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        room = game_service.get_room(room_id)
        player = next((p for p in room.players if p.user_id == user_id), None)

        if not player:
            raise PlayerNotFoundError(user_id)

        current_round = game_service.select_word(room_id, player.id, data.word)

        return {
            "word": current_round.word,
            "word_hint": current_round.word_hint,
            "duration": current_round.duration_seconds,
        }

    @post("/{room_id:uuid}/reset")
    async def reset_game(
        self,
        room_id: UUID,
        game_service: GameService,
    ) -> RoomDetailDTO:
        """Reset game to lobby state.

        Args:
            room_id: The room UUID.
            game_service: Game service instance (injected).

        Returns:
            Reset room details.
        """
        room = game_service.reset_game(room_id)
        return room_to_detail(room)

    @delete("/{room_id:uuid}", status_code=HTTP_204_NO_CONTENT)
    async def delete_room(
        self,
        room_id: UUID,
        game_service: GameService,
    ) -> None:
        """Delete a game room.

        Args:
            room_id: The room UUID.
            game_service: Game service instance (injected).
        """
        game_service.delete_room(room_id)


class GameUIController(Controller):
    """Controller for game UI pages.

    Handles server-rendered HTML pages for the Skribbl game UI.
    """

    path = "/canvas-clash"
    tags: ClassVar[list[str]] = ["Skribbl UI"]
    include_in_schema = False

    @get("/")
    async def game_home(
        self,
        game_service: GameService,
        auth_service: DatabaseAuthService,
        request: Request,
    ) -> Template:
        """Render the CanvasClash game home page.

        Returns:
            Rendered home template.
        """
        # Get available lobby rooms
        lobby_rooms = game_service.get_lobby_rooms()

        # Get active games (for spectating)
        active_games = game_service.get_active_games()

        # Check if app is in debug mode
        is_debug = getattr(request.app, "debug", False)

        # Get logged-in user info if available
        username = None
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            session = await auth_service.get_session(session_id)
            if session and session.user_id:
                user = await auth_service.get_user(session.user_id)
                if user:
                    username = user.username

        return Template(
            template_name="canvas_clash_home.html",
            context={
                "rooms": [
                    {
                        "id": str(r.id),
                        "code": r.room_code,
                        "name": r.name,
                        "player_count": len(r.active_guessers()),
                        "max_players": r.settings.max_players,
                    }
                    for r in lobby_rooms
                ],
                "active_games": [
                    {
                        "id": str(r.id),
                        "code": r.room_code,
                        "name": r.name,
                        "player_count": len(r.active_guessers()),
                        "spectator_count": len(r.spectators()),
                        "current_round": r.current_round_number,
                        "total_rounds": r.settings.rounds_per_game,
                    }
                    for r in active_games
                ],
                "debug_mode": is_debug,
                "username": username,
            },
        )

    @get("/rooms/{room_id:uuid}/lobby")
    async def game_lobby(
        self,
        room_id: UUID,
        game_service: GameService,
        auth_service: DatabaseAuthService,
        request: Request,
    ) -> Template:
        """Render the game lobby page.

        Args:
            room_id: The room UUID.
            game_service: Game service instance.
            auth_service: Auth service instance.
            request: The request object.

        Returns:
            Rendered lobby template.
        """
        room = game_service.get_room(room_id)
        user_id = request.cookies.get("user_id", "")

        # Get auth user ID if logged in
        auth_user_id = None
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            session = await auth_service.get_session(session_id)
            if session and session.user_id:
                auth_user_id = str(session.user_id)

        # Find current player
        current_player = next((p for p in room.players if p.user_id == user_id), None)
        is_host = current_player.is_host if current_player else False

        # Separate players and spectators
        active_guessers = room.active_guessers()
        spectators = room.spectators()
        is_spectator = current_player.is_spectator if current_player else False

        return Template(
            template_name="canvas_clash_lobby.html",
            context={
                "room": {
                    "id": str(room.id),
                    "code": room.room_code,
                    "name": room.name,
                    "is_public": room.settings.is_public,
                    "settings": {
                        "rounds": room.settings.rounds_per_game,
                        "draw_time": room.settings.round_duration_seconds,
                        "custom_words": room.settings.custom_words,
                        "custom_words_only": room.settings.custom_words_only,
                    },
                },
                "players": [
                    {
                        "id": str(p.id),
                        "name": p.user_name,
                        "is_host": p.is_host,
                        "is_spectator": p.is_spectator,
                    }
                    for p in active_guessers
                ],
                "spectators": [
                    {
                        "id": str(p.id),
                        "name": p.user_name,
                    }
                    for p in spectators
                ],
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "is_host": is_host,
                "is_spectator": is_spectator,
            },
        )

    @get("/rooms/{room_id:uuid}/game")
    async def game_screen(
        self,
        room_id: UUID,
        game_service: GameService,
        auth_service: DatabaseAuthService,
        request: Request,
    ) -> Template:
        """Render the active game screen.

        Args:
            room_id: The room UUID.
            game_service: Game service instance.
            auth_service: Auth service instance.
            request: The request object.

        Returns:
            Rendered game template.
        """
        room = game_service.get_room(room_id)
        user_id = request.cookies.get("user_id", "")

        # Get auth user ID if logged in
        auth_user_id = None
        session_id = request.cookies.get(auth_service._config.session_cookie_name)
        if session_id:
            session = await auth_service.get_session(session_id)
            if session and session.user_id:
                auth_user_id = str(session.user_id)

        # Find current player
        current_player = next((p for p in room.players if p.user_id == user_id), None)

        # Check if current user is drawer
        is_drawing = False
        current_word = ""
        if room.current_round and current_player:
            is_drawing = room.current_round.drawer_id == current_player.id
            if is_drawing:
                current_word = room.current_round.word

        # Check debug mode
        is_debug = getattr(request.app, "debug", False)
        debug_word = ""
        if is_debug and room.metadata.get("debug_mode") and room.current_round:
            debug_word = room.current_round.word or ""

        # Check if current user is a spectator
        is_spectator = current_player.is_spectator if current_player else False

        return Template(
            template_name="canvas_clash_game.html",
            context={
                "room": {
                    "id": str(room.id),
                    "code": room.room_code,
                },
                "game": {
                    "current_round": room.current_round_number,
                    "total_rounds": room.settings.rounds_per_game,
                    # Use room.players (all players) not active_players() which filters by connection state
                    # Players may briefly show as disconnected during page transition
                    "players": [
                        {
                            "id": str(p.id),
                            "name": p.user_name,
                            "score": p.score,
                            "is_drawing": room.current_round and room.current_round.drawer_id == p.id,
                            "is_spectator": p.is_spectator,
                        }
                        for p in room.players
                        if not p.is_spectator  # Only show non-spectators in player list
                    ],
                    "spectators": [
                        {
                            "id": str(p.id),
                            "name": p.user_name,
                        }
                        for p in room.players
                        if p.is_spectator
                    ],
                },
                "user_id": user_id,
                "auth_user_id": auth_user_id,
                "is_drawing": is_drawing,
                "is_spectator": is_spectator,
                "current_word": current_word,
                "debug_mode": is_debug and room.metadata.get("debug_mode", False),
                "debug_word": debug_word,
            },
        )

    @get("/rooms/{room_id:uuid}/partials/round_end")
    async def round_end_partial(
        self,
        room_id: UUID,
        word: str,
        round_num: int,
        game_service: GameService,
    ) -> Template:
        """Render round end overlay partial.

        Args:
            room_id: The room UUID.
            word: The word that was drawn.
            round_num: The round number.
            game_service: Game service instance.

        Returns:
            Rendered partial template.
        """
        room = game_service.get_room(room_id)

        # Get the completed round from history (after end_round, current_round is moved to history)
        completed_round = None
        drawer_id = None
        if room.round_history:
            # Find the round matching round_num
            for r in room.round_history:
                if r.round_number == round_num:
                    completed_round = r
                    drawer_id = r.drawer_id
                    break
            # Fallback to last round if not found
            if not completed_round:
                completed_round = room.round_history[-1]
                drawer_id = completed_round.drawer_id

        # Get drawer name
        drawer_name = "Unknown"
        if drawer_id:
            drawer = room.get_player(drawer_id)
            if drawer:
                drawer_name = drawer.user_name

        # Build round scores with per-round points from the completed round's guesses
        round_scores = []
        leaderboard = room.get_leaderboard()

        # Get round-specific points from guesses
        round_points: dict[str, int] = {}
        guess_times: dict[str, float] = {}
        if completed_round:
            for guess in completed_round.guesses:
                if guess.points_awarded > 0:
                    player_id_str = str(guess.player_id)
                    round_points[player_id_str] = guess.points_awarded
                    guess_times[player_id_str] = guess.time_elapsed

        for player, score in leaderboard:
            player_id_str = str(player.id)
            is_drawer = drawer_id and drawer_id == player.id
            points_earned = round_points.get(player_id_str, 0)

            # Drawer gets bonus points based on guessers
            if is_drawer and completed_round:
                drawer_bonus = int(sum(round_points.values()) * room.settings.drawer_points_multiplier)
                points_earned = drawer_bonus

            round_scores.append(
                {
                    "name": player.user_name,
                    "points_earned": points_earned,
                    "total_score": score,
                    "guess_time": guess_times.get(player_id_str),
                    "is_drawer": is_drawer,
                }
            )

        is_final = room.current_round_number >= room.settings.rounds_per_game

        return Template(
            template_name="partials/canvas_clash_round_end.html",
            context={
                "room_id": str(room_id),
                "word": word,
                "round_number": round_num,
                "drawer_name": drawer_name,
                "round_scores": round_scores,
                "leaderboard": [{"name": p.user_name, "total_score": s} for p, s in leaderboard[:3]],
                "is_final_round": is_final,
            },
        )

    @get("/rooms/{room_id:uuid}/partials/game_over")
    async def game_over_partial(
        self,
        room_id: UUID,
        game_service: GameService,
    ) -> Template:
        """Render game over overlay partial.

        Args:
            room_id: The room UUID.
            game_service: Game service instance.

        Returns:
            Rendered partial template.
        """
        from scribbl_py.game.models import GuessResult

        room = game_service.get_room(room_id)
        leaderboard = room.get_leaderboard()

        # Calculate per-player statistics from round history
        player_stats: dict[str, dict] = {}
        for player, _ in leaderboard:
            player_stats[str(player.id)] = {
                "words_guessed": 0,
                "total_guess_time": 0.0,
                "guess_count": 0,
            }

        # Aggregate stats from all rounds
        for round_data in room.round_history:
            for guess in round_data.guesses:
                if guess.result == GuessResult.CORRECT and guess.points_awarded > 0:
                    player_id = str(guess.player_id)
                    if player_id in player_stats:
                        player_stats[player_id]["words_guessed"] += 1
                        player_stats[player_id]["total_guess_time"] += guess.time_elapsed
                        player_stats[player_id]["guess_count"] += 1

        # Build final scores with stats
        final_scores = []
        for player, score in leaderboard:
            player_id = str(player.id)
            stats = player_stats.get(player_id, {"words_guessed": 0, "guess_count": 0, "total_guess_time": 0})

            avg_time = None
            if stats["guess_count"] > 0:
                avg_time = stats["total_guess_time"] / stats["guess_count"]

            final_scores.append(
                {
                    "name": player.user_name,
                    "score": score,
                    "words_guessed": stats["words_guessed"],
                    "avg_guess_time": avg_time,
                }
            )

        # Count total correct guesses
        total_correct_guesses = sum(1 for r in room.round_history for g in r.guesses if g.result == GuessResult.CORRECT)

        return Template(
            template_name="partials/canvas_clash_game_over.html",
            context={
                "room_id": str(room_id),
                "final_scores": final_scores,
                "game_stats": {
                    "total_rounds": room.current_round_number,
                    "total_guesses": total_correct_guesses,
                },
            },
        )

    @post("/debug/test-game")
    async def create_debug_game(
        self,
        game_service: GameService,
        request: Request,
    ) -> dict[str, Any]:
        """Create a debug test game with simulated bot players.

        Only available when the app is running in debug mode.
        Creates a room with short round times and 2 bot players that will
        automatically guess the word.

        Args:
            game_service: Game service instance.
            request: The request object.

        Returns:
            Room details including the room ID for redirection.
        """
        from scribbl_py.game.models import GameSettings

        # Only allow in debug mode
        if not getattr(request.app, "debug", False):
            return Response(
                content={"error": "Debug mode not enabled"},
                status_code=403,
            )

        # Get user info
        user_id = request.cookies.get("user_id", str(UUID(int=0)))

        # Create settings with short round times for testing
        settings = GameSettings(
            round_duration_seconds=10,  # Very short rounds for testing
            rounds_per_game=2,  # Just 2 rounds to test game end
            max_players=8,
        )

        # Create room
        room = game_service.create_room(
            host_user_id=user_id,
            host_name="Debug Host",
            room_name="Debug Test Game",
            settings=settings,
        )

        # Add simulated bot players
        bot1 = game_service.join_room(room.id, "bot-player-1", "Bot Alice")
        bot2 = game_service.join_room(room.id, "bot-player-2", "Bot Bob")

        # Mark bots for auto-guessing (store in room metadata)
        room.metadata["debug_bots"] = [str(bot1.id), str(bot2.id)]
        room.metadata["debug_mode"] = True

        return {
            "room_id": str(room.id),
            "room_code": room.room_code,
            "bots": [
                {"id": str(bot1.id), "name": bot1.user_name},
                {"id": str(bot2.id), "name": bot2.user_name},
            ],
            "settings": {
                "round_duration": settings.round_duration_seconds,
                "rounds_per_game": settings.rounds_per_game,
            },
        }
