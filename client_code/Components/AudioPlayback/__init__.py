from ._anvil_designer import AudioPlaybackTemplate
from anvil import *
import anvil.js


class AudioPlayback(AudioPlaybackTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._audio_blob = None
    self.add_event_handler("x-clear-recording", self.on_clear_recording)

  @property
  def audio_blob(self):
    return self._audio_blob

  @audio_blob.setter
  def audio_blob(self, value):
    self._audio_blob = value
    if self.parent:
      anvil.js.call_js("setupAudioPlayback", value)

  def on_clear_recording(self, **event_args):
    """This is a custom event handler for the 'x-clear-recording' event."""
    pass

  def clear_button_clicked(self, **event_args):
    """Called from JS when the clear button is clicked."""
    self.raise_event("x-clear-recording")
    # Also reset the component's internal state
    self._audio_blob = None
    anvil.js.call_js("resetAudioPlayback")
