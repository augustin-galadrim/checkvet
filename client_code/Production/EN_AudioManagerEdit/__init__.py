from ._anvil_designer import EN_AudioManagerEditTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.users
import json

def safe_value(report, key, default_value):
  """Returns the value associated with 'key' in 'report', or 'default_value' if missing or None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class EN_AudioManagerEdit(EN_AudioManagerEditTemplate):
  def __init__(self, report=None, clicked_value=None, initial_content=None, **properties):
    """
    This form is used to edit an existing report.

    It accepts either:
      - a complete report dictionary via the 'report' parameter, or
      - separate parameters (clicked_value and initial_content) from which a minimal report is built.

    The report dictionary should include:
      - id: the unique ID of the report (used for updating)
      - file_name: the file name of the report
      - report_rich: the existing rich content
      - statut: the current status of the report
      - name: the name of the patient/animal associated with the report
      - (optional) transcript: the transcription text associated with the report
    """
    anvil.users.login_with_form()
    print("Report received in EN_AudioManagerEdit:", report)
    self.init_components(**properties)

    # Build a report dictionary if none is provided.
    if report is None:
      if clicked_value is not None or initial_content is not None:
        report = {
          "id": clicked_value or "",
          "report_rich": initial_content or "",
          "file_name": "Unnamed",
          "statut": "Not Specified",
          "name": "",
          "transcript": ""
        }
      else:
        alert("No report provided. Redirecting to Archives.")
        open_form("Archives.EN_Archives")
        return

    # Use safe_value to ensure each field is defined.
    self.report = {
      "id": safe_value(report, "id", ""),
      "file_name": safe_value(report, "file_name", "Unnamed"),
      "report_rich": safe_value(report, "report_rich", ""),
      "statut": safe_value(report, "statut", "Not Specified"),
      "name": safe_value(report, "name", ""),
      "transcript": safe_value(report, "transcript", "")
    }
    self.report_id = self.report.get("id")
    self.file_name = self.report.get("file_name")
    self.initial_content = self.report.get("report_rich")
    self.statut = self.report.get("statut")
    self.animal_name = self.report.get("name")
    self.transcript = self.report.get("transcript")  # Load transcript value

    # Hide the navigation bar (if present) and show the Back bar.
    if hasattr(self, "retour_bar"):
      self.retour_bar.visible = True
    if hasattr(self, "nav_tabs"):
      self.nav_tabs.visible = False

    # Attach the form's show event.
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
  # Audio recording methods
  # --------------------------
  def start_recording(self, **event_args):
    print("start_recording() called (edit mode).")
    self.recording_state = "recording"

  def pause_recording(self, **event_args):
    print("pause_recording() called (edit mode).")
    self.recording_state = "paused"

  def stop_recording(self, **event_args):
    print("stop_recording() called (edit mode).")
    self.recording_state = "stopped"

  def process_recording(self, audio_blob, **event_args):
    """
    Processes the audio blob by:
      1) Transcribing the audio
      2) Calling 'EN_edit_report' to apply the transcription as an edit command
      3) Updating the editor with the edited report content
    """
    print("process_recording() called with an audio blob in edit mode.")
    try:
      # 1) Transcribe the audio
      transcription = anvil.server.call("process_audio_whisper", audio_blob)

      # 2) Call the new server function 'EN_edit_report',
      #    passing the transcription and the current editor content
      edited_report = anvil.server.call("EN_edit_report", transcription, self.editor_content)

      # 3) Update the editor content
      self.editor_content = edited_report

      return "OK"
    except Exception as e:
      alert(f"Error processing the recording: {str(e)}")

  # --------------------------
  # Editor property
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
  # Status selection
  # --------------------------
  def on_statut_clicked(self, **event_args):
    """Prompt the user to select a new status for the report."""
    choice = alert(
      "Choose the status:",
      buttons=["Needs Correction", "Approved", "Sent", "Cancel"]
    )
    if choice in ["Needs Correction", "Approved", "Sent"]:
      self.statut = choice
      self.call_js("displayBanner", f"Status selected: {choice}", "success")
      return choice
    else:
      return None

  # --------------------------
  # Update report (Save)
  # --------------------------
  def update_report(self, ignored_file_name, content_json, images, **event_args):
    """
    Called when the user clicks "Archive". This method updates the existing report record by calling
    the server function write_report with the expected parameters:
      file_name, animal_name, vet, last_modified, report_rich, statut

    Note: The file_name parameter is ignored and self.file_name is used to keep the original file name.
    """
    print("update_report() called from JS in edit mode")
    try:
      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"HTML content length: {len(html_content)}")
      print(f"Number of images: {len(images)}")
      statut = self.statut or "Not Specified"
      file_name_to_use = self.file_name

      result = anvil.server.call(
        "write_report",
        file_name_to_use,       # Always use the original file name
        self.animal_name,       # Animal name as originally provided
        None,                   # vet: let the server use the current user
        None,                   # last_modified: left to the server
        html_content,           # report_rich: updated content
        statut                  # statut: updated status
      )
      if result:
        self.call_js("displayBanner", "Report successfully updated", "success")
        open_form("Archives.EN_Archives")
      else:
        alert("Failed to update the report. Please try again.")
    except Exception as e:
      print("Exception in update_report:", e)
      alert("Error updating the report: " + str(e))
    return True

  # --------------------------
  # Share report (Export PDF)
  # --------------------------
  def build_report_pdf_relay(self, placeholders, images):
    print("DEBUG: build_report_pdf_relay called in edit mode with placeholders:", placeholders, "and images:", images)
    pdf_base64 = anvil.server.call("build_report_pdf_base64", placeholders, images)
    return pdf_base64

  def get_media_url_relay(self, pdf_media):
    import anvil
    return anvil.get_url(pdf_media)

  # --------------------------
  # New method to relaunch AI using the transcript
  # --------------------------
  def relaunch_ai(self, **event_args):
    """
    Instead of the old approach, now we call 'EN_edit_report' again,
    using the stored transcript and current editor content.
    """
    print("relaunch_ai() called with transcript:", self.transcript)
    try:
      edited_report = anvil.server.call("EN_edit_report", self.transcript, self.editor_content)
      self.editor_content = edited_report
      self.call_js("displayBanner", "Report successfully updated", "success")
    except Exception as e:
      alert("Error relaunching AI: " + str(e))

  # --------------------------
  # Back button
  # --------------------------
  def retour_clicked(self, **event_args):
    """Return to the Archives page without confirmation."""
    open_form("Archives.EN_Archives")
