from ._anvil_designer import AudioManagerEditTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.js
from ...Cache import reports_cache_manager
import time
from ... import TranslationService as t
from ...AppEvents import events


class AudioManagerEdit(AudioManagerEditTemplate):
  def __init__(self, report=None, **properties):
    self.init_components(**properties)
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
    self.update_ui_texts()

    if not self.report.get("id"):
      alert(
        t.t("audioManagerEdit_alert_noReportError"),
        title=t.t("audioManagerEdit_alert_navErrorTitle"),
        large=True,
      )
      open_form("Archives.ArchivesForm")
      return

    self.header_return_1.title = self.report.get(
      "file_name", t.t("audioManagerEdit_default_headerTitle")
    )
    self.text_editor_1.html_content = self.report.get("report_rich", "")
    self.report_footer_1.update_status_display(self.selected_statut)
    self.reset_ui_to_input_state()

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
      alert(t.t("audioManagerEdit_alert_noAudio"))
      return

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_transcribing"))

    anvil_media_blob = anvil.js.to_media(audio_proxy)
    current_content = self.text_editor_1.get_content()
    language = anvil.server.call_s("get_user_info", "favorite_language") or "en"

    try:
      task = anvil.server.call_s(
        "process_audio_whisper", anvil_media_blob, language=language
      )
      elapsed = 0
      while not task.is_completed() and elapsed < 240:
        time.sleep(1)
        elapsed += 1

      if not task.is_completed():
        raise anvil.server.AppOfflineError(t.t("error_transcriptionTimeout"))

      transcription = task.get_return_value()

      if isinstance(transcription, dict) and "error" in transcription:
        raise Exception(f"{t.t('error_transcriptionFailed')}: {transcription['error']}")
      if transcription is None:
        raise Exception(t.t("error_transcriptionEmpty"))

      self.user_feedback_1.set_status(t.t("feedback_applyingModification"))
      edited_report = anvil.server.call_s(
        "edit_report", transcription, current_content, language
      )
      self.text_editor_1.html_content = edited_report

    except Exception as e:
      alert(f"{t.t('error_processingFailed')}: {e}")
    finally:
      self.user_feedback_1.hide()
      self.reset_ui_to_input_state()

  def report_footer_1_status_clicked(self, status_key, **event_args):
    """Handles the status change from the footer component."""
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
    try:
      report_id = self.report.get("id")
      new_html_content = self.text_editor_1.get_content()
      new_status = self.selected_statut
      success = anvil.server.call_s(
        "update_report", report_id, new_html_content, new_status
      )
      if success:
        reports_cache_manager.invalidate()
        alert(t.t("banner_reportUpdateSuccess"), title=t.t("title_success"))
        open_form("Archives.ArchivesForm")
      else:
        alert(t.t("error_reportUpdateFailed"), title=t.t("title_updateFailed"))
    except Exception as e:
      alert(f"{t.t('error_reportSaveFailed')}: {e}")
