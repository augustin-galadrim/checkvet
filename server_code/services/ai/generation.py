import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import time
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
def generate_report(transcription, language):
  """
  Generate report using GPT-4.
  Includes retry mechanism with exponential backoff for API failures.
  """
  logger.info("Starting report generation from transcription.")
  logger.debug(f"Language for generation: {language}")
  logger.debug(f"Incoming transcription (first 100 chars): {transcription[:100]}")

  def _gpt4_generate(prompt_text, transcription_text):
    """Call GPT-4 API with retries and back-off."""
    for attempt in range(RETRY_LIMIT):
      try:
        logger.debug(f"GPT-4 generation attempt {attempt + 1}/{RETRY_LIMIT}.")
        messages = [
          {"role": "system", "content": prompt_text},
          {"role": "user", "content": transcription_text},
        ]

        response = client.chat.completions.create(
          model=DEFAULT_MODEL,
          messages=messages,
          temperature=DEFAULT_TEMPERATURE,
          max_tokens=DEFAULT_MAX_TOKENS,
        )
        logger.debug("GPT-4 API call successful.")
        return response.choices[0].message.content

      except Exception as e:
        wait = 2**attempt
        logger.warning(
          f"GPT-4 generation attempt {attempt + 1}/{RETRY_LIMIT} failed: {e}. "
          f"Retrying in {wait}s..."
        )
        if attempt < RETRY_LIMIT - 1:
          time.sleep(wait)

    logger.error("GPT-4 report generation failed after multiple attempts.", exc_info=True)
    raise Exception("GPT-4 report generation failed after multiple attempts")

  try:
    generation_prompt = get_prompt("generation", language)
    if not generation_prompt:
      logger.error(f"Could not find the 'generation' prompt for language '{language}'.")
      raise Exception("Could not find the 'generation' prompt in the database.")

    logger.debug("Generation prompt loaded successfully.")
    result = _gpt4_generate(generation_prompt, transcription)

    logger.info("Report generation successful.")
    logger.debug(f"Generated report content (first 100 chars): {result[:100]}")
    return result

  except Exception as e:
    logger.error(f"An error occurred in generate_report: {e}", exc_info=True)
    raise Exception(f"Error generating report: {e}")