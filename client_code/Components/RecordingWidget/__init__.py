from ._anvil_designer import RecordingWidgetTemplate
from anvil import *
import anvil.server


class RecordingWidget(RecordingWidgetTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # Define the custom event that this component can raise.
    self.add_event_handler("recording_complete", self.on_recording_complete)

  # Methods called by JavaScript within this component
  def start_recording(self, **event_args):
    print("Component: Recording started")

  def stop_recording(self, **event_args):
    print("Component: Recording stopped")

  def pause_recording(self, **event_args):
    print("Component: Recording paused")

  def show_error(self, error_message, **event_args):
    alert(error_message)

  def handle_js_recording_complete(self, blob, **event_args):
    """Called by this component's own JavaScript when a recording is finished."""
    print("Component: Received audio blob from JavaScript.")
    # Raise the custom 'recording_complete' event, passing the blob as an argument.
    # The parent form will be listening for this.
    self.raise_event("recording_complete", audio_blob=blob)

  def on_recording_complete(self, audio_blob, **event_args):
    """This is the event handler for our custom event. It doesn't need to do anything
    itself, but it must exist for the event to be valid."""
    pass
