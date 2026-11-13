"""Prompts that make Whisper write down fillers instead of smoothing them over.

Whisper leaves most fillers out of its transcript. A prompt full of fillers in the
right language makes the `small` model keep them. Add a language by copying a line.
"""
PROMPTS = {
    "es": "Eh, ehh, eee, mmm, yyy, y... pues, vale, o sea... ehh, mmm.",
    "en": "Um, uh, umm, uhh, like, you know, so... I mean, hmm, uh.",
    "pt": "É, éé, hum, tipo, né, então... ah, hmm, é.",
    "fr": "Euh, euhh, ben, bah, genre, en fait... hum, euh.",
    "it": "Ehm, eh, cioè, tipo, allora... mmm, ehm.",
    "de": "Äh, ähm, öh, also, halt, sozusagen... hm, äh.",
}


def prompt_for(language):
    return PROMPTS.get(language, "Um, uh, mmm, hmm... uh, mmm.")
