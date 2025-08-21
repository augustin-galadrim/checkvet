from ._anvil_designer import MicrophoneTestTemplate
from anvil import *
import anvil.server
import anvil.users
from ... import TranslationService as t
from ...AppEvents import events


class MicrophoneTest(MicrophoneTestTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.reset_to_record_mode
    )
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the form."""
    self.header_return_1.title = t.t("microphoneTest_header_title")
    self.call_js(
      "setElementText", "microphoneTest-h1-title", t.t("microphoneTest_h1_title")
    )
    self.call_js(
      "setElementText",
      "microphoneTest-p-instructions",
      t.t("microphoneTest_p_instructions"),
    )

  def form_show(self, **event_args):
    """Sets the initial UI state to "record mode"."""
    self.update_ui_texts()
    self.reset_to_record_mode()

  def handle_recording_complete(self, audio_blob, **event_args):
    """Switches the UI to "playback mode"."""
    self.recording_widget_1.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True

  def reset_to_record_mode(self, **event_args):
    """Resets the UI to its initial "record mode"."""
    self.audio_playback_1.visible = False
    self.audio_playback_1.call_js("resetAudioPlayback")
    self.recording_widget_1.visible = True
