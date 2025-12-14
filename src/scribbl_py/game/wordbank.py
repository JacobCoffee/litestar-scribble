"""Word bank system for CanvasClash mode game."""

from __future__ import annotations

import copy
import random
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from scribbl_py.game.exceptions import InsufficientWordsError, InvalidCategoryError
from scribbl_py.game.types import DifficultyLevel, WordCategory
from scribbl_py.game.word_lists import DEFAULT_WORD_LISTS

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from uuid import UUID

    from scribbl_py.game.models import GuessResult


class WordBank:
    """Manages word selection and validation for drawing games.

    Provides functionality for:
    - Selecting random words from different categories and difficulty levels
    - Loading custom word lists from files or dictionaries
    - Tracking used words per game session to avoid repetition
    - Detecting close guesses using similarity algorithms

    Attributes:
        word_lists: Dictionary mapping categories and difficulties to word lists.
        used_words: Set of word IDs that have been used in the current game session.
        similarity_threshold: Threshold for close guess detection (0.0-1.0).
    """

    def __init__(
        self,
        *,
        word_lists: dict[WordCategory, dict[DifficultyLevel, list[str]]] | None = None,
        similarity_threshold: float = 0.75,
    ) -> None:
        """Initialize the word bank.

        Args:
            word_lists: Custom word lists organized by category and difficulty.
                       If None, uses default word lists.
            similarity_threshold: Minimum similarity ratio (0.0-1.0) for close matches.
                                Default is 0.75 (75% similar).
        """
        self.word_lists = word_lists if word_lists is not None else copy.deepcopy(DEFAULT_WORD_LISTS)
        self.used_words: dict[UUID, set[str]] = {}
        self.similarity_threshold = max(0.0, min(1.0, similarity_threshold))

    def get_word_options(
        self,
        game_id: UUID,
        *,
        count: int = 3,
        difficulty: DifficultyLevel | None = None,
        category: WordCategory | None = None,
        custom_words: list[str] | None = None,
        custom_words_only: bool = False,
    ) -> list[str]:
        """Get random word options for a drawing round.

        Selects words that haven't been used yet in the current game session.
        If specific category/difficulty aren't provided, randomly selects from all available.
        Custom words from the game host are included in the pool with higher priority.

        Args:
            game_id: Unique identifier for the game session.
            count: Number of word options to return (default 3).
            difficulty: Optional difficulty level to filter by.
            category: Optional category to filter by.
            custom_words: Optional list of custom words from the game host.
            custom_words_only: If True, only use custom words (ignore default word bank).

        Returns:
            List of randomly selected words.

        Raises:
            InvalidCategoryError: If the specified category doesn't exist.
            InvalidDifficultyError: If the specified difficulty doesn't exist.
            InsufficientWordsError: If not enough unused words are available.
        """
        # Debug logging
        logger.info(
            "WordBank.get_word_options called",
            game_id=str(game_id),
            custom_words=custom_words,
            custom_words_only=custom_words_only,
            count=count,
        )

        # Validate inputs
        if category is not None and category not in self.word_lists:
            raise InvalidCategoryError(str(category))

        used = self.used_words.get(game_id, set())

        # Custom words only mode - ignore default word bank
        if custom_words_only and custom_words:
            logger.info("Using CUSTOM WORDS ONLY mode", custom_words=custom_words)
            # Filter to non-empty custom words
            valid_custom = [w for w in custom_words if w]
            available_custom = [w for w in valid_custom if w not in used]

            if len(available_custom) >= count:
                # Enough fresh words available
                selected = random.sample(available_custom, count)
            elif len(valid_custom) >= count:
                # Not enough fresh words, but can reuse some
                # Prioritize unused words, then fill with used ones
                logger.info(
                    "Reusing custom words due to limited pool",
                    available=len(available_custom),
                    total=len(valid_custom),
                    needed=count,
                )
                # Take all available unused words first
                selected = list(available_custom)
                # Fill remaining with random used words
                used_words = [w for w in valid_custom if w in used]
                remaining = count - len(selected)
                if remaining > 0 and used_words:
                    selected.extend(random.sample(used_words, min(remaining, len(used_words))))
                random.shuffle(selected)
            else:
                # Not enough words even with reuse
                raise InsufficientWordsError(count, len(valid_custom))

            # Don't mark words as used here - only mark when actually selected for drawing
            logger.info("Selected custom words", selected=selected)
            return selected

        # Get available word pool from default word lists
        available_words = self._get_available_words(game_id, category=category, difficulty=difficulty)

        # Add custom words that haven't been used (mixed mode)
        if custom_words:
            available_custom = [w for w in custom_words if w and w not in used]
            # Include at least one custom word if available
            if available_custom and count > 1:
                # Select 1 custom word and the rest from default
                custom_selection = random.sample(available_custom, min(1, len(available_custom)))
                remaining_count = count - len(custom_selection)

                # Remove custom words from available_words to avoid duplicates
                custom_lower = {w.lower() for w in available_custom}
                available_words = [w for w in available_words if w.lower() not in custom_lower]

                if len(available_words) >= remaining_count:
                    default_selection = random.sample(available_words, remaining_count)
                    selected = custom_selection + default_selection
                    random.shuffle(selected)  # Randomize order so custom isn't always first
                else:
                    # Not enough default words, use more custom
                    all_available = available_custom + available_words
                    if len(all_available) < count:
                        raise InsufficientWordsError(count, len(all_available))
                    selected = random.sample(all_available, count)
            else:
                # No custom words available or count is 1, use standard logic
                all_available = available_custom + available_words if custom_words else available_words
                # Remove duplicates
                seen = set()
                unique_available = []
                for w in all_available:
                    if w.lower() not in seen:
                        seen.add(w.lower())
                        unique_available.append(w)

                if len(unique_available) < count:
                    raise InsufficientWordsError(count, len(unique_available))
                selected = random.sample(unique_available, count)
        else:
            if len(available_words) < count:
                raise InsufficientWordsError(count, len(available_words))
            selected = random.sample(available_words, count)

        # Don't mark words as used here - only mark when actually selected for drawing
        # The actual selected word is marked via mark_word_used() when drawer picks

        return selected

    def check_guess(self, word: str, guess: str) -> GuessResult:
        """Check if a guess matches the target word.

        Uses case-insensitive comparison and multiple similarity algorithms
        to detect exact matches, close matches, or no matches.

        Args:
            word: The target word to match against.
            guess: The player's guess.

        Returns:
            GuessResult indicating exact match, close match, or no match.
        """
        from scribbl_py.game.models import GuessResult

        # Normalize inputs
        word_normalized = word.lower().strip()
        guess_normalized = guess.lower().strip()

        # Check for exact match
        if word_normalized == guess_normalized:
            return GuessResult.CORRECT

        # Check for close match using multiple criteria
        if self._is_close_match(word_normalized, guess_normalized):
            return GuessResult.CLOSE

        return GuessResult.WRONG

    def load_custom_words(
        self,
        words: dict[WordCategory, dict[DifficultyLevel, list[str]]],
        *,
        merge: bool = True,
    ) -> None:
        """Load custom word lists from a dictionary.

        Args:
            words: Dictionary mapping categories and difficulties to word lists.
            merge: If True, merge with existing words. If False, replace entirely.
        """
        if merge:
            for category, difficulties in words.items():
                if category not in self.word_lists:
                    self.word_lists[category] = {}
                for difficulty, word_list in difficulties.items():
                    if difficulty not in self.word_lists[category]:
                        self.word_lists[category][difficulty] = []
                    # Add only new words (avoid duplicates)
                    existing = set(w.lower() for w in self.word_lists[category][difficulty])
                    new_words = [w for w in word_list if w.lower() not in existing]
                    self.word_lists[category][difficulty].extend(new_words)
        else:
            self.word_lists = words

    def load_custom_words_from_file(
        self,
        file_path: str | Path,
        category: WordCategory,
        difficulty: DifficultyLevel,
        *,
        merge: bool = True,
    ) -> None:
        """Load custom words from a text file (one word per line).

        Args:
            file_path: Path to the text file containing words.
            category: Category to assign the words to.
            difficulty: Difficulty level to assign the words to.
            merge: If True, merge with existing words. If False, replace for this category/difficulty.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            InvalidCategoryError: If the category doesn't exist in word lists.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Word file not found: {file_path}")

        if category not in self.word_lists:
            raise InvalidCategoryError(str(category))

        # Read and clean words from file
        with path.open() as f:
            words = [line.strip() for line in f if line.strip()]

        # Merge or replace
        if merge:
            if difficulty not in self.word_lists[category]:
                self.word_lists[category][difficulty] = []
            existing = set(w.lower() for w in self.word_lists[category][difficulty])
            new_words = [w for w in words if w.lower() not in existing]
            self.word_lists[category][difficulty].extend(new_words)
        else:
            self.word_lists[category][difficulty] = words

    def mark_word_used(self, game_id: UUID, word: str) -> None:
        """Mark a word as used for a game session.

        Called when the drawer actually selects a word to draw.

        Args:
            game_id: Unique identifier for the game session.
            word: The word that was selected.
        """
        if game_id not in self.used_words:
            self.used_words[game_id] = set()
        self.used_words[game_id].add(word)
        logger.debug("Marked word as used", game_id=str(game_id), word=word)

    def reset_game_words(self, game_id: UUID) -> None:
        """Reset the used words tracking for a specific game.

        Args:
            game_id: Unique identifier for the game session.
        """
        if game_id in self.used_words:
            del self.used_words[game_id]

    def get_word_count(
        self,
        *,
        category: WordCategory | None = None,
        difficulty: DifficultyLevel | None = None,
    ) -> int:
        """Get the total number of available words.

        Args:
            category: Optional category to filter by.
            difficulty: Optional difficulty to filter by.

        Returns:
            Total count of words matching the filters.
        """
        total = 0
        categories = [category] if category else list(self.word_lists.keys())

        for cat in categories:
            if cat not in self.word_lists:
                continue
            difficulties = [difficulty] if difficulty else list(self.word_lists[cat].keys())
            for diff in difficulties:
                if diff in self.word_lists[cat]:
                    total += len(self.word_lists[cat][diff])

        return total

    def _get_available_words(
        self,
        game_id: UUID,
        *,
        category: WordCategory | None = None,
        difficulty: DifficultyLevel | None = None,
    ) -> list[str]:
        """Get list of available (unused) words for the game.

        Args:
            game_id: Unique identifier for the game session.
            category: Optional category to filter by.
            difficulty: Optional difficulty to filter by.

        Returns:
            List of available words matching the filters.
        """
        # Determine which categories and difficulties to use
        categories = [category] if category else list(self.word_lists.keys())
        all_words: list[str] = []

        for cat in categories:
            if cat not in self.word_lists:
                continue

            difficulties = [difficulty] if difficulty else list(self.word_lists[cat].keys())
            for diff in difficulties:
                if diff in self.word_lists[cat]:
                    all_words.extend(self.word_lists[cat][diff])

        # Filter out used words
        used = self.used_words.get(game_id, set())
        available = [w for w in all_words if w not in used]

        return available

    def _is_close_match(self, word: str, guess: str) -> bool:
        """Determine if a guess is close to the target word.

        Uses multiple heuristics:
        1. Sequence similarity ratio (main metric)
        2. Common prefix/suffix detection
        3. Single character difference detection
        4. Plural/singular variations

        Args:
            word: The normalized target word.
            guess: The normalized guess.

        Returns:
            True if the guess is considered close to the word.
        """
        # Calculate sequence similarity
        similarity = SequenceMatcher(None, word, guess).ratio()
        if similarity >= self.similarity_threshold:
            return True

        # Check for plural/singular variations
        if self._is_plural_variation(word, guess):
            return True

        # Check for single character difference
        if self._is_single_char_difference(word, guess):
            return True

        # Check for common prefix (at least 70% of word)
        min_prefix_len = int(len(word) * 0.7)
        if len(word) >= 4 and len(guess) >= 4:  # Only for longer words
            if word[:min_prefix_len] == guess[:min_prefix_len]:
                return True

        return False

    def _is_plural_variation(self, word: str, guess: str) -> bool:
        """Check if word and guess are plural/singular variations.

        Args:
            word: The normalized target word.
            guess: The normalized guess.

        Returns:
            True if one is likely a plural of the other.
        """
        # Check simple 's' suffix
        if word + "s" == guess or word == guess + "s":
            return True

        # Check 'es' suffix
        if word + "es" == guess or word == guess + "es":
            return True

        # Check 'ies/y' variation (e.g., "berry" -> "berries")
        if word.endswith("y") and guess == word[:-1] + "ies":
            return True
        if guess.endswith("y") and word == guess[:-1] + "ies":
            return True

        return False

    def _is_single_char_difference(self, word: str, guess: str) -> bool:
        """Check if word and guess differ by only one character.

        Detects:
        - One character insertion
        - One character deletion
        - One character substitution

        Args:
            word: The normalized target word.
            guess: The normalized guess.

        Returns:
            True if only one character differs.
        """
        len_diff = abs(len(word) - len(guess))

        # Must be same length or differ by 1
        if len_diff > 1:
            return False

        if len_diff == 0:
            # Check for single substitution
            differences = sum(1 for w, g in zip(word, guess, strict=False) if w != g)
            return differences == 1

        # Check for single insertion/deletion
        shorter, longer = (word, guess) if len(word) < len(guess) else (guess, word)
        for i in range(len(longer)):
            # Try removing character at position i from longer word
            test = longer[:i] + longer[i + 1 :]
            if test == shorter:
                return True

        return False
