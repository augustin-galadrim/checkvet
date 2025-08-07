from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.js


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    self.audio_playback_1.set_event_handler(
      "x-clear-recording", self.reset_ui_to_recording
    )
    # The queue manager's event is for when the queue count changes.
    self.queue_manager_1.set_event_handler("x_queue_updated", self.on_queue_updated)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Initializes the UI and tells the component to refresh its badge count."""
    self.call_js("setAudioWorkflowState", "input")
    self.queue_manager_1.refresh_badge()

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    Shows the AudioPlayback component and moves the UI to the decision state.
    """
    self.recording_widget_1.visible = False
    self.audio_playback_1.visible = True
    self.audio_playback_1.audio_blob = audio_blob
    self.call_js("setAudioWorkflowState", "decision")

  def reset_ui_to_recording(self, **event_args):
    """Resets the UI to the initial recording state."""
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.call_js("setAudioWorkflowState", "input")

  def queue_button_click(self, **event_args):
    """
    Called from JS when the 'Put in Queue' button is clicked.
    Tells the QueueManager component to handle the saving process.
    """
    if self.audio_playback_1.audio_blob:
      # Tell the component to open its modal and pass it the blob to save.
      self.queue_manager_1.open_title_modal(self.audio_playback_1.audio_blob)
    else:
      self.call_js("displayBanner", "No recording available to save.", "error")

  def on_queue_updated(self, **event_args):
    """
    Event handler for when the queue is updated by the component.
    Resets the main UI back to the recording state.
    """
    self.reset_ui_to_recording()
