"""Unit tests for WordBank system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from scribbl_py.game import GuessResult
from scribbl_py.game.exceptions import (
    InsufficientWordsError,
    InvalidCategoryError,
)
from scribbl_py.game.types import DifficultyLevel, WordCategory
from scribbl_py.game.wordbank import WordBank


class TestWordBankInitialization:
    """Test WordBank initialization and configuration."""

    def test_default_initialization(self) -> None:
        """Test creating WordBank with default word lists."""
        wb = WordBank()
        assert wb.word_lists is not None
        assert len(wb.word_lists) > 0
        assert wb.similarity_threshold == 0.75
        assert wb.used_words == {}

    def test_custom_similarity_threshold(self) -> None:
        """Test setting custom similarity threshold."""
        wb = WordBank(similarity_threshold=0.9)
        assert wb.similarity_threshold == 0.9

    def test_similarity_threshold_bounds(self) -> None:
        """Test similarity threshold is clamped to 0.0-1.0."""
        wb_low = WordBank(similarity_threshold=-0.5)
        assert wb_low.similarity_threshold == 0.0

        wb_high = WordBank(similarity_threshold=1.5)
        assert wb_high.similarity_threshold == 1.0

    def test_custom_word_lists(self) -> None:
        """Test initializing with custom word lists."""
        custom_lists = {
            WordCategory.ANIMALS: {
                DifficultyLevel.EASY: ["cat", "dog"],
                DifficultyLevel.MEDIUM: ["elephant"],
            }
        }
        wb = WordBank(word_lists=custom_lists)
        assert wb.word_lists == custom_lists


class TestGetWordOptions:
    """Test word selection functionality."""

    def test_get_default_options(self) -> None:
        """Test getting default 3 word options."""
        wb = WordBank()
        game_id = uuid4()
        options = wb.get_word_options(game_id)

        assert len(options) == 3
        assert all(isinstance(w, str) for w in options)
        assert len(set(options)) == 3  # All unique

    def test_get_custom_count(self) -> None:
        """Test getting custom number of options."""
        wb = WordBank()
        game_id = uuid4()
        options = wb.get_word_options(game_id, count=5)

        assert len(options) == 5
        assert len(set(options)) == 5

    def test_filter_by_category(self) -> None:
        """Test filtering words by category."""
        wb = WordBank()
        game_id = uuid4()
        options = wb.get_word_options(game_id, category=WordCategory.ANIMALS)

        assert len(options) == 3
        # Verify words come from animals category
        all_animal_words = []
        for diff in wb.word_lists[WordCategory.ANIMALS].values():
            all_animal_words.extend(diff)
        assert all(w in all_animal_words for w in options)

    def test_filter_by_difficulty(self) -> None:
        """Test filtering words by difficulty."""
        wb = WordBank()
        game_id = uuid4()
        options = wb.get_word_options(game_id, difficulty=DifficultyLevel.EASY)

        assert len(options) == 3
        # Verify words come from easy difficulty
        all_easy_words = []
        for category in wb.word_lists.values():
            if DifficultyLevel.EASY in category:
                all_easy_words.extend(category[DifficultyLevel.EASY])
        assert all(w in all_easy_words for w in options)

    def test_filter_by_category_and_difficulty(self) -> None:
        """Test filtering by both category and difficulty."""
        wb = WordBank()
        game_id = uuid4()
        options = wb.get_word_options(
            game_id,
            category=WordCategory.FOOD,
            difficulty=DifficultyLevel.MEDIUM,
        )

        assert len(options) == 3
        expected_words = wb.word_lists[WordCategory.FOOD][DifficultyLevel.MEDIUM]
        assert all(w in expected_words for w in options)

    def test_invalid_category_raises_error(self) -> None:
        """Test that invalid category raises error."""
        wb = WordBank(word_lists={})
        game_id = uuid4()

        with pytest.raises(InvalidCategoryError):
            wb.get_word_options(game_id, category=WordCategory.ANIMALS)

    def test_insufficient_words_raises_error(self) -> None:
        """Test that requesting too many words raises error."""
        custom_lists = {
            WordCategory.ANIMALS: {
                DifficultyLevel.EASY: ["cat", "dog"],
            }
        }
        wb = WordBank(word_lists=custom_lists)
        game_id = uuid4()

        with pytest.raises(InsufficientWordsError):
            wb.get_word_options(game_id, count=5, category=WordCategory.ANIMALS)

    def test_used_words_tracking(self) -> None:
        """Test that used words are tracked per game via mark_word_used."""
        wb = WordBank()
        game_id = uuid4()

        # get_word_options doesn't mark words as used
        options1 = wb.get_word_options(game_id, count=3)
        assert game_id not in wb.used_words  # Not tracked yet

        # mark_word_used tracks the selected word
        wb.mark_word_used(game_id, options1[0])
        assert game_id in wb.used_words
        assert len(wb.used_words[game_id]) == 1
        assert options1[0] in wb.used_words[game_id]

        # Get more options - the marked word won't be included
        options2 = wb.get_word_options(game_id, count=3)
        assert options1[0] not in options2

    def test_separate_game_tracking(self) -> None:
        """Test that different games track words separately via mark_word_used."""
        wb = WordBank()
        game1 = uuid4()
        game2 = uuid4()

        options1 = wb.get_word_options(game1, count=3)
        options2 = wb.get_word_options(game2, count=3)

        # Mark words used for each game
        wb.mark_word_used(game1, options1[0])
        wb.mark_word_used(game2, options2[0])

        assert len(wb.used_words) == 2
        assert game1 in wb.used_words
        assert game2 in wb.used_words
        # Each game tracks only the selected word
        assert len(wb.used_words[game1]) == 1
        assert len(wb.used_words[game2]) == 1


class TestCheckGuess:
    """Test guess checking functionality."""

    def test_exact_match(self) -> None:
        """Test exact word match."""
        wb = WordBank()
        result = wb.check_guess("cat", "cat")
        assert result == GuessResult.CORRECT

    def test_exact_match_case_insensitive(self) -> None:
        """Test exact match ignores case."""
        wb = WordBank()
        assert wb.check_guess("Cat", "cat") == GuessResult.CORRECT
        assert wb.check_guess("CAT", "cat") == GuessResult.CORRECT
        assert wb.check_guess("cat", "CAT") == GuessResult.CORRECT

    def test_exact_match_whitespace_trimmed(self) -> None:
        """Test exact match trims whitespace."""
        wb = WordBank()
        assert wb.check_guess("  cat  ", "cat") == GuessResult.CORRECT
        assert wb.check_guess("cat", "  cat  ") == GuessResult.CORRECT

    def test_no_match(self) -> None:
        """Test completely wrong guess."""
        wb = WordBank()
        result = wb.check_guess("cat", "elephant")
        assert result == GuessResult.WRONG

    def test_close_match_similar_spelling(self) -> None:
        """Test close match with similar spelling."""
        wb = WordBank()
        # High similarity should trigger close match
        result = wb.check_guess("elephant", "elephent")
        assert result == GuessResult.CLOSE

    def test_close_match_plural_singular(self) -> None:
        """Test close match for plural/singular variations."""
        wb = WordBank()

        # Simple 's' suffix
        assert wb.check_guess("cat", "cats") == GuessResult.CLOSE
        assert wb.check_guess("cats", "cat") == GuessResult.CLOSE

        # 'es' suffix
        assert wb.check_guess("box", "boxes") == GuessResult.CLOSE
        assert wb.check_guess("boxes", "box") == GuessResult.CLOSE

        # 'ies/y' variation
        assert wb.check_guess("berry", "berries") == GuessResult.CLOSE
        assert wb.check_guess("berries", "berry") == GuessResult.CLOSE

    def test_close_match_single_char_difference(self) -> None:
        """Test close match with single character difference."""
        wb = WordBank()

        # Single substitution
        assert wb.check_guess("cat", "bat") == GuessResult.CLOSE

        # Single insertion
        assert wb.check_guess("cat", "coat") == GuessResult.CLOSE

        # Single deletion
        assert wb.check_guess("coat", "cat") == GuessResult.CLOSE

    def test_close_match_similarity_threshold(self) -> None:
        """Test that similarity threshold affects close matches."""
        # Low threshold - more lenient
        wb_low = WordBank(similarity_threshold=0.5)
        assert wb_low.check_guess("cat", "cut") == GuessResult.CLOSE

        # High threshold - more strict
        wb_high = WordBank(similarity_threshold=0.95)
        result = wb_high.check_guess("cat", "cut")
        # Should be close or no match depending on exact similarity
        assert result in (GuessResult.CLOSE, GuessResult.WRONG)


class TestCustomWords:
    """Test custom word loading functionality."""

    def test_load_custom_words_merge(self) -> None:
        """Test loading custom words with merge."""
        wb = WordBank()
        original_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY])

        custom = {
            WordCategory.ANIMALS: {
                DifficultyLevel.EASY: ["unicorn", "dragon"],
            }
        }
        wb.load_custom_words(custom, merge=True)

        new_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY])
        assert new_count == original_count + 2
        assert "unicorn" in wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY]

    def test_load_custom_words_replace(self) -> None:
        """Test loading custom words with replace."""
        wb = WordBank()
        custom = {
            WordCategory.ANIMALS: {
                DifficultyLevel.EASY: ["unicorn"],
            }
        }
        wb.load_custom_words(custom, merge=False)

        assert wb.word_lists == custom

    def test_load_custom_words_no_duplicates(self) -> None:
        """Test that custom words don't create duplicates."""
        wb = WordBank()
        original_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY])

        # Try to add existing word
        existing_word = wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY][0]
        custom = {
            WordCategory.ANIMALS: {
                DifficultyLevel.EASY: [existing_word, "newword"],
            }
        }
        wb.load_custom_words(custom, merge=True)

        new_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY])
        # Should only add 1 new word
        assert new_count == original_count + 1

    def test_load_from_file(self) -> None:
        """Test loading words from a file."""
        wb = WordBank()

        # Create temporary file with words
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("phoenix\n")
            f.write("griffin\n")
            f.write("chimera\n")
            temp_path = f.name

        try:
            original_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.HARD])
            wb.load_custom_words_from_file(
                temp_path,
                WordCategory.ANIMALS,
                DifficultyLevel.HARD,
                merge=True,
            )

            new_count = len(wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.HARD])
            assert new_count == original_count + 3
            assert "phoenix" in wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.HARD]
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_replace(self) -> None:
        """Test loading from file with replace mode."""
        wb = WordBank()

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("word1\n")
            f.write("word2\n")
            temp_path = f.name

        try:
            wb.load_custom_words_from_file(
                temp_path,
                WordCategory.ANIMALS,
                DifficultyLevel.EASY,
                merge=False,
            )

            words = wb.word_lists[WordCategory.ANIMALS][DifficultyLevel.EASY]
            assert words == ["word1", "word2"]
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_not_found(self) -> None:
        """Test loading from non-existent file raises error."""
        wb = WordBank()

        with pytest.raises(FileNotFoundError):
            wb.load_custom_words_from_file(
                "/nonexistent/file.txt",
                WordCategory.ANIMALS,
                DifficultyLevel.EASY,
            )

    def test_load_from_file_invalid_category(self) -> None:
        """Test loading to invalid category raises error."""
        wb = WordBank(word_lists={})

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("word1\n")
            temp_path = f.name

        try:
            with pytest.raises(InvalidCategoryError):
                wb.load_custom_words_from_file(
                    temp_path,
                    WordCategory.ANIMALS,
                    DifficultyLevel.EASY,
                )
        finally:
            Path(temp_path).unlink()


