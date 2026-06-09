#!/usr/bin/env python3
"""
Advanced NLP Text Corrector — PySide6 Edition (Multi-DB + Logging + Robust Error Handling)
==============================================================================
Features:
  • Isolated SQLite databases per language (./en/en.db, ./es/es.db, ./de/de.db)
  • Strict relational database schema with indexes and metadata tracking
  • Comprehensive Python logging (file + console)
  • Robust error handling (DB constraints, IO errors, thread safety)
  • Spell checking via BK-tree & Levenshtein distance
  • Grammar checking with language-specific rules
  • Multiple correction strategies (Interactive, Beam Search, MCTS)
  • User dictionary management with database persistence
  • Dark / Light themes
"""

import sys, re, os, json, heapq, random, string, time, logging, traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QTabWidget, QComboBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QLineEdit, QSpinBox, QCheckBox, QMessageBox,
    QSplitter, QToolBar, QStatusBar, QProgressBar,
    QScrollArea, QFormLayout, QRadioButton, QListWidget, 
    QListWidgetItem, QAbstractItemView, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor, QKeySequence

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Logging Configuration
# ═══════════════════════════════════════════════════════════════════

LOG_FILE = "nlp_corrector.log"

def setup_logging():
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # File Handler (captures everything)
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(fh)
    
    # Console Handler (captures warnings and above)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(ch)

logger = logging.getLogger("NLP_Corrector")

# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Built-in Seed Dictionaries
# ═══════════════════════════════════════════════════════════════════

EN_SEED = "a able about above accept across act actually add afraid after afternoon again against age ago agree air all almost along already also always am among an and anger animal answer ant any anybody anymore anything anyplace anyway apart apartment appear apple are area arm army around arrive art as ask at attack attempt attend august aunt author autumn available away baby back bad bag ball ban band bank bar base basic basis bath be beach bean bear beat beautiful became because become bed been before began begin behind being believe bell belong below beside best better between beyond big bill bird birth bit bite black blame blank block blood blow blue board boat body bomb bond bone book border born both bother bottle bottom bound box boy brain branch brave bread break breath bridge brief bright bring broad broke brother brown brush build building burn bus business busy but buy by cabin cage cake call calm came camera camp can cap capital captain capture car card care careful carry case cash cast cat catch cause cell center central century certain chain chair chairman challenge champion chance change channel chapter character charge charm chart chase cheap check cheek cheese chest chicken chief child childhood chin chip choice choose church circle citizen city civil claim class clean clear click client climb clinical clock close cloth clothes cloud club clue cluster coach coal coast coat code coffee cold collar collect college colony color column combination come comfort command comment commit common communicate community company compare competition complete complex computer concern condition conduct confirm congress connect consider contact contain content contest continue control conversation cook cool cooperation copy core corner corporate correct cost could count counter country county couple courage course court cousin cover crack craft crash crazy cream create crime criminal crisis criteria critical crop cross crowd crucial cry cultural cup cure curious current curve custom customer cut cycle dad daily damage dance danger dare dark data date daughter day dead deal dear death debate decade decide decision deck declare decline deep defeat defend defense define definitely degree delay deliver demand democracy demonstrate deny department depend deploy depression derive describe desert deserve design desire desk despite destroy detail detect determine develop device devote dialogue did die diet differ digital dinner direct direction director dirty disappear discipline discover discuss discussion disease dish display distance distinct district disturb divide doctor document does dog dollar domestic door double down downtown draft drag drama dramatic draw drawing dream dress drink drive drop drug dry due during dust duty each eager ear early earn earth ease eastern easy eat economic economy edge edition editor education effect effective effort eight either elderly elect election electric element eliminate else emerge emergency emission emotion emphasis employ empty enable encounter encourage end enemy energy enforce engage engine engineer enjoy enormous enough ensure enter entire entry environment episode equal era error escape especially essay essential establish estate estimate evaluate even evening event eventually ever every evidence evil evolution exact examine example exceed exchange exciting exercise exhibit exist expand expect experience experiment expert explain explore export expose extend extension extensive extent external extra extreme eye face facility fact factor fail fair faith fall familiar family famous fan far farm farmer fascinate fashion fast fat fate father fault favor favorite fear feature federal fee feed feel fellow female fence few fiction field fifteen fight figure file fill film final finally find fine finger finish fire firm first fish fit five fix flag flame flat flee flesh flight flip float flood floor flow flower fly focus fold folk follow food foot football for force foreign forest forever forget form formal former formula forth fortune forward found foundation four fourth frame framework free freedom french frequency frequently fresh friend front fruit fuel full fun function fund funny furniture further future gain galaxy game gang gap garage garden gas gate gather gay gaze gear gender general generate genetic genius gentle gentleman get giant gift girl girlfriend give glad glance glass global glory go goal god gold golden golf gone good govern government governor grab grace grade gradually grand grandfather grandmother grant grass grave gray great green grew grip grocery ground group grow growth guarantee guard guess guest guide guilty guitar gun guy habit hair half hall hand handle hang happen happy harbor hard harm hat hate have he head headline health healthy hear hearing heart heat heavy height help her here hero herself hide high highlight hill him himself hip hire his historian historic historical history hit hold hole holiday home honest honor hope horrible horror horse hospital host hostile hot hotel hour house household housing how however huge human humor hundred hungry hunt hurry hurt husband ice idea ideal identify identity ignore ill illegal illustrate image imagination imagine immediate immediately immigrant impact implement implication imply import important impose impossible impress impression improve incident include income increase increasingly incredible indeed independence independent index indicate individual industrial industry infant infection inflation influence inform information initial initially inner innocent input inquiry inside insist install instance instead institution instrument insurance intellectual intend intense intention interest interesting internal internet interpret interview into introduce invasion invest investigate investment investor invisible involve iron island isolate issue it item its itself jacket jail japanese jet jew jewish job join joint joke journal journalist journey joy judge judgment juice jump junior jury just justice justify keen keep key kid kill kind king kiss kit kitchen knee knife knock know knowledge known lab label labor lack lady lake land landscape language large largely last late lately later latin latter laugh launch law lawn lawsuit lawyer lay layer lead leader leadership leaf league lean learn least leather leave led left leg legal legend lemon length less lesson let letter level liberal library license lid lie life lifestyle lift light like likely limit line link lion lip list listen literally literary literature little live living load loan local locate location lock long look lord lose loss lost lot loud love lovely lover low lower luck lunch lung machine mad magazine mail main maintain major majority make maker male mall man manage management manager manner manufacturer many map margin mark market marriage married marry mask mass massive master match material math matter may maybe mayor me meal mean meaning measure meat mechanism media medical medicine medium meet member membership memory mental mention mentor menu mere merely message metal method middle might military milk million mind mine minister minor minority minute miracle mirror miss mission mistake mix mixture mm-hmm model moderate modern modest mom moment money monitor month mood moon moral more morning mortgage most mostly mother motion mount mountain mouse mouth move movement movie much multiple murder muscle museum music musical muslim must mutual my myself mystery myth nail name narrative narrow nation national natural naturally nature near nearly necessarily necessary neck need negative negotiate negotiation neighbor neighborhood neither nerve nervous net network never nevertheless new newly news newspaper next nice night nine nobody nod noise nor normal normally north northern nose not note nothing notice notion novel now nowhere number numerous nurse nut object objection obligation observation observe obvious obviously occasion occupy occur ocean odd odds off offense offensive offer office officer official often oil ok okay old olympic on once one ongoing online only onto open opening operate operation operator opinion opponent opportunity oppose opposite opposition option or orange order ordinary organ organic organization orient origin original other otherwise ought our ourselves out outcome outside overall overcome overlook owe own owner pace pack package page paid pain paint painting pair pale palm pan panel panic paper parent park parking part partially participate particular particularly partly partner partnership party pass passage passenger passion past patch path patient pattern pause pay payment peace peak peer penalty people per perceive percent percentage perception perfect perfectly perform performance perhaps period permanent permission permit person personal personality personally perspective phase philosophy phone photo photograph phrase physical physically physician piano pick picture pie piece pile pilot pine pink pipe pitch place plan plane planet planning plant plastic plate platform play player please pleasure plenty plus pocket poem poet poetry point pole police policy political politically pollution pool poor pop popular population porch port portion portrait pose position positive possibility possible possibly post pot potato potential potentially pound pour poverty power powerful practical practice pray prayer precisely predict prefer preference pregnancy preparation prepare presence present presentation preserve presidency president presidential press pressure pretend pretty prevent previous previously price primarily primary prime principal principle print printer prior priority prison prisoner privacy private probably problem procedure proceed process produce producer product production profession professional professor profit program progress project prominent promise promote proper properly property proportion proposal propose prospect protect protection protein protest proud prove provide provider province provision psychological public publication publicly pull punch purchase pure purple purpose pursue push put qualify quality quarter quarterback queen question quick quickly quiet quietly quit quite quote race racial racism racist rack radical radio rage rail rain raise range rank rapid rapidly rare rarely rate rather reach react reaction read reader reading ready real realistic reality realize really reason reasonable rebel recall receive recent recently recognition recognize recommend record recover recovery recruit red reduce reduction reflect reflection reform regard regime region regional register regular regulation reinforce reject relate relation relationship relative relatively release relevant relief religion religious reluctant rely remain remaining remarkable remember remind remote remove repeat repeatedly replace reply report reporter represent representation republican reputation request require research researcher resemble reservation resident resist resolution resolve resort resource respond response responsibility responsible rest restaurant restore restriction result retain retire return reveal revenue review revolution rhythm rice rich rid ride rifle right ring rise risk river road rock role roll romantic roof room root rope rose rough roughly round route row royal rub rule run running rural rush sacred sacrifice sad safe safety sake salary sale salt same sample sanction sand satellite satisfaction satisfy sauce save saving say scale scandal scene schedule scholar scholarship school science scientific scientist scope score screen sea search season seat second secondary secret secretary section sector secure security seed seek seem segment seize select selection self sell senate senator senior sense sensitive sentence separate sequence series serious seriously serve service session set setting settle settlement seven several severe sexual shake shall shape share sharp she sheet shelf shell shelter shift shine ship shirt shock shoe shoot shooting shop shopping shore short shortage shot should shoulder shout show shower shut sick side sight sign signal significance significant significantly silence silent silver similar similarly simple simply simultaneously since sing singer single sir sister sit site situation six size ski skill skin sky slave slavery sleep slice slide slight slightly slip slow slowly small smart smell smile smoke smooth snap so so-called soccer social society soft software soil solar soldier solid solution solve somebody somehow someone something sometimes somewhat somewhere son song soon sophisticated sorry sort soul sound source south southeast southern soviet space spanish speak speaker special specialist species specific specifically speech speed spend spent spin spirit spiritual split spokesman sport spot spread spring spy square squeeze stability stable staff stage stair stake stand standard standing star stare start starting state statement station status stay steady steal steam steel steep stem step stick still stock stomach stone stop storage store storm story straight strange stranger strategic strategy stream street strength stress stretch strict strike string strip stroke strong strongly structure struggle student studio study stuff stupid style subject submit substantial succeed success successful successfully such suddenly suffer sufficient sugar suggest suit summer sun super supply support supporter suppose sure surely surface surgery surprise surprisingly surround surrounding survey survival survive suspect suspend suspicion sustain swallow swear sweet swim swing switch symbol symptom system table tackle tactic tail take tale talent talk tall tank tape target task taste tax taxpayer tea teach teacher teaching team tear technique technology television tell temperature temporary ten tend tendency term terms terrible test testify testimony testing text than thank that the theater their them theme themselves then theory therapy there therefore these they thick thin thing think thinking third thirty this those though thought thousand threat threaten three throat through throughout throw thus ticket tie tight till time tiny tip tire tired title to today toe together tomorrow tone tonight too tool top topic toss total totally touch tough tour tourist toward towards tower town toy trace track trade tradition traditional traffic trail train training trait transfer transform transformation transition translate transmission transport trap travel treat treatment treaty tree tremendous trend trial tribe trick trip trouble truck true truly trust truth try tube tunnel turn tv twelve twenty twice twin two type typical typically ugly ultimate ultimately unable uncle under undergo understand understanding unemployment unfold unfortunately unhappy uniform union unique unit united universe university unknown unless unlike unlikely until unusual up upon upper urban urge us use used useful user usual usually vacation valley valuable value variable variation variety various vast vehicle venture version versus very veteran via victim victory video view village violation violence virtual virtually visible vision visit visitor visual vital voice volume voluntary volunteer vote voter vulnerable wage wait wake walk wall wander want war warning wash waste watch water wave way weak weakness wealth weapon wear weather web website wedding week weekend weigh weight welcome welfare well west western wet what whatever wheel when whenever where whereas wherever whether which while whisper white who whole whom whose why wide widely widespread wife wild will willing win wind window wine wing winner winter wire wisdom wise wish with withdraw without witness woman women wonder wonderful wood wooden word work worker working works workshop world worried worry worse worst worth worthy would wound wrap write writer writing wrong yard yeah year yell yellow yes yesterday yet yield you young youngster your yourself youth zone".split()

