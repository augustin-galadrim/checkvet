from ._anvil_designer import EN_MicrophoneTestTemplate
from anvil import *
import anvil.server
import anvil.users

class EN_MicrophoneTest(EN_MicrophoneTestTemplate):
  def __init__(self, **properties):
    # Connect the user using the standard login form
    anvil.users.login_with_form()
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    print("EN_MicrophoneTest form displayed.")

  # Relay function called from JS when the user starts recording.
  def start_test_recording(self, **event_args):
    print("start_test_recording() called from the front-end.")

  # Relay function called from JS when the user pauses recording.
  def pause_test_recording(self, **event_args):
    print("pause_test_recording() called from the front-end.")

  # Relay function called from JS when the user stops recording.
  def stop_test_recording(self, **event_args):
    print("stop_test_recording() called from the front-end.")

  # Relay function to show errors.
  def show_error(self, error_message, **event_args):
    alert(error_message)

  # Relay function that processes the test recording.
  # It calls the server function process_and_log_test.
  # After successful processing, the user is redirected to the AudioManager form.
  def process_test_recording(self, audio_blob, **event_args):
    print("process_test_recording() called with a test audio blob.")
    try:
      transcription = anvil.server.call("process_and_log_test", audio_blob)
      print("Returned transcription:", transcription)
      open_form("EN_Settings")
      return transcription
    except Exception as e:
      alert("Error processing the test recording: " + str(e))
