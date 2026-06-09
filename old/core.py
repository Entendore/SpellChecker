import re
import configparser
from collections import Counter, defaultdict

# spaCy model should be loaded by the application that uses this core module
# import spacy
# nlp = spacy.load("en_core_web_sm")

class AdvancedTextCorrector:
    def __init__(self, config_file='config.ini', nlp_model=None):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # --- 1. Load Dictionaries and Models ---
        self.word_counts = Counter(self._load_corpus())
        self.bigram_counts = defaultdict(Counter)
        self._build_bigram_model(self._load_corpus())
        
        # Load user's custom dictionary
        self.user_words = set()
        try:
            with open(self.config.get('paths', 'user_dictionary'), 'r') as f:
                self.user_words = set(line.strip().lower() for line in f)
        except (configparser.NoSectionError, FileNotFoundError):
            pass # Silently handle missing file

        # Combine main dictionary with user's words
        self.all_known_words = set(self.word_counts.keys()) | self.user_words
        self.N = sum(self.word_counts.values())
        
        # The spaCy model is passed in to keep the core independent
        self.nlp = nlp_model

        # --- 2. Define Grammar Rules and Contractions ---
        self.grammar_rules = self._init_grammar_rules()
        self.contractions = self._init_contractions()

    def _load_corpus(self):
        """Loads a corpus. For this example, it's hardcoded."""
        return "hello world this is a test of the spell checker it should work well enough for a demonstration we are going to the park and we will have a lot of fun there is no problem with that".lower().split()

    def _build_bigram_model(self, corpus):
        """Builds a bigram model (word -> next_word -> frequency)."""
        for i in range(len(corpus) - 1):
            prev_word, current_word = corpus[i], corpus[i+1]
            self.bigram_counts[prev_word][current_word] += 1

    def _init_grammar_rules(self):
        """Defines simple pattern-based grammar rules."""
        return [
            {
                "pattern": re.compile(r'\byour\b', re.IGNORECASE),
                "message": "Did you mean 'you're' (you are)?",
                "suggestion": "you're"
            },
            {
                "pattern": re.compile(r'\bits\b', re.IGNORECASE),
                "message": "Did you mean 'it's' (it is)?",
                "suggestion": "it's"
            }
        ]

    def _init_contractions(self):
        """Defines common English contractions."""
        return {
            "dont": "do not", "wont": "will not", "cant": "cannot", "im": "i am",
            "youre": "you are", "theyre": "they are"
        }

    def _expand_contractions(self, text):
        """Expands common contractions in a text."""
        words = text.split()
        expanded_words = [self.contractions.get(word.lower(), word) for word in words]
        return " ".join(expanded_words)

    def add_word(self, word):
        """Adds a word to the user's custom dictionary. Returns a status message."""
        word_lower = word.lower()
        if word_lower not in self.user_words:
            self.user_words.add(word_lower)
            self.all_known_words.add(word_lower)
            try:
                with open(self.config.get('paths', 'user_dictionary'), 'a') as f:
                    f.write(word_lower + '\n')
                return f"Success: '{word}' added to your dictionary."
            except (configparser.NoSectionError, IOError):
                return "Error: Could not write to user dictionary file."
        else:
            return f"Info: '{word}' is already in your dictionary."

    def correct_text(self, text):
        """Finds errors and provides suggestions in a text."""
        if not self.nlp:
            return [{"error": "spaCy model not loaded."}]

        expanded_text = self._expand_contractions(text)
        doc = self.nlp(expanded_text)
        tokens = [token.text for token in doc]
        
        errors = []

        # --- Spell Checking ---
        for i, token in enumerate(tokens):
            if token.isalpha() and token.lower() not in self.all_known_words:
                candidates = self._candidates(token.lower())
                if candidates:
                    prev_word = tokens[i-1].lower() if i > 0 else None
                    best_candidate = self._rank_candidates(token.lower(), candidates, prev_word)
                    errors.append({
                        "type": "spelling",
                        "index": i,
                        "original": token,
                        "suggestion": best_candidate
                    })

        # --- Grammar Checking ---
        for rule in self.grammar_rules:
            for match in rule["pattern"].finditer(expanded_text):
                errors.append({
                    "type": "grammar",
                    "index": match.start(),
                    "original": match.group(),
                    "suggestion": rule["suggestion"],
                    "message": rule["message"]
                })
        
        errors.sort(key=lambda x: x['index'])
        return errors

    def _candidates(self, word):
        """Generates possible spelling corrections for a word."""
        letters = 'abcdefghijklmnopqrstuvwxyz'
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [L + R[1:] for L, R in splits if R]
        transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
        replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
        inserts = [L + c + R for L, R in splits for c in letters]
        return set(deletes + transposes + replaces + inserts)

    def _rank_candidates(self, misspelled_word, candidates, prev_word):
        """Ranks candidates based on word frequency and bigram probability."""
        known_candidates = [c for c in candidates if c in self.all_known_words]
        if not known_candidates:
            return misspelled_word

        if not prev_word:
            return max(known_candidates, key=lambda w: self.word_counts.get(w, 1))
        
        best_candidate = max(known_candidates, key=lambda w: self.bigram_counts[prev_word].get(w, 0))
        
        if self.bigram_counts[prev_word].get(best_candidate, 0) == 0:
            return max(known_candidates, key=lambda w: self.word_counts.get(w, 1))
            
        return best_candidate

def apply_corrections(text, errors, user_decisions):
    """Applies the user's decisions to the original text."""
    corrected_text = text
    for error_info in sorted(errors, key=lambda x: x['index'], reverse=True):
        decision = user_decisions.get(error_info['index'])
        if decision and decision != 'ignore':
            replacement = decision
            start, end = error_info['index'], error_info['index'] + len(error_info['original'])
            corrected_text = corrected_text[:start] + replacement + corrected_text[end:]
    return corrected_text