ES_SEED = "a al ahora algo algunos ante antes apellido aquél aquí así aunque año años cada casi caso casa cine ciudad como con conocer creo cual cuando de del desde donde dos él ella ellos en entre era es esa ese eso esta estado estos está estoy esto euro ejemplo el ella ellos embargo en entre era eres esa ese esto esto están estaban estar estas este estoy fin fue fuera gran ha habíamos haber hace hacer habían hasta hay hoy la las le les lo los me mi mismo mucho muy más mí mío nada ni no nos nosotras nosotros nuestra nuestro o otra otro otros para parte pasar pero poco por porque primero puede cuando que quien qué se sea señora señor si sí siempre sobre solo somos su sus suyo sí también tan tanto te tienen tengo ti tiene todo tu tú un una unas uno unos usted ustedes va van veces ver vez y ya yo él caminar camina caminé escuela compra manzana está mesa ayer ella va la una".split()

DE_SEED = "aber alle als am an auch auf aus bei bin bis bist da dann das dem den der des die dieser du durch ein eine einem einer es für gegen hat habe haben hier ich ihm ihn ihm in ist ja je kann keine können man mehr mich mir mit nach nicht nichts nun nur oder ohne so soll seine seinem seiner sich sie sind so etwas um und uns unter vom von vor war was wenn wer wie wir wird wo zu zum zur gehen geht ging zur schule kauft ein apfel ist auf tisch und gestern sie".split()

SEED_MAP = {"en": EN_SEED, "es": ES_SEED, "de": DE_SEED}


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: NLP Engine — Levenshtein & BK-Tree
# ═══════════════════════════════════════════════════════════════════

def levenshtein(a: str, b: str) -> int:
    if not a: return len(b)
    if not b: return len(a)
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i - 1] == b[j - 1]: dp[i][j] = dp[i - 1][j - 1]
            else: dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i][j - 1], dp[i - 1][j])
    return dp[n][m]

class BKNode:
    __slots__ = ('word', 'children')
    def __init__(self, word: str):
        self.word = word
        self.children: Dict[int, 'BKNode'] = {}

class BKTree:
    def __init__(self):
        self.root: Optional[BKNode] = None

    def add(self, word: str):
        if not self.root:
            self.root = BKNode(word)
            return
        node = self.root
        while True:
            dist = levenshtein(word, node.word)
            if dist in node.children:
                node = node.children[dist]
            else:
                node.children[dist] = BKNode(word)
                break

    def query(self, word: str, max_dist: int) -> List[Tuple[str, int]]:
        result = []
        def _dfs(node: BKNode):
            dist = levenshtein(word, node.word)
            if dist <= max_dist:
                result.append((node.word, dist))
            for d in range(max(0, dist - max_dist), dist + max_dist + 1):
                child = node.children.get(d)
                if child: _dfs(child)
        if self.root: _dfs(self.root)
        return result

    def build_from_list(self, words: List[str]):
        self.root = None
        shuffled = list(words)
        random.shuffle(shuffled)
        for w in shuffled: self.add(w)


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Per-Language Database Manager
# ═══════════════════════════════════════════════════════════════════

