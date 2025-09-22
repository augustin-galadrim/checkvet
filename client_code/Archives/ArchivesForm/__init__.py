from ._anvil_designer import ArchivesFormTemplate
from anvil import *
import anvil.server
import anvil.users
from ...Cache import reports_cache_manager
from ... import TranslationService as t
from ...LoggingClient import ClientLogger
from ...AppEvents import events
from ...AuthHelpers import setup_auth_handlers
from datetime import datetime


def safe_value(data_dict, key, default_value):
  if data_dict is None:
    return default_value
  val = data_dict.get(key)
  return default_value if val is None else val


class ArchivesForm(ArchivesFormTemplate):
  def __init__(self, **properties):
    self.logger = ClientLogger(self.__class__.__name__)
    self.logger.info("Initializing...")
    self.init_components(**properties)
    setup_auth_handlers(self)
    events.subscribe("language_changed", self.update_ui_texts)
    self.add_event_handler("show", self.form_show)

    self.is_supervisor = False
    self.has_structure = False
    self.my_reports = []
    self.structure_reports = []
    self.structure_name = None
    self.affiliated_vets = []
    self.status_options_keys = []
    self.my_patients = []
    self.current_search_query = ""
    self.selected_statuses = []
    self.selected_vets_emails = []
    self.selected_patient_ids = []
    self.logger.debug("Initialization complete.")

  def update_ui_texts(self, **event_args):
    self.call_js(
      "setElementText", "archivesForm-button-create", t.t("archivesForm_button_create")
    )
    self.call_js(
      "setPlaceholder",
      "archivesForm-input-search",
      t.t("archivesForm_input_search_placeholder"),
    )
    self.call_js(
      "setElementText", "archivesForm-tab-myReports", t.t("archivesForm_tab_myReports")
    )
    self.call_js(
      "setElementText",
      "archivesForm-tab-structureReports",
      t.t("archivesForm_tab_structureReports"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h2-myReportsTitle",
      t.t("archivesForm_h2_myReportsTitle"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-myReportsFilter",
      t.t("archivesForm_button_filter"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h2-structureTitle",
      t.t("archivesForm_h2_structureTitle"),
    )
    self.call_js(
      "setElementTitle",
      "archivesForm-button-refresh",
      t.t("archivesForm_button_refresh_tooltip"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-structureFilter",
      t.t("archivesForm_button_filter"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h3-myReportsFilterTitle",
      t.t("archivesForm_h3_myReportsFilterTitle"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h4-myReportsStatus",
      t.t("archivesForm_h4_filterByStatus"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h4-myReportsPatient",
      t.t("archivesForm_h4_filterByPatient"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-myReportsReturn",
      t.t("archivesForm_button_filterReturn"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-myReportsApply",
      t.t("archivesForm_button_filterApply"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h3-structureFilterTitle",
      t.t("archivesForm_h3_structureFilterTitle"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h4-structureStatus",
      t.t("archivesForm_h4_filterByStatus"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-h4-structureVet",
      t.t("archivesForm_h4_filterByVet"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-structureReturn",
      t.t("archivesForm_button_filterReturn"),
    )
    self.call_js(
      "setElementText",
      "archivesForm-button-structureApply",
      t.t("archivesForm_button_filterApply"),
    )

    locale_texts = {
      "monthNames": [
        t.t("month_jan"),
        t.t("month_feb"),
        t.t("month_mar"),
        t.t("month_apr"),
        t.t("month_may"),
        t.t("month_jun"),
        t.t("month_jul"),
        t.t("month_aug"),
        t.t("month_sep"),
        t.t("month_oct"),
        t.t("month_nov"),
        t.t("month_dec"),
      ],
      "notAvailable": t.t("renderer_notAvailable"),
      "noPatient": t.t("renderer_noPatient"),
      "unknownVet": t.t("renderer_unknownVet"),
      "notSpecified": t.t("renderer_notSpecified"),
      "noMyReports": t.t("renderer_noMyReports"),
      "noStructureReports": t.t("renderer_noStructureReports"),
    }
    self.call_js("setLocaleTexts", locale_texts)

  def form_show(self, **event_args):
    self.logger.info("Form showing...")
    self.header_nav_1.active_tab = "Archives"
    self.update_ui_texts()
    self.call_js("resetActiveTabState")

    user_data = anvil.server.call_s("read_user")
    if not user_data:
      alert("Could not load your user profile. Please try again.")
      open_form("StartupForm")
      return

    self.is_supervisor = user_data.get("supervisor", False)
    self.structure_name = user_data.get("structure")

    self.logger.debug(f"User is supervisor: {self.is_supervisor}")

    try:
      self.logger.debug("Fetching filter options from server...")
      self.status_options_keys = anvil.server.call_s("get_status_options")
      self.my_patients = anvil.server.call_s("get_my_patients_for_filtering")
      self.logger.info("Successfully fetched filter options.")
    except Exception as e:
      self.logger.error("Could not load filter options.", e)
      alert(f"Could not load filter options: {e}")
      self.status_options_keys = []
      self.my_patients = []

    (
      my_reports,
      structure_reports,
      cached_has_structure,
      cached_structure_name,
      cached_affiliated_vets,
    ) = reports_cache_manager.get()

    if my_reports is not None:
      self.logger.info("Cache hit. Loading reports from client-side cache.")
      self.my_reports = my_reports
      self.structure_reports = structure_reports or []
      self.has_structure = cached_has_structure
      self.structure_name = cached_structure_name
      self.affiliated_vets = cached_affiliated_vets or []
    else:
      self.logger.warning(
        "Cache is invalid or expired. Fetching fresh reports from server."
      )
      self.call_js("showArchivesSpinner")
      try:
        fresh_my_reports = anvil.server.call_s("read_reports") or []
        fresh_structure_reports = []
        self.has_structure = not user_data.get("is_independent", True)

        if self.is_supervisor and self.has_structure:
          self.logger.info(
            f"Supervisor has structure '{self.structure_name}': {self.has_structure}"
          )
          fresh_structure_reports = (
            anvil.server.call_s("get_reports_by_structure", self.structure_name) or []
          )
          self.affiliated_vets = (
            anvil.server.call_s("get_vets_in_structure", self.structure_name) or []
          )
        else:
          self.affiliated_vets = []

        self.my_reports = fresh_my_reports
        self.structure_reports = fresh_structure_reports
        reports_cache_manager.set(
          my_reports=self.my_reports,
          structure_reports=self.structure_reports,
          has_structure=self.has_structure,
          structure_name=self.structure_name,
          affiliated_vets=self.affiliated_vets,
        )
        self.logger.info("Successfully fetched and cached fresh reports.")
      except Exception as e:
        self.logger.error("An error occurred while loading reports from server.", e)
        alert(f"An error occurred while loading reports: {e}")
        self.my_reports = []
        self.structure_reports = []
      finally:
        self.call_js("hideArchivesSpinner")

    status_options_for_js = [
      {"key": key, "display": t.t(key)} for key in self.status_options_keys
    ]
    self.logger.debug("Setting up UI via JavaScript.")
    self.call_js(
      "setupUI",
      self.is_supervisor,
      self.has_structure,
      self.affiliated_vets,
      self.structure_name,
      status_options_for_js,
      self.my_patients,
    )
    self.apply_filters("my_reports")
    self.call_js("reAttachArchivesEvents")
    self.logger.info("Form setup complete.")

  def refresh_data_click(self, active_tab, **event_args):
    self.logger.info(
      f"Refresh button clicked on tab: '{active_tab}'. Invalidating cache."
    )
    reports_cache_manager.invalidate()
    self.call_js("showArchivesSpinner")
    try:
      self.my_reports = anvil.server.call_s("read_reports") or []
      if self.is_supervisor and self.has_structure:
        self.structure_reports = (
          anvil.server.call_s("get_reports_by_structure", self.structure_name) or []
        )

      reports_cache_manager.set(
        my_reports=self.my_reports,
        structure_reports=self.structure_reports,
        has_structure=self.has_structure,
        structure_name=self.structure_name,
        affiliated_vets=self.affiliated_vets,
      )
      self.logger.info("Successfully refreshed and cached report data.")
    except Exception as e:
      self.logger.error("An error occurred while refreshing reports.", e)
      alert(f"An error occurred while refreshing reports: {e}")
      self.my_reports = []
      self.structure_reports = []
    finally:
      self.call_js("hideArchivesSpinner")
    self.apply_filters(active_tab)
    alert(t.t("archivesForm_alert_refreshed"))

  def apply_filters(self, report_type="my_reports"):
    self.logger.info(f"Applying filters for '{report_type}'.")
    source_reports = (
      self.my_reports if report_type == "my_reports" else self.structure_reports
    )
    filtered_list = list(source_reports)
    initial_count = len(filtered_list)

    if self.current_search_query:
      search_term = self.current_search_query.lower()
      self.logger.debug(f"Filtering by search term: '{search_term}'")
      if report_type == "structure_reports":
        filtered_list = [
          r
          for r in filtered_list
          if (search_term in (r.get("name") or "").lower())
          or (search_term in (r.get("vet_display_name") or "").lower())
        ]
      else:
        filtered_list = [
          r for r in filtered_list if (search_term in (r.get("name") or "").lower())
        ]

    if self.selected_statuses:
      self.logger.debug(f"Filtering by statuses: {self.selected_statuses}")
      filtered_list = [
        r
        for r in filtered_list
        if safe_value(r, "statut", "not_specified") in self.selected_statuses
      ]

    if report_type == "structure_reports":
      if self.selected_vets_emails:
        self.logger.debug(f"Filtering by vet emails: {self.selected_vets_emails}")
        filtered_list = [
          r for r in filtered_list if r.get("owner_email") in self.selected_vets_emails
        ]
    else:
      if self.selected_patient_ids:
        self.logger.debug(f"Filtering by patient IDs: {self.selected_patient_ids}")
        filtered_list = [
          r for r in filtered_list if r.get("animal_id") in self.selected_patient_ids
        ]

    self.logger.info(
      f"Filtering complete. {initial_count} reports -> {len(filtered_list)} reports."
    )
    for report in filtered_list:
      report["statut_display"] = t.t(report.get("statut", "not_specified"))

    if report_type == "my_reports":
      self.call_js("populateMyReports", filtered_list)
    else:
      self.call_js("populateStructureReports", filtered_list)

  def apply_my_reports_filters(self, statuses, patient_ids, **event_args):
    self.logger.debug(
      f"Received 'my_reports' filters from JS: statuses={statuses}, patient_ids={patient_ids}"
    )
    self.selected_statuses = statuses
    self.selected_patient_ids = patient_ids
    self.apply_filters("my_reports")

  def apply_structure_filters(self, statuses, vet_emails, **event_args):
    self.logger.debug(
      f"Received 'structure_reports' filters from JS: statuses={statuses}, vet_emails={vet_emails}"
    )
    self.selected_statuses = statuses
    self.selected_vets_emails = vet_emails
    self.apply_filters("structure_reports")

  def search_reports(self, query, active_tab, **event_args):
    self.logger.info(f"Searching reports on tab '{active_tab}' with query: '{query}'")
    self.current_search_query = query
    self.apply_filters(active_tab)

  def delete_report(self, report_id, active_tab, **event_args):
    if confirm(t.t("archivesForm_confirm_delete")):
      self.logger.info(f"Attempting to delete report with ID: {report_id}")
      try:
        if anvil.server.call_s("delete_report", report_id):
          self.logger.info(
            f"Successfully deleted report. Invalidating cache and reloading."
          )
          reports_cache_manager.invalidate()
          self.form_show()
        else:
          self.logger.error(
            f"Server returned failure for deleting report ID: {report_id}"
          )
          alert("Failed to delete the report on the server.")
      except Exception as e:
        self.logger.error(f"An error occurred while deleting report ID: {report_id}", e)
        alert(f"An error occurred while deleting the report: {e}")

  def open_report_editor(self, report, **event_args):
    report_id = report.get("id")
    self.logger.info(f"Opening report editor for report ID: {report_id}")
    try:
      safe_report = {
        "id": report_id,
        "name": report.get("name"),
        "report_rich": report.get("report_rich"),
        "statut": report.get("statut"),
      }
      open_form("Archives.AudioManagerEdit", report=safe_report)
    except Exception as e:
      self.logger.error(f"Error opening report editor for report ID: {report_id}", e)
      alert(f"Error opening report editor: {e}")
      open_form("Archives.ArchivesForm")

  def create_new_report(self, **event_args):
    self.logger.info(
      "Create new report clicked. Invalidating cache and opening production form."
    )
    reports_cache_manager.invalidate()
    open_form("Production.AudioManagerForm")
