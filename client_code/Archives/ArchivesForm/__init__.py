from ._anvil_designer import ArchivesFormTemplate
from anvil import *
import anvil.server
import anvil.users


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

    # --- State variables ---
    self.is_supervisor = False
    self.has_structure = False

    self.my_reports = []
    self.structure_reports = []

    self.structure_name = None
    self.affiliated_vets = []

    # --- Filter states ---
    self.current_status_filter = "Afficher tout"
    self.selected_vets_emails = []

  def form_show(self, **event_args):
    """
    Called when the form is shown. It determines the user's role and structure affiliation,
    then loads the appropriate data and configures the UI.
    """
    user = anvil.users.get_user()
    self.is_supervisor = user and user["supervisor"]
    self.header_nav_1.active_tab = "Archives"

    try:
      # ALL users (including supervisors) need to load their own reports.
      print("Loading personal reports for the current user.")
      self.my_reports = anvil.server.call("read_reports") or []
      self.call_js("populateMyReports", self.my_reports)

      if self.is_supervisor:
        self.structure_name = anvil.server.call("pick_user_structure")
        self.has_structure = bool(
          self.structure_name and self.structure_name != "Indépendant"
        )

        if self.has_structure:
          print(
            f"User is a supervisor for structure: '{self.structure_name}'. Loading structure data."
          )
          self.affiliated_vets = (
            anvil.server.call("get_affiliated_vets_details", self.structure_name) or []
          )
          self.structure_reports = (
            anvil.server.call("get_reports_by_structure", self.structure_name) or []
          )

          # Tell JS to set up the full supervisor UI with two tabs
          self.call_js("setupUI", True, True, self.affiliated_vets, self.structure_name)
          self.call_js("populateStructureReports", self.structure_reports)
        else:
          print("User is a supervisor but has no structure assigned.")
          # Tell JS to set up the supervisor UI but hide the structure tab/features
          self.call_js("setupUI", True, False, [], None)
      else:
        print("User is a regular vet.")
        # Tell JS to set up the standard vet UI
        self.call_js("setupUI", False, False, [], None)

      # Initially, apply filters to the default view (My Reports)
      self.apply_filters("my_reports")

    except Exception as e:
      print(f"Error during form show: {e}")
      alert("An error occurred while loading reports.")
      self.my_reports = []
      self.structure_reports = []
      self.call_js("populateMyReports", [])
      self.call_js("populateStructureReports", [])

  def apply_filters(self, report_type="my_reports"):
    """
    Applies current filters to the specified list of reports (either personal or structure).
    """
    source_reports = (
      self.my_reports if report_type == "my_reports" else self.structure_reports
    )

    # 1. Filter by status
    if self.current_status_filter == "Afficher tout":
      status_filtered = source_reports
    else:
      status_filtered = [
        r
        for r in source_reports
        if safe_value(r, "statut", "Non spécifié") == self.current_status_filter
      ]

    # 2. For structure reports, apply vet filter if active
    final_filtered = status_filtered
    if report_type == "structure_reports" and self.selected_vets_emails:
      final_filtered = [
        r for r in status_filtered if r.get("owner_email") in self.selected_vets_emails
      ]

    # Update the correct UI section
    if report_type == "my_reports":
      self.call_js("populateMyReports", final_filtered)
    else:
      self.call_js("populateStructureReports", final_filtered)

  # --- Event Handlers Called from JavaScript ---

  def filter_reports_by_status(self, filter_val, active_tab, **event_args):
    self.current_status_filter = filter_val
    self.apply_filters(active_tab)

  def filter_reports_by_vets(self, vets_emails_list, **event_args):
    if self.is_supervisor:
      self.selected_vets_emails = vets_emails_list
      self.apply_filters("structure_reports")  # This only applies to the structure tab

  def search_reports(self, query, active_tab, **event_args):
    target_populate_func = "populateMyReports"

    if not query:
      self.apply_filters(active_tab)
      return

    try:
      # Call the appropriate server function based on which tab is active
      if self.is_supervisor and active_tab == "structure_reports":
        results = anvil.server.call("search_reports_for_all_vets_in_structure", query)
        target_populate_func = "populateStructureReports"
      else:
        results = anvil.server.call("search_reports", query)

      self.call_js(target_populate_func, [r for r in results if r is not None])
    except Exception as e:
      alert(f"Search failed: {e}")

  def delete_report(self, report_rich, active_tab, **event_args):
    if confirm("Are you sure you want to delete this report?"):
      try:
        if anvil.server.call("delete_report", report_rich):
          # Remove from the correct local list and refresh
          if active_tab == "my_reports":
            self.my_reports = [
              r
              for r in self.my_reports
              if safe_value(r, "report_rich", "") != report_rich
            ]
          else:
            self.structure_reports = [
              r
              for r in self.structure_reports
              if safe_value(r, "report_rich", "") != report_rich
            ]
          self.apply_filters(active_tab)
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
    open_form("Production.AudioManagerForm")

  # --- Supervisor-only Functions ---

  def search_users_for_modal(self, search_input, **event_args):
    if self.is_supervisor:
      try:
        return anvil.server.call("search_users", search_input)
      except Exception as e:
        return []
    return []

  def add_vet_to_structure(self, user_email, **event_args):
    if self.is_supervisor:
      try:
        result = anvil.server.call("add_authorized_vet", None, user_email)
        # Refresh vet list in the modal
        self.affiliated_vets = (
          anvil.server.call("get_affiliated_vets_details", self.structure_name) or []
        )
        self.call_js("setAffiliatedVets", self.affiliated_vets)
        return result
      except Exception as e:
        alert(f"Error adding vet: {e}")
    return None
