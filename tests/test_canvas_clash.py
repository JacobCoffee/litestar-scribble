"""Integration tests for Canvas Clash game mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scribbl_py.game.models import GameState, GuessResult
from scribbl_py.services.game import GameService

if TYPE_CHECKING:
    pass


@pytest.fixture
def game_service() -> GameService:
    """Create a fresh GameService instance for each test."""
    return GameService()


class TestGameService:
    """Test GameService functionality."""

    def test_create_room(self, game_service: GameService) -> None:
        """Test room creation."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host Player",
            room_name="Test Room",
        )

        assert room.name == "Test Room"
        assert room.room_code is not None
        assert len(room.room_code) == 6
        assert room.game_state == GameState.LOBBY
        assert len(room.players) == 1
        assert room.players[0].user_name == "Host Player"
        assert room.players[0].is_host is True

    def test_join_room(self, game_service: GameService) -> None:
        """Test joining a room."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )

        player = game_service.join_room(
            room_id=room.id,
            user_id="player-456",
            user_name="Player 2",
        )

        assert player.user_name == "Player 2"
        assert player.is_host is False
        assert len(room.players) == 2

    def test_reconnect_preserves_state(self, game_service: GameService) -> None:
        """Test that reconnecting preserves player state."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )

        # Join first time
        player1 = game_service.join_room(
            room_id=room.id,
            user_id="player-456",
            user_name="Player 2",
        )
        original_id = player1.id

        # Simulate disconnect and reconnect
        player1_reconnected = game_service.join_room(
            room_id=room.id,
            user_id="player-456",  # Same user_id
            user_name="Player 2",
        )

        # Should be same player
        assert player1_reconnected.id == original_id
        assert len(room.players) == 2  # Not duplicated

    def test_start_game_requires_min_players(self, game_service: GameService) -> None:
        """Test that starting game requires at least 2 players."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )

        with pytest.raises(Exception) as exc_info:
            game_service.start_game(room.id, room.players[0].id)

        assert "at least 2 players" in str(exc_info.value).lower()

    def test_start_game_creates_round(self, game_service: GameService) -> None:
        """Test that starting game creates first round."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        game_service.join_room(room.id, "player-456", "Player 2")

        first_round = game_service.start_game(room.id, room.players[0].id)

        assert first_round is not None
        assert first_round.round_number == 1
        assert first_round.word_options is not None
        assert len(first_round.word_options) == 3
        assert room.game_state == GameState.WORD_SELECTION

    def test_select_word_changes_state(self, game_service: GameService) -> None:
        """Test that selecting word changes game state to DRAWING."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Get drawer
        drawer = room.get_player(first_round.drawer_id)
        assert drawer is not None

        # Select word
        word = first_round.word_options[0]
        current_round = game_service.select_word(room.id, drawer.id, word)

        assert current_round.word == word
        assert room.game_state == GameState.DRAWING

    def test_guess_correct(self, game_service: GameService) -> None:
        """Test correct guess awards points."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        player2 = game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Select word
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)

        # Determine guesser (non-drawer)
        guesser = player2 if player2.id != drawer.id else room.players[0]

        # Submit correct guess
        guess, _ = game_service.submit_guess(room.id, guesser.id, word)

        assert guess.result == GuessResult.CORRECT
        assert guess.points_awarded > 0
        assert guesser.has_guessed is True

    def test_guess_wrong(self, game_service: GameService) -> None:
        """Test wrong guess doesn't award points."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        player2 = game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Select word
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)

        # Determine guesser
        guesser = player2 if player2.id != drawer.id else room.players[0]

        # Submit wrong guess
        guess, _ = game_service.submit_guess(room.id, guesser.id, "wrong_word_xyz")

        assert guess.result == GuessResult.WRONG
        assert guess.points_awarded == 0

    def test_guess_not_allowed_in_word_selection(self, game_service: GameService) -> None:
        """Test that guessing is not allowed during word selection phase."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        player2 = game_service.join_room(room.id, "player-456", "Player 2")
        game_service.start_game(room.id, room.players[0].id)

        # Don't select word - stay in WORD_SELECTION state
        assert room.game_state == GameState.WORD_SELECTION

        # Try to guess
        guesser = player2
        with pytest.raises(Exception) as exc_info:
            game_service.submit_guess(room.id, guesser.id, "some_guess")

        assert "not in drawing phase" in str(exc_info.value).lower()

    def test_drawer_cannot_guess(self, game_service: GameService) -> None:
        """Test that drawer gets DRAWER result when trying to guess."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )
        game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Select word
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)

        # Try to guess as drawer - returns DRAWER result, not exception
        guess, msg = game_service.submit_guess(room.id, drawer.id, word)

        assert guess.result == GuessResult.DRAWER
        assert "drawer cannot guess" in msg.content.lower()

    def test_get_room_by_code(self, game_service: GameService) -> None:
        """Test retrieving room by code."""
        room = game_service.create_room(
            host_user_id="host-123",
            host_name="Host",
            room_name="Test Room",
        )

        retrieved = game_service.get_room_by_code(room.room_code)
        assert retrieved.id == room.id

    def test_multiple_rooms_created(self, game_service: GameService) -> None:
        """Test creating and managing multiple rooms."""
        room1 = game_service.create_room("host-1", "Host 1", "Room 1")
        room2 = game_service.create_room("host-2", "Host 2", "Room 2")

        # Both rooms should exist and be retrievable
        assert game_service.get_room(room1.id).name == "Room 1"
        assert game_service.get_room(room2.id).name == "Room 2"

        # Start one room (needs 2 players)
        game_service.join_room(room1.id, "player-1", "Player 1")
        game_service.start_game(room1.id, room1.players[0].id)

        # Room1 should be in word selection, room2 still in lobby
        assert room1.game_state == GameState.WORD_SELECTION
        assert room2.game_state == GameState.LOBBY


class TestGameFlow:
    """Test complete game flow scenarios."""

    def test_full_round_flow(self, game_service: GameService) -> None:
        """Test a complete round from start to end."""
        # Setup
        room = game_service.create_room("host-123", "Host", "Test Room")
        player2 = game_service.join_room(room.id, "player-456", "Player 2")
        player3 = game_service.join_room(room.id, "player-789", "Player 3")

        # Start game
        first_round = game_service.start_game(room.id, room.players[0].id)
        drawer = room.get_player(first_round.drawer_id)

        # Select word
        word = first_round.word_options[1]
        game_service.select_word(room.id, drawer.id, word)
        assert room.game_state == GameState.DRAWING

        # Guessers guess
        guessers = [p for p in room.active_players() if p.id != drawer.id]

        # First guesser gets it right
        guess1, _ = game_service.submit_guess(room.id, guessers[0].id, word)
        assert guess1.result == GuessResult.CORRECT
        assert guessers[0].has_guessed is True

        # Second guesser gets it right
        guess2, _ = game_service.submit_guess(room.id, guessers[1].id, word)
        assert guess2.result == GuessResult.CORRECT

        # All guessed - round should be ready to end
        all_guessed = all(p.has_guessed for p in guessers)
        assert all_guessed is True

    def test_multiple_rooms_independent(self, game_service: GameService) -> None:
        """Test that multiple rooms operate independently."""
        room1 = game_service.create_room("host-1", "Host 1", "Room 1")
        room2 = game_service.create_room("host-2", "Host 2", "Room 2")

        game_service.join_room(room1.id, "p1", "Player 1")
        game_service.join_room(room2.id, "p2", "Player 2")

        # Start room1
        game_service.start_game(room1.id, room1.players[0].id)

        # Room2 should still be in lobby
        assert room1.game_state == GameState.WORD_SELECTION
        assert room2.game_state == GameState.LOBBY


class TestWordBank:
    """Test word bank functionality."""

    def test_word_options_are_different(self, game_service: GameService) -> None:
        """Test that word options for selection are all different."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        game_service.join_room(room.id, "player-456", "Player 2")

        first_round = game_service.start_game(room.id, room.players[0].id)

        options = first_round.word_options
        assert len(options) == len(set(options))  # All unique

    def test_word_hint_format(self, game_service: GameService) -> None:
        """Test that word hint shows correct format."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]  # Use actual word option
        game_service.select_word(room.id, drawer.id, word)

        # Hint should be underscores
        hint = room.current_round.word_hint
        assert "_" in hint


class TestRoundTransitions:
    """Test round transition functionality."""

    def test_end_round_returns_results(self, game_service: GameService) -> None:
        """Test that ending a round returns correct results."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Select word to start round
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)

        # End the round
        results = game_service.end_round(room.id)

        assert results["word"] == word
        assert results["round_number"] == 1
        assert "leaderboard" in results
        assert results["is_game_over"] is False

    def test_next_round_increments_round_number(self, game_service: GameService) -> None:
        """Test that next_round properly advances the round."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        # Complete first round
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)
        game_service.end_round(room.id)

        # Start next round
        second_round = game_service.next_round(room.id)

        assert second_round.round_number == 2
        assert second_round.word_options is not None
        assert len(second_round.word_options) == 3
        assert room.game_state == GameState.WORD_SELECTION

    def test_drawer_rotates_between_rounds(self, game_service: GameService) -> None:
        """Test that the drawer changes between rounds."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        player2 = game_service.join_room(room.id, "player-456", "Player 2")
        first_round = game_service.start_game(room.id, room.players[0].id)

        first_drawer_id = first_round.drawer_id

        # Complete first round
        drawer = room.get_player(first_round.drawer_id)
        word = first_round.word_options[0]
        game_service.select_word(room.id, drawer.id, word)
        game_service.end_round(room.id)

        # Start next round
        second_round = game_service.next_round(room.id)

        # Drawer should be different (with 2 players, it alternates)
        assert second_round.drawer_id != first_drawer_id

    def test_game_ends_after_all_rounds(self, game_service: GameService) -> None:
        """Test that game ends when all rounds are complete."""
        room = game_service.create_room("host-123", "Host", "Test Room")
        game_service.join_room(room.id, "player-456", "Player 2")

        # Reduce rounds for faster test
        room.settings.rounds_per_game = 2

        first_round = game_service.start_game(room.id, room.players[0].id)

        # Complete first round
        drawer = room.get_player(first_round.drawer_id)
        game_service.select_word(room.id, drawer.id, first_round.word_options[0])
        game_service.end_round(room.id)

        # Start and complete second round
        second_round = game_service.next_round(room.id)
        drawer = room.get_player(second_round.drawer_id)
        game_service.select_word(room.id, drawer.id, second_round.word_options[0])
        results = game_service.end_round(room.id)

        assert results["is_game_over"] is True
        assert room.game_state == GameState.GAME_OVER
