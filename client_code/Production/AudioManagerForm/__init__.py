from ._anvil_designer import AudioManagerFormTemplate
from anvil import *
import anvil.server
import anvil.js
import time
from ... import TranslationService as t
from ...Cache import template_cache_manager, user_settings_cache, reports_cache_manager
from ...LoggingClient import ClientLogger
from ...AppEvents import events


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
    self.recording_widget.set_event_handler(
      "recording_complete", self.handle_new_recording
    )
    self.audio_playback_1.set_event_handler(
      "x-clear_recording", self.clear_recording_handler
    )
    self.all_templates, self.all_patients = [], []
    self.selected_template_language = "en"
    self.mode = "initial_generation"
    self.raw_transcription = None
    self.selected_template = None
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
      "audioManager-strong-modTitle",
      t.t("audioManager_strong_modTitle"),
    )
    self.call_js(
      "setElementText", "audioManager-span-modDesc", t.t("audioManager_span_modDesc")
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
    self.header_nav_1.active_tab = "Production"
    self.update_ui_texts()
    self.call_js("setFormMode", self.mode)

    # Registration & Installation Checks...
    # (Existing logic remains the same)

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

  def process_uploaded_audio(self, audio_blob, **event_args):
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    self.call_js("setAudioWorkflowState", "decision")

  def handle_new_recording(self, audio_blob, **event_args):
    self.audio_playback_1.audio_blob = audio_blob
    self.recording_widget.visible = False
    self.audio_playback_1.visible = True
    self.call_js("setAudioWorkflowState", "decision")

  def clear_recording_handler(self, **event_args):
    self.reset_audio_workflow()

  def process_recording(self, **event_args):
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      return alert(t.t("audioManager_alert_noAudio"))

    editor_content = self.text_editor_1.get_content()
    if self.selected_template is None:
      return alert(t.t("audioManager_alert_noTemplate"))

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_transcribing"))
    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    lang = self.selected_template_language

    try:
      self.raw_transcription = self._transcribe_audio(anvil_media_blob, lang)
      self.user_feedback_1.set_status(t.t("feedback_generating"))
      report_content = self._generate_report_from_transcription(
        self.raw_transcription, lang
      )
      self.user_feedback_1.set_status(t.t("feedback_formatting"))
      final_html = self._format_report(report_content, editor_content, lang)
      self.text_editor_1.html_content = final_html
      self.mode = "modification"
      self.call_js("setFormMode", self.mode)
    except anvil.server.AppOfflineError:
      alert(t.t("alert_offlineSave"))
      self.queue_manager_1.open_title_modal(js_blob_proxy)
    except Exception as e:
      self.logger.error("An exception occurred in process_recording.", e)
      self.call_js("displayBanner", f"{t.t('error_processingFailed')}: {e}", "error")
      if confirm(t.t("confirm_offlineSaveOnError")):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def reset_audio_workflow(self, **event_args):
    self.audio_playback_1.visible = False
    self.audio_playback_1.audio_blob = None
    self.recording_widget.visible = True
    self.call_js("setAudioWorkflowState", "input")

  def process_modification(self, **event_args):
    js_blob_proxy = self.audio_playback_1.audio_blob
    if not js_blob_proxy:
      return alert(t.t("audioManager_alert_noAudioCommand"))

    self.call_js("setAudioWorkflowState", "processing")
    self.user_feedback_1.show(t.t("feedback_transcribing"))
    anvil_media_blob = anvil.js.to_media(js_blob_proxy)
    current_content = self.text_editor_1.get_content()
    lang = self.selected_template_language

    try:
      transcription = self._transcribe_audio(anvil_media_blob, lang)
      self.user_feedback_1.set_status(t.t("feedback_applyingModification"))
      edited_report = anvil.server.call_s(
        "edit_report", transcription, current_content, lang
      )
      self.text_editor_1.html_content = edited_report
    except anvil.server.AppOfflineError:
      alert(t.t("alert_offlineSave"))
      self.queue_manager_1.open_title_modal(js_blob_proxy)
    except Exception as e:
      self.logger.error("An exception occurred in process_modification.", e)
      self.call_js("displayBanner", f"{t.t('error_processingFailed')}: {e}", "error")
      if confirm(t.t("confirm_offlineSaveOnError")):
        self.queue_manager_1.open_title_modal(js_blob_proxy)
    finally:
      self.user_feedback_1.hide()
      self.reset_audio_workflow()

  def _transcribe_audio(self, audio_blob, lang):
    task = anvil.server.call_s("process_audio_whisper", audio_blob, language=lang)
    elapsed = 0
    while not task.is_completed() and elapsed < 240:
      time.sleep(1)
      elapsed += 1
    if not task.is_completed():
      raise anvil.server.AppOfflineError(t.t("error_transcriptionTimeout"))
    transcription = task.get_return_value()
    if isinstance(transcription, dict) and "error" in transcription:
      raise Exception(f"{t.t('error_transcriptionFailed')}: {transcription['error']}")
    return transcription

  def _generate_report_from_transcription(self, transcription, lang):
    return anvil.server.call_s("generate_report", transcription, lang)

  def _format_report(self, report_content, template, lang):
    return anvil.server.call_s("format_report", report_content, template, lang)

  def report_footer_1_status_clicked(self, status_key, **event_args):
    if status_key:
      self.selected_statut = status_key
      self.report_footer_1.update_status_display(status_key)
      status_display = (
        t.t(status_key)
        if status_key and status_key != "not_specified"
        else t.t("reportFooter_button_status")
      )
      self.call_js(
        "displayBanner", f"{t.t('banner_statusSetTo')}: {status_display}", "success"
      )

  def report_footer_1_save_clicked(self, **event_args):
    self.call_js("openPatientModalForSave")

  def save_report(self, selected_patient, **event_args):
    try:
      if not isinstance(selected_patient, dict):
        return alert(t.t("audioManager_alert_invalidPatient"))
      animal_name = selected_patient.get("name")
      animal_id = selected_patient.get("id")
      if animal_id is None:
        details = selected_patient.get("details", {})
        animal_id = anvil.server.call_s(
          "write_animal_first_time",
          animal_name,
          type=details.get("type"),
          proprietaire=details.get("proprietaire"),
        )

      html_content = self.text_editor_1.get_content()
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
        reports_cache_manager.invalidate()
        self.call_js("displayBanner", t.t("audioManager_banner_saveSuccess"), "success")
        return True
      else:
        alert(t.t("audioManager_alert_saveFailed"))
        return False
    except Exception as e:
      self.logger.error("An exception occurred during save_report.", e)
      raise

  def queue_manager_1_x_import_item(self, item_id, audio_blob, **event_args):
    self.audio_playback_1.audio_blob = audio_blob
    self.audio_playback_1.visible = True
    self.recording_widget.visible = False
    self.call_js("setAudioWorkflowState", "decision")
