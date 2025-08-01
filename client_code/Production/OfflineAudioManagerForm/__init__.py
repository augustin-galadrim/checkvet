from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid
import time
import anvil.js


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    # REMOVED: self.current_audio_blob is no longer needed in Python
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self.reset_ui_to_recording()
    self.call_js("initializeDBAndQueue")

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    MODIFIED: This function now tells JavaScript to store the original blob.
    """
    print("Offline Form: Received audio. Storing blob in JavaScript.")
    # NEW: Store the original, cloneable blob in the global JS variable.
    self.call_js("clientSideAudioManager.storeBlob", audio_blob)

    # Update the UI as before
    self.recording_widget_1.visible = False
    self.audio_playback_1.visible = True
    self.audio_playback_1.audio_blob = audio_blob
    self.call_js("showDecisionButtons", True)

  def reset_ui_to_recording(
    self, **event_args
  ):  # Add **event_args to make it callable from JS
    """Resets the UI. This is now a utility function called by JavaScript."""
    print("Offline Form: Resetting UI via call from JavaScript.")
    self.call_js("clientSideAudioManager.clearBlob")

    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.call_js("showDecisionButtons", False)

  def discard_button_click(self, **event_args):
    self.reset_ui_to_recording()

  def queue_button_click(self, **event_args):
    self.call_js("openTitleModalForQueueing")

  def save_to_queue_with_title(self, title, **event_args):
    """
    MODIFIED: This function now ONLY creates and sends metadata.
    The JavaScript side handles everything else.
    """
    print(f"Offline Form: Sending metadata for title: {title}")

    metadata = {
      "id": f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}",
      "timestamp": time.time(),
      "status": "queued",
      "title": title or "Untitled Recording",
    }

    # Call the JS function. It will handle the rest.
    self.call_js("storeAudioInQueue", metadata)
