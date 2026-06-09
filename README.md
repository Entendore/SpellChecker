# Advanced NLP Text Corrector

A multi-language spell checker and grammar corrector with an interactive PySide6 GUI. Powered by BK-Trees, n-gram language models, beam search, and Monte-Carlo tree search.

## Features

**Core NLP Engine**
- Spell checking via Levenshtein distance and BK-Tree fuzzy matching.
- Grammar correction using regex-based language rules.
- Confusion pair detection (e.g., their/there, affect/effect).
- Context-aware suggestions using bigram and trigram frequency models.
- Three correction modes: Interactive, Beam Search, and MCTS.

**GUI and UX**
- Dark and Light theme toggle.
- Live error highlighting (spelling, grammar, confusion) in the editor.
- Real-time word, character, and unknown-word statistics.
- Color-coded error table rows by decision state (accepted, ignored, custom).
- Add-to-dictionary button per error.
- Double-click error row to jump and select in the editor.
- Right-click context menu with suggestions.
- Diff-highlight view in the auto-corrected tab.
- Next and previous error navigation.
- Save, export, and copy-corrected buttons.
- Search filter in the user-dictionary list.
- Keyboard shortcuts (F7, Ctrl+Enter, Ctrl+S).
- Confirmation prompts and auto-recheck after applying corrections.

## Quick Start

1. **Install dependencies**
   ```bash
   pip install PySide6
   ```

2. **Initialize the databases**
   Creates the `database/` folder and seeds each language with a small built-in vocabulary.
   ```bash
   python init_databases.py
   ```

3. **Download real dictionaries (Recommended)**
   Downloads ~50,000 word-frequency entries per language from the FrequencyWords project, plus curated grammar rules and confusion pairs. Requires an internet connection.
   ```bash
   python download_dictionaries.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

## How It Works

**Spell Checking Pipeline**
Input text is tokenized. Known words are checked against confusion pairs. Unknown words are queried against a BK-Tree (max edit distance 2) to generate candidates, which are then ranked by n-gram frequency.

**Grammar Rules**
Regex patterns matched against the full text with priority ordering and replacement templates. Rules currently cover:
- English: your/you're, its/it's, a/an, repeated words, could of, contractions.
- Spanish: hay/ay, más/mas, aún/aun, qué/que, sé/se.
- German: das/dass, seit/seid, wider/wieder, muss spelling.
- French: a/à, ou/où, ce/se, la/là, du/dû, sur/sûr.
- Italian: e/è, li/lì, la/là, se/sé, ne/né.
- All languages: Repeated word detection.

**Confusion Pairs**
Homophones and commonly confused words are flagged even when both forms are valid dictionary entries, providing context hints and explanatory messages.

**Database Schema**
Each language uses an isolated SQLite database (`database/{lang}.db`).

| Table | Purpose |
|-------|---------|
| `metadata` | Schema version, last download date, word count |
| `dictionary` | Words, frequency, user flag |
| `bigrams` | Two-word co-occurrence counts |
| `trigrams` | Three-word co-occurrence counts |
| `grammar_rules` | Regex patterns, messages, replacements |
| `confusion_pairs` | Wrong/correct pairs with context hints |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `F7` | Run spell and grammar check |
| `Ctrl+Enter` | Apply accepted corrections |
| `Ctrl+S` | Save text to file |
| `Ctrl+Shift+X` | Clear all |

## Adding Custom Words

- Click the add-to-dictionary button next to any error to add the original word to the user dictionary.
- Use the User Dictionary tab to add or remove words manually.
- Import entire corpora via the Import Corpus button (plain text files).
