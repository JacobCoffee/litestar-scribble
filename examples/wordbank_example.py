"""Example usage of the WordBank system for Skribbl mode.

This example demonstrates:
- Creating a WordBank instance
- Selecting random word options
- Checking guesses (exact, close, and no match)
- Loading custom words
- Managing game sessions
"""

from __future__ import annotations

from uuid import uuid4

from scribbl_py.game import DifficultyLevel, GuessResult, WordBankService, WordCategory


def main() -> None:
    """Demonstrate WordBank functionality."""
    print("=== WordBank System Demo ===\n")

    # 1. Create a WordBank instance
    print("1. Creating WordBank with default word lists...")
    word_bank = WordBankService(similarity_threshold=0.75)
    print(f"   Total words available: {word_bank.get_word_count()}")
    print(
        f"   Animals (Easy): {word_bank.get_word_count(category=WordCategory.ANIMALS, difficulty=DifficultyLevel.EASY)}"
    )
    print()

    # 2. Start a game and get word options
    game_id = uuid4()
    print(f"2. Starting game {game_id}")
    print("   Getting 3 random word options for drawer...")
    options = word_bank.get_word_options(game_id, count=3)
    print(f"   Options: {options}")
    print()

    # 3. Simulate drawer selecting a word
    selected_word = options[0]
    print(f"3. Drawer selected: '{selected_word}'")
    print()

    # 4. Check various guesses
    print("4. Testing guess checking...")

    # Exact match
    result = word_bank.check_guess(selected_word, selected_word)
    print(f"   Guess '{selected_word}' -> {result}")

    # Case insensitive
    result = word_bank.check_guess(selected_word, selected_word.upper())
    print(f"   Guess '{selected_word.upper()}' -> {result}")

    # Close match (plural)
    if not selected_word.endswith("s"):
        plural = selected_word + "s"
        result = word_bank.check_guess(selected_word, plural)
        print(f"   Guess '{plural}' -> {result}")

    # Close match (typo)
    if len(selected_word) > 3:
        typo = selected_word[0] + "x" + selected_word[2:]
        result = word_bank.check_guess(selected_word, typo)
        print(f"   Guess '{typo}' -> {result}")

    # No match
    result = word_bank.check_guess(selected_word, "completely wrong")
    print(f"   Guess 'completely wrong' -> {result}")
    print()

    # 5. Get category-specific words
    print("5. Getting words from specific category...")
    animal_options = word_bank.get_word_options(
        game_id,
        count=3,
        category=WordCategory.ANIMALS,
        difficulty=DifficultyLevel.MEDIUM,
    )
    print(f"   Animals (Medium): {animal_options}")
    print()

    # 6. Load custom words
    print("6. Adding custom words...")
    custom_words = {
        WordCategory.OBJECTS: {
            DifficultyLevel.EASY: ["lightsaber", "pokeball", "portal gun"],
        }
    }
    word_bank.load_custom_words(custom_words, merge=True)
    print(f"   Added {len(custom_words[WordCategory.OBJECTS][DifficultyLevel.EASY])} custom objects")
    print()

    # 7. Demonstrate word tracking (no repeats)
    print("7. Testing word tracking (no repeats in same game)...")
    all_words = set()
    for i in range(3):
        words = word_bank.get_word_options(game_id, count=5, category=WordCategory.FOOD)
        all_words.update(words)
        print(f"   Round {i + 1}: {words}")

    print(f"   Total unique words selected: {len(all_words)}")
    print(f"   All different: {len(all_words) == 15}")
    print()

    # 8. Reset game
    print("8. Resetting game...")
    word_bank.reset_game_words(game_id)
    print("   Words can now be reused in new rounds")
    print()

    # 9. Demonstrate different difficulty levels
    print("9. Comparing difficulty levels...")
    for difficulty in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]:
        words = word_bank.get_word_options(
            game_id,
            count=3,
            category=WordCategory.TECHNOLOGY,
            difficulty=difficulty,
        )
        print(f"   {difficulty.value.upper()}: {words}")
    print()

    # 10. Demonstrate close match detection
    print("10. Testing close match detection algorithms...")
    test_cases = [
        ("elephant", "elephent", "Single char difference"),
        ("cat", "cats", "Plural variation"),
        ("berry", "berries", "Y->IES variation"),
        ("running", "runing", "Double char to single"),
        ("program", "programme", "Similar spelling"),
    ]

    for word, guess, description in test_cases:
        result = word_bank.check_guess(word, guess)
        status = "✓" if result == GuessResult.CLOSE else "✗"
        print(f"   {status} '{word}' vs '{guess}': {result} ({description})")


if __name__ == "__main__":
    main()
