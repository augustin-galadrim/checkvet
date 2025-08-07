from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import time
import anvil.js


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    self.audio_playback_1.set_event_handler(
      "x_clear_recording", self.reset_ui_to_recording
    )
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Initializes the UI and the offline database."""
    self.call_js("setAudioWorkflowState", "input")
    self.call_js("initializeDBAndQueue")

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    Shows the AudioPlayback component and moves the UI to the decision state.
    The blob is now reliably stored in the component's property.
    """
    print("Offline Form: Received audio. Showing decision UI.")
    self.recording_widget_1.visible = False
    self.audio_playback_1.visible = True
    self.audio_playback_1.audio_blob = audio_blob
    self.call_js("setAudioWorkflowState", "decision")

  def reset_ui_to_recording(self, **event_args):
    """Resets the UI to the initial recording state."""
    print("Offline Form: Resetting UI to recording state.")
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.call_js("setAudioWorkflowState", "input")

  def queue_button_click(self, **event_args):
    """Opens the modal to get a title for the recording."""
    self.call_js("openTitleModalForQueueing")

  def get_current_audio_blob(self):
    """
    A client-side relay function that returns the current Anvil Media object
    from the playback component, making it accessible to JavaScript just before saving.
    """
    print("Python (Offline): get_current_audio_blob called from JavaScript.")
    return self.audio_playback_1.audio_blob