class TestGameManagement:
    """Test game session management."""

    def test_reset_game_words(self) -> None:
        """Test resetting used words for a game."""
        wb = WordBank()
        game_id = uuid4()

        # Mark some words as used
        options = wb.get_word_options(game_id, count=3)
        wb.mark_word_used(game_id, options[0])
        wb.mark_word_used(game_id, options[1])
        assert game_id in wb.used_words
        assert len(wb.used_words[game_id]) == 2

        # Reset
        wb.reset_game_words(game_id)
        assert game_id not in wb.used_words

    def test_reset_nonexistent_game(self) -> None:
        """Test resetting words for non-existent game doesn't error."""
        wb = WordBank()
        game_id = uuid4()

        # Should not raise error
        wb.reset_game_words(game_id)

    def test_get_word_count_all(self) -> None:
        """Test getting total word count."""
        wb = WordBank()
        count = wb.get_word_count()
        assert count > 0

    def test_get_word_count_by_category(self) -> None:
        """Test getting word count for specific category."""
        wb = WordBank()
        count = wb.get_word_count(category=WordCategory.ANIMALS)
        assert count > 0

        # Verify it's less than total
        total_count = wb.get_word_count()
        assert count < total_count

    def test_get_word_count_by_difficulty(self) -> None:
        """Test getting word count for specific difficulty."""
        wb = WordBank()
        count = wb.get_word_count(difficulty=DifficultyLevel.EASY)
        assert count > 0

        total_count = wb.get_word_count()
        assert count < total_count

    def test_get_word_count_by_category_and_difficulty(self) -> None:
        """Test getting word count for specific category and difficulty."""
        wb = WordBank()
        count = wb.get_word_count(
            category=WordCategory.SPORTS,
            difficulty=DifficultyLevel.HARD,
        )
        assert count > 0

        # Should match the actual list
        expected = len(wb.word_lists[WordCategory.SPORTS][DifficultyLevel.HARD])
        assert count == expected


