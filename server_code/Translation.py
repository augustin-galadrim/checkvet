import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def get_translations_for_lang(lang_code):
  """Fetches all translations for a given language from the Data Table."""
  translations = {}
  for row in app_tables.translations.search():
    # Ensure the column exists before accessing it
    if row[lang_code]:
      translations[row['key']] = row[lang_code]
  return translations