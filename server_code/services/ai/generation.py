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

  def _gpt4_generate(prompt_text, transcription_text):
    """Call GPT-4 API with retries and back-off."""
    for attempt in range(RETRY_LIMIT):
      try:
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

        return response.choices[0].message.content
      except Exception as e:
        wait = 2**attempt
        print(
          f"[WARN] GPT-4 attempt {attempt + 1}/{RETRY_LIMIT} failed: {e}. "
          f"Retrying in {wait}s..."
        )
        if attempt < RETRY_LIMIT - 1:
          time.sleep(wait)
    # If we get here, all retries failed
    raise Exception("GPT-4 report generation failed after multiple attempts")

  try:
    generation_prompt = get_prompt("generation", language)
    if not generation_prompt:
      raise Exception("Could not find the 'generation' prompt in the database.")
    result = _gpt4_generate(generation_prompt, transcription)
    print("[DEBUG] Report generation done")
    return result

  except Exception as e:
    print(f"[ERROR] generate_report: {e}")
    raise Exception(f"Error generating report: {e}")
