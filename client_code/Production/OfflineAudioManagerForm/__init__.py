from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.js


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # The event handler is renamed to match the working form for consistency.
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.reset_ui_to_recording
    )
    # The queue manager's event is for when the queue count changes.
    self.queue_manager_1.set_event_handler("x_queue_updated", self.on_queue_updated)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Initializes the UI and tells the component to refresh its badge count."""
    self.call_js("setAudioWorkflowState", "input")
    self.queue_manager_1.refresh_badge()

  def handle_new_recording(self, audio_blob, **event_args):
    """
    Called when the RecordingWidget completes a recording.
    Shows the AudioPlayback component and moves the UI to the decision state.
    This logic now mirrors the working AudioManagerForm.
    """
    self.recording_widget_1.visible = False
    # The audio_blob property is set on the playback component.
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
    """
    Called from JS when the 'Put in Queue' button is clicked.
    This exactly mimics the offline path of the AudioManagerForm. It retrieves
    the raw audio blob proxy and tells the QueueManager to handle the saving process.
    """
    audio_proxy = self.audio_playback_1.audio_blob
    if audio_proxy:
      # Tell the component to open its naming modal and pass it the raw
      # JS Blob Proxy to save. This is the correct format for the component.
      self.queue_manager_1.open_title_modal(audio_proxy)
    else:
      self.js.call_js("displayBanner", "No recording available to save.", "error")

  def on_queue_updated(self, **event_args):
    """
    Event handler for when the queue is updated by the component.
    Resets the main UI back to the recording state after an item is successfully queued.
    """
    self.reset_ui_to_recording()
