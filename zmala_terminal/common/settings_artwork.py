"""Packaged pictograms and shared language flags; no fonts or network needed."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets/settings'
LANGUAGE_FLAGS = {
    'de': 'de', 'en': 'gb', 'es': 'es', 'fr': 'fr', 'pl': 'pl', 'pt': 'pt',
    'el': 'gr', 'ru': 'ru', 'ur': 'pk', 'ar': 'sa', 'hi': 'in', 'bn': 'bd',
    'th': 'th', 'ko': 'kr', 'ja': 'jp', 'zh-Hans': 'cn',
}


# @llr LLR-TERM-CONFIG-019
def artwork_path(key, language='en'):
    if key == 'language':
        return ASSETS / 'flags' / (LANGUAGE_FLAGS[language]+'.png')
    return ASSETS / (key+'.png')
