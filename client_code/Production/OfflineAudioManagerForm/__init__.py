from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.reset_ui_to_recording
    )
    self.queue_manager_1.set_event_handler("x_queue_updated", self.on_queue_updated)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.call_js(
      "setElementText",
      "offlineAudioManager-h2-title",
      t.t("offlineAudioManager_h2_title"),
    )
    self.call_js(
      "setElementText",
      "offlineAudioManager-p-instructions",
      t.t("offlineAudioManager_p_instructions"),
    )
    self.call_js(
      "setElementText",
      "offlineAudioManager-button-discard",
      t.t("offlineAudioManager_button_discard"),
    )
    self.call_js(
      "setElementText",
      "offlineAudioManager-button-queue",
      t.t("offlineAudioManager_button_queue"),
    )

  def form_show(self, **event_args):
    """Initializes the UI and tells the component to refresh its badge count."""
    # Load translations first, defaulting to 'en' in offline mode
    t.load_language(t.CURRENT_LANG or "en")
    self.update_ui_texts()
    self.call_js("setAudioWorkflowState", "input")
    self.queue_manager_1.refresh_badge()

  def handle_new_recording(self, audio_blob, mime_type, **event_args):
    """Shows the AudioPlayback component and moves the UI to the decision state."""
    self.recording_widget_1.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.call_js("setAudioWorkflowState", "decision")

  def reset_ui_to_recording(self, **event_args):
    """Resets the UI to the initial recording state."""
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.call_js("resetAudioPlayback")
    self.call_js("setAudioWorkflowState", "input")

  def queue_button_click(self, **event_args):
    """Tells the QueueManager to handle the saving process."""
    audio_proxy = self.audio_playback_1.audio_blob
    if audio_proxy:
      self.queue_manager_1.open_title_modal(audio_proxy)
    else:
      self.call_js(
        "displayBanner", t.t("offlineAudioManager_alert_noRecording"), "error"
      )

  def on_queue_updated(self, **event_args):
    """Resets the main UI back to the recording state after an item is successfully queued."""
    self.reset_ui_to_recording()
