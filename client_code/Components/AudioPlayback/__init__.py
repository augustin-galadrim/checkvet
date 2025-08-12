from ._anvil_designer import AudioPlaybackTemplate
from anvil import *
import anvil.js


class AudioPlayback(AudioPlaybackTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._audio_blob = None
    self.add_event_handler("x-clear_recording", self.on_clear_recording)

    # Add the 'show' event handler
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """This method is called when the component is shown on the screen."""
    # Explicitly tell the JavaScript to attach its event listeners.
    anvil.js.call_js("initializeAudioPlayer")

  @property
  def audio_blob(self):
    return self._audio_blob

  @audio_blob.setter
  def audio_blob(self, value):
    self._audio_blob = value
    if self.parent:
      # This part is correct and sets the audio source.
      anvil.js.call_js("setupAudioPlayback", value)

  def on_clear_recording(self, **event_args):
    """This is a custom event handler for the 'x-clear_recording' event."""
    pass

  def clear_button_clicked(self, **event_args):
    """Called from JS when the clear button is clicked."""
    self.raise_event("x-clear_recording")
    self._audio_blob = None
