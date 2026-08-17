import re
import heapq
from collections import Counter
from nltk import trigrams, word_tokenize

# -----------------------
# Spell Correction
# -----------------------
def words(text):
    return re.findall(r'\w+', text.lower())

# Load corpus and create vocabulary
with open('big.txt', 'r', encoding='utf-8') as f:
    corpus = f.read()

WORD_COUNTS = Counter(words(corpus))

def P(word, N=sum(WORD_COUNTS.values())):
    return WORD_COUNTS[word] / N

def edits1(word):
    letters    = 'abcdefghijklmnopqrstuvwxyz'
    splits     = [(word[:i], word[i:]) for i in range(len(word)+1)]
    deletes    = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1]+R[0]+R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts    = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)

def known(words):
    return set(w for w in words if w in WORD_COUNTS)

def candidates(word):
    return known([word]) or known(edits1(word)) or [word]

# -----------------------
# N-gram Language Model
# -----------------------
tokens = word_tokenize(corpus.lower())
trigrams_list = list(trigrams(tokens))
trigram_freq = Counter(trigrams_list)
total_trigrams = sum(trigram_freq.values())

def trigram_score(triplet):
    return (trigram_freq[triplet] + 1) / total_trigrams  # Laplace smoothing

# -----------------------
# Beam Search + MDP
# -----------------------
def beam_search_mdp(sentence, beam_width=5):
    words_list = word_tokenize(sentence.lower())
    beams = [([], 1)]  # (current_sequence, cumulative_score)

    for i, word in enumerate(words_list):
        new_beams = []
        word_cands = candidates(word)

        for seq, score in beams:
            for cand in word_cands:
                # Reward based on trigram
                if len(seq) >= 2:
                    tri = (seq[-2], seq[-1], cand)
                    reward = trigram_score(tri)
                else:
                    reward = 1  # beginning of sentence
                new_score = score * reward
                new_beams.append((seq + [cand], new_score))

        # Keep top beam_width sequences
        beams = heapq.nlargest(beam_width, new_beams, key=lambda x: x[1])

    best_sequence = max(beams, key=lambda x: x[1])[0]
    return " ".join(best_sequence)

# -----------------------
# Example
# -----------------------
sentence = "I love progrmming in Pythn and writting code"
corrected = beam_search_mdp(sentence, beam_width=5)

print("Original:", sentence)
print("Corrected:", corrected)
