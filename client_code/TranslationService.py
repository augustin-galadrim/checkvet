import anvil.server

TRANSLATIONS = {}
CURRENT_LANG = 'en' # Default language

def load_language(lang_code='en'):
  """Loads a language into the global TRANSLATIONS dictionary."""
  global TRANSLATIONS, CURRENT_LANG
  try:
    lang_code = lang_code.lower()
    # Use call_cache to automatically handle caching on the client
    TRANSLATIONS = anvil.server.call('get_translations_for_lang', lang_code)
    CURRENT_LANG = lang_code
    print(f"Successfully loaded language: {lang_code}")
  except Exception as e:
    print(f"Could not load '{lang_code}', falling back to 'en'. Error: {e}")
    if lang_code != 'en':
      load_language('en')

def t(key, **kwargs):
  """The main translation function. Gets a translation by its key."""
  template = TRANSLATIONS.get(key, f"<{key}>")
  return template.format(**kwargs)