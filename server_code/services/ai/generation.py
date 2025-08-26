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

from . import transcription
from . import formatting

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

    logger.error(
      "GPT-4 report generation failed after multiple attempts.", exc_info=True
    )
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


@anvil.server.callable
def process_audio_for_report(audio_blob, language, mime_type, template_html):
  """
  Launches the full audio-to-report pipeline as a background task.
  This is the primary entry point for the client.
  """
  print("Launching report creation background task...")
  task = anvil.server.launch_background_task(
    "bg_create_report_from_audio", audio_blob, language, mime_type, template_html
  )
  return task


@anvil.server.background_task
def bg_create_report_from_audio(audio_blob, language, mime_type, template_html):
  """
  Full pipeline background task:
  1. Transcribes audio.
  2. Generates a structured report from the transcription.
  3. Formats the report into the final HTML.
  This version includes progress updates for the client.
  """
  try:
    # Step 1: Transcribe Audio
    anvil.server.task_state["step"] = (
      "feedback_transcribing"  # Set state for the client
    )
    print("Pipeline [1/3]: Transcribing audio...")
    raw_transcription = transcription.transcribe_audio(audio_blob, language, mime_type)
    print(f"Pipeline [1/3] SUCCESS. Transcription: {raw_transcription[:100]}...")

    # Step 2: Generate Report from the transcription
    anvil.server.task_state["step"] = "feedback_generating"  # Set state for the client
    print("Pipeline [2/3]: Generating structured report...")
    report_content = generate_report(raw_transcription, language)
    print("Pipeline [2/3] SUCCESS.")

    # Step 3: Format the report into the final HTML
    anvil.server.task_state["step"] = "feedback_formatting"  # Set state for the client
    print("Pipeline [3/3]: Formatting final report...")
    final_html = formatting.format_report(report_content, template_html, language)
    print("Pipeline [3/3] SUCCESS. Pipeline complete.")

    return {
      "success": True,
      "final_html": final_html,
      "raw_transcription": raw_transcription,
    }

  except Exception as e:
    print(f"ERROR: The report creation pipeline failed. Error: {e}")
    return {"success": False, "error": str(e)}
