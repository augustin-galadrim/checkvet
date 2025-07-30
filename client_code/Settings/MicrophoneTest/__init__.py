from ._anvil_designer import MicrophoneTestTemplate
from anvil import *
import anvil.server
import anvil.users


class MicrophoneTest(MicrophoneTestTemplate):
  def __init__(self, **properties):
    # Connect the user using the standard login form
    anvil.users.login_with_form()
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_test_recording
    )
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    print("Formulaire MicrophoneTest affiché.")

  # Relay function to show errors.
  def show_error(self, error_message, **event_args):
    alert(error_message)

  def handle_test_recording(self, audio_blob, **event_args):
    """This event handler is called by the RecordingWidget."""
    self.process_test_recording(audio_blob)

  def process_test_recording(self, audio_blob, **event_args):
    print("process_test_recording() appelé avec un blob audio de test.")
    try:
      transcription = anvil.server.call("process_and_log_test", audio_blob)
      print("Transcription renvoyée :", transcription)
      open_form("Settings.Settings")
      return transcription
    except Exception as e:
      alert("Erreur lors du traitement de l'enregistrement de test : " + str(e))
