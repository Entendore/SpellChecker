import re
import random
from collections import defaultdict

# ------------------------------
# Levenshtein distance
# ------------------------------
def levenshtein(a, b):
    n, m = len(a), len(b)
    dp = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1): dp[i][0] = i
    for j in range(m+1): dp[0][j] = j
    for i in range(1,n+1):
        for j in range(1,m+1):
            if a[i-1]==b[j-1]:
                dp[i][j]=dp[i-1][j-1]
            else:
                dp[i][j]=1+min(dp[i-1][j-1], dp[i][j-1], dp[i-1][j])
    return dp[n][m]

# ------------------------------
# BK-tree
# ------------------------------
class BKNode:
    def __init__(self, word):
        self.word = word
        self.children = {}

class BKTree:
    def __init__(self):
        self.root = None
    
    def add(self, word):
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
    
    def query(self, word, max_dist):
        result = []
        def dfs(node):
            dist = levenshtein(word, node.word)
            if dist <= max_dist:
                result.append((node.word, dist))
            for d in range(dist-max_dist, dist+max_dist+1):
                child = node.children.get(d)
                if child:
                    dfs(child)
        if self.root:
            dfs(self.root)
        return result

# ------------------------------
# Multi-language dictionaries
# ------------------------------
DICTIONARIES = {
    "en": ["he","she","walk","walks","go","goes","to","the","school","buy","buys","an","apple","is","on","table","and","yesterday"],
    "es": ["ella","camina","caminar","va","a","la","escuela","compra","una","manzana","está","en","mesa","y","ayer"],
    "de": ["sie","geht","gehen","zur","schule","kauft","ein","apfel","ist","auf","tisch","und","gestern"]
}

class LanguageProfile:
    def __init__(self, words):
        self.words = set(words)
        self.freqs = {w:1 for w in words}
        self.bk = BKTree()
        for w in words:
            self.bk.add(w)

def build_profile(lang="en"):
    words = DICTIONARIES[lang]
    return LanguageProfile(words)

# ------------------------------
# Tokenization / detokenization
# ------------------------------
def tokenize(sentence):
    return re.findall(r"\w+|[^\w\s]", sentence, re.UNICODE)

def detokenize(tokens):
    out = ""
    for t in tokens:
        if re.match(r'^\w+$', t):
            if out and not out.endswith(" "):
                out += " "
            out += t
        else:
            out += t
    return out.strip()

# ------------------------------
# Candidate generation
# ------------------------------
def generate_candidates(word, profile, max_edit=2, top_k=8):
    lw = word.lower()
    cand_set = set()
    if profile.bk.root:
        for term, d in profile.bk.query(lw, max_edit):
            if term in profile.words:
                cand_set.add(term)
    if lw in profile.words:
        cand_set.add(lw)
    candidates = list(cand_set)
    candidates.sort(key=lambda w: (-profile.freqs.get(w,0), levenshtein(lw,w)))
    return candidates[:top_k] if candidates else [lw]

# ------------------------------
# POS tags (dummy)
# ------------------------------
def pos_tags(tokens):
    verbs_en = ["go","walk","buy","is","are","eat","write","run","play","walks","buys","goes"]
    verbs_es = ["camina","caminar","va","compra","está"]
    verbs_de = ["geht","gehen","kauft","ist"]
    tags = []
    for t in tokens:
        if t.lower() in verbs_en + verbs_es + verbs_de:
            tags.append("VERB")
        else:
            tags.append("OTHER")
    return tags

# ------------------------------
# Grammar rules
# ------------------------------
GRAMMAR_RULES_EN = [
    lambda tokens, tags, profile: [(i+1,"insert 'and'","and") for i in range(len(tokens)-1) if tags[i]=="VERB" and tags[i+1]=="VERB"],
    lambda tokens, tags, profile: [(i,"insert 'the'","the") for i in range(1,len(tokens)) if tokens[i].lower() in ["apple","table","school"] and tokens[i-1].lower() not in ["a","an","the"]]
]

GRAMMAR_RULES_ES = [
    lambda tokens, tags, profile: [(i+1,"insert 'y'","y") for i in range(len(tokens)-1) if tags[i]=="VERB" and tags[i+1]=="VERB"]
]

GRAMMAR_RULES_DE = [
    lambda tokens, tags, profile: [(i+1,"insert 'und'","und") for i in range(len(tokens)-1) if tags[i]=="VERB" and tokens[i+1]=="VERB"]
]

# ------------------------------
# Scoring
# ------------------------------
def score_sentence(tokens, profile, grammar_rules):
    grammar_issues = sum(len(rule(tokens, pos_tags(tokens), profile)) for rule in grammar_rules)
    freq_score = sum(profile.freqs.get(t.lower(),0) for t in tokens if t.isalpha())
    return freq_score - 2 * grammar_issues

# ------------------------------
# MCTS correction
# ------------------------------
def mcts_correct(tokens, profile, grammar_rules, iterations=500):
    best_tokens = tokens[:]
    best_score = score_sentence(tokens, profile, grammar_rules)
    for _ in range(iterations):
        i = random.randrange(len(tokens))
        candidates = generate_candidates(tokens[i], profile)
        new_tokens = tokens[:]
        new_tokens[i] = random.choice(candidates)
        for rule in grammar_rules:
            errs = rule(new_tokens, pos_tags(new_tokens), profile)
            for idx, _, val in errs:
                if idx < len(new_tokens):
                    new_tokens.insert(idx,val)
        score = score_sentence(new_tokens, profile, grammar_rules)
        if score > best_score:
            best_score = score
            best_tokens = new_tokens
    return best_tokens, best_score

# ------------------------------
# Correct sentence interface
# ------------------------------
def correct_sentence(sentence, profile, grammar_rules, planner="mcts", iterations=500):
    tokens = tokenize(sentence)
    if planner=="beam":
        for i in range(len(tokens)):
            candidates = generate_candidates(tokens[i], profile)
            tokens[i] = candidates[0]
        corrected_tokens = tokens
        score = score_sentence(tokens, profile, grammar_rules)
    else:
        corrected_tokens, score = mcts_correct(tokens, profile, grammar_rules, iterations)
    corrected_sentence = detokenize(corrected_tokens)
    return corrected_sentence, score

# ------------------------------
# Demo sentences
# ------------------------------
demo_sentences = {
    "en": ["She walk to the schhol and buy an aple.", "He go to shcool yesterday."],
    "es": ["Ella caminar a la escuel y compra un manzana.", "Ella va a la escule ayer."],
    "de": ["Sie geht zur schule und kauft ein apfel.", "Sie gehen zur schule gestern."]
}

# ------------------------------
# Run demo
# ------------------------------
if __name__=="__main__":
    for lang, sentences in demo_sentences.items():
        profile = build_profile(lang)
        grammar_rules = {
            "en": GRAMMAR_RULES_EN,
            "es": GRAMMAR_RULES_ES,
            "de": GRAMMAR_RULES_DE
        }[lang]
        
        print(f"\n--- Language: {lang.upper()} ---")
        for s in sentences:
            corrected, score = correct_sentence(s, profile, grammar_rules, planner="mcts", iterations=400)
            print("Original :", s)
            print("Corrected:", corrected)
            print("Score    :", score)
