from ._anvil_designer import AudioManagerEditTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ...Cache import reports_cache_manager, user_settings_cache
import time
from ... import TranslationService as t
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers
from ...LoggingClient import ClientLogger


class AudioManagerEdit(AudioManagerEditTemplate):
  def __init__(self, report=None, **properties):
    self.init_components(**properties)
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")
    setup_auth_handlers(self)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.reset_ui_to_input_state
    )
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)
    self.report = report if report is not None else {}
    self.selected_statut = self.report.get("statut")
    self.current_audio_mime_type = None
    self.logger.debug("Initialization complete.")

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.call_js(
      "setElementText",
      "audioManagerEdit-button-discard",
      t.t("audioManagerEdit_button_discard"),
    )
    self.call_js(
      "setElementText",
      "audioManagerEdit-button-process",
      t.t("audioManagerEdit_button_process"),
    )
    self.call_js(
      "setElementText",
      "audioManagerEdit-p-instructions",
      t.t("audioManagerEdit_p_instructions"),
    )
    self.call_js(
      "setElementText",
      "audioManagerEdit-strong-example",
      t.t("audioManagerEdit_strong_example"),
    )
    self.call_js(
      "setElementText",
      "audioManagerEdit-em-exampleText",
      t.t("audioManagerEdit_em_exampleText"),
    )

  def form_show(self, **event_args):
    """Called when the form is shown. Sets up the initial state."""
    self.logger.info("Form showing...")
    self.update_ui_texts()

    if not self.report.get("id"):
      self.logger.error("Navigation error: Form shown without a valid report object.")
      alert(
        t.t("audioManagerEdit_alert_noReportError"),
        title=t.t("audioManagerEdit_alert_navErrorTitle"),
        large=True,
      )
      open_form("Archives.ArchivesForm")
      return

    self.logger.debug(
      f"Editing report ID: {self.report.get('id')}, Name: '{self.report.get('file_name')}'."
    )

    self.header_return_1.title = self.report.get(
      "file_name", t.t("audioManagerEdit_default_headerTitle")
    )
    self.text_editor_1.html_content = self.report.get("report_rich", "")
    self.report_footer_1.update_status_display(self.selected_statut)
    self.reset_ui_to_input_state()
    self.logger.info("Form setup complete.")

  def handle_new_recording(self, audio_blob, mime_type, **event_args):
    """Event handler from RecordingWidget. Moves UI to the 'decision' state."""
    self.logger.info("New recording received from widget.")
    self.current_audio_mime_type = mime_type
    self.audio_playback_1.audio_blob = audio_blob
    self.call_js("setAudioWorkflowState", "decision")

  def reset_ui_to_input_state(self, **event_args):
    """Resets the UI to its initial state, ready for a new recording."""
    self.logger.debug("Resetting UI to 'input' state.")
    self.audio_playback_1.call_js("resetAudioPlayback")
    self.call_js("setAudioWorkflowState", "input")

  def process_modification(self, **event_args):
    """Orchestrates the modification process using a background task."""
    self.logger.info("Starting report modification process.")
    audio_proxy = self.audio_playback_1.audio_blob
    if not audio_proxy:
      self.logger.warning("Modification halted: No audio command available.")
      alert(t.t("audioManagerEdit_alert_noAudio"))
      return

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_transcribing"))

    anvil_media_blob = anvil.js.to_media(audio_proxy)
    current_content = self.text_editor_1.get_content()
    if user_settings_cache.get("language") is not None:
      language = user_settings_cache["language"]
    else:
      user_data = anvil.server.call_s("read_user")
      language = user_data.get("favorite_language", "en") if user_data else "en"
    self.logger.debug(f"Using language '{language}' for modification command.")

    try:
      task = anvil.server.call(
        "process_audio_for_edit",
        anvil_media_blob,
        language,
        self.current_audio_mime_type,
        current_content,
      )

      last_displayed_step = "feedback_transcribing"
      while not task.is_completed():
        time.sleep(1)
        state = task.get_state()
        current_step = state.get("step")

        if current_step and current_step != last_displayed_step:
          self.user_feedback_1.set_status(t.t(current_step))
          last_displayed_step = current_step

      result = task.get_return_value()

      if result and result.get("success"):
        self.logger.info("Report editing pipeline completed successfully.")
        self.text_editor_1.html_content = result.get("edited_html")
      else:
        error_msg = result.get("error", "An unknown error occurred.")
        self.logger.error(f"Report editing pipeline failed: {error_msg}")
        alert(f"{t.t('error_processingFailed')}: {error_msg}")

    except Exception as e:
      self.logger.error("A critical client-side error occurred during modification.", e)
      alert(f"{t.t('error_processingFailed')}: {e}")
    finally:
      self.user_feedback_1.hide()
      self.reset_ui_to_input_state()

  def report_footer_1_status_clicked(self, status_key, **event_args):
    """Handles the status change from the footer component."""
    self.logger.info(f"Report status changed to '{status_key}'.")
    self.selected_statut = status_key
    self.report_footer_1.update_status_display(status_key)
    status_display = (
      t.t(status_key)
      if status_key and status_key != "not_specified"
      else t.t("reportFooter_button_status")
    )
    self.call_js(
      "displayBanner", f"{t.t('banner_statusSetTo')}: {status_display}", "success"
    )

  def report_footer_1_save_clicked(self, **event_args):
    """Handles the save button click from the footer component."""
    self.logger.info(f"Save clicked for report ID '{self.report.get('id')}'.")
    try:
      report_id = self.report.get("id")
      new_html_content = self.text_editor_1.get_content()
      new_status = self.selected_statut
      success = anvil.server.call_s(
        "update_report", report_id, new_html_content, new_status
      )
      if success:
        self.logger.info("Report updated successfully on the server.")
        reports_cache_manager.invalidate()
        alert(t.t("banner_reportUpdateSuccess"), title=t.t("title_success"))
        open_form("Archives.ArchivesForm")
      else:
        self.logger.error("Server returned failure while updating the report.")
        alert(t.t("error_reportUpdateFailed"), title=t.t("title_updateFailed"))
    except Exception as e:
      self.logger.error("An exception occurred while saving the report.", e)
      alert(f"{t.t('error_reportSaveFailed')}: {e}")
