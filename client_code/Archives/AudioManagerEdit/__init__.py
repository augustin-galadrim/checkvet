from ._anvil_designer import AudioManagerEditTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ...Cache import reports_cache_manager
import time  # <--- FIX: Added the required import for time.sleep()


class AudioManagerEdit(AudioManagerEditTemplate):
  def __init__(self, report=None, **properties):
    self.init_components(**properties)

    # --- Setup Event Handlers for Components ---
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.reset_ui_to_input_state
    )
    self.add_event_handler("show", self.form_show)

    # --- Initialize State ---
    self.report = report if report is not None else {}
    self.selected_statut = self.report.get("statut")

  def form_show(self, **event_args):
    """Called when the form is shown. Sets up the initial state."""
    if not self.report.get("id"):
      alert(
        "Error: No report was provided to edit.", title="Navigation Error", large=True
      )
      open_form("Archives.ArchivesForm")
      return

    self.header_return_1.title = self.report.get("file_name", "Edit Report")
    self.text_editor_1.html_content = self.report.get("report_rich", "")
    self.report_footer_1.update_status_display(self.selected_statut)
    self.reset_ui_to_input_state()

  # --- UI WORKFLOW METHODS ---

  def handle_new_recording(self, audio_blob, **event_args):
    """Event handler from RecordingWidget. Moves UI to the 'decision' state."""
    self.audio_playback_1.audio_blob = audio_blob
    self.call_js("setAudioWorkflowState", "decision")

  def reset_ui_to_input_state(self, **event_args):
    """Resets the UI to its initial state, ready for a new recording."""
    self.audio_playback_1.call_js("resetAudioPlayback")
    self.call_js("setAudioWorkflowState", "input")

  def process_modification(self, **event_args):
    """Orchestrates the modification process: transcribe, then edit."""
    audio_proxy = self.audio_playback_1.audio_blob
    if not audio_proxy:
      alert("No audio command available to process.")
      return

    # 1. Provide immediate user feedback
    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show("Transcribing command...")

    # 2. Convert JS proxy to Anvil Media and get current content
    anvil_media_blob = anvil.js.to_media(audio_proxy)
    current_content = self.text_editor_1.get_content()
    # Assuming user's language preference can be determined or is defaulted
    language = anvil.server.call_s("get_user_info", "favorite_language") or "en"

    try:
      # 3. Transcribe the audio command
      task = anvil.server.call_s(
        "process_audio_whisper", anvil_media_blob, language=language
      )

      # --- FIX: Replaced the direct get_return_value() with a waiting loop ---
      elapsed = 0
      while not task.is_completed() and elapsed < 240:  # 4-minute timeout
        time.sleep(1)
        elapsed += 1

      if not task.is_completed():
        raise anvil.server.AppOfflineError(
          "Transcription is taking too long. Please try again."
        )

      transcription = task.get_return_value()
      # --- END OF FIX ---

      print("Transcription:", transcription)

      if isinstance(transcription, dict) and "error" in transcription:
        raise Exception(f"Transcription failed: {transcription['error']}")

      if transcription is None:
        raise Exception(
          "Transcription returned an empty result. The audio may have been silent."
        )

      # 4. Apply the edit
      self.user_feedback_1.set_status("Applying modification...")
      edited_report = anvil.server.call_s(
        "edit_report", transcription, current_content, language
      )
      self.text_editor_1.html_content = edited_report

    except Exception as e:
      alert(f"An error occurred while processing the modification: {e}")
    finally:
      # 5. Always reset the UI
      self.user_feedback_1.hide()
      self.reset_ui_to_input_state()

  # --- DATA PERSISTENCE METHODS ---

  def report_footer_1_status_clicked(self, status_key, **event_args):
    """Handles the status change from the footer component."""
    self.selected_statut = status_key
    self.report_footer_1.update_status_display(status_key)
    self.call_js(
      "displayBanner",
      f"Status set to: {status_key.replace('_', ' ').title()}",
      "success",
    )

  def report_footer_1_save_clicked(self, **event_args):
    """Handles the save button click from the footer component."""
    try:
      report_id = self.report.get("id")
      new_html_content = self.text_editor_1.get_content()
      new_status = self.selected_statut

      # Call the new, dedicated server function for updating
      success = anvil.server.call_s(
        "update_report", report_id, new_html_content, new_status
      )

      if success:
        reports_cache_manager.invalidate()
        alert("Report updated successfully!", title="Success")
        open_form("Archives.ArchivesForm")
      else:
        alert("Failed to update the report on the server.", title="Update Failed")

    except Exception as e:
      alert(f"An error occurred while saving the report: {e}")
