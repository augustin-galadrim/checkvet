from ._anvil_designer import AudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
import anvil.users
import base64
import anvil.media
import anvil.js
import time
from ... import TranslationService as t


def safe_value(item, key, default_value):
  """Returns the value associated with 'key' in 'item', or 'default_value' if the key is missing or None."""
  if item is None:
    return default_value
  val = item.get(key)
  return default_value if val is None else val


class AudioManagerForm(AudioManagerFormTemplate):
  def __init__(
    self,
    clicked_value=None,
    template_name=None,
    initial_content=None,
    prompt=None,
    **properties,
  ):
    print("[DEBUG] Initializing AudioManagerForm")
    print(
      f"[DEBUG] __init__ parameters: clicked_value={clicked_value}, template_name={template_name}, initial_content={initial_content}, prompt={prompt}"
    )
    self.init_components(**properties)
    self.recording_widget.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x_clear_recording", self.clear_recording_handler
    )
    # Store user-provided parameters
    self.clicked_value = clicked_value
    self.template_name = template_name
    self.initial_content = initial_content
    self.prompt = prompt

    # Storage for raw transcription
    self.raw_transcription = None

    # Recording state
    self.recording_state = "idle"

    # User-selected status will be stored here
    self.selected_statut = None

    self.audio_chunks = []

    def silent_error_handler(err):
      print(f"[DEBUG] Silent error handler: {err}")
      # Optional: Add logging here
      pass

    set_default_error_handling(silent_error_handler)

    # When displaying the form, execute form_show
    self.add_event_handler("show", self.form_show)
    self.audio_playback_1.visible = False
    print("[DEBUG] __init__ completed.")

  def update_ui_texts(self):
    """Sets all text on the form using the TranslationService."""

    # Mode Toggles
    self.call_js("setElementText", "recordButton", t.t("record_button"))
    self.call_js("setElementText", "uploadButton", t.t("upload_button"))

    # Upload Section
    self.call_js("setElementText", "upload_text_drop", t.t("upload_text_drop"))
    self.call_js(
      "setElementText", "upload_description_select", t.t("upload_description_select")
    )
    self.call_js("setElementText", "upload_button_select", t.t("upload_button_select"))

    # Parameters
    self.call_js("setElementText", "label_template", t.t("label_template"))
    self.call_js("setElementText", "label_language", t.t("label_language"))
    self.call_js(
      "setElementText",
      "select_template_placeholder",
      t.t("select_template_placeholder"),
    )

    # Modals
    self.call_js("setElementText", "select_patient_title", t.t("select_patient_title"))
    self.call_js("setElementText", "newPatientBtn", t.t("new_patient_button"))
    self.call_js(
      "setElementText", "select_template_title", t.t("select_template_title")
    )
    self.call_js("setPlaceholderById", "searchInput", t.t("search_patient_placeholder"))
    self.call_js(
      "setPlaceholderById", "templateSearchInput", t.t("search_template_placeholder")
    )

  def form_show(self, **event_args):
    print("[DEBUG] Starting form_show in AudioManagerForm")
    self.update_ui_texts()

    # Check user info and mobile installation
    additional_info = anvil.server.call("get_user_info", "additional_info")
    if not additional_info:
      open_form("RegistrationFlow")
      return

    mobile_installation = anvil.server.call("get_user_info", "mobile_installation")

    if not mobile_installation:
      is_ios_device = self.call_js("isIOS")
      if is_ios_device:
        open_form("MobileInstallationFlow")
        return

    # Set the default language based on user preference
    try:
      user_lang = anvil.server.call("get_user_info", "favorite_language")
      print(f"[DEBUG] User's favorite language is: {user_lang}")
      self.call_js("setLanguageDropdown", user_lang)
    except Exception as e:
      print(f"[ERROR] Could not set user's language: {e}")
      self.call_js("setLanguageDropdown", "en")  # Default to EN on error

    templates = anvil.server.call("read_templates")
    print(f"Found {len(templates)} templates")
    self.call_js("populateTemplateModal", templates)

    if self.initial_content:
      print("[DEBUG] Loading initial content in editor.")
      self.text_editor_1.html_content = self.initial_content
    elif self.clicked_value is not None:
      print("[DEBUG] clicked_value provided, loading report content.")
      self.load_report_content()

    print("[DEBUG] Rebuilding patient search field.")
    self.call_js("rebuildPatientSearchInput")

    self.queue_manager_1.refresh_badge()

    print("[DEBUG] form_show completed.")

  def refresh_session_relay(self, **event_args):
    """Called when the application comes back online or the tab returns to foreground, to keep user session active."""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def load_report_content(self):
    print(f"[DEBUG] Loading report content for clicked_value: {self.clicked_value}")
    try:
      content, error = anvil.server.call("load_report_content", self.clicked_value)
      print(
        f"[DEBUG] Result from load_report_content: content={content}, error={error}"
      )
      if error:
        alert(error)
      elif content:
        self.text_editor_1.html_content = content
      else:
        alert("Unexpected error: no content returned.")
    except Exception as e:
      print(f"[ERROR] Exception in load_report_content: {e}")

  def show_error(self, error_message, **event_args):
    print(f"[DEBUG] show_error() called with message: {error_message}")
    alert(error_message)

  def process_uploaded_audio(self, audio_blob, **event_args):
    """
    Processes an uploaded audio file by making the playback component visible.
    """
    print("[DEBUG] process_uploaded_audio() called with an audio blob.")
    # This function should NOT process the audio, only prepare it for the user.
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    anvil.js.call_js("setAudioWorkflowState", "decision")
    return "OK"

  def import_audio_from_queue(self, audio_blob, **event_args):
    """
    Receives an audio blob from the JS queue and sets up the UI for processing.
    This is the new relay function.
    """
    print("AudioManagerForm: Importing audio from offline queue.")
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.recording_widget.visible = False
    anvil.js.call_js("setAudioWorkflowState", "decision")

  # -------------------------
  # Language detection
  # -------------------------
  def get_selected_language(self):
    """
    Gets the currently selected language based on the flag emoji
    in the language dropdown.
    Returns: 'fr' or 'en'
    """
    try:
      language_emoji = self.call_js("getDropdownSelectedValue", "langueDropdown")
      print(f"[DEBUG] Selected language emoji: {language_emoji}")
      if language_emoji == "🇫🇷":
        return "fr"
      elif language_emoji == "🇬🇧":
        return "en"
      else:
        # Default to en if unknown
        print(f"[DEBUG] Unknown language emoji: {language_emoji}, defaulting to en")
        return "en"
    except Exception as e:
      print(f"[ERROR] Error getting selected language: {e}")
      return "en"

  def get_current_audio_blob(self, **event_args):
    """
    A client-side relay function that returns the current Anvil Media object
    from the playback component. This allows JavaScript to retrieve it for
    actions like offline queueing.
    """
    print("Python: get_current_audio_blob called from JavaScript.")
    return self.audio_playback_1.audio_blob

  def handle_new_recording(self, audio_blob, **event_args):
    """
    Called when the RecordingWidget completes a recording.
    Stores the raw JS Blob Proxy and shows the playback component.
    """
    # 'audio_blob' here is the raw JS Blob Proxy. We store it directly.
    self.current_audio_proxy = audio_blob

    self.recording_widget.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    anvil.js.call_js("setAudioWorkflowState", "decision")

  def clear_recording_handler(self, **event_args):
    """Handles the x-clear-recording event from the AudioPlayback component."""
    print("AudioManagerForm: Clearing recording.")
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.recording_widget.visible = True
    anvil.js.call_js("setAudioWorkflowState", "input")

  def prepare_ui_for_processing(self, **event_args):
    """
    A fast, client-side only method to provide immediate visual feedback.
    It shows the recording widget and hides the playback controls.
    """
    print("AudioManagerForm: Preparing UI for processing feedback.")
    self.recording_widget.visible = True
    self.audio_playback_1.visible = False
    anvil.js.call_js("toggleMode", "record")
    anvil.js.call_js("setAudioWorkflowState", "input")

  def process_recording(self, **event_args):
    """
    Orchestrates the processing of the audio.
    - If ONLINE, it converts the blob to an Anvil Media object for the server.
    - If OFFLINE, it passes the raw JS Blob Proxy to the QueueManager component.
    """
    print("AMF PY: process_recording initiated.")

    # We start with the raw JavaScript Blob Proxy from the playback component.
    # It has not been converted yet.
    js_blob_proxy = self.audio_playback_1.audio_blob
    print(
      f"AMF PY [LOG 1]: Retrieved raw JS Blob Proxy from playback. Type: {type(js_blob_proxy)}"
    )

    if not js_blob_proxy:
      print("[ERROR] No audio blob found in the playback component.")
      self.call_js("displayBanner", "No audio available to process.", "error")
      self.recording_widget.visible = False
      self.audio_playback_1.visible = True
      anvil.js.call_js("setAudioWorkflowState", "decision")
      return "ERROR"

    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    lang = self.get_selected_language()

    try:
      transcription = self._transcribe_audio(anvil_media_blob, lang)
      report_content = self._generate_report_from_transcription(transcription, lang)
      final_html = self._format_report(report_content, lang)
      self.text_editor_1.html_content = final_html
      print("[DEBUG] process_recording completed successfully.")
      return "OK"

    except anvil.server.AppOfflineError:
      print("[DEBUG] AppOfflineError caught. Triggering offline save.")
      alert("Connection lost. Your recording has been saved to the offline queue.")
      self.queue_manager_1.open_title_modal(js_blob_proxy)
      return "OFFLINE_SAVE"

    except Exception as e:
      print(f"[ERROR] An exception occurred in process_recording: {e}")
      self.call_js("displayBanner", f"Error: {e}", "error")
      if confirm("An unexpected error occurred. Save to offline queue?"):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
        return "OFFLINE_SAVE"
      else:
        return "ERROR"

  def _transcribe_audio(self, audio_blob, lang):
    """Helper to handle the transcription step."""
    task = anvil.server.call_s("process_audio_whisper", audio_blob, language=lang)

    elapsed = 0
    while not task.is_completed() and elapsed < 240:
      time.sleep(1)
      elapsed += 1

    if not task.is_completed():
      raise anvil.server.AppOfflineError("Transcription is taking too long.")

    transcription = task.get_return_value()
    if isinstance(transcription, dict) and "error" in transcription:
      raise Exception(f"Transcription failed: {transcription['error']}")

    self.raw_transcription = transcription
    return transcription

  def _generate_report_from_transcription(self, transcription, lang):
    """Helper to handle the report generation step."""
    return anvil.server.call_s("generate_report", transcription, lang)

  def _format_report(self, report_content, lang):
    """Helper to format and display the final report."""
    final_html = anvil.server.call_s("format_report", report_content, lang)
    return final_html

  # 1) called for each chunk
  def receive_audio_chunk(self, b64_chunk, index, total, **event_args):
    if not self.audio_chunks or len(self.audio_chunks) != total:
      self.audio_chunks = [""] * total
    self.audio_chunks[index] = b64_chunk
    return "OK"

  # 2) consolidation without bytearray or massive join
  def process_consolidated_audio(self, **event_args):
    if not self.audio_chunks or "" in self.audio_chunks:
      return {"error": "Not all audio chunks have been received."}

    data_bytes = b""
    for part in self.audio_chunks:  # incremental concatenation
      data_bytes += base64.b64decode(part)

    self.audio_chunks = []  # reset

    media = anvil.BlobMedia(
      content=data_bytes, content_type="audio/webm", name="recording.webm"
    )

    return self.process_recording(media)

  # -------------------------
  # iOS format processing
  # -------------------------
  def convert_audio_format_if_needed(self, audio_blob, file_name, **event_args):
    """
    Checks if the audio format is compatible (especially for iOS Voice Memos) and converts if necessary.
    iOS Voice Memos typically use .m4a format, which is compatible with our processing.
    """
    print(f"[DEBUG] Checking audio format for: {file_name}")

    try:
      # Check file extension
      file_extension = file_name.lower().split(".")[-1] if "." in file_name else ""

      if file_extension in ["m4a", "mp3", "wav", "aac"]:
        # Formats already compatible with our system
        print(f"[DEBUG] Compatible audio format: {file_extension}")
        return audio_blob
      else:
        # We could implement conversion here
        # For now, just alert the user
        print(f"[DEBUG] Non-optimal audio format: {file_extension}")
        if file_extension not in ["m4a"]:
          alert(
            f"Note: The {file_extension} format is not optimized for iOS Voice Memos (which uses m4a)."
          )
        return audio_blob

    except Exception as e:
      print(f"[ERROR] Error checking audio format: {e}")
      return audio_blob  # Return original blob on error

  # -------------------------
  # Method for "Status" button
  # -------------------------
  def report_footer_1_status_clicked(self, **event_args):
    print("[DEBUG] report_footer_1_status_clicked called")
    status_options = anvil.server.call("get_status_options")

    buttons = [(opt.replace("_", " ").title(), opt) for opt in status_options]
    buttons.append(("Cancel", None))

    choice = alert("Choose status:", buttons=buttons)

    if choice:
      self.selected_statut = choice
      self.report_footer_1.update_status_display(choice)
      self.call_js(
        "displayBanner", f"Status chosen: {choice.replace('_', ' ').title()}", "success"
      )
    return choice

  def report_footer_1_save_clicked(self, **event_args):
    """
    This method is called when the 'Archive' button in the footer is clicked.
    It starts the save process by opening the patient selection modal.
    """
    print(
      "DEBUG: AudioManagerForm -> report_footer_1_save_clicked: Event handler triggered."
    )
    print("DEBUG: AudioManagerForm -> Getting content from text_editor_1...")
    html_content = self.text_editor_1.get_content()
    print(f"DEBUG: AudioManagerForm -> Content received (length: {len(html_content)}).")
    print("DEBUG: AudioManagerForm -> Calling JS function 'openPatientModalForSave'.")
    self.call_js("openPatientModalForSave", html_content)
    print("DEBUG: AudioManagerForm -> JS call to 'openPatientModalForSave' finished.")

  def save_report(self, content_json, images, selected_patient, **event_args):
    """
    This method is now called by the JavaScript `continueSave` function AFTER a
    patient has been selected from the modal.
    """
    print("[DEBUG] save_report() called from JS after patient selection.")
    try:
      # This logic is mostly the same as your original save function.

      # Check that selected_patient is a dict
      if not isinstance(selected_patient, dict):
        print(
          f"[DEBUG] selected_patient is not a dict. Searching for patient: {selected_patient}"
        )
        matches = self.search_patients_relay(selected_patient)
        if len(matches) == 1:
          selected_patient = matches[0]
        elif len(matches) > 1:
          alert("Multiple patients found. Please select one from the list.")
          return
        else:
          alert("No patient found with this name.")
          return

      animal_name = selected_patient.get("name")
      unique_id = selected_patient.get("unique_id")

      if unique_id is None:
        print("[DEBUG] New patient detected, creating via write_animal_first_time")
        details = selected_patient.get("details", {})
        type_val = details.get("type")
        proprietaire_val = details.get("proprietaire")
        new_unique_id = anvil.server.call(
          "write_animal_first_time",
          animal_name,
          type=type_val,
          proprietaire=proprietaire_val,
        )
        unique_id = new_unique_id

        # The content is passed in as a JSON string from JS, so we parse it.
      html_content = json.loads(content_json).get("content", "")
      statut = self.selected_statut or "not_specified"

      print("[DEBUG] Calling write_report_first_time with unique_id.")
      result = anvil.server.call(
        "write_report_first_time",
        animal_name=animal_name,
        report_rich=html_content,
        statut=statut,
        unique_id=unique_id,
        transcript=self.raw_transcription,
      )

      if result:
        self.call_js("displayBanner", "Report saved successfully", "success")
      else:
        alert("Failed to save report. Please try again.")

    except Exception as e:
      print(f"[ERROR] Exception in save_report: {e}")
      raise

    return True

  def get_new_patient_details(self):
    print("[DEBUG] get_new_patient_details() called")
    form_content = ColumnPanel(spacing=10)
    form_content.add_component(TextBox(placeholder="Name"))
    form_content.add_component(TextBox(placeholder="Species"))
    form_content.add_component(TextBox(placeholder="Owner"))
    result = alert(
      content=form_content,
      title="Enter new patient details",
      buttons=["OK", "Cancel"],
    )
    print(f"[DEBUG] Result get_new_patient_details: {result}")
    if result == "OK":
      components = form_content.get_components()
      details = {
        "name": components[0].text,
        "type": components[1].text,
        "proprietaire": components[2].text,
      }
      print(f"[DEBUG] New patient details: {details}")
      return details
    else:
      print("[DEBUG] get_new_patient_details canceled by user.")
      return None

  # -------------------------
  # Front-end relay for patient search
  # -------------------------
  def search_patients_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_patients_relay called with search_term: {search_term}")
    try:
      results = anvil.server.call("search_patients", search_term)
      print(f"[DEBUG] Results from search_patients_relay: {results}")
      return results
    except Exception as e:
      print(f"[ERROR] Error in search_patients_relay: {e}")
      return []

  def search_template_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_template_relay called with search_term: {search_term}")
    try:
      # Call the simplified 'search_templates' function without the language parameter.
      results = anvil.server.call("search_templates", search_term)

      if results is None:
        results = []

        # The transformation logic remains the same.
      transformed_results = []
      for template in results:
        if template is None:
          continue
        transformed_result = {
          "id": safe_value(template, "id", ""),
          "name": safe_value(template, "name", ""),
          "display": safe_value(template, "display", False),
          "html": safe_value(template, "html", ""),
        }
        transformed_results.append(transformed_result)

      print(f"[DEBUG] Transformed template results: {transformed_results}")
      return transformed_results
    except Exception as e:
      print(f"[ERROR] Error in search_template_relay: {e}")
      return []

  def queue_manager_1_x_import_item(self, item_id, audio_blob, **event_args):
    """Handles the import event from the QueueManager component."""
    print(f"AudioManagerForm: Importing item {item_id} from queue.")
    self.import_audio_from_queue(audio_blob)
