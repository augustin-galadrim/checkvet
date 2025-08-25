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
def format_report(transcription, template, language):
  """Generate report using GPT-4"""
  logger.info("Starting report formatting.")
  logger.debug(f"Language for formatting: {language}")
  logger.debug(f"Incoming transcription (first 100 chars): {transcription[:100]}")
  logger.debug(f"Template for formatting (first 100 chars): {template[:100]}")

  formatting_prompt_template = get_prompt("formatting", language)
  if not formatting_prompt_template:
    logger.error(f"Could not find the 'formatting' prompt for language '{language}'.")
    raise Exception("Could not find the 'formatting' prompt in the database.")

  logger.debug("Formatting prompt loaded successfully.")

  try:
    user_prompt = f"""
    Transcription: {transcription}\n Template: {template}
    """

    messages = [
      {"role": "system", "content": formatting_prompt_template},
      {"role": "user", "content": user_prompt},
    ]

    logger.debug("Making API call to format report...")
    response = client.chat.completions.create(
      model=DEFAULT_MODEL,
      messages=messages,
      temperature=DEFAULT_TEMPERATURE,
      max_tokens=DEFAULT_MAX_TOKENS,
    )

    result = response.choices[0].message.content
    logger.info("Report formatting successful.")
    logger.debug(f"Formatted report (first 100 chars): {result[:100]}")
    return result

  except Exception as e:
    logger.error(f"GPT-4 API error during formatting: {str(e)}", exc_info=True)
    raise Exception("Error generating report")