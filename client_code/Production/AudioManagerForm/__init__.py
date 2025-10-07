from ._anvil_designer import AudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.js
import time
from ... import TranslationService as t
from ...Cache import template_cache_manager, reports_cache_manager
from ...LoggingClient import ClientLogger
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers


def safe_value(item, key, default_value):
  if item is None:
    return default_value
  val = item.get(key)
  return default_value if val is None else val


class AudioManagerForm(AudioManagerFormTemplate):
  def __init__(self, **properties):
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")
    self.init_components(**properties)
    setup_auth_handlers(self)
    self.recording_widget.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.clear_recording_handler
    )
    self.all_templates, self.all_patients = [], []
    self.selected_template_language = "en"
    self.mode = "initial_generation"
    self.current_audio_mime_type = None
    self.raw_transcription = None
    self.selected_template = None
    self.selected_status = None
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)
    self.audio_playback_1.visible = False

  def update_ui_texts(self, **event_args):
    """Sets all translatable text on the component."""
    self.call_js(
      "setElementText",
      "audioManager-label-template",
      t.t("audioManager_label_template"),
    )
    self.call_js(
      "setElementText",
      "audioManager-span-templatePlaceholder",
      t.t("audioManager_span_templatePlaceholder"),
    )
    self.call_js(
      "setElementText",
      "audioManager-p-instructions",
      t.t("audioManagerEdit_p_instructions"),
    )
    self.call_js(
      "setElementText",
      "audioManager-strong-example",
      t.t("audioManagerEdit_strong_example"),
    )
    self.call_js(
      "setElementText",
      "audioManager-em-exampleText",
      t.t("audioManagerEdit_em_exampleText"),
    )
    self.call_js(
      "setElementText",
      "audioManager-div-recordToggle",
      t.t("audioManager_div_recordToggle"),
    )
    self.call_js(
      "setElementText",
      "audioManager-div-uploadToggle",
      t.t("audioManager_div_uploadToggle"),
    )
    self.call_js(
      "setElementText",
      "audioManager-div-uploadText",
      t.t("audioManager_div_uploadText"),
    )
    self.call_js(
      "setElementText", "audioManager-p-uploadDesc", t.t("audioManager_p_uploadDesc")
    )
    self.call_js(
      "setElementText",
      "audioManager-label-uploadButton",
      t.t("audioManager_label_uploadButton"),
    )
    self.call_js(
      "setElementText",
      "audioManager-button-discard",
      t.t("audioManager_button_discard"),
    )
    self.call_js(
      "setElementText",
      "audioManager-button-process",
      t.t("audioManager_button_process"),
    )
    self.call_js(
      "setElementText", "audioManager-button-modify", t.t("audioManager_button_modify")
    )
    self.call_js(
      "setElementText",
      "audioManager-h3-newPatientTitle",
      t.t("audioManager_h3_newPatientTitle"),
    )
    self.call_js(
      "setElementText",
      "audioManager-label-newPatientName",
      t.t("audioManager_label_newPatientName"),
    )
    self.call_js(
      "setPlaceholder",
      "new-patient-name",
      t.t("audioManager_placeholder_newPatientName"),
    )
    self.call_js(
      "setElementText",
      "audioManager-label-newPatientSpecies",
      t.t("audioManager_label_newPatientSpecies"),
    )
    self.call_js(
      "setPlaceholder",
      "new-patient-type",
      t.t("audioManager_placeholder_newPatientSpecies"),
    )
    self.call_js(
      "setElementText",
      "audioManager-label-newPatientOwner",
      t.t("audioManager_label_newPatientOwner"),
    )
    self.call_js(
      "setPlaceholder",
      "new-patient-owner",
      t.t("audioManager_placeholder_newPatientOwner"),
    )
    self.call_js(
      "setElementText",
      "audioManager-button-newPatientCancel",
      t.t("audioManager_button_newPatientCancel"),
    )
    self.call_js(
      "setElementText",
      "audioManager-button-newPatientSave",
      t.t("audioManager_button_newPatientSave"),
    )
    self.call_js(
      "setElementText",
      "audioManager-h3-selectPatientTitle",
      t.t("audioManager_h3_selectPatientTitle"),
    )
    self.call_js(
      "setPlaceholder",
      "audioManager-input-patientSearch",
      t.t("audioManager_placeholder_patientSearch"),
    )
    self.call_js(
      "setElementText",
      "audioManager-h3-selectTemplateTitle",
      t.t("audioManager_h3_selectTemplateTitle"),
    )
    self.call_js(
      "setPlaceholder",
      "audioManager-input-templateSearch",
      t.t("audioManager_placeholder_templateSearch"),
    )

    locale_texts = {
      "invalidFile": t.t("audioManager_alert_invalidFile"),
      "newPatientBtn": t.t("audioManager_button_newPatient"),
      "patientNameRequired": t.t("audioManager_alert_patientNameRequired"),
    }
    self.call_js("setLocaleTexts", locale_texts)

  def form_show(self, **event_args):
    self.logger.info("Form showing...")
    self.update_ui_texts()
    self.call_js("setFormMode", self.mode)

    template_data = template_cache_manager.get()
    if template_data is None:
      template_data = anvil.server.call_s("read_templates")
      template_cache_manager.set(template_data)
    self.all_templates = template_data.get("templates", [])
    default_template_id = template_data.get("default_template_id")

    try:
      self.all_patients = anvil.server.call_s("get_my_patients_for_filtering")
      self.call_js("populatePatientModal", self.all_patients)
    except Exception as e:
      self.logger.error("Could not load patients.", e)

    displayable_templates = [t for t in self.all_templates if t.get("display")]
    self.call_js("populateTemplateModal", displayable_templates)

    if default_template_id:
      default_template = next(
        (t for t in displayable_templates if t["id"] == default_template_id), None
      )
      if default_template:
        self.call_js("selectTemplate", default_template, False)
        self.selected_template_language = default_template.get("language", "en")

    self.queue_manager_1.refresh_badge()
    self.logger.info("Form setup complete.")

  def set_selected_template(self, template_data, **event_args):
    """Callback depuis JS pour stocker l'objet du modèle sélectionné."""
    self.selected_template = template_data
    self.logger.info(f"Template '{template_data.get('name')}' sélectionné.")

  def load_template_content(self, html_content, **event_args):
    """Callback de JS pour charger le contenu d'un template dans l'éditeur."""
    self.text_editor_1.reset_content_and_history(html_content)

  def search_template_relay(self, search_term, **event_args):
    searchable_templates = [t for t in self.all_templates if t.get("display")]
    search_term = search_term.lower()
    if not search_term:
      return searchable_templates
    return [t for t in searchable_templates if search_term in t.get("name", "").lower()]

  def set_active_template_language(self, language, **event_args):
    self.selected_template_language = language or "en"

  def process_uploaded_audio(self, audio_blob, mime_type, **event_args):
    self.current_audio_mime_type = mime_type
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    self.call_js("setAudioWorkflowState", "decision")

  def handle_new_recording(self, audio_blob, mime_type, **event_args):
    self.logger.info(
      f"New recording received from widget. MIME Type: {mime_type}, Blob Size: {audio_blob.size} bytes"
    )
    self.current_audio_mime_type = mime_type  # Store the mime_type
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    self.call_js("setAudioWorkflowState", "decision")

  def clear_recording_handler(self, **event_args):
    self.reset_audio_workflow()

  def process_recording(self, **event_args):
    """
    Orchestrates the report creation process using a background task.
    """

    self.logger.info("Starting report creation process.")
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      return alert(t.t("audioManager_alert_noAudio"))
    if self.selected_template is None:
      return alert(t.t("audioManager_alert_noTemplate"))

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_uploading"))

    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    lang = self.selected_template_language
    template_html = self.text_editor_1.get_content()

    try:
      task = anvil.server.call(
        "process_audio_for_report",
        anvil_media_blob,
        lang,
        self.current_audio_mime_type,
        template_html,
      )

      last_displayed_step = "feedback_uploading"
      while not task.is_completed():
        time.sleep(1)
        state = task.get_state()
        current_step = state.get("step")

        if current_step and current_step != last_displayed_step:
          self.user_feedback_1.set_status(t.t(current_step))
          last_displayed_step = current_step

      result = task.get_return_value()

      if result and result.get("success"):
        self.logger.info("Report pipeline completed successfully.")
        self.text_editor_1.html_content = result.get("final_html")
        self.raw_transcription = result.get("raw_transcription")
        self.mode = "modification"
        self.call_js("setFormMode", self.mode)
      else:
        error_msg = result.get("error", "An unknown error occurred.")
        self.logger.error(f"Report pipeline failed: {error_msg}")
        alert(f"{t.t('error_processingFailed')}: {error_msg}")
        if confirm(t.t("confirm_offlineSaveOnError")):
          self.queue_manager_1.open_title_modal(js_blob_proxy)

    except anvil.server.AppOfflineError:
      self.logger.warning("Connection lost during processing. Saving to offline queue.")
      alert(t.t("alert_offlineSave"))
      self.queue_manager_1.open_title_modal(js_blob_proxy)
    except Exception as e:
      self.logger.error(f"A critical client-side error occurred: {e}", e)
      alert(f"{t.t('error_processingFailed')}: {e}")
      if confirm(t.t("confirm_offlineSaveOnError")):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def reset_audio_workflow(self, **event_args):
    self.logger.debug("Resetting audio workflow to initial input state.")
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.recording_widget.visible = True
    self.call_js("setAudioWorkflowState", "input")

  def process_modification(self, **event_args):
    """
    Orchestrates the modification process using a background task.
    """
    self.logger.info("Starting report modification process.")
    audio_proxy = self.audio_playback_1.audio_blob
    if not audio_proxy:
      self.logger.warning("Modification halted: No audio command available.")
      return alert(t.t("audioManager_alert_noAudioCommand"))
    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_uploading"))

    anvil_media_blob = anvil.js.to_media(audio_proxy)
    current_content = self.text_editor_1.get_content()
    language = self.selected_template_language
    self.logger.debug(f"Using language '{language}' for modification command.")

    try:
      task = anvil.server.call(
        "process_audio_for_edit",
        anvil_media_blob,
        language,
        self.current_audio_mime_type,
        current_content,
      )

      last_displayed_step = "feedback_uploading"
      while not task.is_completed():
        time.sleep(1)
        state = task.get_state()
        current_step = state.get("step")

        if current_step and current_step != last_displayed_step:
          self.user_feedback_1.set_status(t.t(current_step))
          last_displayed_step = current_step

      result = task.get_return_value()

      if result and result.get("success"):
        self.logger.info("Report editing pipeline completed successfully.")
        self.text_editor_1.html_content = result.get("edited_html")
      else:
        error_msg = result.get("error", "An unknown error occurred.")
        self.logger.error(f"Report editing pipeline failed: {error_msg}")
        alert(f"{t.t('error_processingFailed')}: {error_msg}")
        if confirm(t.t("confirm_offlineSaveOnError")):
          self.queue_manager_1.open_title_modal(audio_proxy)

    except anvil.server.AppOfflineError:
      self.logger.warning(
        "Connection lost during modification. Saving command to offline queue."
      )
      alert(t.t("alert_offlineSave"))
      self.queue_manager_1.open_title_modal(audio_proxy)
    except anvil.server.TimeoutError as e:
      self.logger.error("Launching the task took too much time.", e)
      alert(t.t("alert_offlineSave"))
      self.queue_manager_1.open_title_modal(audio_proxy)
    except TypeError as e:  # when user navigates to another page
      self.logger.error("A TypeError occurred during modification.", e)
    except Exception as e:
      self.logger.error(
        "A critical client-side error occurred during modification",
        e,
      )
      alert(f"{t.t('error_processingFailed')}")
      if confirm(t.t("confirm_offlineSaveOnError")):
        self.queue_manager_1.open_title_modal(audio_proxy)
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def report_footer_1_status_clicked(self, status_key, **event_args):
    if status_key:
      self.selected_status = status_key
      self.report_footer_1.update_status_display(status_key)
      status_display = (
        t.t(status_key)
        if status_key and status_key != "not_specified"
        else t.t("reportFooter_button_status")
      )
      self.logger.info(f"Report status changed to '{status_key}'.")
      self.call_js(
        "displayBanner", f"{t.t('banner_statusSetTo')}: {status_display}", "success"
      )

  def report_footer_1_save_clicked(self, **event_args):
    self.logger.info("'Save' button clicked, opening patient selection modal.")
    self.call_js("openPatientModalForSave")

  def save_report(self, selected_patient, **event_args):
    self.logger.info("Attempting to save the report.")
    try:
      if not isinstance(selected_patient, dict):
        self.logger.error(
          f"Save failed: Invalid patient data provided. Data: {selected_patient}"
        )
        return alert(t.t("audioManager_alert_invalidPatient"))

      animal_name = selected_patient.get("name")
      animal_id = selected_patient.get("id")
      self.logger.debug(f"Saving report for patient: '{animal_name}' (ID: {animal_id})")

      if animal_id is None:
        details = selected_patient.get("details", {})
        self.logger.info(f"Patient '{animal_name}' is new. Creating new animal record.")
        animal_id = anvil.server.call_s(
          "write_animal_first_time",
          animal_name,
          type=details.get("type"),
          proprietaire=details.get("proprietaire"),
        )
        self.logger.info(f"New animal record created with ID: {animal_id}")
        if animal_id:
          new_patient_obj = {"id": animal_id, "name": animal_name}

          # 1. Mettre à jour la liste Python
          self.all_patients.append(new_patient_obj)
          self.all_patients.sort(key=lambda x: x["name"])  # Garder la liste triée

          # 2. Appeler le JS pour mettre à jour sa liste
          self.call_js("addPatientToLocalList", new_patient_obj)
          self.logger.info(
            f"Locally updated patient list with new patient: {animal_name}"
          )
        else:
          # Gérer le cas où la création de l'animal échoue
          self.logger.error(
            "Failed to get a valid ID for the new animal. Aborting save."
          )
          alert("There was a problem creating the new patient record on the server.")
          return False

      html_content = self.text_editor_1.get_content()
      statut = self.selected_status or "not_specified"

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
        self.logger.info("Report saved successfully on the server.")
        reports_cache_manager.invalidate()
        self.call_js("displayBanner", t.t("audioManager_banner_saveSuccess"), "success")
        return True
      else:
        self.logger.error("Server returned failure while saving the report.")
        alert(t.t("audioManager_alert_saveFailed"))
        return False
    except Exception as e:
      self.logger.error("An exception occurred during save_report.", e)
      raise

  def queue_manager_1_x_import_item(self, item_id, audio_blob, mime_type, **event_args):
    self.logger.info(f"Importing item '{item_id}' from offline queue.")
    self.current_audio_mime_type = mime_type
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.recording_widget.visible = False
    self.call_js("setAudioWorkflowState", "decision")
