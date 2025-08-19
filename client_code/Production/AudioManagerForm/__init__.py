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
from ...Cache import template_cache_manager, user_settings_cache


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
    print("[DEBUG] AudioManagerForm: Initializing...")
    self.init_components(**properties)
    print(
      "[DEBUG] AudioManagerForm: Components (including TextEditor) have been initialized in Python."
    )

    self.recording_widget.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.clear_recording_handler
    )
    # Store user-provided parameters
    self.clicked_value = clicked_value
    self.template_name = template_name
    self.initial_content = initial_content
    self.prompt = prompt

    # *** FIX: Add a variable to store all templates ***
    self.all_templates = []
    self.all_patients = []
    self.selected_template_language = "en"

    # Storage for raw transcription
    self.raw_transcription = None

    # Recording state
    self.recording_state = "idle"

    # User-selected status will be stored here
    self.selected_statut = None

    self.audio_chunks = []

    def silent_error_handler(err):
      print(f"[DEBUG] Silent error handler: {err}")
      pass

    set_default_error_handling(silent_error_handler)

    self.add_event_handler("show", self.form_show)
    self.audio_playback_1.visible = False
    print("[DEBUG] AudioManagerForm: __init__ completed.")

  def update_ui_texts(self):
    """Sets all text on the form using the TranslationService."""
    anvil.js.call_js("setElementText", "recordButton", t.t("record_button"))
    anvil.js.call_js("setElementText", "uploadButton", t.t("upload_button"))
    anvil.js.call_js("setElementText", "upload_text_drop", t.t("upload_text_drop"))
    anvil.js.call_js(
      "setElementText", "upload_description_select", t.t("upload_description_select")
    )
    anvil.js.call_js(
      "setElementText", "upload_button_select", t.t("upload_button_select")
    )
    anvil.js.call_js("setElementText", "label_template", t.t("label_template"))
    anvil.js.call_js("setElementText", "label_language", t.t("label_language"))
    anvil.js.call_js(
      "setElementText",
      "select_template_placeholder",
      t.t("select_template_placeholder"),
    )
    anvil.js.call_js(
      "setElementText", "select_patient_title", t.t("select_patient_title")
    )
    anvil.js.call_js("setElementText", "newPatientBtn", t.t("new_patient_button"))
    anvil.js.call_js(
      "setElementText", "select_template_title", t.t("select_template_title")
    )
    anvil.js.call_js("setPlaceholder", "searchInput", t.t("search_patient_placeholder"))
    anvil.js.call_js(
      "setPlaceholder", "templateSearchInput", t.t("search_template_placeholder")
    )

  def form_show(self, **event_args):
    print("[DEBUG] AudioManagerForm: form_show event triggered.")
    self.update_ui_texts()

    additional_info = user_settings_cache.get("additional_info")
    if additional_info is None:
      print("Fetching 'additional_info' from server.")
      additional_info = anvil.server.call_s("get_user_info", "additional_info")
      user_settings_cache["additional_info"] = additional_info

    if not additional_info:
      open_form("RegistrationFlow")
      return

    # 2. Check for mobile_installation
    mobile_installation = user_settings_cache.get("mobile_installation")
    if mobile_installation is None:
      print("Fetching 'mobile_installation' from server.")
      mobile_installation = anvil.server.call_s("get_user_info", "mobile_installation")
      user_settings_cache["mobile_installation"] = mobile_installation

    if not mobile_installation:
      is_ios_device = self.call_js("isIOS")
      if is_ios_device:
        open_form("MobileInstallationFlow")
        return

    cached_lang = user_settings_cache.get("language")
    if cached_lang:
      self.call_js("setLanguageDropdown", cached_lang)
    else:
      try:
        user_lang = anvil.server.call_s("get_user_info", "favorite_language")
        user_settings_cache["language"] = user_lang
        self.call_js("setLanguageDropdown", user_lang)
      except Exception as e:
        print(f"[ERROR] Could not set user's language: {e}")
        self.call_js("setLanguageDropdown", "en")

    template_data = template_cache_manager.get()
    if template_data is None:
      print("Fetching fresh templates from server.")
      template_data = anvil.server.call_s("read_templates")
      template_cache_manager.set(template_data)

    self.all_templates = template_data.get("templates", [])
    default_template_id = template_data.get("default_template_id")

    try:
      self.all_patients = anvil.server.call_s('get_my_patients_for_filtering')
      self.call_js("populatePatientModal", self.all_patients)
    except Exception as e:
      print(f"[ERROR] Could not load patients: {e}")
      self.all_patients = []

    displayable_templates = [t for t in self.all_templates if t.get("display") is True]

    self.call_js("populateTemplateModal", displayable_templates)

    # Automatically select the default template if one is set
    if default_template_id:
      default_template = next(
        (t for t in displayable_templates if t["id"] == default_template_id), None
      )
      if default_template:
        # The 'false' argument prevents the modal from trying to close
        self.call_js("selectTemplate", default_template, False)
        # ** FIX: Set the language from the default template when the form loads **
        self.selected_template_language = default_template.get("language", "en")
        print(
          f"[DEBUG] Default template set. Language is now: {self.selected_template_language}"
        )

    if self.initial_content:
      print(
        "[DEBUG] AudioManagerForm: Setting TextEditor content from 'initial_content' parameter."
      )
      self.text_editor_1.html_content = self.initial_content
    elif self.clicked_value is not None:
      self.load_report_content()

    self.queue_manager_1.refresh_badge()

    print("[DEBUG] AudioManagerForm: form_show completed.")

  def search_template_relay(self, search_term, **event_args):
    """MODIFIED to filter by the 'display' property and use the local self.all_templates list."""
    print(f"[DEBUG] Client-side template search with term: {search_term}")

    searchable_templates = [t for t in self.all_templates if t.get("display") is True]

    search_term = search_term.lower()
    if not search_term:
      return searchable_templates

    return [t for t in searchable_templates if search_term in t.get("name", "").lower()]

  def refresh_session_relay(self, **event_args):
    """Called when the application comes back online or the tab returns to foreground, to keep user session active."""
    try:
      return anvil.server.call_s("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def load_report_content(self):
    print(
      f"[DEBUG] AudioManagerForm: Loading report content for clicked_value: {self.clicked_value}"
    )
    try:
      content, error = anvil.server.call_s("load_report_content", self.clicked_value)
      print(f"[DEBUG] AudioManagerForm: Result from load_report_content: error={error}")
      if error:
        alert(error)
      elif content:
        print(
          "[DEBUG] AudioManagerForm: Setting TextEditor content from loaded report."
        )
        self.text_editor_1.html_content = content
      else:
        alert("Unexpected error: no content returned.")
    except Exception as e:
      print(f"[ERROR] Exception in load_report_content: {e}")

  def show_error(self, error_message, **event_args):
    print(f"[DEBUG] show_error() called with message: {error_message}")
    alert(error_message)

  def set_active_template_language(self, language, **event_args):
    """Called from JavaScript whenever a template is selected by the user."""
    self.selected_template_language = language or "en"
    print(
      f"[DEBUG] User selected a new template. Language is now: {self.selected_template_language}"
    )

  def process_uploaded_audio(self, audio_blob, **event_args):
    """
    Processes an uploaded audio file by making the playback component visible.
    """
    print("[DEBUG] process_uploaded_audio() called with an audio blob.")
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    anvil.js.call_js("setAudioWorkflowState", "decision")
    return "OK"

  def import_audio_from_queue(self, audio_blob, **event_args):
    """
    Receives an audio blob from the JS queue and sets up the UI for processing.
    """
    print("AudioManagerForm: Importing audio from offline queue.")
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.recording_widget.visible = False
    anvil.js.call_js("setAudioWorkflowState", "decision")

  def get_selected_language(self):
    """
    Gets the currently selected language based on the flag emoji.
    """
    try:
      language_emoji = self.call_js("getDropdownSelectedValue", "langueDropdown")
      return "fr" if language_emoji == "🇫🇷" else "en"
    except Exception as e:
      print(f"[ERROR] Error getting selected language: {e}")
      return "en"

  def get_current_audio_blob(self, **event_args):
    """
    Returns the current Anvil Media object from the playback component.
    """
    return self.audio_playback_1.audio_blob

  def handle_new_recording(self, audio_blob, **event_args):
    """
    Called when the RecordingWidget completes a recording.
    """
    self.current_audio_proxy = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    anvil.js.call_js("setAudioWorkflowState", "decision")

  def clear_recording_handler(self, **event_args):
    """Handles the x-clear-recording event from the AudioPlayback component."""
    print("AudioManagerForm: Clearing recording.")
    self.audio_playback_1.visible = False
    self.audio_playback_1.call_js(
      "resetAudioPlayback"
    )  # Explicitly reset the component's UI
    self.recording_widget.visible = True
    anvil.js.call_js("setAudioWorkflowState", "input")

  def prepare_ui_for_processing(self, **event_args):
    """
    Provides immediate visual feedback before processing.
    """
    print("AudioManagerForm: Preparing UI for processing feedback.")
    self.recording_widget.visible = True
    self.audio_playback_1.visible = False
    anvil.js.call_js("toggleMode", "record")
    anvil.js.call_js("setAudioWorkflowState", "input")

  def process_recording(self, **event_args):
    """
    Orchestrates the processing of the audio with user feedback.
    """
    print("[DEBUG] AudioManagerForm: process_recording initiated.")
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      alert("No audio available to process.")
      self.call_js("setAudioWorkflowState", "decision")  # Revert UI
      return "ERROR"

    print("[DEBUG] AudioManagerForm: Getting template content from TextEditor.")
    template = self.text_editor_1.get_content()
    if not template or not template.strip():
      alert("Cannot process without a template. Please select a template first.")
      self.call_js("setAudioWorkflowState", "decision")  # Revert UI
      return "ERROR"

    # --- Start of new feedback logic ---
    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show("Transcribing audio...")
    # --- End of new feedback logic ---

    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    lang = self.selected_template_language

    try:
      # Step 1: Transcription
      transcription = self._transcribe_audio(anvil_media_blob, lang)

      # Step 2: Generation
      self.user_feedback_1.set_status("Generating report from transcription...")
      report_content = self._generate_report_from_transcription(transcription, lang)

      # Step 3: Formatting
      self.user_feedback_1.set_status("Formatting final report...")
      final_html = self._format_report(report_content, template, lang)

      print(
        "[DEBUG] AudioManagerForm: Setting final generated content into TextEditor."
      )
      self.text_editor_1.html_content = final_html
      print("[DEBUG] AudioManagerForm: process_recording completed successfully.")
      return "OK"

    except anvil.server.AppOfflineError:
      print("[DEBUG] AppOfflineError caught. Triggering offline save.")
      alert("Connection lost. Your recording has been saved to the offline queue.")
      self.queue_manager_1.open_title_modal(js_blob_proxy)
      return "OFFLINE_SAVE"

    except Exception as e:
      print(f"[ERROR] An exception occurred in process_recording: {e}")
      anvil.js.call_js("displayBanner", f"Error: {e}", "error")
      if confirm("An unexpected error occurred. Save to offline queue?"):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
        return "OFFLINE_SAVE"
      else:
        return "ERROR"

    finally:
      # --- This block ensures the UI is always reset ---
      self.user_feedback_1.hide()
      # We reset to the initial input state after processing is done
      self.reset_ui_to_input_state()

  def reset_ui_to_input_state(self):
    """Helper method to reset the UI to its default input state."""
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.recording_widget.visible = True
    self.call_js("setAudioWorkflowState", "input")

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

  def _format_report(self, report_content, template, lang):
    """Helper to format and display the final report."""
    return anvil.server.call_s("format_report", report_content, template, lang)

  def receive_audio_chunk(self, b64_chunk, index, total, **event_args):
    if not self.audio_chunks or len(self.audio_chunks) != total:
      self.audio_chunks = [""] * total
    self.audio_chunks[index] = b64_chunk
    return "OK"

  def process_consolidated_audio(self, **event_args):
    if not self.audio_chunks or "" in self.audio_chunks:
      return {"error": "Not all audio chunks have been received."}
    data_bytes = b"".join(base64.b64decode(part) for part in self.audio_chunks)
    self.audio_chunks = []
    media = anvil.BlobMedia(
      content=data_bytes, content_type="audio/webm", name="recording.webm"
    )
    return self.process_recording(media)

  def convert_audio_format_if_needed(self, audio_blob, file_name, **event_args):
    print(f"[DEBUG] Checking audio format for: {file_name}")
    try:
      file_extension = file_name.lower().split(".")[-1] if "." in file_name else ""
      if file_extension in ["m4a", "mp3", "wav", "aac"]:
        print(f"[DEBUG] Compatible audio format: {file_extension}")
        return audio_blob
      else:
        print(f"[DEBUG] Non-optimal audio format: {file_extension}")
        if file_extension not in ["m4a"]:
          alert(
            f"Note: The {file_extension} format is not optimized for iOS Voice Memos (which uses m4a)."
          )
        return audio_blob
    except Exception as e:
      print(f"[ERROR] Error checking audio format: {e}")
      return audio_blob

  def report_footer_1_status_clicked(self, status_key, **event_args):
    """
    Handles the status change from the footer component.
    The dialog is now handled entirely within the component.
    """
    if status_key:
      self.selected_statut = status_key
      self.report_footer_1.update_status_display(status_key)
      self.call_js(
        "displayBanner",
        f"Status chosen: {status_key.replace('_', ' ').title()}",
        "success",
      )

  def report_footer_1_save_clicked(self, **event_args):
    html_content = self.text_editor_1.get_content()
    self.call_js("openPatientModalForSave", html_content)

  def save_report(self, content_json, images, selected_patient, **event_args):
    try:
      # If the patient is a newly created one, it won't have an ID yet.
      if not isinstance(selected_patient, dict):
        alert("Invalid patient data provided.")
        return False

      animal_name = selected_patient.get("name")
      animal_id = selected_patient.get("id") # Use the 'id' key which now holds the Anvil ID

      # If the animal_id is None, it means it's a new patient.
      if animal_id is None:
        details = selected_patient.get("details", {})
        # The server function now returns the new row's Anvil ID
        animal_id = anvil.server.call_s(
          "write_animal_first_time",
          animal_name,
          type=details.get("type"),
          proprietaire=details.get("proprietaire"),
        )

      html_content = json.loads(content_json).get("content", "")
      statut = self.selected_statut or "not_specified"

      # Call the updated server function with animal_id
      result = anvil.server.call_s(
        "write_report_first_time",
        animal_name=animal_name,
        report_rich=html_content,
        statut=statut,
        animal_id=animal_id, # Pass the Anvil ID
        transcript=self.raw_transcription,
        language=self.selected_template_language
      )

      if result:
        anvil.js.call_js("displayBanner", t.t("report_save_success"), "success")
        return True
      else:
        alert(t.t("report_save_fail"))
        return False
    except Exception as e:
      print(f"[ERROR] Exception in save_report: {e}")
      raise
    return True

  def queue_manager_1_x_import_item(self, item_id, audio_blob, **event_args):
    print(f"AudioManagerForm: Importing item {item_id} from queue.")
    self.import_audio_from_queue(audio_blob)