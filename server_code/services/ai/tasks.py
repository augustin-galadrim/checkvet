import anvil.server
from . import transcription, generation, formatting, edition
from ...logging_server import get_logger

logger = get_logger(__name__)

# --- REPORT GENERATION PIPELINE ---


@anvil.server.callable
def process_audio_for_report(audio_blob, language, mime_type, template_html):
  """
  Launches the full audio-to-report pipeline as a background task.
  This is the primary entry point for the client for new reports.
  """
  logger.info("Launching report creation background task...")
  task = anvil.server.launch_background_task(
    "bg_create_report_from_audio", audio_blob, language, mime_type, template_html
  )
  return task


@anvil.server.background_task
def bg_create_report_from_audio(audio_blob, language, mime_type, template_html):
  """
  Full pipeline background task for generation:
  1. Transcribes audio.
  2. Generates a structured report from the transcription.
  3. Formats the report into the final HTML.
  This includes progress updates for the client.
  """
  try:
    # Step 1: Transcribe Audio
    anvil.server.task_state["step"] = "feedback_transcribing"
    logger.info("GENERATION PIPELINE [1/3]: Transcribing audio...")
    raw_transcription = transcription.transcribe_audio(audio_blob, language, mime_type)
    logger.info("GENERATION PIPELINE [1/3] SUCCESS.")

    # Step 2: Generate Report from the transcription
    anvil.server.task_state["step"] = "feedback_generating"
    logger.info("GENERATION PIPELINE [2/3]: Generating structured report...")
    report_content = generation.generate_report(raw_transcription, language)
    logger.info("GENERATION PIPELINE [2/3] SUCCESS.")

    # Step 3: Format the report into the final HTML
    anvil.server.task_state["step"] = "feedback_formatting"
    logger.info("GENERATION PIPELINE [3/3]: Formatting final report...")
    final_html = formatting.format_report(report_content, template_html, language)
    logger.info("GENERATION PIPELINE [3/3] SUCCESS. Pipeline complete.")

    return {
      "success": True,
      "final_html": final_html,
      "raw_transcription": raw_transcription,
    }

  except Exception as e:
    logger.error(f"The report generation pipeline failed: {e}", exc_info=True)
    return {"success": False, "error": str(e)}


# --- REPORT EDITION PIPELINE ---


@anvil.server.callable
def process_audio_for_edit(audio_blob, language, mime_type, current_report_content):
  """
  Launches the audio-to-edit pipeline as a background task.
  This is the primary entry point for the client for editing reports.
  """
  logger.info("Launching report edition background task...")
  task = anvil.server.launch_background_task(
    "bg_edit_report_from_audio", audio_blob, language, mime_type, current_report_content
  )
  return task


@anvil.server.background_task
def bg_edit_report_from_audio(audio_blob, language, mime_type, current_report_content):
  """
  Full pipeline background task for editing:
  1. Transcribes the audio command.
  2. Applies the command to the report content.
  This includes progress updates for the client.
  """
  try:
    # Step 1: Transcribe Audio Command
    anvil.server.task_state["step"] = "feedback_transcribing"
    logger.info("EDITION PIPELINE [1/2]: Transcribing audio command...")
    transcription_command = transcription.transcribe_audio(
      audio_blob, language, mime_type
    )
    logger.info("EDITION PIPELINE [1/2] SUCCESS.")

    # Step 2: Apply the modification to the report
    anvil.server.task_state["step"] = "feedback_applyingModification"
    logger.info("EDITION PIPELINE [2/2]: Applying modification to report...")
    edited_html = edition.edit_report(
      transcription_command, current_report_content, language
    )
    logger.info("EDITION PIPELINE [2/2] SUCCESS. Pipeline complete.")

    return {
      "success": True,
      "edited_html": edited_html,
    }

  except Exception as e:
    logger.error(f"The report edition pipeline failed: {e}", exc_info=True)
    return {"success": False, "error": str(e)}
