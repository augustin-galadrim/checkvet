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
      "recording_complete", self.handle_offline_recording
    )
    self.current_audio_blob = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Runs when the form is shown. Initializes the UI and IndexedDB."""
    self.reset_ui_to_recording()
    self.call_js("initializeDBAndQueue")

  def handle_offline_recording(self, audio_blob, **event_args):
    """
    Called when the widget has a recording. Transitions UI to decision state.
    This is the critical point where we stabilize the blob.
    """
    print("Offline Form: Received audio from widget. Showing playback.")

    # Stabilize the blob immediately by converting it to an Anvil Media Object.
    # This is for long-term storage (e.g., sending to the queue).
    self.current_audio_blob = anvil.js.to_media(audio_blob)

    # --- KEY CHANGE: Make the component visible BEFORE setting the blob ---
    # This ensures the component's DOM elements are available for the JS call.
    self.recording_widget_1.visible = False
    self.audio_playback_1.visible = True

    # Now, set the audio_blob property. The setter in the AudioPlayback component
    # will call the necessary JavaScript to set up the player.
    # We pass the original JS blob proxy, which is what URL.createObjectURL needs.
    self.audio_playback_1.audio_blob = audio_blob

    # Finally, show the decision buttons (Queue/Discard)
    self.call_js("showDecisionButtons", True)

  def reset_ui_to_recording(self):
    """Resets the UI to the initial recording state."""
    self.current_audio_blob = None
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.call_js("showDecisionButtons", False)

  def discard_button_click(self, **event_args):
    """Handles click on the Discard button."""
    print("Offline Form: Discarding audio.")
    self.reset_ui_to_recording()

  def queue_button_click(self, **event_args):
    """Handles click on 'Put in Queue'. Opens the modal to ask for a title."""
    # We now check for the stable Anvil Media Object.
    if self.current_audio_blob:
      self.call_js("openTitleModalForQueueing")
    else:
      alert("No recording available to queue.")

  def save_to_queue_with_title(self, title, **event_args):
    """
    Called from JS after the user enters a title.
    Saves the audio blob and metadata to the IndexedDB queue.
    """
    # Check for the stored Anvil Media Object.
    if not self.current_audio_blob:
      self.call_js("displayBanner", "Error: No audio data to save.", "error")
      return

    print(f"Offline Form: Queuing recording with title: {title}")

    # Create metadata for the recording
    metadata = {
      "id": f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}",
      "timestamp": time.time(),
      "status": "queued",
      "title": title or "Untitled Recording",
    }

    # Call the JS function to store the data in IndexedDB.
    # We now pass the stable Anvil Media Object. Anvil's JS library
    # can correctly handle this object and convert it back to a Blob for IndexedDB.
    self.call_js("storeAudioInQueue", self.current_audio_blob, metadata)

    # Provide feedback and reset the UI
    self.call_js(
      "displayBanner", f"'{metadata['title']}' saved to offline queue.", "success"
    )
    self.reset_ui_to_recording()
