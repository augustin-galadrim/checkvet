# In server_code/services/ai/prompts_service.py
import anvil.server
from anvil.tables import app_tables
from ..logging_server import get_logger
logger = get_logger(__name__)

@anvil.server.callable
def get_prompt(task, language):
  """Fetches a specific prompt from the database."""
  row = app_tables.prompts.get(task=task, language=language)
  if row:
    return row["text"]
    # Fallback to English if the specified language is not found
  if language != "en":
    row = app_tables.prompts.get(task=task, language="en")
    if row:
      return row["text"]
  return None  # Or raise an error
