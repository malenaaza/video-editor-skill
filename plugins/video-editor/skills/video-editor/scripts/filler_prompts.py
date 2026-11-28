"""Prompts that make Whisper write down fillers instead of smoothing them over.

Whisper leaves most fillers out of its transcript. A prompt full of fillers in the
right language makes the `small` model keep them. Add a language by copying a line.
"""
import re

PROMPTS = {
    "es": "Eh, ehh, eee, mmm, yyy, y... pues, vale, o sea... ehh, mmm.",
    "en": "Um, uh, umm, uhh, like, you know, so... I mean, hmm, uh.",
    "pt": "É, éé, hum, tipo, né, então... ah, hmm, é.",
    "fr": "Euh, euhh, ben, bah, genre, en fait... hum, euh.",
    "it": "Ehm, eh, cioè, tipo, allora... mmm, ehm.",
    "de": "Äh, ähm, öh, also, halt, sozusagen... hm, äh.",
}


DEFAULT = "Um, uh, mmm, hmm... uh, mmm."

# Whisper also takes language names ("spanish"), and my-setup.md writes regions ("es_ES", "Spanish (Spain)").
NAMES = {"spanish": "es", "español": "es", "castellano": "es", "english": "en", "inglés": "en",
         "portuguese": "pt", "português": "pt", "french": "fr", "français": "fr", "italian": "it",
         "italiano": "it", "german": "de", "deutsch": "de"}


def code(language):
    """'es', 'es_ES', 'es-MX', 'ES', 'Spanish', 'Spanish (Spain)' -> 'es'; unknown or empty -> ''."""
    word = re.split(r"[-_ (]", (language or "").strip().lower(), maxsplit=1)[0]
    return NAMES.get(word, word)


def prompt_for(language):
    return PROMPTS.get(code(language), DEFAULT)
