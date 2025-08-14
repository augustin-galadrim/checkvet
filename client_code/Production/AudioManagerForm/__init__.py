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
    print("[DEBUG] Initializing AudioManagerForm")
    self.init_components(**properties)
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
    print("[DEBUG] __init__ completed.")

  def update_ui_texts(self):
    """Sets all text on the form using the TranslationService."""
    self.call_js("setElementText", "recordButton", t.t("record_button"))
    self.call_js("setElementText", "uploadButton", t.t("upload_button"))
    self.call_js("setElementText", "upload_text_drop", t.t("upload_text_drop"))
    self.call_js(
      "setElementText", "upload_description_select", t.t("upload_description_select")
    )
    self.call_js("setElementText", "upload_button_select", t.t("upload_button_select"))
    self.call_js("setElementText", "label_template", t.t("label_template"))
    self.call_js("setElementText", "label_language", t.t("label_language"))
    self.call_js(
      "setElementText",
      "select_template_placeholder",
      t.t("select_template_placeholder"),
    )
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

    if self.initial_content:
      self.text_editor_1.html_content = self.initial_content
    elif self.clicked_value is not None:
      self.load_report_content()

    self.call_js("rebuildPatientSearchInput")
    self.queue_manager_1.refresh_badge()
    print("[DEBUG] form_show completed.")

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
    print(f"[DEBUG] Loading report content for clicked_value: {self.clicked_value}")
    try:
      content, error = anvil.server.call_s("load_report_content", self.clicked_value)
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
    print("AMF PY: process_recording initiated.")
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      alert("No audio available to process.")
      self.call_js("setAudioWorkflowState", "decision")  # Revert UI
      return "ERROR"

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
    lang = self.get_selected_language()

    try:
      # Step 1: Transcription
      transcription = self._transcribe_audio(anvil_media_blob, lang)

      # Step 2: Generation
      self.user_feedback_1.set_status("Generating report from transcription...")
      report_content = self._generate_report_from_transcription(transcription, lang)

      # Step 3: Formatting
      self.user_feedback_1.set_status("Formatting final report...")
      final_html = self._format_report(report_content, template, lang)

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

  def report_footer_1_status_clicked(self, **event_args):
    status_options = anvil.server.call_s("get_status_options")
    buttons = [(opt.replace("_", " ").title(), opt) for opt in status_options] + [
      ("Cancel", None)
    ]
    choice = alert("Choose status:", buttons=buttons)
    if choice:
      self.selected_statut = choice
      self.report_footer_1.update_status_display(choice)
      self.call_js(
        "displayBanner", f"Status chosen: {choice.replace('_', ' ').title()}", "success"
      )
    return choice

  def report_footer_1_save_clicked(self, **event_args):
    html_content = self.text_editor_1.get_content()
    self.call_js("openPatientModalForSave", html_content)

  def save_report(self, content_json, images, selected_patient, **event_args):
    try:
      if not isinstance(selected_patient, dict):
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
        details = selected_patient.get("details", {})
        unique_id = anvil.server.call_s(
          "write_animal_first_time",
          animal_name,
          type=details.get("type"),
          proprietaire=details.get("proprietaire"),
        )
      html_content = json.loads(content_json).get("content", "")
      statut = self.selected_statut or "not_specified"
      result = anvil.server.call_s(
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
    form_content = ColumnPanel(spacing=10, tag=self)
    form_content.add_component(TextBox(placeholder="Name"))
    form_content.add_component(TextBox(placeholder="Species"))
    form_content.add_component(TextBox(placeholder="Owner"))
    if (
      alert(
        content=form_content,
        title="Enter new patient details",
        buttons=["OK", "Cancel"],
      )
      == "OK"
    ):
      components = form_content.get_components()
      return {
        "name": components[0].text,
        "type": components[1].text,
        "proprietaire": components[2].text,
      }
    return None

  def search_patients_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_patients_relay called with search_term: {search_term}")
    try:
      return anvil.server.call_s("search_patients", search_term)
    except Exception as e:
      print(f"[ERROR] Error in search_patients_relay: {e}")
      return []

  def queue_manager_1_x_import_item(self, item_id, audio_blob, **event_args):
    print(f"AudioManagerForm: Importing item {item_id} from queue.")
    self.import_audio_from_queue(audio_blob)
