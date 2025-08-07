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
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    self.queue_manager_1.refresh_badge()

  def handle_recording_complete(self, audio_blob, **event_args):
    """
    Directly opens the QueueManager's modal to save the new recording.
    """
    print("Offline Form: Received audio. Opening queue save modal.")
    self.queue_manager_1.open_title_modal(audio_blob)
