from ._anvil_designer import AudioPlaybackTemplate
from anvil import *
import anvil.js
from ... import TranslationService as t
from ...AppEvents import events


class AudioPlayback(AudioPlaybackTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._audio_blob = None
    self.add_event_handler("x-clear_recording", self.on_clear_recording)

    # Subscribe to language changes
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """This method is called when the component is shown on the screen."""
    self.update_ui_texts()
    # This call now safely re-attaches event listeners every time the form is shown.
    anvil.js.call_js("attachPlaybackEventListeners")

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    clear_tooltip = t.t("audioPlayback_button_clear_tooltip")
    self.call_js("setElementTitle", "audioPlayback-button-clear", clear_tooltip)

  @property
  def audio_blob(self):
    return self._audio_blob

  @audio_blob.setter
  def audio_blob(self, value):
    self._audio_blob = value
    if self.parent:
      anvil.js.call_js("setupAudioPlayback", value)

  def on_clear_recording(self, **event_args):
    """This is a custom event handler for the 'x-clear_recording' event."""
    pass

  def clear_button_clicked(self, **event_args):
    """Called from JS when the clear button is clicked."""
    self.raise_event("x-clear_recording")
    self._audio_blob = None