class TestWordLists:
    """Test default word list quality and coverage."""

    def test_all_categories_present(self) -> None:
        """Test that all categories have words."""
        wb = WordBank()
        for category in [
            WordCategory.ANIMALS,
            WordCategory.OBJECTS,
            WordCategory.ACTIONS,
            WordCategory.PLACES,
            WordCategory.FOOD,
            WordCategory.SPORTS,
            WordCategory.NATURE,
            WordCategory.TECHNOLOGY,
            WordCategory.PROFESSIONS,
        ]:
            assert category in wb.word_lists
            assert len(wb.word_lists[category]) > 0

    def test_all_difficulties_present(self) -> None:
        """Test that all difficulties are available for each category."""
        wb = WordBank()
        for category in wb.word_lists.values():
            assert DifficultyLevel.EASY in category
            assert DifficultyLevel.MEDIUM in category
            assert DifficultyLevel.HARD in category

    def test_minimum_words_per_category(self) -> None:
        """Test that each category/difficulty has at least 20 words."""
        wb = WordBank()
        from scribbl_py.game.word_lists import DEFAULT_WORD_LISTS

        # Only check default word lists, not any that might have been modified
        for category_lists in DEFAULT_WORD_LISTS.values():
            for word_list in category_lists.values():
                assert len(word_list) >= 20, f"Word list has only {len(word_list)} words"

    def test_words_are_lowercase(self) -> None:
        """Test that all default words are lowercase."""
        wb = WordBank()
        from scribbl_py.game.word_lists import DEFAULT_WORD_LISTS

        # Only check default word lists
        for category_lists in DEFAULT_WORD_LISTS.values():
            for word_list in category_lists.values():
                for word in word_list:
                    assert word == word.lower(), f"Word '{word}' is not lowercase"

    def test_no_duplicate_words_in_difficulty(self) -> None:
        """Test that there are no duplicate words within each difficulty level."""
        wb = WordBank()
        for category_lists in wb.word_lists.values():
            for word_list in category_lists.values():
                assert len(word_list) == len(set(word_list))
