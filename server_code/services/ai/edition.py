import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from . import (
  client,
  RETRY_LIMIT,
  DEFAULT_MODEL,
  DEFAULT_TEMPERATURE,
  DEFAULT_MAX_TOKENS,
)
from ..prompts_service import get_prompt
from ...logging_server import get_logger

logger = get_logger(__name__)


@anvil.server.callable
def edit_report(transcription, report, language):
  """
  Processes transcribed voice commands to edit a veterinary report.

  Args:
      transcription (str): The transcribed voice command with editing instructions
      report (str): The current report content to be edited

  Returns:
      str: The edited report content
  """
  logger.info("Starting report editing process.")
  logger.debug(f"Language for edition: {language}")
  logger.debug(f"Edition command (transcription): {transcription}")
  logger.debug(f"Original report content (first 100 chars): {report[:100]}")

  edition_prompt = get_prompt("edition", language)
  if not edition_prompt:
    logger.error(f"Could not find the 'edition' prompt for language '{language}'.")
    raise Exception("Could not find the 'edition' prompt in the database.")

  logger.debug("Edition prompt loaded successfully.")

  try:
    system_prompt = edition_prompt
    user_prompt = f"Report: {report}\nTranscription: {transcription}"

    messages = [
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
    ]

    logger.debug("Making API call to edit report...")
    response = client.chat.completions.create(
      model=DEFAULT_MODEL,
      messages=messages,
      temperature=DEFAULT_TEMPERATURE,
      max_tokens=DEFAULT_MAX_TOKENS,
    )

    result = response.choices[0].message.content
    logger.info("Report edited successfully.")
    logger.debug(f"Edited report (first 100 chars): {result[:100]}")
    return result

  except Exception as e:
    logger.error(f"GPT-4 API error during editing: {str(e)}", exc_info=True)
    raise Exception(f"Error editing report: {str(e)}")
