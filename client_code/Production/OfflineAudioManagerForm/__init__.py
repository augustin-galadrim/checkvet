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
    # This handler connects the RecordingWidget's 'recording_complete' event
    # to our method for processing the new audio.
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording_complete
    )
    # This will hold the stable Anvil Media Object of the recording.
    self.current_audio_blob = None
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Runs when the form is shown. Initializes the UI and IndexedDB."""
    self.reset_ui_to_recording()
    self.call_js("initializeDBAndQueue")

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    This function is triggered when the RecordingWidget has a complete recording.
    It mirrors the workflow of the online AudioManagerForm by:
      1. Stabilizing the audio blob into a durable Anvil Media Object.
      2. Making the AudioPlayback component visible.
      3. Setting the blob on the playback component to enable listening.
      4. Showing the decision buttons ('Queue'/'Discard').
    """
    print(
      "Offline Form: Received audio from widget. Transitioning to playback/decision state."
    )

    # 1. Stabilize the blob immediately by converting it to an Anvil Media Object.
    # This is crucial for reliable storage and passing the data to the server or queue.
    self.current_audio_blob = anvil.js.to_media(audio_blob)

    # 2. Update the UI: Hide the recorder and show the player.
    # It is important to make the player component visible *before* setting its
    # audio_blob property to ensure its HTML elements are in the DOM.
    self.recording_widget_1.visible = False
    self.audio_playback_1.visible = True

    # 3. Set the audio_blob property on the AudioPlayback component.
    # This passes the original JavaScript blob proxy, which the component uses
    # internally to create an object URL for the <audio> element.
    self.audio_playback_1.audio_blob = audio_blob

    # 4. Show the decision buttons to the user.
    self.call_js("showDecisionButtons", True)

  def reset_ui_to_recording(self):
    """Resets the UI to the initial recording state, clearing any previous audio."""
    print("Offline Form: Resetting UI to initial recording state.")
    self.current_audio_blob = None
    self.recording_widget_1.visible = True
    self.audio_playback_1.visible = False
    # It's good practice to clear the blob property on the component as well.
    self.audio_playback_1.audio_blob = None
    self.call_js("showDecisionButtons", False)

  def discard_button_click(self, **event_args):
    """Handles the click on the 'Discard' button by resetting the UI."""
    self.reset_ui_to_recording()

  def queue_button_click(self, **event_args):
    """
    Handles the click on the 'Put in Queue' button.
    It checks for a valid recording and opens a modal for the user to name it.
    """
    if self.current_audio_blob:
      self.call_js("openTitleModalForQueueing")
    else:
      alert("No recording available to queue.")

  def save_to_queue_with_title(self, title, **event_args):
    """
    Called from JavaScript after the user enters a title in the modal.
    Saves the stabilized audio blob and metadata to the IndexedDB queue.
    """
    # Use the stabilized Anvil Media Object for saving.
    if not self.current_audio_blob:
      self.call_js("displayBanner", "Error: No audio data to save.", "error")
      return

    print(f"Offline Form: Queuing recording with title: {title}")

    # Create metadata for the recording.
    metadata = {
      "id": f"rec_{int(time.time())}_{uuid.uuid4().hex[:6]}",
      "timestamp": time.time(),
      "status": "queued",
      "title": title or "Untitled Recording",
    }

    # Call the JavaScript function to store the Anvil Media Object and metadata.
    # Anvil's framework handles the conversion back to a JavaScript Blob for IndexedDB.
    self.call_js("storeAudioInQueue", self.audio_playback_1.audio_blob, metadata)

    # Provide user feedback and reset the UI for the next recording.
    self.call_js(
      "displayBanner", f"'{metadata['title']}' saved to offline queue.", "success"
    )
    self.reset_ui_to_recording()
