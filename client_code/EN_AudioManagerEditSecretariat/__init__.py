from ._anvil_designer import EN_AudioManagerEditSecretariatTemplate
from anvil import *
import anvil.server
import anvil.users
import json

def safe_value(report, key, default_value):
  """Returns the value associated with 'key' in 'report', or 'default_value' if missing or None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class EN_AudioManagerEditSecretariat(EN_AudioManagerEditSecretariatTemplate):
  def __init__(self, report=None, clicked_value=None, initial_content=None, **properties):
    """
    This form is used to edit an existing report.

    It accepts either:
      - a complete report dictionary via the 'report' parameter, or
      - separate parameters (clicked_value and initial_content) from which a minimal report is built.

    The report dictionary is expected to contain:
      - id: the unique ID of the report (used for updating)
      - file_name: the report file name
      - report_rich: the existing rich text content
      - statut: the current report status
      - name: the name of the patient/animal associated with the report
    """
    anvil.users.login_with_form()
    self.init_components(**properties)
    print("Report received in EN_AudioManagerEditSecretariat:", report)

    # Build a report dictionary if one is not provided.
    if report is None:
      if clicked_value is not None or initial_content is not None:
        report = {
          'id': clicked_value or "",
          'report_rich': initial_content or "",
          'file_name': 'Unnamed',
          'statut': 'Not specified',
          'name': ''
        }
      else:
        alert("No report provided. Redirecting to EN_Archives.")
        open_form("EN_Archives")
        return

    # Use safe_value to ensure each field is defined.
    self.report = {
      'id': safe_value(report, 'id', ""),
      'file_name': safe_value(report, 'file_name', "Unnamed"),
      'report_rich': safe_value(report, 'report_rich', ""),
      'statut': safe_value(report, 'statut', "Not specified"),
      'name': safe_value(report, 'name', "")
    }
    self.report_id = self.report.get('id')
    self.file_name = self.report.get('file_name')
    self.initial_content = self.report.get('report_rich')
    self.statut = self.report.get('statut')
    self.animal_name = self.report.get('name')

    # Hide the navigation bar (if present) and display the Back bar.
    if hasattr(self, 'retour_bar'):
      self.retour_bar.visible = True
    if hasattr(self, 'nav_tabs'):
      self.nav_tabs.visible = False

    # Do not set the editor content immediately (avoid calling JS before the DOM is ready)
    # self.editor_content = self.initial_content

    # Attach the "show" event handler.
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """When the form is shown, ensure the editor displays the current report content."""
    if self.initial_content:
      self.editor_content = self.initial_content

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False
  # --------------------------
  # Audio Recording Methods
  # --------------------------
  def start_recording(self, **event_args):
    print("start_recording() called (edit mode).")

  def pause_recording(self, **event_args):
    print("pause_recording() called (edit mode).")

  def stop_recording(self, **event_args):
    print("stop_recording() called (edit mode).")

  def process_recording(self, audio_blob, **event_args):
    """
    Processes the audio blob: transcribes, generates the report update, and updates the editor.
    A fixed placeholder prompt is used.
    """
    print("process_recording() called with an audio blob in edit mode.")
    try:
      # Set a fixed placeholder prompt.
      self.prompt = "This is a placeholder prompt for audio processing in secretariat."

      # Transcribe the audio.
      transcription = anvil.server.call("process_audio_whisper", audio_blob)
      # Generate the report content based on the transcription and prompt.
      report_content = anvil.server.call("generate_report", self.prompt, transcription)
      # Format the report content as rich text.
      report_final = anvil.server.call("format_report", report_content)

      # Update the editor with the new report content.
      self.editor_content = report_final
      return "OK"
    except Exception as e:
      alert(f"Error processing the recording: {str(e)}")

  # --------------------------
  # Editor Content Property
  # --------------------------
  @property
  def editor_content(self):
    try:
      return self.call_js("getEditorContent")
    except Exception as e:
      print("ERROR retrieving editor content:", e)
      return None

  @editor_content.setter
  def editor_content(self, value):
    try:
      self.call_js("setEditorContent", value)
    except Exception as e:
      print("ERROR setting editor content:", e)

  # --------------------------
  # Status Selection
  # --------------------------
  def on_statut_clicked(self, **event_args):
    """Prompt the user to select a new status for the report."""
    choice = alert("Choose status:", buttons=["needs correction", "validated", "sent", "Cancel"])
    if choice in ["needs correction", "validated", "sent"]:
      self.statut = choice
      self.call_js("displayBanner", f"Status selected: {choice}", "success")
      return choice
    else:
      return None

  # --------------------------
  # Update Report (Save)
  # --------------------------
  def update_report(self, ignored_file_name, content_json, images, **event_args):
    """
    Called when the user clicks on "Archive". This method updates the existing report record
    by calling the server function write_report with the parameters in the expected order:
      file_name, animal_name, vet, last_modified, report_rich, statut

    Note: The file_name parameter is ignored and self.file_name is used to preserve the original file name.
    """
    print("update_report() called from JS in edit mode")
    try:
      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"HTML content length: {len(html_content)}")
      print(f"Number of images: {len(images)}")

      # Use the chosen status or the default value.
      statut = self.statut or "Not specified"

      # Always use the original file name stored in self.file_name.
      file_name_to_use = self.file_name

      result = anvil.server.call(
          "write_report",
          file_name_to_use,       # Always use the original file name
          self.animal_name,       # Report's associated animal/patient name
          None,                   # vet: let the server use the current user
          None,                   # last_modified: left to the server
          html_content,           # report_rich: updated content
          statut                  # statut: updated status
      )

      if result:
        self.call_js("displayBanner", "Report updated successfully", "success")
        open_form("EN_ArchivesSecretariat")
      else:
        alert("Failed to update report. Please try again.")
    except Exception as e:
      print("Exception in update_report:", e)
      alert("Error updating report: " + str(e))
    return True

  # --------------------------
  # Share Report (Export PDF)
  # --------------------------
  def build_report_pdf_relay(self, placeholders, images):
    print("build_report_pdf_relay called in edit mode with placeholders:", placeholders, "and images:", images)
    pdf_base64 = anvil.server.call("build_report_pdf_base64", placeholders, images)
    return pdf_base64

  def get_media_url_relay(self, pdf_media):
    import anvil
    return anvil.get_url(pdf_media)

  # --------------------------
  # Back Button
  # --------------------------
  def retour_clicked(self, **event_args):
    """Return to the EN_ArchivesSecretariat page without confirmation."""
    open_form("EN_ArchivesSecretariat")
