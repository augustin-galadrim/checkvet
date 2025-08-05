from ._anvil_designer import MicrophoneTestTemplate
from anvil import *
import anvil.server
import anvil.users


class MicrophoneTest(MicrophoneTestTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # 1. Set up the event handlers for our components
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    self.audio_playback_1.set_event_handler(
      "x-clear-recording", self.reset_to_record_mode
    )

    # 2. Set the initial state of the form when it loads
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """
    This method is called when the form is first displayed.
    It sets the initial UI state to "record mode".
    """
    self.reset_to_record_mode()

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    This method is called by the RecordingWidget when a recording is finished.
    It switches the UI to "playback mode".
    """
    print("Recording complete. Switching to playback mode.")

    # 1. Make the recording widget invisible
    self.recording_widget_1.visible = False

    # 2. Pass the recorded audio to the playback component
    self.audio_playback_1.audio_blob = audio_blob

    # 3. Make the playback component visible
    self.audio_playback_1.visible = True

  def reset_to_record_mode(self, **event_args):
    """
    This method is called by the AudioPlayback component when its 'clear'
    button is clicked. It resets the UI to its initial "record mode".
    """
    print("Resetting to record mode.")

    # 1. Make the playback component invisible and clear its audio
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None

    # 2. Make the recording widget visible again
    self.recording_widget_1.visible = True
