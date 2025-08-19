from ._anvil_designer import ArchivesFormTemplate
from anvil import *
import anvil.server
import anvil.users
from ...Cache import reports_cache_manager
from ... import TranslationService as t  # <-- Import the TranslationService
import time


def safe_value(data_dict, key, default_value):
  """A helper function to safely get a value from a dictionary."""
  if data_dict is None:
    return default_value
  val = data_dict.get(key)
  return default_value if val is None else val


class ArchivesForm(ArchivesFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

    # State variables
    self.is_supervisor = False
    self.has_structure = False
    self.my_reports = []
    self.structure_reports = []
    self.structure_name = None
    self.affiliated_vets = []
    self.status_options_keys = [] 
    self.my_patients = []

    # Filter state variables
    self.current_search_query = ""
    self.selected_statuses = []
    self.selected_vets_emails = []
    self.selected_patient_ids = []

  def form_show(self, **event_args):
    """
    Called when the form is shown. Now fetches filter options and translates them.
    """
    self.call_js("resetActiveTabState")
    user = anvil.users.get_user()
    self.is_supervisor = user and user["supervisor"]
    self.header_nav_1.active_tab = "Archives"

    try:
      self.status_options_keys = anvil.server.call_s('get_status_options')
      self.my_patients = anvil.server.call_s('get_my_patients_for_filtering')
    except Exception as e:
      alert(f"Could not load filter options: {e}")
      self.status_options_keys = []
      self.my_patients = []

    # --- Data fetching logic (remains the same) ---
    my_reports, structure_reports = reports_cache_manager.get()

    if my_reports is not None:
      self.my_reports = my_reports
      self.structure_reports = structure_reports or []
    else:
      print("Cache is invalid or expired. Fetching fresh reports from server.")
      try:
        fresh_my_reports = anvil.server.call_s("read_reports") or []
        fresh_structure_reports = []

        if self.is_supervisor:
          self.structure_name = anvil.server.call_s("get_user_info", "structure")
          self.has_structure = bool(
            self.structure_name and self.structure_name != "independent"
          )
          if self.has_structure:
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
          my_reports=self.my_reports, structure_reports=self.structure_reports
        )

      except Exception as e:
        alert(f"An error occurred while loading reports: {e}")
        self.my_reports = []
        self.structure_reports = []

    # --- NEW: Translate status keys before sending to JavaScript ---
    status_options_for_js = [
      {"key": key, "display": t.t(key)} for key in self.status_options_keys
    ]

    # --- MODIFIED: Pass the translated status options to JS ---
    self.call_js(
      "setupUI",
      self.is_supervisor,
      self.has_structure,
      self.affiliated_vets,
      self.structure_name,
      status_options_for_js, # <-- Pass the pre-translated list
      self.my_patients
    )
    self.apply_filters("my_reports")
    self.call_js("reAttachArchivesEvents")

  def refresh_data_click(self, active_tab, **event_args):
    print(f"Refresh button clicked on tab: {active_tab}. Invalidating cache.")
    reports_cache_manager.invalidate()

    try:
      self.my_reports = anvil.server.call_s("read_reports") or []
      if self.is_supervisor and self.has_structure:
        self.structure_reports = (
          anvil.server.call_s("get_reports_by_structure", self.structure_name) or []
        )
      reports_cache_manager.set(
        my_reports=self.my_reports, structure_reports=self.structure_reports
      )
    except Exception as e:
      alert(f"An error occurred while refreshing reports: {e}")
      self.my_reports = []
      self.structure_reports = []

    self.apply_filters(active_tab)
    alert("Reports have been refreshed.")

  def apply_filters(self, report_type="my_reports"):
    source_reports = (
      self.my_reports if report_type == "my_reports" else self.structure_reports
    )
    filtered_list = list(source_reports) # Create a copy to modify

    if self.current_search_query:
      search_term = self.current_search_query.lower()
      if report_type == "structure_reports":
        filtered_list = [
          r for r in filtered_list
          if (search_term in (r.get("name") or "").lower())
          or (search_term in (r.get("file_name") or "").lower())
          or (search_term in (r.get("vet_display_name") or "").lower())
        ]
      else:
        filtered_list = [
          r for r in filtered_list
          if (search_term in (r.get("name") or "").lower())
          or (search_term in (r.get("file_name") or "").lower())
        ]

    if self.selected_statuses:
      filtered_list = [
        r for r in filtered_list
        if safe_value(r, "statut", "not_specified") in self.selected_statuses
      ]

    if report_type == "structure_reports":
      if self.selected_vets_emails:
        filtered_list = [
          r for r in filtered_list if r.get("owner_email") in self.selected_vets_emails
        ]
    else: 
      if self.selected_patient_ids:
        filtered_list = [
          r for r in filtered_list if r.get("animal_id") in self.selected_patient_ids
        ]

    # --- NEW: Add translated status text to each report dictionary for JS ---
    for report in filtered_list:
      report['statut_display'] = t.t(report.get('statut', 'not_specified'))

    if report_type == "my_reports":
      self.call_js("populateMyReports", filtered_list)
    else:
      self.call_js("populateStructureReports", filtered_list)

  def apply_my_reports_filters(self, statuses, patient_ids, **event_args):
    self.selected_statuses = statuses
    self.selected_patient_ids = patient_ids
    self.apply_filters("my_reports")

  def apply_structure_filters(self, statuses, vet_emails, **event_args):
    self.selected_statuses = statuses
    self.selected_vets_emails = vet_emails
    self.apply_filters("structure_reports")

  def search_reports(self, query, active_tab, **event_args):
    self.current_search_query = query
    self.selected_statuses = []
    self.selected_patient_ids = []
    self.selected_vets_emails = []
    self.apply_filters(active_tab)

  def delete_report(self, report_id, active_tab, **event_args):
    if confirm("Are you sure you want to delete this report?"):
      try:
        if anvil.server.call_s("delete_report", report_id):
          reports_cache_manager.invalidate()
          self.form_show()
        else:
          alert("Failed to delete the report on the server.")
      except Exception as e:
        alert(f"An error occurred while deleting the report: {e}")

  def open_report_editor(self, report, **event_args):
    try:
      safe_report = {
        "id": report.get("id"),
        "file_name": report.get("file_name"),
        "report_rich": report.get("report_rich"),
        "statut": report.get("statut"),
        "name": report.get("name"),
      }
      open_form("Archives.AudioManagerEdit", report=safe_report)
    except Exception as e:
      alert(f"Error opening report editor: {e}")
      open_form("ArchivesForm")

  def create_new_report(self, **event_args):
    reports_cache_manager.invalidate()
    open_form("Production.AudioManagerForm")