class DatabaseManager:
    """Manages a dedicated SQLite database for a single language inside its own folder."""
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db_dir = os.path.join(os.getcwd(), lang_code)
        self.db_path = os.path.join(self.db_dir, f"{lang_code}.db")
        self.conn = None
        self._init_db_structure()

    def _init_db_structure(self):
        """Create directory, connect to DB, and enforce strict schema."""
        logger.info(f"Initializing database for '{self.lang_code}' at: {self.db_path}")
        try:
            os.makedirs(self.db_dir, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys = ON")
            cursor = self.conn.cursor()

            # Metadata Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS metadata (
                                key TEXT PRIMARY KEY, 
                                value TEXT NOT NULL)""")

            # Dictionary Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS dictionary (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                word TEXT NOT NULL UNIQUE,
                                freq INTEGER NOT NULL DEFAULT 1,
                                is_user INTEGER NOT NULL DEFAULT 0,
                                created_at TEXT NOT NULL,
                                updated_at TEXT NOT NULL)""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dict_word ON dictionary(word)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_dict_user ON dictionary(is_user)")

            # Bigrams Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS bigrams (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                w1 TEXT NOT NULL,
                                w2 TEXT NOT NULL,
                                freq INTEGER NOT NULL DEFAULT 1,
                                UNIQUE(w1, w2))""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bigrams_w1 ON bigrams(w1)")

            # Trigrams Table
            cursor.execute("""CREATE TABLE IF NOT EXISTS trigrams (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                w1 TEXT NOT NULL,
                                w2 TEXT NOT NULL,
                                w3 TEXT NOT NULL,
                                freq INTEGER NOT NULL DEFAULT 1,
                                UNIQUE(w1, w2, w3))""")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trigrams_w1w2 ON trigrams(w1, w2)")

            self.conn.commit()
            
            # Seed if empty
            cursor.execute("SELECT COUNT(*) FROM dictionary")
            if cursor.fetchone()[0] == 0:
                logger.info(f"Database empty for '{self.lang_code}'. Seeding with built-in dictionary...")
                self._seed_database()
            else:
                logger.debug(f"Database for '{self.lang_code}' already populated.")

        except sqlite3.Error as e:
            logger.critical(f"Database initialization failed for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"Database init error: {e}")
        except Exception as e:
            logger.critical(f"Unexpected error initializing DB for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise

    def _seed_database(self):
        words = SEED_MAP.get(self.lang_code, [])
        if not words: return
        now = datetime.utcnow().isoformat()
        freq = Counter(words)
        try:
            with self.conn:
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at) 
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?""",
                    [(w, f, now, now, f, now) for w, f in freq.items()]
                )
                self._upsert_ngrams_internal(words)
        except sqlite3.Error as e:
            logger.error(f"Seeding database failed: {e}")

    def _upsert_ngrams_internal(self, tokens: List[str]):
        """Helper to calculate and upsert ngrams during import/seed."""
        bigram_freq = Counter(zip(tokens, tokens[1:]))
        trigram_freq = Counter(zip(tokens, tokens[1:], tokens[2:]))
        
        self.conn.executemany(
            """INSERT INTO bigrams (w1, w2, freq) VALUES (?, ?, ?)
               ON CONFLICT(w1, w2) DO UPDATE SET freq = freq + ?""",
            [(w1, w2, f, f) for (w1, w2), f in bigram_freq.items()]
        )
        self.conn.executemany(
            """INSERT INTO trigrams (w1, w2, w3, freq) VALUES (?, ?, ?, ?)
               ON CONFLICT(w1, w2, w3) DO UPDATE SET freq = freq + ?""",
            [(w1, w2, w3, f, f) for (w1, w2, w3), f in trigram_freq.items()]
        )

    def load_words(self) -> Dict[str, int]:
        try:
            cursor = self.conn.execute("SELECT word, freq FROM dictionary")
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to load words for '{self.lang_code}': {e}")
            return {}

    def load_user_words(self) -> Set[str]:
        try:
            cursor = self.conn.execute("SELECT word FROM dictionary WHERE is_user=1")
            return {row[0] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to load user words for '{self.lang_code}': {e}")
            return set()

    def load_bigrams(self) -> Dict[str, Counter]:
        try:
            cursor = self.conn.execute("SELECT w1, w2, freq FROM bigrams")
            counts = defaultdict(Counter)
            for w1, w2, freq in cursor.fetchall(): counts[w1][w2] = freq
            return counts
        except sqlite3.Error as e:
            logger.error(f"Failed to load bigrams for '{self.lang_code}': {e}")
            return defaultdict(Counter)

    def load_trigrams(self) -> Counter:
        try:
            cursor = self.conn.execute("SELECT w1, w2, w3, freq FROM trigrams")
            counts = Counter()
            for w1, w2, w3, freq in cursor.fetchall(): counts[(w1, w2, w3)] = freq
            return counts
        except sqlite3.Error as e:
            logger.error(f"Failed to load trigrams for '{self.lang_code}': {e}")
            return Counter()

    def add_word(self, word: str):
        word = word.lower().strip()
        if not word: return
        now = datetime.utcnow().isoformat()
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at) 
                       VALUES (?, 1, 1, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + 1, is_user = 1, updated_at = ?""",
                    (word, now, now, now)
                )
        except sqlite3.Error as e:
            logger.error(f"Failed to add word '{word}': {e}")

    def remove_user_word(self, word: str):
        word = word.lower().strip()
        try:
            with self.conn:
                self.conn.execute("DELETE FROM dictionary WHERE word=? AND is_user=1", (word,))
        except sqlite3.Error as e:
            logger.error(f"Failed to remove word '{word}': {e}")

    def import_corpus(self, text: str):
        tokens = re.findall(r'\w+', text.lower())
        if not tokens: 
            logger.warning("No tokens found in corpus to import.")
            return

        word_freq = Counter(tokens)
        now = datetime.utcnow().isoformat()
        
        logger.info(f"Importing corpus into '{self.lang_code}' DB. Tokens: {len(tokens)}")
        try:
            with self.conn:
                # Upsert Words
                self.conn.executemany(
                    """INSERT INTO dictionary (word, freq, is_user, created_at, updated_at) 
                       VALUES (?, ?, 0, ?, ?)
                       ON CONFLICT(word) DO UPDATE SET freq = freq + ?, updated_at = ?""",
                    [(w, f, now, now, f, now) for w, f in word_freq.items()]
                )
                # Upsert N-Grams
                self._upsert_ngrams_internal(tokens)
            logger.info(f"Corpus successfully imported to '{self.lang_code}'.")
        except sqlite3.Error as e:
            logger.error(f"Corpus import failed for '{self.lang_code}': {e}\n{traceback.format_exc()}")
            raise RuntimeError(f"Database error during import: {e}")

    def get_db_size_mb(self) -> float:
        try:
            return os.path.getsize(self.db_path) / (1024 * 1024)
        except OSError:
            return 0.0


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Language Profile & Advanced Text Corrector
# ═══════════════════════════════════════════════════════════════════

class LanguageProfile:
    def __init__(self, lang_code: str):
        self.lang_code = lang_code
        self.db = DatabaseManager(lang_code)
        self.words_freq: Dict[str, int] = {}
        self.words: Set[str] = set()
        self.user_words: Set[str] = set()
        self.bk = BKTree()
        self.bigram_counts: Dict[str, Counter] = defaultdict(Counter)
        self.trigram_counts: Counter = Counter()
        self.grammar_rules = self._init_grammar_rules()
        self.refresh_from_db()

    def refresh_from_db(self):
        logger.debug(f"Refreshing language profile from DB for '{self.lang_code}'")
        self.words_freq = self.db.load_words()
        self.words = set(self.words_freq.keys())
        self.user_words = self.db.load_user_words()
        self.bk = BKTree()
        self.bk.build_from_list(list(self.words))
        self.bigram_counts = self.db.load_bigrams()
        self.trigram_counts = self.db.load_trigrams()

    def _init_grammar_rules(self) -> List[Dict]:
        rules = []
        if self.lang_code == "en":
            rules.extend([
                {"pattern": re.compile(r'\b(your)\s+(going|coming|doing|being|making|having)\b', re.IGNORECASE), "message": "Did you mean 'you're' (you are)?", "replacement": r"you're \2"},
                {"pattern": re.compile(r'\b(the)\s+(the)\b', re.IGNORECASE), "message": "Repeated word detected.", "replacement": r"the"},
                {"pattern": re.compile(r'\b(a)\s+([aeiou]\w+)', re.IGNORECASE), "message": "Use 'an' before vowel sounds.", "replacement": r"an \2"},
            ])
        elif self.lang_code == "de":
            rules.append({"pattern": re.compile(r'\b(und)\s+(und)\b', re.IGNORECASE), "message": "Wiederholtes Wort.", "replacement": r"und"})
        return rules


class TextCorrector:
    def __init__(self):
        self.profiles: Dict[str, LanguageProfile] = {}
        self.current_lang = "en"
        self._build_profiles()

    def _build_profiles(self):
        for code in ["en", "es", "de"]:
            try:
                self.profiles[code] = LanguageProfile(code)
            except Exception as e:
                logger.critical(f"Failed to build profile for {code}: {e}")

    def set_language(self, lang: str):
        self.current_lang = lang

    def add_word(self, word: str, lang: str = None) -> str:
        lang = lang or self.current_lang
        word = word.lower().strip()
        if not word: return "Empty word."
        try:
            self.profiles[lang].db.add_word(word)
            self.profiles[lang].refresh_from_db()
            logger.info(f"Added word '{word}' to {lang}")
            return f"✓ '{word}' added to {lang.upper()} dictionary."
        except Exception as e:
            logger.error(f"Error adding word: {e}")
            return f"Error adding word: {e}"

    def remove_word(self, word: str, lang: str = None) -> str:
        lang = lang or self.current_lang
        word = word.lower().strip()
        try:
            if word in self.profiles[lang].user_words:
                self.profiles[lang].db.remove_user_word(word)
                self.profiles[lang].refresh_from_db()
                logger.info(f"Removed word '{word}' from {lang}")
                return f"✓ '{word}' removed from {lang.upper()} user dict."
            return f"'{word}' not in user dict."
        except Exception as e:
            logger.error(f"Error removing word: {e}")
            return f"Error removing word: {e}"

    def import_corpus(self, file_path: str, lang: str = None):
        lang = lang or self.current_lang
        try:
            text = Path(file_path).read_text(encoding='utf-8')
            self.profiles[lang].db.import_corpus(text)
            self.profiles[lang].refresh_from_db()
            return True, f"Imported corpus to {lang.upper()}. DB updated."
        except IOError as e:
            logger.error(f"File read error: {e}")
            return False, f"Failed to read file: {e}"
        except Exception as e:
            logger.error(f"Import error: {e}")
            return False, f"Import failed: {e}"

    @staticmethod
    def tokenize(text: str) -> List[Dict]:
        tokens = []
        for m in re.finditer(r"\w+|[^\w\s]|\s+", text, re.UNICODE):
            tokens.append({"text": m.group(), "start": m.start(), "end": m.end(), "is_word": bool(re.fullmatch(r"\w+", m.group()))})
        return tokens

    def generate_candidates(self, word: str, max_edit: int = 2, top_k: int = 8) -> List[str]:
        profile = self.profiles[self.current_lang]
        lw = word.lower()
        if lw in profile.words: return [lw]
        
        cand_set = set()
        if profile.bk.root:
            for term, d in profile.bk.query(lw, max_edit):
                if term in profile.words: cand_set.add(term)
                    
        letters = string.ascii_lowercase
        splits = [(lw[:i], lw[i:]) for i in range(len(lw) + 1)]
        edits1 = set([L + R[1:] for L, R in splits if R] + [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1] + [L + c + R[1:] for L, R in splits if R for c in letters] + [L + c + R for L, R in splits for c in letters])
        for w in edits1:
            if w in profile.words: cand_set.add(w)
                
        candidates = sorted(cand_set, key=lambda w: (-profile.words_freq.get(w, 0), levenshtein(lw, w)))
        return candidates[:top_k] if candidates else [lw]

    def _rank_candidates(self, misspelled: str, candidates: List[str], prev_word: Optional[str]) -> str:
        profile = self.profiles[self.current_lang]
        if not candidates: return misspelled
        if not prev_word: return max(candidates, key=lambda w: profile.words_freq.get(w, 1))
        best = max(candidates, key=lambda w: profile.bigram_counts.get(prev_word, {}).get(w, 0))
        if profile.bigram_counts.get(prev_word, {}).get(best, 0) == 0:
            return max(candidates, key=lambda w: profile.words_freq.get(w, 1))
        return best

    def correct_text_interactive(self, text: str) -> List[Dict]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        errors = []
        prev_word = None

        for tok in tokens:
            if not tok["is_word"]: continue
            word = tok["text"]
            lw = word.lower()
            if len(lw) <= 1 or lw.isdigit(): 
                prev_word = lw
                continue
            if lw in profile.words: 
                prev_word = lw
                continue
            
            candidates = self.generate_candidates(word)
            best = self._rank_candidates(lw, candidates, prev_word)
            errors.append({"type": "spelling", "start": tok["start"], "end": tok["end"], "original": word, "suggestion": best, "message": f"Unknown word. Did you mean '{best}'?", "all_candidates": candidates[:5]})
            prev_word = lw

        for rule in profile.grammar_rules:
            for m in rule["pattern"].finditer(text):
                suggestion = m.expand(rule["replacement"])
                errors.append({"type": "grammar", "start": m.start(), "end": m.end(), "original": m.group(), "suggestion": suggestion, "message": rule["message"], "all_candidates": [suggestion]})

        errors.sort(key=lambda e: e["start"])
        return errors

    def correct_beam_search(self, text: str, beam_width: int = 5) -> Tuple[str, float]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        word_tokens = [t for t in tokens if t["is_word"]]
        words = [t["text"].lower() for t in word_tokens]

        beams: List[Tuple[List[str], float]] = [([], 1.0)]
        total_tri = max(sum(profile.trigram_counts.values()), 1)

        for i, word in enumerate(words):
            new_beams = []
            cands = self.generate_candidates(word, top_k=beam_width)
            for seq, score in beams:
                for cand in cands:
                    if len(seq) >= 2:
                        reward = (profile.trigram_counts.get((seq[-2], seq[-1], cand), 0) + 1) / total_tri
                    elif len(seq) >= 1:
                        reward = (profile.bigram_counts.get(seq[-1], {}).get(cand, 0) + 1) / max(sum(profile.bigram_counts.get(seq[-1], {}).values()), 1)
                    else:
                        reward = profile.words_freq.get(cand, 1) / max(sum(profile.words_freq.values()), 1)
                    new_beams.append((seq + [cand], score * reward))
            beams = heapq.nlargest(beam_width, new_beams, key=lambda x: x[1])

        best_seq, best_score = max(beams, key=lambda x: x[1]) if beams else (words, 0.0)
        return self._reconstruct(tokens, word_tokens, best_seq), best_score

    def correct_mcts(self, text: str, iterations: int = 500) -> Tuple[str, float]:
        profile = self.profiles[self.current_lang]
        tokens = self.tokenize(text)
        word_tokens = [t for t in tokens if t["is_word"]]
        words = [t["text"] for t in word_tokens]

        best_tokens = words[:]
        best_score = self._score_sentence([w.lower() for w in best_tokens], profile)

        for _ in range(iterations):
            if not words: break
            i = random.randrange(len(words))
            candidates = self.generate_candidates(words[i])
            new_tokens = best_tokens[:]
            new_tokens[i] = random.choice(candidates)
            score = self._score_sentence([w.lower() for w in new_tokens], profile)
            if score > best_score:
                best_score = score
                best_tokens = new_tokens

        return self._reconstruct(tokens, word_tokens, [w.lower() for w in best_tokens]), best_score

    def _score_sentence(self, words: List[str], profile: LanguageProfile) -> float:
        freq_score = sum(profile.words_freq.get(w, 0) for w in words)
        grammar_penalty = sum(len(list(r["pattern"].finditer(" ".join(words)))) for r in profile.grammar_rules)
        return freq_score - 10 * grammar_penalty

    def _reconstruct(self, all_tokens, word_tokens, new_words) -> str:
        result, wi = [], 0
        for tok in all_tokens:
            if tok["is_word"] and wi < len(new_words):
                replacement = self._preserve_case(tok["text"], new_words[wi])
                result.append((tok["start"], tok["end"], replacement))
                wi += 1
        if not result: return "".join(t["text"] for t in all_tokens)
        parts, last_end = [], 0
        for start, end, repl in result:
            parts.append("".join(t["text"] for t in all_tokens if last_end <= t["start"] < start))
            parts.append(repl)
            last_end = end
        parts.append("".join(t["text"] for t in all_tokens if t["start"] >= last_end))
        return "".join(parts)

    @staticmethod
    def _preserve_case(original: str, replacement: str) -> str:
        if original.isupper(): return replacement.upper()
        if original and original[0].isupper(): return replacement.capitalize()
        return replacement

    @staticmethod
    def apply_corrections(text: str, errors: List[Dict], decisions: Dict) -> str:
        corrected = text
        for err in sorted(errors, key=lambda e: e["start"], reverse=True):
            decision = decisions.get(err["start"])
            if decision and decision != "ignore":
                corrected = corrected[:err["start"]] + decision + corrected[err["end"]:]
        return corrected

    def get_stats(self, text: str) -> Dict:
        tokens = self.tokenize(text)
        words = [t for t in tokens if t["is_word"]]
        profile = self.profiles.get(self.current_lang)
        unknown = 0
        if profile:
            unknown = sum(1 for w in words if w["text"].lower() not in profile.words and len(w["text"]) > 1)
        return {"chars": len(text), "words": len(words), "unknown_words": unknown}


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Worker Thread
# ═══════════════════════════════════════════════════════════════════

class CorrectionWorker(QThread):
    finished = Signal(object)
    def __init__(self, corrector, text, mode, **kwargs):
        super().__init__()
        self.corrector, self.text, self.mode, self.kwargs = corrector, text, mode, kwargs

    def run(self):
        try:
            if self.mode == "interactive":
                self.finished.emit({"errors": self.corrector.correct_text_interactive(self.text)})
            elif self.mode == "beam":
                c, s = self.corrector.correct_beam_search(self.text, self.kwargs.get("beam_width", 5))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "mcts":
                c, s = self.corrector.correct_mcts(self.text, self.kwargs.get("iterations", 500))
                self.finished.emit({"corrected": c, "score": s})
            elif self.mode == "import":
                ok, msg = self.corrector.import_corpus(self.kwargs["path"])
                self.finished.emit({"import_ok": ok, "import_msg": msg})
        except Exception as e:
            logger.error(f"Worker Thread Error: {e}\n{traceback.format_exc()}")
            self.finished.emit({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Custom Widgets
# ═══════════════════════════════════════════════════════════════════

class HighlightTextEdit(QTextEdit):
    def __init__(self, parent=None, readonly=False):
        super().__init__(parent)
        self.setReadOnly(readonly)
        font = QFont("Consolas", 11); font.setStyleHint(QFont.Monospace); self.setFont(font)

    def clear_highlights(self): self.setExtraSelections([])

    def highlight_errors(self, errors: List[Dict]):
        extra = []
        colors = {"spelling": QColor(255, 80, 80, 80), "grammar": QColor(80, 140, 255, 80), "contraction": QColor(255, 180, 40, 80)}
        underlines = {"spelling": QColor(255, 0, 0), "grammar": QColor(0, 80, 255), "contraction": QColor(200, 120, 0)}
        for err in errors:
            sel = QTextEdit.ExtraSelection()
            cursor = self.textCursor(); cursor.setPosition(err["start"]); cursor.setPosition(err["end"], QTextCursor.KeepAnchor)
            sel.cursor = cursor
            sel.format.setBackground(colors.get(err["type"], QColor(200, 200, 200, 80)))
            sel.format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
            sel.format.setUnderlineColor(underlines.get(err["type"], QColor(128, 128, 128)))
            extra.append(sel)
        self.setExtraSelections(extra)


class ErrorTableWidget(QTableWidget):
    decision_changed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["#", "Type", "Original", "Suggestion", "Message", "Action"])
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self._errors, self._decisions = [], {}

    def set_errors(self, errors: List[Dict]):
        self._errors, self._decisions = errors, {}
        self.setRowCount(len(errors))
        icons = {"spelling": "✏️", "grammar": "📖", "contraction": "📝"}
        for i, err in enumerate(errors):
            self.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.setItem(i, 1, QTableWidgetItem(f"{icons.get(err['type'], '❓')} {err['type'].capitalize()}"))
            self.setItem(i, 2, QTableWidgetItem(err["original"]))
            combo = QComboBox()
            for c in err.get("all_candidates", [err["suggestion"]]): combo.addItem(c)
            combo.currentTextChanged.connect(lambda text, start=err["start"]: self._on_combo(start, text))
            self.setCellWidget(i, 3, combo)
            self.setItem(i, 4, QTableWidgetItem(err.get("message", "")))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            for text, slot in [("✓", self._on_accept), ("✗", self._on_ignore), ("✎", self._on_custom)]:
                btn = QPushButton(text); btn.setFixedSize(28, 28)
                btn.clicked.connect(lambda _, start=err["start"], s=slot: s(start))
                action_layout.addWidget(btn)
            self.setCellWidget(i, 5, action_widget)

    def _on_accept(self, start: int):
        for err in self._errors:
            if err["start"] == start:
                self._decisions[start] = err["suggestion"]; self.decision_changed.emit(start, err["suggestion"]); break

    def _on_ignore(self, start: int):
        self._decisions[start] = "ignore"; self.decision_changed.emit(start, "ignore")

    def _on_custom(self, start: int):
        text, ok = QInputDialog.getText(self, "Custom Correction", "Enter your correction:")
        if ok and text.strip():
            self._decisions[start] = text.strip(); self.decision_changed.emit(start, text.strip())

    def _on_combo(self, start: int, text: str):
        if start in self._decisions and self._decisions[start] != "ignore":
            self._decisions[start] = text; self.decision_changed.emit(start, text)

    def get_decisions(self) -> Dict: return dict(self._decisions)
    def accept_all(self):
        for err in self._errors: self._decisions[err["start"]] = err["suggestion"]
    def ignore_all(self):
        for err in self._errors: self._decisions[err["start"]] = "ignore"


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Styles & Main Window
# ═══════════════════════════════════════════════════════════════════

DARK_STYLE = """
QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QTextEdit { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; padding: 8px; }
QTextEdit[readOnly="true"] { background-color: #1e1e2e; }
QLineEdit { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; }
QPushButton { background-color: #45475a; color: #cdd6f4; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #585b70; }
QPushButton#primaryBtn { background-color: #89b4fa; color: #1e1e2e; }
QPushButton#primaryBtn:hover { background-color: #74c7ec; }
QPushButton#dangerBtn { background-color: #f38ba8; color: #1e1e2e; }
QPushButton#successBtn { background-color: #a6e3a1; color: #1e1e2e; }
QComboBox { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px 8px; }
QComboBox QAbstractItemView { background-color: #181825; color: #cdd6f4; selection-background-color: #45475a; }
QTabWidget::pane { border: 1px solid #45475a; border-radius: 6px; }
QTabBar::tab { background-color: #313244; color: #cdd6f4; padding: 8px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #45475a; font-weight: bold; }
QTableWidget { background-color: #181825; alternate-background-color: #1e1e2e; color: #cdd6f4; gridline-color: #45475a; border: 1px solid #45475a; border-radius: 6px; }
QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 6px; border: 1px solid #45475a; font-weight: bold; }
QGroupBox { border: 1px solid #45475a; border-radius: 8px; margin-top: 12px; padding-top: 16px; font-weight: bold; }
QLabel#statsLabel { background-color: #313244; border-radius: 6px; padding: 6px 12px; }
QListWidget { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 6px; }
QListWidget::item:selected { background-color: #45475a; }
QSpinBox { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
QStatusBar { background-color: #181825; color: #a6adc8; border-top: 1px solid #45475a; }
QToolBar { background-color: #181825; border-bottom: 1px solid #45475a; spacing: 6px; padding: 4px; }
QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; background-color: #181825; color: #cdd6f4; }
QProgressBar::chunk { background-color: #89b4fa; border-radius: 3px; }
QScrollBar:vertical { background: #1e1e2e; width: 10px; }
QScrollBar::handle:vertical { background: #45475a; border-radius: 5px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""

LIGHT_STYLE = """
QMainWindow, QWidget { background-color: #eff1f5; color: #4c4f69; font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QTextEdit { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; padding: 8px; }
QTextEdit[readOnly="true"] { background-color: #e6e9ef; }
QLineEdit { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; }
QPushButton { background-color: #ccd0da; color: #4c4f69; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #bcc0cc; }
QPushButton#primaryBtn { background-color: #1e66f5; color: #ffffff; }
QPushButton#dangerBtn { background-color: #d20f39; color: #ffffff; }
QPushButton#successBtn { background-color: #40a02b; color: #ffffff; }
QComboBox { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 4px; padding: 4px 8px; }
QTabWidget::pane { border: 1px solid #bcc0cc; border-radius: 6px; }
QTabBar::tab { background-color: #e6e9ef; color: #4c4f69; padding: 8px 20px; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }
QTabBar::tab:selected { background-color: #ccd0da; font-weight: bold; }
QTableWidget { background-color: #ffffff; alternate-background-color: #e6e9ef; color: #4c4f69; gridline-color: #bcc0cc; border: 1px solid #bcc0cc; border-radius: 6px; }
QHeaderView::section { background-color: #e6e9ef; color: #4c4f69; padding: 6px; border: 1px solid #bcc0cc; font-weight: bold; }
QGroupBox { border: 1px solid #bcc0cc; border-radius: 8px; margin-top: 12px; padding-top: 16px; font-weight: bold; }
QLabel#statsLabel { background-color: #e6e9ef; border-radius: 6px; padding: 6px 12px; }
QListWidget { background-color: #ffffff; color: #4c4f69; border: 1px solid #bcc0cc; border-radius: 6px; }
QStatusBar { background-color: #e6e9ef; color: #6c6f85; border-top: 1px solid #bcc0cc; }
QToolBar { background-color: #e6e9ef; border-bottom: 1px solid #bcc0cc; spacing: 6px; padding: 4px; }
QProgressBar { border: 1px solid #bcc0cc; border-radius: 4px; text-align: center; background-color: #ffffff; color: #4c4f69; }
QProgressBar::chunk { background-color: #1e66f5; border-radius: 3px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            self.corrector = TextCorrector()
        except RuntimeError as e:
            logger.critical(f"Application cannot start due to DB init error: {e}")
            QMessageBox.critical(None, "Fatal Error", f"Database initialization failed:\n{e}\n\nCheck logs: {LOG_FILE}")
            sys.exit(1)

        self.current_errors = []
        self.worker = None
        self._dark_mode = True
        self._settings = QSettings("NlpCorrector", "AdvancedCorrector")

        self.setWindowTitle("✍️ Advanced NLP Text Corrector (Structured Isolated DBs)")
        self.setMinimumSize(1100, 750)
        self.resize(1300, 850)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._restore_settings()
        self._apply_theme()
        logger.info("Application UI initialized successfully.")

    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar"); toolbar.setMovable(False); self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("  Language: "))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English (en)", "Español (es)", "Deutsch (de)"])
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        toolbar.addWidget(self.lang_combo)
        toolbar.addSeparator(); toolbar.addWidget(QLabel(" Mode: "))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Interactive", "Beam Search", "MCTS"])
        toolbar.addWidget(self.mode_combo); toolbar.addSeparator()

        self.btn_check = QPushButton("🔍 Check Text"); self.btn_check.setObjectName("primaryBtn")
        self.btn_check.clicked.connect(self._check_text); toolbar.addWidget(self.btn_check)
        self.btn_apply = QPushButton("✅ Apply Corrections"); self.btn_apply.setObjectName("successBtn")
        self.btn_apply.clicked.connect(self._apply_corrections); self.btn_apply.setEnabled(False)
        toolbar.addWidget(self.btn_apply); toolbar.addSeparator()

        self.btn_theme = QPushButton("🌙"); self.btn_theme.setFixedSize(32, 32)
        self.btn_theme.clicked.connect(self._toggle_theme); toolbar.addWidget(self.btn_theme)

    def _build_central(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QVBoxLayout(central); main_layout.setContentsMargins(8, 8, 8, 8)
        self.tabs = QTabWidget(); main_layout.addWidget(self.tabs)
        self._build_correction_tab()
        self._build_file_tab()
        self._build_dictionary_tab()
        self._build_settings_tab()

    def _build_correction_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(8, 8, 8, 8)
        stats_layout = QHBoxLayout(); self.stats_labels = {}
        for key in ["Characters", "Words", "Unknown"]:
            lbl = QLabel(f"{key}: 0"); lbl.setObjectName("statsLabel")
            stats_layout.addWidget(lbl); self.stats_labels[key] = lbl
        stats_layout.addStretch(); layout.addLayout(stats_layout)

        splitter = QSplitter(Qt.Horizontal)
        input_group = QGroupBox("Input Text"); input_layout = QVBoxLayout(input_group)
        self.input_edit = HighlightTextEdit(); self.input_edit.textChanged.connect(self._update_stats)
        input_layout.addWidget(self.input_edit); splitter.addWidget(input_group)
        output_group = QGroupBox("Corrected Text"); output_layout = QVBoxLayout(output_group)
        self.output_edit = HighlightTextEdit(readonly=True); output_layout.addWidget(self.output_edit)
        splitter.addWidget(output_group); splitter.setSizes([600, 600]); layout.addWidget(splitter, stretch=3)

        error_group = QGroupBox("Detected Errors"); error_layout = QVBoxLayout(error_group)
        self.error_table = ErrorTableWidget(); self.error_table.decision_changed.connect(self._on_decision_changed)
        error_layout.addWidget(self.error_table)
        btn_row = QHBoxLayout()
        btn_accept_all = QPushButton("Accept All"); btn_accept_all.setObjectName("successBtn"); btn_accept_all.clicked.connect(self._accept_all)
        btn_ignore_all = QPushButton("Ignore All"); btn_ignore_all.setObjectName("dangerBtn"); btn_ignore_all.clicked.connect(self._ignore_all)
        self.error_count_label = QLabel("0 errors found"); btn_row.addWidget(btn_accept_all); btn_row.addWidget(btn_ignore_all)
        btn_row.addStretch(); btn_row.addWidget(self.error_count_label); error_layout.addLayout(btn_row)
        layout.addWidget(error_group, stretch=2); self.tabs.addTab(tab, "✍️ Correct Text")

    def _build_file_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(8, 8, 8, 8)
        file_row = QHBoxLayout(); self.file_path_edit = QLineEdit(); self.file_path_edit.setPlaceholderText("Select a text file…")
        file_row.addWidget(self.file_path_edit)
        btn_browse = QPushButton("📁 Browse"); btn_browse.clicked.connect(lambda: self.file_path_edit.setText(QFileDialog.getOpenFileName(self, "Open Text File")[0]))
        file_row.addWidget(btn_browse)
        btn_load = QPushButton("📂 Load"); btn_load.setObjectName("primaryBtn"); btn_load.clicked.connect(self._load_file)
        file_row.addWidget(btn_load); layout.addLayout(file_row)

        splitter = QSplitter(Qt.Horizontal)
        orig_group = QGroupBox("Original"); orig_layout = QVBoxLayout(orig_group)
        self.file_original_edit = HighlightTextEdit(readonly=True); orig_layout.addWidget(self.file_original_edit); splitter.addWidget(orig_group)
        corr_group = QGroupBox("Corrected"); corr_layout = QVBoxLayout(corr_group)
        self.file_corrected_edit = HighlightTextEdit(readonly=True); corr_layout.addWidget(self.file_corrected_edit); splitter.addWidget(corr_group)
        splitter.setSizes([500, 500]); layout.addWidget(splitter, stretch=3)

        btn_row = QHBoxLayout()
        btn_process = QPushButton("🔄 Process File"); btn_process.setObjectName("primaryBtn"); btn_process.clicked.connect(self._process_file)
        btn_save = QPushButton("💾 Save Corrected"); btn_save.setObjectName("successBtn"); btn_save.clicked.connect(self._save_corrected_file)
        btn_row.addStretch(); btn_row.addWidget(btn_process); btn_row.addWidget(btn_save)
        layout.addLayout(btn_row); self._file_original_text = ""; self.tabs.addTab(tab, "📁 File Mode")

    def _build_dictionary_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(8, 8, 8, 8)
        lang_row = QHBoxLayout(); lang_row.addWidget(QLabel("Language:"))
        self.dict_lang_combo = QComboBox(); self.dict_lang_combo.addItems(["en", "es", "de"])
        self.dict_lang_combo.currentTextChanged.connect(self._refresh_dictionary_list)
        lang_row.addWidget(self.dict_lang_combo); lang_row.addStretch()
        self.dict_search = QLineEdit(); self.dict_search.setPlaceholderText("🔍 Search…"); self.dict_search.textChanged.connect(self._filter_dictionary)
        lang_row.addWidget(self.dict_search); layout.addLayout(lang_row)
        self.dict_list = QListWidget(); self.dict_list.setAlternatingRowColors(True); layout.addWidget(self.dict_list, stretch=1)
        add_row = QHBoxLayout(); self.dict_word_input = QLineEdit(); self.dict_word_input.setPlaceholderText("Add word…"); self.dict_word_input.returnPressed.connect(self._add_dict_word)
        add_row.addWidget(self.dict_word_input)
        btn_add = QPushButton("➕ Add"); btn_add.setObjectName("successBtn"); btn_add.clicked.connect(self._add_dict_word); add_row.addWidget(btn_add)
        btn_remove = QPushButton("➖ Remove"); btn_remove.setObjectName("dangerBtn"); btn_remove.clicked.connect(self._remove_dict_word); add_row.addWidget(btn_remove)
        layout.addLayout(add_row)
        self.dict_info_label = QLabel(""); layout.addWidget(self.dict_info_label)
        self._refresh_dictionary_list(); self.tabs.addTab(tab, "📖 Dictionary")

    def _build_settings_tab(self):
        tab = QWidget(); layout = QVBoxLayout(tab); layout.setContentsMargins(8, 8, 8, 8)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content = QWidget(); cl = QVBoxLayout(content)

        theme_group = QGroupBox("Appearance"); tl = QHBoxLayout(theme_group)
        self.radio_dark = QRadioButton("Dark"); self.radio_light = QRadioButton("Light"); self.radio_dark.setChecked(True)
        self.radio_dark.toggled.connect(lambda c: self._set_theme(c)); tl.addWidget(self.radio_dark); tl.addWidget(self.radio_light); cl.addWidget(theme_group)

        param_group = QGroupBox("Correction Parameters"); pl = QFormLayout(param_group)
        self.spin_max_edit = QSpinBox(); self.spin_max_edit.setRange(1, 4); self.spin_max_edit.setValue(2); pl.addRow("Max edit distance:", self.spin_max_edit)
        self.spin_top_k = QSpinBox(); self.spin_top_k.setRange(1, 20); self.spin_top_k.setValue(8); pl.addRow("Top-K candidates:", self.spin_top_k)
        self.spin_beam_width = QSpinBox(); self.spin_beam_width.setRange(1, 20); self.spin_beam_width.setValue(5); pl.addRow("Beam width:", self.spin_beam_width)
        self.spin_mcts_iter = QSpinBox(); self.spin_mcts_iter.setRange(50, 5000); self.spin_mcts_iter.setValue(500); self.spin_mcts_iter.setSingleStep(100); pl.addRow("MCTS iterations:", self.spin_mcts_iter)
        cl.addWidget(param_group)

        db_group = QGroupBox("Isolated Language Databases (SQLite)"); dl = QVBoxLayout(db_group)
        dl.addWidget(QLabel("Each language uses its own DB file in a dedicated folder within the CWD."))
        btn_load_corpus = QPushButton("📂 Import Corpus to Active Language DB (Updates Dict & N-Grams)")
        btn_load_corpus.setObjectName("primaryBtn"); btn_load_corpus.clicked.connect(self._import_corpus_to_db); dl.addWidget(btn_load_corpus)
        self.db_info_label = QLabel(""); dl.addWidget(self.db_info_label)
        cl.addWidget(db_group)

        log_group = QGroupBox("Application Logs"); ll = QVBoxLayout(log_group)
        ll.addWidget(QLabel(f"Log File: {os.path.abspath(LOG_FILE)}"))
        btn_open_log = QPushButton("📂 Open Log File"); btn_open_log.clicked.connect(lambda: os.startfile(os.path.abspath(LOG_FILE)) if sys.platform == "win32" else os.system(f"open {os.path.abspath(LOG_FILE)}") if sys.platform == "darwin" else os.system(f"xdg-open {os.path.abspath(LOG_FILE)}"))
        ll.addWidget(btn_open_log)
        cl.addWidget(log_group)

        cl.addStretch(); scroll.setWidget(content); layout.addWidget(scroll); self.tabs.addTab(tab, "⚙️ Settings")
        self._update_db_info()

    def _build_statusbar(self):
        self.statusBar().showMessage("Ready")
        self.progress_bar = QProgressBar(); self.progress_bar.setFixedWidth(200); self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    # ── Theme & Settings ──────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(DARK_STYLE if self._dark_mode else LIGHT_STYLE)
        self.btn_theme.setText("☀️" if self._dark_mode else "🌙")

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode; self.radio_dark.setChecked(self._dark_mode); self._apply_theme()

    def _set_theme(self, is_dark): self._dark_mode = is_dark; self._apply_theme()

    def _restore_settings(self):
        self._dark_mode = self._settings.value("theme", "dark") == "dark"
        self.lang_combo.setCurrentIndex(int(self._settings.value("lang", 0)))

    def closeEvent(self, event):
        self._settings.setValue("theme", "dark" if self._dark_mode else "light")
        self._settings.setValue("lang", self.lang_combo.currentIndex())
        logger.info("Application closing. Saving settings.")
        event.accept()

    # ── Language & Stats ──────────────────────────────────────────

    def _on_lang_changed(self, index):
        self.corrector.set_language(["en", "es", "de"][index])
        self.dict_lang_combo.setCurrentIndex(index); self._update_stats(); self._update_db_info()

    def _update_stats(self):
        s = self.corrector.get_stats(self.input_edit.toPlainText())
        self.stats_labels["Characters"].setText(f"Characters: {s['chars']}")
        self.stats_labels["Words"].setText(f"Words: {s['words']}")
        self.stats_labels["Unknown"].setText(f"Unknown: {s['unknown_words']}")

    def _update_db_info(self):
        lang = self.corrector.current_lang
        p = self.corrector.profiles[lang]
        db_path = os.path.abspath(p.db.db_path)
        db_size = p.db.get_db_size_mb()
        self.db_info_label.setText(f"Lang: {lang.upper()} | Path: {db_path} | Size: {db_size:.2f} MB\nWords: {len(p.words)} | User Words: {len(p.user_words)} | Bigrams: {sum(len(v) for v in p.bigram_counts.values())} | Trigrams: {len(p.trigram_counts)}")

    # ── Correction Logic ──────────────────────────────────────────

    def _check_text(self):
        text = self.input_edit.toPlainText().strip()
        if not text: return
        mode_text = self.mode_combo.currentText()
        mode = "interactive" if mode_text == "Interactive" else ("beam" if mode_text == "Beam Search" else "mcts")
        kwargs = {}
        if mode == "beam": kwargs["beam_width"] = self.spin_beam_width.value()
        elif mode == "mcts": kwargs["iterations"] = self.spin_mcts_iter.value()

        logger.info(f"Starting text check. Mode: {mode}, Lang: {self.corrector.current_lang}")
        self.btn_check.setEnabled(False); self.progress_bar.setVisible(True); self.progress_bar.setRange(0, 0)
        self.worker = CorrectionWorker(self.corrector, text, mode, **kwargs)
        self.worker.finished.connect(self._on_correction_done); self.worker.start()

    def _on_correction_done(self, result):
        self.btn_check.setEnabled(True); self.progress_bar.setVisible(False)
        if "error" in result: 
            logger.error(f"Correction failed: {result['error']}")
            self.statusBar().showMessage(f"Error: {result['error']}")
            QMessageBox.critical(self, "Processing Error", result["error"])
            return

        if "errors" in result:
            self.current_errors = result["errors"]; self.current_decisions = {}
            self.input_edit.clear_highlights(); self.input_edit.highlight_errors(self.current_errors)
            self.error_table.set_errors(self.current_errors)
            self.error_count_label.setText(f"{len(self.current_errors)} errors found")
            self.btn_apply.setEnabled(bool(self.current_errors))
            self.statusBar().showMessage(f"Found {len(self.current_errors)} error(s).")
            logger.info(f"Interactive check found {len(self.current_errors)} errors.")
        else:
            self.output_edit.setPlainText(result["corrected"])
            self.error_table.setRowCount(0); self.error_count_label.setText(f"Auto-corrected (score: {result['score']:.4f})")
            self.btn_apply.setEnabled(False); self.statusBar().showMessage("Auto-correction complete.")
            logger.info("Auto-correction complete.")

    def _apply_corrections(self):
        if not self.current_errors: return
        decisions = self.error_table.get_decisions()
        for err in self.current_errors:
            if err["start"] not in decisions: decisions[err["start"]] = err["suggestion"]
        self.output_edit.setPlainText(TextCorrector.apply_corrections(self.input_edit.toPlainText(), self.current_errors, decisions))
        self.input_edit.clear_highlights(); self.btn_apply.setEnabled(False)
        logger.info("Corrections applied to text.")

    def _accept_all(self): self.error_table.accept_all()
    def _ignore_all(self): self.error_table.ignore_all()
    def _on_decision_changed(self, start, decision): self.current_decisions[start] = decision

    # ── File Logic ────────────────────────────────────────────────

    def _load_file(self):
        path = self.file_path_edit.text().strip()
        if not path: return
        try:
            self._file_original_text = Path(path).read_text(encoding='utf-8')
            self.file_original_edit.setPlainText(self._file_original_text); self.file_corrected_edit.clear()
            logger.info(f"Loaded file: {path}")
        except IOError as e:
            logger.error(f"Failed to load file: {e}")
            QMessageBox.critical(self, "File Error", str(e))

    def _process_file(self):
        if not self._file_original_text: return
        self.btn_check.setEnabled(False); self.progress_bar.setVisible(True); self.progress_bar.setRange(0, 0)
        mode_text = self.mode_combo.currentText()
        mode = "interactive" if mode_text == "Interactive" else ("beam" if mode_text == "Beam Search" else "mcts")
        self.worker = CorrectionWorker(self.corrector, self._file_original_text, mode)
        self.worker.finished.connect(self._on_file_done); self.worker.start()

    def _on_file_done(self, result):
        self.btn_check.setEnabled(True); self.progress_bar.setVisible(False)
        if "error" in result: 
            logger.error(f"File processing failed: {result['error']}")
            self.statusBar().showMessage(result["error"]); return
        if "errors" in result:
            errors = result["errors"]; decisions = {e["start"]: e["suggestion"] for e in errors}
            self.file_corrected_edit.setPlainText(TextCorrector.apply_corrections(self._file_original_text, errors, decisions))
            self.file_original_edit.highlight_errors(errors); self.statusBar().showMessage(f"Corrected {len(errors)} errors.")
        else:
            self.file_corrected_edit.setPlainText(result["corrected"]); self.statusBar().showMessage("Auto-correction complete.")

    def _save_corrected_file(self):
        text = self.file_corrected_edit.toPlainText()
        if not text: return
        path, _ = QFileDialog.getSaveFileName(self, "Save", "corrected.txt", "Text Files (*.txt)")
        if path:
            try: 
                Path(path).write_text(text, encoding='utf-8')
                self.statusBar().showMessage(f"Saved to {path}")
                logger.info(f"Saved corrected file to {path}")
            except IOError as e:
                logger.error(f"Failed to save file: {e}")
                QMessageBox.critical(self, "Save Error", str(e))

    # ── Dictionary Logic ──────────────────────────────────────────

    def _refresh_dictionary_list(self):
        lang = self.dict_lang_combo.currentText()
        profile = self.corrector.profiles.get(lang)
        if not profile: return
        self.dict_list.clear()
        for w in sorted(profile.words):
            is_user = w in profile.user_words
            self.dict_list.addItem(f"{'⭐ ' if is_user else ''}{w}")
        self.dict_info_label.setText(f"Total: {len(profile.words)} (User: {len(profile.user_words)})")

    def _filter_dictionary(self):
        search = self.dict_search.text().lower().strip()
        for i in range(self.dict_list.count()):
            self.dict_list.item(i).setHidden(bool(search) and search not in self.dict_list.item(i).text().lower())

    def _add_dict_word(self):
        word = self.dict_word_input.text().strip()
        if not word: return
        result = self.corrector.add_word(word, self.dict_lang_combo.currentText())
        self.dict_word_input.clear(); self._refresh_dictionary_list(); self._update_db_info(); self.statusBar().showMessage(result)

    def _remove_dict_word(self):
        current = self.dict_list.currentItem()
        if not current: return
        word = current.text().replace("⭐ ", "")
        result = self.corrector.remove_word(word, self.dict_lang_combo.currentText())
        self._refresh_dictionary_list(); self._update_db_info(); self.statusBar().showMessage(result)

    def _import_corpus_to_db(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Corpus to DB", "", "Text Files (*.txt)")
        if not path: return
        self.progress_bar.setVisible(True); self.progress_bar.setRange(0, 0); self.btn_check.setEnabled(False)
        self.worker = CorrectionWorker(self.corrector, "", "import", path=path)
        self.worker.finished.connect(self._on_import_done); self.worker.start()

    def _on_import_done(self, result):
        self.btn_check.setEnabled(True); self.progress_bar.setVisible(False)
        if result.get("import_ok"):
            self._refresh_dictionary_list(); self._update_db_info()
            self.statusBar().showMessage(result["import_msg"])
            logger.info(result["import_msg"])
            QMessageBox.information(self, "Success", result["import_msg"] + "\n\nIsolated DB updated.")
        else:
            logger.error(result.get("import_msg", "Unknown error"))
            QMessageBox.critical(self, "Import Error", result.get("import_msg", "Unknown error"))


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Entry Point
# ═══════════════════════════════════════════════════════════════════

def main():
    # Initialize logging system first
    setup_logging()
    logger.info("Starting Application...")

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("NLP Corrector")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Unhandled exception at top level: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()