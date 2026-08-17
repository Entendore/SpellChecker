#!/usr/bin/env python3
"""
Dictionary Downloader & Grammar Importer for NLP Text Corrector
================================================================
Downloads real word-frequency lists from public GitHub sources,
inserts comprehensive grammar rules and confusion pairs into
each language's SQLite database in ./database/

Sources:
  • Word lists:  https://github.com/hermitdave/FrequencyWords
                 (OpenSubtitles 2018, 50k words per language)
  • Grammar rules & confusion pairs: hand-curated per language

Usage:
  python download_dictionaries.py
"""

import os
import re
import logging
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from collections import Counter

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Logging — Terminal Only
# ═══════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("Downloader")

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Configuration
# ═══════════════════════════════════════════════════════════════════

DB_FOLDER = "database"
FREQ_BASE_URL = (
    "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
    "master/content/2018/{lang}/{lang}_50k.txt"
)

LANGUAGES = [
    "en", "es", "de", "fr", "it",
    "hi", "ja", "zh", "ko", "vi",
    "sw", "zu", "yo", "am", "ha",
    "nv", "qu", "chr", "oj", "iu",
]

LANG_NAMES = {
    "en": "English", "es": "Spanish", "de": "German", "fr": "French",
    "it": "Italian", "hi": "Hindi", "ja": "Japanese", "zh": "Mandarin",
    "ko": "Korean", "vi": "Vietnamese", "sw": "Swahili", "zu": "Zulu",
    "yo": "Yoruba", "am": "Amharic", "ha": "Hausa", "nv": "Navajo",
    "qu": "Quechua", "chr": "Cherokee", "oj": "Ojibwe", "iu": "Inuktitut",
}

# Languages likely available on FrequencyWords
DOWNLOAD_LANGS = {"en", "es", "de", "fr", "it", "hi", "ja", "zh", "ko",
                  "vi", "sw", "zu", "yo", "am", "ha"}

# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Schema SQL (with grammar_rules + confusion_pairs)
# ═══════════════════════════════════════════════════════════════════

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dictionary (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    word       TEXT    NOT NULL UNIQUE,
    freq       INTEGER NOT NULL DEFAULT 1,
    is_user    INTEGER NOT NULL DEFAULT 0 CHECK(is_user IN (0, 1)),
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word);
CREATE INDEX IF NOT EXISTS idx_dict_user ON dictionary(is_user);

CREATE TABLE IF NOT EXISTS bigrams (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    w1   TEXT    NOT NULL,
    w2   TEXT    NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    UNIQUE(w1, w2)
);
CREATE INDEX IF NOT EXISTS idx_bigrams_w1 ON bigrams(w1);

CREATE TABLE IF NOT EXISTS trigrams (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    w1   TEXT    NOT NULL,
    w2   TEXT    NOT NULL,
    w3   TEXT    NOT NULL,
    freq INTEGER NOT NULL DEFAULT 1,
    UNIQUE(w1, w2, w3)
);
CREATE INDEX IF NOT EXISTS idx_trigrams_w1w2 ON trigrams(w1, w2);

CREATE TABLE IF NOT EXISTS grammar_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type   TEXT    NOT NULL,
    pattern     TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    replacement TEXT    NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 0,
    enabled     INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_grammar_type ON grammar_rules(rule_type);

CREATE TABLE IF NOT EXISTS confusion_pairs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    wrong         TEXT    NOT NULL,
    correct       TEXT    NOT NULL,
    context_hint  TEXT,
    message       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_confusion_wrong ON confusion_pairs(wrong);
