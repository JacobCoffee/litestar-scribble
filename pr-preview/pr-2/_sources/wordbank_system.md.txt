# WordBank System Documentation

The WordBank system provides comprehensive word selection and validation functionality for the Skribbl Mode drawing game.

## Overview

The WordBank manages:
- **Word Selection**: Random word selection from categorized lists
- **Difficulty Levels**: Easy, Medium, and Hard word categories
- **Custom Words**: Support for loading custom word lists
- **Guess Validation**: Intelligent matching with close-guess detection
- **Session Management**: Track used words per game to avoid repetition

## Features

### Word Categories

The system includes 10 built-in categories with 600+ words:

- **Animals**: Common and exotic animals (e.g., cat, elephant, platypus)
- **Objects**: Everyday items and tools (e.g., chair, telescope, abacus)
- **Actions**: Verbs and activities (e.g., run, meditate, somersault)
- **Places**: Locations and landmarks (e.g., park, pyramid, acropolis)
- **Food**: Cuisine from around the world (e.g., pizza, ratatouille, kimchi)
- **Sports**: Athletic activities (e.g., soccer, curling, pentathlon)
- **Movies**: Film-related concepts (e.g., superhero, plot twist, allegory)
- **Nature**: Natural phenomena (e.g., waterfall, aurora borealis, ecosystem)
- **Technology**: Tech terms (e.g., smartphone, blockchain, quantum computing)
- **Professions**: Occupations (e.g., teacher, archaeologist, anesthesiologist)

### Difficulty Levels

Each category has three difficulty levels:

- **Easy**: Common, simple words (20+ words per category)
- **Medium**: Moderately challenging words (20+ words per category)
- **Hard**: Complex, specialized terms (20+ words per category)

### Close Guess Detection

The system intelligently detects "close" guesses using multiple algorithms:

1. **Sequence Similarity**: Uses difflib's SequenceMatcher (default 75% threshold)
2. **Plural/Singular Variations**: Detects simple plurals (s, es, ies/y)
3. **Single Character Differences**: Catches typos (substitution, insertion, deletion)
4. **Common Prefix Detection**: Identifies partial matches for longer words

## Usage

### Basic Usage

```python
from uuid import uuid4
from scribbl_py.game import WordBankService

# Create word bank instance
word_bank = WordBankService()

# Start a game session
game_id = uuid4()

# Get 3 random word options for the drawer
options = word_bank.get_word_options(game_id, count=3)
# Example: ['elephant', 'pizza', 'running']

# Drawer selects a word
selected_word = options[0]

# Check player guesses
result = word_bank.check_guess(selected_word, "elephant")
# Returns: GuessResult.CORRECT

result = word_bank.check_guess(selected_word, "elephent")
# Returns: GuessResult.CLOSE

result = word_bank.check_guess(selected_word, "cat")
# Returns: GuessResult.WRONG
```

### Category and Difficulty Filtering

```python
from scribbl_py.game import DifficultyLevel, WordCategory

# Get words from specific category
animals = word_bank.get_word_options(
    game_id,
    count=3,
    category=WordCategory.ANIMALS
)

# Get words of specific difficulty
easy_words = word_bank.get_word_options(
    game_id,
    count=3,
    difficulty=DifficultyLevel.EASY
)

# Combine filters
hard_food = word_bank.get_word_options(
    game_id,
    count=3,
    category=WordCategory.FOOD,
    difficulty=DifficultyLevel.HARD
)
```

### Custom Words

#### From Dictionary

```python
custom_words = {
    WordCategory.OBJECTS: {
        DifficultyLevel.EASY: ["lightsaber", "pokeball"],
        DifficultyLevel.MEDIUM: ["portal gun", "time turner"],
    }
}

# Merge with existing words
word_bank.load_custom_words(custom_words, merge=True)

# Replace existing words
word_bank.load_custom_words(custom_words, merge=False)
```

#### From File

```python
# Load words from text file (one word per line)
word_bank.load_custom_words_from_file(
    "my_words.txt",
    category=WordCategory.OBJECTS,
    difficulty=DifficultyLevel.MEDIUM,
    merge=True
)
```

### Game Session Management

```python
# Words are automatically tracked per game
game1 = uuid4()
game2 = uuid4()

# Each game has separate word tracking
words1 = word_bank.get_word_options(game1, count=5)
words2 = word_bank.get_word_options(game2, count=5)
# words1 and words2 can overlap

# Words won't repeat within the same game
more_words1 = word_bank.get_word_options(game1, count=5)
# Guaranteed to be different from words1

# Reset word tracking for new game
word_bank.reset_game_words(game1)
# Now words can be reused
```

