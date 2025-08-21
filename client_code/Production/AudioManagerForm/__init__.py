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
from ...LoggingClient import ClientLogger


def safe_value(item, key, default_value):
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
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")
    self.init_components(**properties)
    self.logger.debug("Components initialized.")

    self.recording_widget.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.clear_recording_handler
    )
    self.clicked_value = clicked_value
    self.template_name = template_name
    self.initial_content = initial_content
    self.prompt = prompt

    self.all_templates = []
    self.all_patients = []
    self.selected_template_language = "en"

    # NEW: Add mode for state management
    self.mode = "initial_generation"  # Can be 'initial_generation' or 'modification'
    self.logger.info(f"Form initialized in '{self.mode}' mode.")

    self.raw_transcription = None
    self.recording_state = "idle"
    self.selected_statut = None
    self.audio_chunks = []

    def silent_error_handler(err):
      self.logger.error("A silent error occurred.", err)
      pass

    set_default_error_handling(silent_error_handler)
    self.add_event_handler("show", self.form_show)
    self.audio_playback_1.visible = False
    self.logger.info("Initialization complete.")

  def update_ui_texts(self):
    self.logger.debug("Updating UI texts based on current language.")
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
    self.logger.info("Form showing...")
    # NEW: Set the initial UI mode in JS
    self.call_js("setFormMode", self.mode)
    self.update_ui_texts()

    additional_info = user_settings_cache.get("additional_info")
    if additional_info is None:
      self.logger.warning("Cache miss for 'additional_info', fetching from server.")
      additional_info = anvil.server.call_s("get_user_info", "additional_info")
      user_settings_cache["additional_info"] = additional_info

    if not additional_info:
      self.logger.info(
        "User has not completed registration. Redirecting to RegistrationFlow."
      )
      open_form("RegistrationFlow")
      return

    mobile_installation = user_settings_cache.get("mobile_installation")
    if mobile_installation is None:
      self.logger.warning("Cache miss for 'mobile_installation', fetching from server.")
      mobile_installation = anvil.server.call_s("get_user_info", "mobile_installation")
      user_settings_cache["mobile_installation"] = mobile_installation

    if not mobile_installation:
      is_ios_device = self.call_js("isIOS")
      if is_ios_device:
        self.logger.info(
          "iOS device detected without mobile install record. Redirecting to MobileInstallationFlow."
        )
        open_form("MobileInstallationFlow")
        return

    cached_lang = user_settings_cache.get("language")
    if cached_lang:
      self.logger.debug(f"Setting language from cache: {cached_lang}")
      self.call_js("setLanguageDropdown", cached_lang)
    else:
      try:
        self.logger.warning("Cache miss for 'language', fetching from server.")
        user_lang = anvil.server.call_s("get_user_info", "favorite_language")
        user_settings_cache["language"] = user_lang
        self.call_js("setLanguageDropdown", user_lang)
      except Exception as e:
        self.logger.error("Could not set user's language.", e)
        self.call_js("setLanguageDropdown", "en")

    template_data = template_cache_manager.get()
    if template_data is None:
      self.logger.warning("Cache miss for templates, fetching from server.")
      template_data = anvil.server.call_s("read_templates")
      template_cache_manager.set(template_data)

    self.all_templates = template_data.get("templates", [])
    default_template_id = template_data.get("default_template_id")

    try:
      self.all_patients = anvil.server.call_s("get_my_patients_for_filtering")
      self.call_js("populatePatientModal", self.all_patients)
    except Exception as e:
      self.logger.error("Could not load patients.", e)
      self.all_patients = []

    displayable_templates = [t for t in self.all_templates if t.get("display") is True]
    self.call_js("populateTemplateModal", displayable_templates)

    if default_template_id:
      default_template = next(
        (t for t in displayable_templates if t["id"] == default_template_id), None
      )
      if default_template:
        self.call_js("selectTemplate", default_template, False)
        self.selected_template_language = default_template.get("language", "en")
        self.logger.info(
          f"Default template '{default_template.get('name')}' set. Language is now: {self.selected_template_language}"
        )

    if self.initial_content:
      self.logger.info("Setting TextEditor content from 'initial_content' parameter.")
      self.text_editor_1.html_content = self.initial_content
    elif self.clicked_value is not None:
      self.load_report_content()

    self.queue_manager_1.refresh_badge()
    self.logger.info("Form setup complete.")

  def search_template_relay(self, search_term, **event_args):
    self.logger.debug(f"Client-side template search with term: '{search_term}'")
    searchable_templates = [t for t in self.all_templates if t.get("display") is True]
    search_term = search_term.lower()
    if not search_term:
      return searchable_templates
    return [t for t in searchable_templates if search_term in t.get("name", "").lower()]

  def refresh_session_relay(self, **event_args):
    try:
      return anvil.server.call_s("check_and_refresh_session")
    except Exception as e:
      self.logger.error("Error in refresh_session_relay.", e)
      return False

  def load_report_content(self):
    self.logger.info(f"Loading report content for clicked_value: {self.clicked_value}")
    try:
      content, error = anvil.server.call_s("load_report_content", self.clicked_value)
      if error:
        alert(error)
        self.logger.error(
          f"Server returned error while loading report content: {error}"
        )
      elif content:
        self.logger.info("Setting TextEditor content from loaded report.")
        self.text_editor_1.html_content = content
    except Exception as e:
      self.logger.error("Exception in load_report_content.", e)

  def show_error(self, error_message, **event_args):
    self.logger.error(f"Showing error alert to user: {error_message}")
    alert(error_message)

  def set_active_template_language(self, language, **event_args):
    self.selected_template_language = language or "en"
    self.logger.info(
      f"User selected a new template. Language is now: {self.selected_template_language}"
    )

  def process_uploaded_audio(self, audio_blob, **event_args):
    self.logger.info("Processing an uploaded audio file.")
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    # The workflow is always 'decision', JS will show the correct buttons based on mode
    anvil.js.call_js("setAudioWorkflowState", "decision")
    return "OK"

  def import_audio_from_queue(self, audio_blob, **event_args):
    self.logger.info("Importing audio from offline queue.")
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.recording_widget.visible = False
    anvil.js.call_js("setAudioWorkflowState", "decision")

  def handle_new_recording(self, audio_blob, **event_args):
    self.logger.info("Handling new recording from RecordingWidget.")
    self.current_audio_proxy = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    # The workflow state is now always 'decision'. JS will show the correct buttons.
    anvil.js.call_js("setAudioWorkflowState", "decision")

  def clear_recording_handler(self, **event_args):
    self.logger.info("Clearing current recording and resetting audio UI.")
    self.reset_audio_workflow()

  def process_recording(self, **event_args):
    self.logger.info("Process recording (initial generation) initiated.")
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      alert("No audio available to process.")
      self.logger.error("process_recording called with no available audio.")
      return "ERROR"

    template = self.text_editor_1.get_content()
    if not template or not template.strip():
      alert("Cannot process without a template. Please select a template first.")
      self.logger.error("process_recording called with no template selected.")
      return "ERROR"

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show("Transcribing audio...")
    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    lang = self.selected_template_language

    try:
      transcription = self._transcribe_audio(anvil_media_blob, lang)
      self.user_feedback_1.set_status("Generating report from transcription...")
      report_content = self._generate_report_from_transcription(transcription, lang)
      self.user_feedback_1.set_status("Formatting final report...")
      final_html = self._format_report(report_content, template, lang)

      self.logger.info("Setting final generated content into TextEditor.")
      self.text_editor_1.html_content = final_html

      self.logger.info(
        "Initial generation successful. Switching to 'modification' mode."
      )
      self.mode = "modification"
      self.call_js("setFormMode", self.mode)  # Update the UI to reflect the new mode

      self.logger.info("process_recording completed successfully.")
      return "OK"

    except anvil.server.AppOfflineError:
      self.logger.warning("AppOfflineError caught. Triggering offline save.")
      alert("Connection lost. Your recording has been saved to the offline queue.")
      self.queue_manager_1.open_title_modal(js_blob_proxy)
      return "OFFLINE_SAVE"

    except Exception as e:
      self.logger.error("An exception occurred in process_recording.", e)
      anvil.js.call_js("displayBanner", f"Error: {e}", "error")
      if confirm("An unexpected error occurred. Save to offline queue?"):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
        return "OFFLINE_SAVE"
      else:
        return "ERROR"
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def reset_audio_workflow(self, **event_args):
    self.logger.debug("Resetting audio UI to initial input state.")
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.recording_widget.visible = True
    self.call_js("setAudioWorkflowState", "input")

  def process_modification(self, **event_args):
    self.logger.info("Process modification initiated.")
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      alert("No audio command available to process.")
      self.logger.error("process_modification called with no available audio.")
      return "ERROR"

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show("Transcribing command...")
    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    current_content = self.text_editor_1.get_content()
    lang = self.selected_template_language

    try:
      transcription = self._transcribe_audio(anvil_media_blob, lang)
      self.user_feedback_1.set_status("Applying modification...")
      edited_report = anvil.server.call_s(
        "edit_report", transcription, current_content, lang
      )
      self.text_editor_1.html_content = edited_report
      self.logger.info("Modification applied successfully.")
      return "OK"

    except anvil.server.AppOfflineError:
      self.logger.warning(
        "AppOfflineError caught during modification. Triggering offline save."
      )
      alert("Connection lost. Your recording has been saved to the offline queue.")
      self.queue_manager_1.open_title_modal(js_blob_proxy)
      return "OFFLINE_SAVE"

    except Exception as e:
      self.logger.error("An exception occurred in process_modification.", e)
      anvil.js.call_js("displayBanner", f"Error: {e}", "error")
      if confirm("An unexpected error occurred. Save to offline queue?"):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
        return "OFFLINE_SAVE"
      else:
        return "ERROR"
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def _transcribe_audio(self, audio_blob, lang):
    self.logger.info("Starting transcription...")
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
    self.logger.info("Transcription successful.")
    return transcription

  def _generate_report_from_transcription(self, transcription, lang):
    self.logger.info("Starting report generation...")
    report = anvil.server.call_s("generate_report", transcription, lang)
    self.logger.info("Report generation successful.")
    return report

  def _format_report(self, report_content, template, lang):
    self.logger.info("Starting final report formatting...")
    formatted_report = anvil.server.call_s(
      "format_report", report_content, template, lang
    )
    self.logger.info("Report formatting successful.")
    return formatted_report

  def report_footer_1_status_clicked(self, status_key, **event_args):
    if status_key:
      self.selected_statut = status_key
      self.report_footer_1.update_status_display(status_key)
      self.logger.info(f"Report status set to: '{status_key}'")
      self.call_js(
        "displayBanner",
        f"Status chosen: {status_key.replace('_', ' ').title()}",
        "success",
      )

  def report_footer_1_save_clicked(self, **event_args):
    self.logger.info("Save button clicked, opening patient modal for save.")
    html_content = self.text_editor_1.get_content()
    self.call_js("openPatientModalForSave", html_content)

  def save_report(self, content_json, images, selected_patient, **event_args):
    self.logger.info("Attempting to save report.")
    try:
      if not isinstance(selected_patient, dict):
        alert("Invalid patient data provided.")
        self.logger.error(
          "Invalid patient data provided to save_report.", selected_patient
        )
        return False

      animal_name = selected_patient.get("name")
      animal_id = selected_patient.get("id")

      self.logger.debug(f"Saving report for patient: {animal_name} (ID: {animal_id})")

      if animal_id is None:
        details = selected_patient.get("details", {})
        self.logger.info(f"Patient '{animal_name}' is new. Creating new animal record.")
        animal_id = anvil.server.call_s(
          "write_animal_first_time",
          animal_name,
          type=details.get("type"),
          proprietaire=details.get("proprietaire"),
        )
        self.logger.info(f"New animal created with ID: {animal_id}")

      html_content = json.loads(content_json).get("content", "")
      statut = self.selected_statut or "not_specified"

      result = anvil.server.call_s(
        "write_report_first_time",
        animal_name=animal_name,
        report_rich=html_content,
        statut=statut,
        animal_id=animal_id,
        transcript=self.raw_transcription,
        language=self.selected_template_language,
      )

      if result:
        self.logger.info("Report saved successfully.")
        anvil.js.call_js("displayBanner", t.t("report_save_success"), "success")
        return True
      else:
        self.logger.error("Server returned failure while saving report.")
        alert(t.t("report_save_fail"))
        return False
    except Exception as e:
      self.logger.error("An exception occurred during save_report.", e)
      raise
    return True

  def queue_manager_1_x_import_item(self, item_id, audio_blob, **event_args):
    self.logger.info(f"Importing item {item_id} from queue.")
    self.import_audio_from_queue(audio_blob)