"""

# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Grammar Rules Per Language
# ═══════════════════════════════════════════════════════════════════

GRAMMAR_RULES = {
    # ── English ──────────────────────────────────────────────────
    "en": [
        {"rule_type": "regex", "pattern": r"\b(your)\s+(going|coming|doing|being|making|having|running|talking|walking|looking|trying|working|playing|saying|taking|getting|feeling|moving|living|giving|reading|writing|thinking|sitting|standing|sleeping|eating|drinking|watching|listening|waiting|leaving|putting|bringing|keeping|letting|setting|hitting|cutting|shutting|hurting|costing)\b",
         "message": "Did you mean 'you're' (you are)?", "replacement": r"you're \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(its)\s+(a|an|the|been|not|very|so|too|really|quite|just|also|still|already|always|never|often|probably|likely|certainly|definitely|clearly|obviously|apparently|supposed|going|been)\b",
         "message": "Did you mean 'it's' (it is)?", "replacement": r"it's \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(there)\s+(going|coming|doing|being|making|having|running|looking|trying|working|playing|taking|getting|sitting|standing|sleeping|eating|watching|waiting|leaving|coming|supposed)\b",
         "message": "Did you mean 'they're' (they are)?", "replacement": r"they're \2", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(a)\s+([aeiou]\w+)", "message": "Use 'an' before vowel sounds.", "replacement": r"an \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(an)\s+([bcdfghjklmnpqrstvwxyz]\w+)", "message": "Use 'a' before consonant sounds.", "replacement": r"a \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(could|would|should|must)\s+of\b", "message": "Use 'have' instead of 'of' after modal verbs.", "replacement": r"\1 have", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(alot)\b", "message": "'alot' is not a word. Did you mean 'a lot'?", "replacement": r"a lot", "priority": 9},
        {"rule_type": "regex", "pattern": r"\b(i)\s+\w+", "message": "Capitalize 'I' as a pronoun.", "replacement": r"I", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(cannot)\s+(help|but|stand|bear|afford)\b", "message": "Correct usage: 'cannot' + verb.", "replacement": r"cannot \2", "priority": 1},
        {"rule_type": "regex", "pattern": r"\b(im)\s+(not|sure|going|sorry|happy|glad|afraid|tired|hungry|thirsty|busy|ready|interested|concerned|aware|excited|worried|curious|impressed|confident|certain)\b",
         "message": "Did you mean 'I'm' (I am)?", "replacement": r"I'm \2", "priority": 10},
        {"rule_type": "regex", "pattern": r"\b(didnt|doesnt|dont|cant|wont|wouldnt|couldnt|shouldnt|wasnt|werent|isnt|arent|hasnt|havent|hadnt)\b",
         "message": "Missing apostrophe in contraction.", "replacement": r"\1", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(he|she|it)\s+(don't)\b", "message": "Use 'doesn't' with 3rd person singular.", "replacement": r"\1 doesn't", "priority": 7},
    ],

    # ── Spanish ──────────────────────────────────────────────────
    "es": [
        {"rule_type": "regex", "pattern": r"\b(hay)\s+(un|una|el|la|los|las|mucho|mucha|muchos|muchas|poco|poca|pocos|pocas|más|menos)\b",
         "message": "Verifique: 'hay' (verbo haber) vs 'ay' (interjección).", "replacement": r"hay \2", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(mas)\s+(que|de|el|la|los|las|un|una)\b",
         "message": "¿Quiso decir 'más' (con acento)?", "replacement": r"más \2", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(aun)\s+(cuando|que|si)\b",
         "message": "¿Quiso decir 'aún' (todavía)?", "replacement": r"aún \2", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(que)\s+(el|la|los|las|un|una|es|son|está|están|tiene|tienen|puede|pueden|ha|han|sea|sean|fue|fueron)\b",
         "message": "¿Quiso decir 'qué' (interrogativo/exclamativo)? Verifique el contexto.", "replacement": r"que \2", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(como)\s+(esta|estan|estas|esto|eso|aquel)\b",
         "message": "¿Quiso decir 'cómo' (interrogativo)?", "replacement": r"cómo \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(solo)\s+(un|una|el|la|por|con|de|en|a)\b",
         "message": "¿Quiso decir 'sólo' (solamente)?", "replacement": r"sólo \2", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Palabra repetida.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(mi)\s+(casa|familia|madre|padre|hermano|hermana|vida|trabajo|corazón|amor|nombre|país|tierra|pueblo|mundo)\b",
         "message": "¿Quiso decir 'mí' (pronombre)? Si es posesivo, es correcto.", "replacement": r"mi \2", "priority": 1},
        {"rule_type": "regex", "pattern": r"\b(tu)\s+(casa|familia|madre|padre|vida|trabajo|nombre|país)\b",
         "message": "Verifique: 'tu' (posesivo) vs 'tú' (pronombre).", "replacement": r"tu \2", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(el)\s+(es|era|está|estaba|será|sería|ha|había|puede|podía|tiene|tenía|quiere|quería|sabe|sabía|va|iba|viene|venía)\b",
         "message": "¿Quiso decir 'él' (pronombre)?", "replacement": r"él \2", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(se)\s+(el|la|los|las|un|una)\b",
         "message": "¿Quiso decir 'sé' (verbo saber)?", "replacement": r"sé \2", "priority": 3},
    ],

    # ── German ───────────────────────────────────────────────────
    "de": [
        {"rule_type": "regex", "pattern": r"\b(das)\s+(wir|ich|du|er|sie|es|ihr|Sie)\s+(machen|wollen|können|müssen|sollen|dürfen|werden|haben|sein|lassen|bringen|geben|finden|wissen|denken|glauben|sehen|kommen|gehen|brauchen|versuchen)\b",
         "message": "Meinten Sie 'dass' (Konjunktion)?", "replacement": r"dass \2 \3", "priority": 9},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Wiederholtes Wort erkannt.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(seit)\s+(\d{4}|\d+\s+(tagen|wochen|monaten|jahren|stunden|minuten))\b",
         "message": "Zeitangabe mit 'seit' korrekt.", "replacement": r"seit \2", "priority": 1},
        {"rule_type": "regex", "pattern": r"\b(seid)\s+(ihr|Ihr)\b",
         "message": "Verwechselung von 'seit' (Zeit) und 'seid' (Verb). Prüfen Sie den Kontext.",
         "replacement": r"seit ihr", "priority": 7},
        {"rule_type": "regex", "pattern": r"\b(wider)\s+(erwartung|Willen|spiegeln|richten)\b",
         "message": "Meinten Sie 'wider' oder 'wieder'?", "replacement": r"wider \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(muss)\b", "message": "Rechtschreibung: 'muss' (neue Rechtschreibung) statt 'muß'.", "replacement": r"muss", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(dem)\s+(dem)\b", "message": "Wiederholter Artikel erkannt.", "replacement": r"dem", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(der)\s+(der)\b", "message": "Wiederholter Artikel erkannt.", "replacement": r"der", "priority": 4},
    ],

    # ── French ───────────────────────────────────────────────────
    "fr": [
        {"rule_type": "regex", "pattern": r"\b(a)\s+(fait|été|vu|pris|mis|donné|dit|voulu|pu|dû|su|cru|dû|eu|venu|allé|resté|devenu|paru|semblé|né|mort)\b",
         "message": "Vérifiez: 'a' (verbe avoir) vs 'à' (préposition).", "replacement": r"a \2", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(ou)\s+(est|sont|était|sera|serait|a|ont|avait|aura|aurait|peut|doit|va|vient|faut|semble|paraît|reste)\b",
         "message": "Vouliez-vous dire 'où' (lieu/question)?", "replacement": r"où \2", "priority": 7},
        {"rule_type": "regex", "pattern": r"\b(ce)\s+(est|sont|sera|serait|était|fut|serait|semble|paraît|devient|reste|a|ont)\b",
         "message": "Vérifiez: 'ce' (démonstratif) vs 'se' (réfléchi).", "replacement": r"ce \2", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Mot répété détecté.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(la)\s+(ou|et|mais|donc|car|ni|que|qui|quand|si|comme|puisque)\b",
         "message": "Vouliez-vous dire 'là' (lieu)?", "replacement": r"là \2", "priority": 6},
        {"rule_type": "regex", "pattern": r"\b(du)\s+(fait|coup|moins|reste|même|tout)\b",
         "message": "Vérifiez: 'du' (article) vs 'dû' (participe passé).", "replacement": r"du \2", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(sur)\s+(le|la|les|un|une|ce|cette|ces|mon|ton|son|ma|ta|sa|mes|tes|ses|notre|votre|leur)\b",
         "message": "Vérifiez: 'sur' (préposition) vs 'sûr' (certain).", "replacement": r"sur \2", "priority": 2},
        {"rule_type": "regex", "pattern": r"\b(nos)\s+(amis|enfants|parents|voisins|collègues|élèves|étudiants)\b",
         "message": "Vérifiez: 'nos' (possessif) vs 'nôtre' (le nôtre).", "replacement": r"nos \2", "priority": 3},
    ],

    # ── Italian ──────────────────────────────────────────────────
    "it": [
        {"rule_type": "regex", "pattern": r"\b(e)\s+(stato|stata|stati|state|andato|andata|andati|andate|venuto|venuta|venuti|venute|detto|fatto|visto|potuto|voluto|dovuto|saputo|avuto|dato|messo|preso|scritto|letto|conosciuto)\b",
         "message": "Verificare: 'è' (verbo essere) vs 'e' (congiunzione).", "replacement": r"è \2", "priority": 8},
        {"rule_type": "regex", "pattern": r"\b(li)\s+(ho|hai|ha|abbiamo|avete|hanno|vedo|vedi|vede|vediamo|vedete|vedono|conosco|conosci|conosce|conosciamo|conoscete|conoscono)\b",
         "message": "Verificare: 'li' (pronome) vs 'lì' (avverbio di luogo).", "replacement": r"li \2", "priority": 5},
        {"rule_type": "regex", "pattern": r"\b(la)\s+(è|ha|aveva|avrà|sarebbe|può|deve|vuole|sa|sta|va|viene|dà|fa|basta|sembra|pare|resta|diventa)\b",
         "message": "Verificare: 'là' (avverbio) vs 'la' (articolo/pronome).", "replacement": r"la \2", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Parola ripetuta rilevata.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(se)\s+(io|tu|lui|lei|noi|voi|loro|ne|ci|vi)\b",
         "message": "Verificare: 'sé' (pronome riflessivo) vs 'se' (congiunzione).", "replacement": r"se \2", "priority": 4},
        {"rule_type": "regex", "pattern": r"\b(ne)\s+(ho|hai|ha|abbiamo|avete|hanno|sono|sei|è|siamo|siete)\b",
         "message": "Verificare: 'né' (congiunzione negativa) vs 'ne' (pronome/partitivo).", "replacement": r"ne \2", "priority": 5},
    ],

    # ── Hindi ────────────────────────────────────────────────────
    "hi": [
        {"rule_type": "regex", "pattern": r"(\S+)\s+\1", "message": "दोहराया गया शब्द।", "replacement": r"\1", "priority": 3},
    ],

    # ── Japanese (Romaji) ────────────────────────────────────────
    "ja": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
        {"rule_type": "regex", "pattern": r"\b(watashi)\s+(wa|ga|no|ni|wo|de|to|mo|kara|made|e|yori)\b",
         "message": "Check: 'watashi' (私) particle usage.", "replacement": r"watashi \2", "priority": 1},
    ],

    # ── Mandarin (Pinyin) ────────────────────────────────────────
    "zh": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Korean (Romanized) ───────────────────────────────────────
    "ko": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Vietnamese ───────────────────────────────────────────────
    "vi": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Từ lặp phát hiện.", "replacement": r"\1", "priority": 3},
    ],

    # ── Swahili ──────────────────────────────────────────────────
    "sw": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Neno limekizwa.", "replacement": r"\1", "priority": 3},
    ],

    # ── Zulu ─────────────────────────────────────────────────────
    "zu": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Yoruba ───────────────────────────────────────────────────
    "yo": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Amharic ──────────────────────────────────────────────────
    "am": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Hausa ────────────────────────────────────────────────────
    "ha": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Navajo ───────────────────────────────────────────────────
    "nv": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Quechua ──────────────────────────────────────────────────
    "qu": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Cherokee ─────────────────────────────────────────────────
    "chr": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Ojibwe ───────────────────────────────────────────────────
    "oj": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],

    # ── Inuktitut ────────────────────────────────────────────────
    "iu": [
        {"rule_type": "regex", "pattern": r"\b(\w+)\s+\1\b", "message": "Repeated word detected.", "replacement": r"\1", "priority": 3},
    ],
}

# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Confusion Pairs Per Language
# ═══════════════════════════════════════════════════════════════════

CONFUSION_PAIRS = {
    "en": [
        ("their", "there", "location", "Did you mean 'there' (location)?"),
        ("their", "they're", "contraction", "Did you mean 'they're' (they are)?"),
        ("there", "their", "possession", "Did you mean 'their' (possessive)?"),
        ("there", "they're", "contraction", "Did you mean 'they're' (they are)?"),
        ("your", "you're", "contraction", "Did you mean 'you're' (you are)?"),
        ("youre", "you're", "contraction", "Did you mean 'you're' (you are)?"),
        ("its", "it's", "contraction", "Did you mean 'it's' (it is)?"),
        ("its'", "it's", "contraction", "Did you mean 'it's' (it is)?"),
        ("affect", "effect", "verb/noun", "Did you mean 'effect' (noun)? If verb, 'affect' is correct."),
        ("effect", "affect", "noun/verb", "Did you mean 'affect' (verb)? If noun, 'effect' is correct."),
        ("then", "than", "comparison", "Did you mean 'than' (comparison)?"),
        ("than", "then", "time/sequence", "Did you mean 'then' (time/sequence)?"),
        ("lose", "loose", "not-tight", "Did you mean 'loose' (not tight)? If 'lose' (fail to win), this is correct."),
        ("loose", "lose", "misplace/fail", "Did you mean 'lose' (misplace/fail)?"),
        ("accept", "except", "exclusion", "Did you mean 'except' (exclusion)?"),
        ("except", "accept", "receive", "Did you mean 'accept' (receive)?"),
        ("weather", "whether", "if/whether", "Did you mean 'whether' (if)?"),
        ("whether", "weather", "climate", "Did you mean 'weather' (climate)?"),
        ("piece", "peace", "no-war", "Did you mean 'peace' (no war)?"),
        ("peace", "piece", "part", "Did you mean 'piece' (part)?"),
        ("principal", "principle", "rule/belief", "Did you mean 'principle' (rule/belief)?"),
        ("principle", "principal", "head/main", "Did you mean 'principal' (head/main)?"),
        ("stationary", "stationery", "writing-supplies", "Did you mean 'stationery' (writing supplies)?"),
        ("stationery", "stationary", "not-moving", "Did you mean 'stationary' (not moving)?"),
        ("complement", "compliment", "praise", "Did you mean 'compliment' (praise)?"),
        ("compliment", "complement", "complete", "Did you mean 'complement' (complete)?"),
        ("desert", "dessert", "sweet-food", "Did you mean 'dessert' (sweet food)?"),
        ("dessert", "desert", "dry-land/abandon", "Did you mean 'desert' (dry land/abandon)?"),
        ("advise", "advice", "noun", "Did you mean 'advice' (noun)? 'Advise' is a verb."),
        ("advice", "advise", "verb", "Did you mean 'advise' (verb)? 'Advice' is a noun."),
        ("breath", "breathe", "verb", "Did you mean 'breathe' (verb)? 'Breath' is a noun."),
        ("breathe", "breath", "noun", "Did you mean 'breath' (noun)? 'Breathe' is a verb."),
        ("choose", "chose", "past-tense", "Did you mean 'chose' (past tense)? 'Choose' is present."),
        ("chose", "choose", "present", "Did you mean 'choose' (present)? 'Chose' is past."),
        ("quite", "quiet", "silent", "Did you mean 'quiet' (silent)?"),
        ("quiet", "quite", "very/fairly", "Did you mean 'quite' (very/fairly)?"),
        ("through", "threw", "past-throw", "Did you mean 'threw' (past of throw)?"),
        ("threw", "through", "via", "Did you mean 'through' (via)?"),
        ("weak", "week", "7-days", "Did you mean 'week' (7 days)?"),
        ("week", "weak", "not-strong", "Did you mean 'weak' (not strong)?"),
        ("aloud", "allowed", "permitted", "Did you mean 'allowed' (permitted)?"),
        ("allowed", "aloud", "out-loud", "Did you mean 'aloud' (out loud)?"),
        ("bare", "bear", "animal/carry", "Did you mean 'bear' (animal/carry)?"),
        ("bear", "bare", "naked", "Did you mean 'bare' (naked)?"),
        ("brake", "break", "smash", "Did you mean 'break' (smash)?"),
        ("break", "brake", "stop", "Did you mean 'brake' (stop)?"),
        ("coarse", "course", "class/path", "Did you mean 'course' (class/path)?"),
        ("course", "coarse", "rough", "Did you mean 'coarse' (rough)?"),
        ("hear", "here", "location", "Did you mean 'here' (location)?"),
        ("here", "hear", "listen", "Did you mean 'hear' (listen)?"),
        ("hole", "whole", "entire", "Did you mean 'whole' (entire)?"),
        ("whole", "hole", "opening", "Did you mean 'hole' (opening)?"),
        ("know", "no", "negative", "Did you mean 'no' (negative)?"),
        ("no", "know", "understand", "Did you mean 'know' (understand)?"),
        ("meet", "meat", "food", "Did you mean 'meat' (food)?"),
        ("meat", "meet", "encounter", "Did you mean 'meet' (encounter)?"),
        ("plain", "plane", "aircraft", "Did you mean 'plane' (aircraft)?"),
        ("plane", "plain", "simple", "Did you mean 'plain' (simple)?"),
        ("right", "write", "verb", "Did you mean 'write' (verb)?"),
        ("write", "right", "correct/direction", "Did you mean 'right' (correct/direction)?"),
        ("sail", "sale", "selling", "Did you mean 'sale' (selling)?"),
        ("sale", "sail", "boat", "Did you mean 'sail' (boat)?"),
        ("scene", "seen", "viewed", "Did you mean 'seen' (viewed)?"),
        ("seen", "scene", "view", "Did you mean 'scene' (view)?"),
        ("site", "sight", "vision", "Did you mean 'sight' (vision)?"),
        ("sight", "site", "location", "Did you mean 'site' (location)?"),
        ("wait", "weight", "heaviness", "Did you mean 'weight' (heaviness)?"),
        ("weight", "wait", "delay", "Did you mean 'wait' (delay)?"),
        ("ware", "wear", "clothing", "Did you mean 'wear' (clothing)?"),
        ("wear", "ware", "goods", "Did you mean 'ware' (goods)?"),
        ("were", "where", "location", "Did you mean 'where' (location)?"),
        ("where", "were", "past-be", "Did you mean 'were' (past of be)?"),
    ],

    "es": [
        ("hay", "ay", "interjección", "¿Quiso decir 'ay' (interjección)?"),
        ("ay", "hay", "verbo-haber", "¿Quiso decir 'hay' (verbo haber)?"),
        ("mas", "más", "cantidad", "¿Quiso decir 'más' (con acento, cantidad)?"),
        ("más", "mas", "pero", "¿Quiso decir 'mas' (pero)?"),
        ("aun", "aún", "todavía", "¿Quiso decir 'aún' (todavía)?"),
        ("aún", "aun", "incluso", "¿Quiso decir 'aun' (incluso)?"),
        ("como", "cómo", "interrogativo", "¿Quiso decir 'cómo' (interrogativo)?"),
        ("cómo", "como", "comparativo", "¿Quiso decir 'como' (comparativo)?"),
        ("que", "qué", "interrogativo", "¿Quiso decir 'qué' (interrogativo)?"),
        ("qué", "que", "relativo", "¿Quiso decir 'que' (relativo)?"),
        ("mi", "mí", "pronombre", "¿Quiso decir 'mí' (pronombre)?"),
        ("mí", "mi", "posesivo", "¿Quiso decir 'mi' (posesivo)?"),
        ("tu", "tú", "pronombre", "¿Quiso decir 'tú' (pronombre)?"),
        ("tú", "tu", "posesivo", "¿Quiso decir 'tu' (posesivo)?"),
        ("el", "él", "pronombre", "¿Quiso decir 'él' (pronombre)?"),
        ("él", "el", "artículo", "¿Quiso decir 'el' (artículo)?"),
        ("se", "sé", "verbo-saber", "¿Quiso decir 'sé' (verbo saber)?"),
        ("sé", "se", "pronombre", "¿Quiso decir 'se' (pronombre)?"),
        ("te", "té", "bebida", "¿Quiso decir 'té' (bebida)?"),
        ("té", "te", "pronombre", "¿Quiso decir 'te' (pronombre)?"),
        ("si", "sí", "afirmación", "¿Quiso decir 'sí' (afirmación)?"),
        ("sí", "si", "condicional", "¿Quiso decir 'si' (condicional)?"),
        ("solo", "sólo", "solamente", "¿Quiso decir 'sólo' (solamente)?"),
        ("sólo", "solo", "adjetivo", "¿Quiso decir 'solo' (adjetivo)?"),
        ("cuyo", "cuyos", "concordancia", "Verifique concordancia de 'cuyo/cuyos'."),
        ("cuya", "cuyas", "concordancia", "Verifique concordancia de 'cuya/cuyas'."),
        ("ha", "a", "preposición", "¿Quiso decir 'a' (preposición) en vez de 'ha' (verbo)?"),
        ("a", "ha", "verbo", "¿Quiso decir 'ha' (verbo haber)?"),
        ("echo", "hecho", "participio", "¿Quiso decir 'hecho' (participio de hacer)?"),
        ("hecho", "echo", "verbo-echar", "¿Quiso decir 'echo' (verbo echar)?"),
        ("valla", "vaya", "interjección", "¿Quiso decir 'vaya' (interjección)?"),
        ("vaya", "valla", "cerca", "¿Quiso decir 'valla' (cerca)?"),
        ("baya", "vaya", "interjección", "¿Quiso decir 'vaya' (interjección)?"),
        ("haya", "aya", "niñera", "¿Quiso decir 'aya' (niñera)?"),
        ("aya", "haya", "verbo-haber", "¿Quiso decir 'haya' (verbo haber)?"),
        ("halla", "haya", "verbo-haber", "¿Quiso decir 'haya' (verbo haber)?"),
        ("haya", "halla", "verbo-hallar", "¿Quiso decir 'halla' (verbo hallar)?"),
    ],

    "de": [
        ("das", "dass", "Konjunktion", "Meinten Sie 'dass' (Konjunktion)?"),
        ("dass", "das", "Artikel", "Meinten Sie 'das' (Artikel)?"),
        ("seit", "seid", "Verb-sein", "Meinten Sie 'seid' (Verb sein, 2. Person Plural)?"),
        ("seid", "seit", "Zeitangabe", "Meinten Sie 'seit' (Zeitangabe)?"),
        ("wider", "wieder", "nochmals", "Meinten Sie 'wieder' (nochmals)?"),
        ("wieder", "wider", "gegen", "Meinten Sie 'wider' (gegen)?"),
        ("waren", "waren", "Verb-sein", "Kontext prüfen: 'waren' (Verb) vs 'Waren' (Güter)."),
        ("weisen", "wiesen", "Präteritum", "Meinten Sie 'wiesen' (Präteritum von weisen)?"),
        ("muß", "muss", "neue-Rechtschreibung", "Verwenden Sie 'muss' (neue Rechtschreibung)."),
        ("fass", "Fass", "Großschreibung", "Substantive werden großgeschrieben: 'Fass'."),
    ],

    "fr": [
        ("a", "à", "préposition", "Vouliez-vous dire 'à' (préposition)?"),
        ("à", "a", "verbe-avoir", "Vouliez-vous dire 'a' (verbe avoir, présent)?"),
        ("ou", "où", "lieu", "Vouliez-vous dire 'où' (lieu/question)?"),
        ("où", "ou", "conjonction", "Vouliez-vous dire 'ou' (conjonction)?"),
        ("ce", "se", "réfléchi", "Vouliez-vous dire 'se' (pronom réfléchi)?"),
        ("se", "ce", "démonstratif", "Vouliez-vous dire 'ce' (déterminant)?"),
        ("la", "là", "lieu", "Vouliez-vous dire 'là' (lieu)?"),
        ("là", "la", "article", "Vouliez-vous dire 'la' (article)?"),
        ("du", "dû", "participe", "Vouliez-vous dire 'dû' (participe passé de devoir)?"),
        ("dû", "du", "article", "Vouliez-vous dire 'du' (article)?"),
        ("sur", "sûr", "certain", "Vouliez-vous dire 'sûr' (certain)?"),
        ("sûr", "sur", "préposition", "Vouliez-vous dire 'sur' (préposition)?"),
        ("nos", "nôtre", "possessif-pronoun", "Vouliez-vous dire 'le nôtre' (pronom possessif)?"),
        ("votre", "vôtre", "possessif-pronoun", "Vouliez-vous dire 'le vôtre' (pronom possessif)?"),
        ("leur", "leurre", "leurres", "Vérifiez le contexte: 'leur' vs 'leurre'."),
        ("et", "est", "verbe", "Vouliez-vous dire 'est' (verbe être)?"),
        ("est", "et", "conjonction", "Vouliez-vous dire 'et' (conjonction)?"),
        ("mon", "m'ont", "verbe", "Vouliez-vous dire 'm'ont' (ils m'ont)?"),
        ("son", "sont", "verbe", "Vouliez-vous dire 'sont' (verbe être)?"),
        ("sont", "son", "possessif", "Vouliez-vous dire 'son' (possessif)?"),
        ("peu", "peut", "verbe", "Vouliez-vous dire 'peut' (verbe pouvoir)?"),
        ("peut", "peu", "quantité", "Vouliez-vous dire 'peu' (quantité)?"),
        ("tout", "tous", "pluriel", "Vouliez-vous dire 'tous' (pluriel)?"),
        ("tous", "tout", "singulier", "Vouliez-vous dire 'tout' (singulier)?"),
    ],

    "it": [
        ("e", "è", "verbo-essere", "Volevate dire 'è' (verbo essere)?"),
        ("è", "e", "congiunzione", "Volevate dire 'e' (congiunzione)?"),
        ("li", "lì", "avverbio-luogo", "Volevate dire 'lì' (avverbio di luogo)?"),
        ("lì", "li", "pronome", "Volevate dire 'li' (pronome)?"),
        ("la", "là", "avverbio-luogo", "Volevate dire 'là' (avverbio di luogo)?"),
        ("là", "la", "articolo", "Volevate dire 'la' (articolo)?"),
        ("se", "sé", "pronome-riflessivo", "Volevate dire 'sé' (pronome riflessivo)?"),
        ("sé", "se", "congiunzione", "Volevate dire 'se' (congiunzione)?"),
        ("ne", "né", "negazione", "Volevate dire 'né' (congiunzione negativa)?"),
        ("né", "ne", "pronome", "Volevate dire 'ne' (pronome/partitivo)?"),
        ("da", "dà", "verbo-dare", "Volevate dire 'dà' (verbo dare)?"),
        ("dà", "da", "preposizione", "Volevate dire 'da' (preposizione)?"),
        ("si", "sì", "affermazione", "Volevate dire 'sì' (affermazione)?"),
        ("sì", "si", "pronome", "Volevate dire 'si' (pronome)?"),
        ("te", "té", "bevanda", "Volevate dire 'té' (bevanda)?"),
        ("té", "te", "pronome", "Volevate dire 'te' (pronome)?"),
    ],
}

# For languages without specific confusion pairs, we add nothing (empty list is fine)

# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Download & Import Engine
# ═══════════════════════════════════════════════════════════════════

class DictionaryDownloader:
    """Downloads word lists and imports grammar data for one language."""

    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), DB_FOLDER)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None

    def run(self):
        logger.info(f"{'='*60}")
        logger.info(f"Processing: {self.lang_code.upper()} ({LANG_NAMES.get(self.lang_code, '?')})")
        logger.info(f"{'='*60}")
        self._ensure_dir()
        self._connect()
        self._apply_schema()
        self._download_and_import_words()
        self._import_grammar_rules()
        self._import_confusion_pairs()
        self._set_metadata()
        self._disconnect()

    # ── Lifecycle ───────────────────────────────────────────────

    def _ensure_dir(self):
        os.makedirs(self.db_dir, exist_ok=True)

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA synchronous = NORMAL")

    def _disconnect(self):
        if self.conn:
            self.conn.close()

    def _apply_schema(self):
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    # ── Word Download ───────────────────────────────────────────

    def _download_and_import_words(self):
        if self.lang_code not in DOWNLOAD_LANGS:
            logger.info(f"  No remote dictionary for '{self.lang_code}'. Keeping existing data.")
            return

        # Check if already has substantial data
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        existing = cursor.fetchone()[0]
        if existing >= 10000:
            logger.info(f"  Already {existing} words in DB. Skipping download.")
            return

        url = FREQ_BASE_URL.format(lang=self.lang_code)
        logger.info(f"  Downloading: {url}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NLP-Corrector/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            logger.info(f"  Downloaded {len(raw):,} bytes.")
            self._parse_and_import_freq(raw)
        except urllib.error.HTTPError as e:
            logger.warning(f"  HTTP {e.code} — no word list available for '{self.lang_code}'.")
        except urllib.error.URLError as e:
            logger.error(f"  Network error: {e.reason}")
        except Exception as e:
            logger.error(f"  Download failed: {e}")

    def _parse_and_import_freq(self, raw: str):
        """Parse FrequencyWords format: 'word freq' per line."""
        lines = raw.strip().split("\n")
        logger.info(f"  Parsing {len(lines):,} lines …")

        now = datetime.utcnow().isoformat()
        word_data = []
        all_words = []

        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                word, freq_str = parts[0], parts[1]
                try:
                    freq = int(freq_str)
                except ValueError:
                    continue
                word_data.append((word, freq, now))
                # Repeat word by log of frequency for n-gram generation
                repeat = min(max(1, int(freq ** 0.15)), 50)
                all_words.extend([word] * repeat)
            elif len(parts) == 1 and parts[0]:
                word_data.append((parts[0], 1, now))
                all_words.append(parts[0])

        if not word_data:
            logger.warning("  No valid words parsed.")
            return

        logger.info(f"  Importing {len(word_data):,} unique words …")

        try:
            with self.conn:
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at)
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET
                         freq = freq + excluded.freq,
                         updated_at = excluded.updated_at""",
                    [(w, f, now, now) for w, f, now in word_data],
                )

                # Bigrams
                bigram_freq = Counter(zip(all_words, all_words[1:]))
                logger.info(f"  Importing {len(bigram_freq):,} bigrams …")
                self.conn.executemany(
                    """INSERT INTO bigrams (w1, w2, freq) VALUES (?, ?, ?)
                       ON CONFLICT(w1, w2) DO UPDATE SET freq = freq + ?""",
                    [(w1, w2, f, f) for (w1, w2), f in bigram_freq.items()],
                )

                # Trigrams
                trigram_freq = Counter(zip(all_words, all_words[1:], all_words[2:]))
                logger.info(f"  Importing {len(trigram_freq):,} trigrams …")
                self.conn.executemany(
                    """INSERT INTO trigrams (w1, w2, w3, freq) VALUES (?, ?, ?, ?)
                       ON CONFLICT(w1, w2, w3) DO UPDATE SET freq = freq + ?""",
                    [(w1, w2, w3, f, f) for (w1, w2, w3), f in trigram_freq.items()],
                )

            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dictionary")
            total = cursor.fetchone()[0]
            logger.info(f"  ✅ Dictionary now has {total:,} words.")

        except sqlite3.Error as e:
            logger.error(f"  Import failed: {e}")

    # ── Grammar Rules ───────────────────────────────────────────

    def _import_grammar_rules(self):
        rules = GRAMMAR_RULES.get(self.lang_code, [])
        if not rules:
            logger.info(f"  No grammar rules for '{self.lang_code}'.")
            return

        logger.info(f"  Importing {len(rules)} grammar rules …")

        try:
            with self.conn:
                # Clear old rules and insert fresh
                self.conn.execute("DELETE FROM grammar_rules")
                self.conn.executemany(
                    """INSERT INTO grammar_rules (rule_type, pattern, message, replacement, priority, enabled)
                       VALUES (?, ?, ?, ?, ?, 1)""",
                    [(r["rule_type"], r["pattern"], r["message"], r["replacement"], r.get("priority", 0))
                     for r in rules],
                )
            logger.info(f"  ✅ {len(rules)} grammar rules imported.")
        except sqlite3.Error as e:
            logger.error(f"  Grammar rules import failed: {e}")

    # ── Confusion Pairs ─────────────────────────────────────────

    def _import_confusion_pairs(self):
        pairs = CONFUSION_PAIRS.get(self.lang_code, [])
        if not pairs:
            logger.info(f"  No confusion pairs for '{self.lang_code}'.")
            return

        logger.info(f"  Importing {len(pairs)} confusion pairs …")

        try:
            with self.conn:
                self.conn.execute("DELETE FROM confusion_pairs")
                self.conn.executemany(
                    """INSERT INTO confusion_pairs (wrong, correct, context_hint, message)
                       VALUES (?, ?, ?, ?)""",
                    [(p[0], p[1], p[2], p[3]) for p in pairs],
                )
            logger.info(f"  ✅ {len(pairs)} confusion pairs imported.")
        except sqlite3.Error as e:
            logger.error(f"  Confusion pairs import failed: {e}")

    # ── Metadata ────────────────────────────────────────────────

    def _set_metadata(self):
        now = datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        word_count = cursor.fetchone()[0]

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("last_download_date", now),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("schema_version", "2.0"),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("lang_name", LANG_NAMES.get(self.lang_code, self.lang_code)),
                )
                self.conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    ("word_count", str(word_count)),
                )
        except sqlite3.Error as e:
            logger.error(f"  Metadata write failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Main
# ═══════════════════════════════════════════════════════════════════

def main():
    logger.info("╔══════════════════════════════════════════════════╗")
    logger.info("║  NLP Text Corrector — Dictionary Downloader     ║")
    logger.info("║  Downloads 50k word lists + grammar rules       ║")
    logger.info("║  for 20 languages into ./database/              ║")
    logger.info("╚══════════════════════════════════════════════════╝")
    logger.info(f"Target: {os.path.join(os.getcwd(), DB_FOLDER)}\n")

    success, fail = 0, 0
    for lang in LANGUAGES:
        try:
            DictionaryDownloader(lang).run()
            success += 1
        except Exception as e:
            logger.error(f"FATAL for {lang}: {e}")
            fail += 1
        logger.info("")

    logger.info("=" * 60)
    logger.info(f"✅ Done! {success} succeeded, {fail} failed out of {len(LANGUAGES)} languages.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()