### Configuration

#### Similarity Threshold

```python
# Stricter matching (0.0 - 1.0, default 0.75)
word_bank = WordBankService(similarity_threshold=0.9)

# More lenient matching
word_bank = WordBankService(similarity_threshold=0.6)
```

## API Reference

### WordBankService

#### `__init__(*, word_lists=None, similarity_threshold=0.75)`

Create a new WordBank instance.

**Parameters:**
- `word_lists`: Optional custom word lists (defaults to built-in lists)
- `similarity_threshold`: Threshold for close match detection (0.0-1.0)

#### `get_word_options(game_id, *, count=3, difficulty=None, category=None)`

Get random word options for a round.

**Parameters:**
- `game_id`: UUID of the game session
- `count`: Number of words to return (default 3)
- `difficulty`: Optional DifficultyLevel filter
- `category`: Optional WordCategory filter

**Returns:** List of word strings

**Raises:**
- `InvalidCategoryError`: Invalid category specified
- `InsufficientWordsError`: Not enough words available

#### `check_guess(word, guess)`

Check if a guess matches the target word.

**Parameters:**
- `word`: The target word
- `guess`: The player's guess

**Returns:** `GuessResult` enum value:
- `CORRECT`: Exact match
- `CLOSE`: Close match (trigger hint)
- `WRONG`: No match

#### `load_custom_words(words, *, merge=True)`

Load custom words from dictionary.

**Parameters:**
- `words`: Dictionary mapping categories/difficulties to word lists
- `merge`: If True, merge with existing words; if False, replace

#### `load_custom_words_from_file(file_path, category, difficulty, *, merge=True)`

Load custom words from a text file.

**Parameters:**
- `file_path`: Path to text file (one word per line)
- `category`: WordCategory to assign words to
- `difficulty`: DifficultyLevel to assign words to
- `merge`: If True, merge with existing words; if False, replace

**Raises:**
- `FileNotFoundError`: File doesn't exist
- `InvalidCategoryError`: Invalid category

#### `reset_game_words(game_id)`

Reset used word tracking for a game session.

**Parameters:**
- `game_id`: UUID of the game session

#### `get_word_count(*, category=None, difficulty=None)`

Get total number of available words.

**Parameters:**
- `category`: Optional category filter
- `difficulty`: Optional difficulty filter

**Returns:** Integer count of words

## Close Guess Algorithm

The close guess detection uses multiple heuristics to determine if a guess is "close enough" to warrant a hint:

### 1. Sequence Similarity
Uses Python's `difflib.SequenceMatcher` to calculate similarity ratio:
```python
similarity = SequenceMatcher(None, word, guess).ratio()
if similarity >= threshold:  # default 0.75
    return CLOSE
```

### 2. Plural/Singular Detection
Handles common pluralization patterns:
- Simple 's': cat → cats
- 'es' suffix: box → boxes
- 'ies/y' variation: berry → berries

### 3. Single Character Difference
Detects typos with one character different:
- **Substitution**: cat → bat
- **Insertion**: cat → coat
- **Deletion**: coat → cat

### 4. Common Prefix
For longer words (4+ chars), checks if 70% of the word matches:
```python
min_prefix = int(len(word) * 0.7)
if word[:min_prefix] == guess[:min_prefix]:
    return CLOSE
```

## Best Practices

### For Game Implementation

1. **Create one WordBank instance per game server** (reuse across games)
2. **Use game_id to track word usage** per session
3. **Reset game words** when starting a new game
4. **Handle GuessResult.CLOSE** by showing "Player X is close!" message
5. **Filter by category/difficulty** based on game settings

### For Custom Words

1. **Keep custom words lowercase** for consistency
2. **Avoid very short words** (< 3 characters) for better gameplay
3. **Test close match detection** for new word lists
4. **Organize by difficulty** appropriately

### Performance

- WordBank uses deep copy for thread safety
- Word selection is O(n) where n = available words
- Close guess detection is O(m) where m = word length
- Typical performance: < 1ms for word selection, < 0.1ms for guess checking

## Examples

See `examples/wordbank_example.py` for a comprehensive demonstration of all features.

## Testing

Run the test suite:
```bash
uv run pytest tests/test_game_wordbank.py -v
```

Tests cover:
- Initialization and configuration
- Word selection and filtering
- Guess checking (all match types)
- Custom word loading
- Game session management
- Word list quality assurance
