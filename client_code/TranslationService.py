import anvil.server
from . import Locales

TRANSLATION_MODE = "local"

TRANSLATIONS = {}
CURRENT_LANG = "en"


def load_language(lang_code="en"):
  """
  Loads translations for the given language code based on the TRANSLATION_MODE.
  """
  global TRANSLATIONS, CURRENT_LANG
  try:
    lang_code = lang_code.lower()

    if TRANSLATION_MODE == "database":
      print(f"Loading language '{lang_code}' from the database.")
      # Use the existing server call to fetch translations
      TRANSLATIONS = anvil.server.call_s("get_translations_for_lang", lang_code)
    else:  # "local" mode
      print(f"Loading language '{lang_code}' from the local module.")
      # Fetch the translations from the LOCALES dictionary in the Locales.py module
      TRANSLATIONS = Locales.LOCALES.get(lang_code, {})

    CURRENT_LANG = lang_code
    print(f"Successfully loaded language: {lang_code} in '{TRANSLATION_MODE}' mode.")

  except Exception as e:
    print(f"Could not load '{lang_code}', falling back to 'en'. Error: {e}")
    # Fallback logic for both modes
    if lang_code != "en":
      if TRANSLATION_MODE == "local":
        TRANSLATIONS = Locales.LOCALES.get("en", {})
        CURRENT_LANG = "en"
      else:
        try:
          TRANSLATIONS = anvil.server.call_s("get_translations_for_lang", "en")
          CURRENT_LANG = "en"
        except Exception as fallback_e:
          print(f"Critical: Fallback to load 'en' from database also failed. Error: {fallback_e}")
          TRANSLATIONS = {}  # Ensure translations is an empty dict on total failure
          CURRENT_LANG = "en"


def t(key, **kwargs):
  """
  Translates a key using the currently loaded language dictionary.
  If the key is not found, it returns the key itself wrapped in angle brackets.
  """
  template = TRANSLATIONS.get(key, f"<{key}>")
  return template.format(**kwargs)