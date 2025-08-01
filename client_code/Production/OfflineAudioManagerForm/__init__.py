from ._anvil_designer import OfflineAudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid
import time


class OfflineAudioManagerForm(OfflineAudioManagerFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_offline_recording
    )
    self.current_audio_blob = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Runs when the form becomes visible."""
    self.reset_ui_to_recording()
    self.call_js("updateQueueDisplay")
    # Add a queue button if it doesn't exist
    self.call_js("addQueueButton")

  def handle_offline_recording(self, audio_blob, **event_args):
    """This method is called when the widget has a recording."""
    print("Offline Form: Received audio from widget. Showing playback.")
    self.current_audio_blob = audio_blob
    self.recording_widget_1.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.call_js("showDecisionButtons", True)

  def reset_ui_to_recording(self):
    """Resets the UI to the initial recording state."""
    self.current_audio_blob = None
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.call_js("showDecisionButtons", False)

  def discard_button_click(self, **event_args):
    """Handles click on the Discard button or clear event from playback."""
    print("Offline Form: Discarding audio.")
    self.reset_ui_to_recording()

  def queue_button_click(self, **event_args):
    """Handles click on the 'Put in Queue' button."""
    if self.current_audio_blob:
      # This JS function will now open the modal to ask for a title
      self.call_js("openTitleModalForQueueing")
    else:
      alert("No recording available to queue.")

  def save_to_queue_with_title(self, title, **event_args):
    """
    Called from JS after the user enters a title in the modal.
    Saves the audio blob and metadata to the local queue.
    """
    if not self.current_audio_blob:
      alert("Error: No audio data to save.")
      return

    print(f"Offline Form: Queuing recording with title: {title}")

    metadata = {
      "id": f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}",
      "timestamp": time.time(),
      "status": "pending",
      "title": title or "Untitled Recording",
    }

    self.call_js("storeAudioInQueue", self.current_audio_blob, metadata)
    self.call_js(
      "displayBanner", f"'{metadata['title']}' saved to offline queue.", "success"
    )

    # Reset the UI for the next recording
    self.reset_ui_to_recording()

  def process_queued_audio(self, item_id, audio_data, item_metadata):
    """
    This function remains as a relay to the server.
    It will be called by JS when the user is in the ONLINE form and processes the queue.
    """
    print(f"[RELAY] Processing queued audio item {item_id}")
    try:
      # The server call still needs to exist to process the queue when online.
      return anvil.server.call(
        "process_and_archive_offline_recording", audio_data, item_metadata
      )
    except Exception as e:
      print(f"[ERROR] Failed to process queued item {item_id}: {e}")
      return {"success": False, "error": str(e)}
