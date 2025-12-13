"""Tests for room permission features (kick/ban/transfer host)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from scribbl_py.game.models import GameRoom, GameSettings, Player, PlayerState


class TestRoomKick:
    """Tests for kicking players from rooms."""

    def test_host_can_kick_player(self) -> None:
        """Test that host can kick a player."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        kicked = room.kick_player(host.id, player.id)

        assert kicked is not None
        assert kicked.id == player.id
        assert kicked.connection_state == PlayerState.LEFT

    def test_non_host_cannot_kick(self) -> None:
        """Test that non-host cannot kick players."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player1 = Player(id=uuid4(), user_id="player1", user_name="Player1")
        player2 = Player(id=uuid4(), user_id="player2", user_name="Player2")

        room.players = [host, player1, player2]
        room.host_id = host.id

        with pytest.raises(ValueError, match="Only the host can kick"):
            room.kick_player(player1.id, player2.id)

    def test_cannot_kick_host(self) -> None:
        """Test that host cannot be kicked."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        with pytest.raises(ValueError, match="Cannot kick the host"):
            room.kick_player(host.id, host.id)

    def test_kicked_player_can_rejoin(self) -> None:
        """Test that kicked player can rejoin the room."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        # Kick the player
        room.kick_player(host.id, player.id)

        # Player should be able to rejoin (create new player with same user_id)
        new_player = Player(id=uuid4(), user_id="player123", user_name="Player")
        room.add_player(new_player)

        assert new_player in room.players


class TestRoomBan:
    """Tests for banning players from rooms."""

    def test_host_can_ban_player(self) -> None:
        """Test that host can ban a player."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        banned = room.ban_player(host.id, player.id)

        assert banned is not None
        assert banned.id == player.id
        assert banned.connection_state == PlayerState.LEFT
        assert "player123" in room.banned_user_ids

    def test_non_host_cannot_ban(self) -> None:
        """Test that non-host cannot ban players."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player1 = Player(id=uuid4(), user_id="player1", user_name="Player1")
        player2 = Player(id=uuid4(), user_id="player2", user_name="Player2")

        room.players = [host, player1, player2]
        room.host_id = host.id

        with pytest.raises(ValueError, match="Only the host can ban"):
            room.ban_player(player1.id, player2.id)

    def test_cannot_ban_host(self) -> None:
        """Test that host cannot be banned."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        with pytest.raises(ValueError, match="Cannot ban the host"):
            room.ban_player(host.id, host.id)

    def test_banned_player_cannot_rejoin(self) -> None:
        """Test that banned player cannot rejoin the room."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        # Ban the player
        room.ban_player(host.id, player.id)

        # Player should NOT be able to rejoin
        new_player = Player(id=uuid4(), user_id="player123", user_name="Player")
        with pytest.raises(ValueError, match="banned"):
            room.add_player(new_player)

    def test_unban_player(self) -> None:
        """Test that host can unban a player."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        # Ban then unban
        room.ban_player(host.id, player.id)
        assert "player123" in room.banned_user_ids

        result = room.unban_player(host.id, "player123")
        assert result is True
        assert "player123" not in room.banned_user_ids

        # Player should now be able to rejoin
        new_player = Player(id=uuid4(), user_id="player123", user_name="Player")
        room.add_player(new_player)
        assert new_player in room.players


class TestTransferHost:
    """Tests for transferring host privileges."""

    def test_host_can_transfer(self) -> None:
        """Test that host can transfer privileges."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")

        room.players = [host, player]
        room.host_id = host.id

        result = room.transfer_host(host.id, player.id)

        assert result is True
        assert not host.is_host
        assert player.is_host
        assert room.host_id == player.id

    def test_non_host_cannot_transfer(self) -> None:
        """Test that non-host cannot transfer privileges."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player1 = Player(id=uuid4(), user_id="player1", user_name="Player1")
        player2 = Player(id=uuid4(), user_id="player2", user_name="Player2")

        room.players = [host, player1, player2]
        room.host_id = host.id

        with pytest.raises(ValueError, match="Only the host can transfer"):
            room.transfer_host(player1.id, player2.id)

    def test_cannot_transfer_to_disconnected(self) -> None:
        """Test that cannot transfer to disconnected player."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(
            id=uuid4(),
            user_id="player123",
            user_name="Player",
            connection_state=PlayerState.DISCONNECTED,
        )

        room.players = [host, player]
        room.host_id = host.id

        with pytest.raises(ValueError, match="disconnected"):
            room.transfer_host(host.id, player.id)

    def test_cannot_transfer_to_spectator(self) -> None:
        """Test that cannot transfer to spectator."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        spectator = Player(
            id=uuid4(),
            user_id="spectator123",
            user_name="Spectator",
            is_spectator=True,
        )

        room.players = [host, spectator]
        room.host_id = host.id

        with pytest.raises(ValueError, match="spectator"):
            room.transfer_host(host.id, spectator.id)


class TestIsHost:
    """Tests for is_host method."""

    def test_is_host_returns_true_for_host(self) -> None:
        """Test is_host returns True for host."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        room.players = [host]
        room.host_id = host.id

        assert room.is_host(host.id) is True

    def test_is_host_returns_false_for_non_host(self) -> None:
        """Test is_host returns False for non-host."""
        room = GameRoom(settings=GameSettings())
        host = Player(id=uuid4(), user_id="host123", user_name="Host", is_host=True)
        player = Player(id=uuid4(), user_id="player123", user_name="Player")
        room.players = [host, player]
        room.host_id = host.id

        assert room.is_host(player.id) is False
