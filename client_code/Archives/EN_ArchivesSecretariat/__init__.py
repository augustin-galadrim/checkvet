from ._anvil_designer import EN_ArchivesSecretariatTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

def safe_value(report, key, default_value):
  """Returns the value associated with 'key' in 'report', or 'default_value' if missing or None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class EN_ArchivesSecretariat(EN_ArchivesSecretariatTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

    # State variables
    self.reports = []                # Complete list of reports
    self.current_status_filter = "Show all"
    self.selected_vets = []          # List of selected veterinarian names

    try:
      self.structure = anvil.server.call("pick_user_info", "structure")
      self.affiliated_vets = anvil.server.call("pick_structure", self.structure, "affiliated_vets")
    except Exception as e:
      print("Error retrieving structure or affiliated veterinarians:", e)
      self.structure = None
      self.affiliated_vets = []

  def form_show(self, **event_args):
    """Runs when the form is shown."""
    try:
      raw_reports = anvil.server.call("get_reports_by_structure", self.structure)
      # Exclude any None entries
      self.reports = [r for r in raw_reports if r is not None]
    except Exception as e:
      print("Error retrieving reports:", e)
      self.reports = []

    try:
      self.call_js("setAffiliatedVets", self.affiliated_vets)
      self.call_js("setStructure", self.structure)
    except Exception as e:
      print("Error sending structure/veterinarian data to JS:", e)

    self._apply_combined_filters()

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def _apply_combined_filters(self):
    """Combine the status filter and the veterinarian selection."""
    try:
      # 1) Filter by status
      if self.current_status_filter == "Show all":
        subset_status = self.reports
      else:
        subset_status = [
          r for r in self.reports
          if safe_value(r, 'statut', "Not specified") == self.current_status_filter
        ]

      # 2) Filter by selected veterinarians (self.selected_vets)
      if not self.selected_vets:
        final_subset = subset_status
      else:
        selected_vets_email = []
        for vet in self.selected_vets:
          email = anvil.server.call("pick_user_email", vet, "email")
          selected_vets_email.append(email)
        final_subset = [
          report for report in subset_status
          if report.get("owner_email") in selected_vets_email
        ]

      # Populate the front-end with the filtered results
      self.call_js("populateReports", [r for r in final_subset if r is not None])
    except Exception as e:
      print("Error applying combined filters:", e)

  def open_audio_manager_form(self, report, **event_args):
    """Opens the audio manager form when a row is clicked (except on the trash icon)."""
    try:
      safe_report = {
        'id': safe_value(report, 'id', ""),
        'file_name': safe_value(report, 'file_name', "Untitled"),
        'report_rich': safe_value(report, 'report_rich', ""),
        'statut': safe_value(report, 'statut', "Not specified"),
        'name': safe_value(report, 'name', "")
      }
      # Pass the entire report (as safe_report) to preserve all keys
      open_form("Archives.EN_AudioManagerEditSecretariat", report=safe_report)
    except Exception as e:
      print("Error opening audio manager form:", e)
      alert("Error opening the report. Redirecting to EN_ArchivesSecretariat.")
      open_form("Archives.EN_ArchivesSecretariat")

  def open_production_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    open_form("Templates.EN_Templates")

  def open_settings_form(self, **event_args):
    open_form("Settings.EN_Settings")

  def open_create_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def filter_reports_client(self, filter_val, **event_args):
    """Called from JS when a status filter is selected."""
    self.current_status_filter = filter_val
    self._apply_combined_filters()

  def filter_reports_vets(self, vets_list, **event_args):
    """Called from JS when a veterinarian filter is applied."""
    self.selected_vets = vets_list
    self._apply_combined_filters()

  def search_reports_client(self, query, **event_args):
    """Called from JS when the search bar input changes."""
    print("search_reports_client called with query:", query)
    if not query:
      self._apply_combined_filters()
      return

    try:
      results = anvil.server.call('search_reports_for_all_vets_in_structure', query)
    except Exception as e:
      print("Server search error:", e)
      results = None

    # If server call fails or returns an unexpected value, fallback to client-side filtering
    if not isinstance(results, list):
      fallback_results = []
      for rep in self.reports:
        file_name = rep.get('file_name') or ""
        animal = rep.get('animal') or {}
        animal_name = animal.get('name', "")
        if query.lower() in file_name.lower() or query.lower() in animal_name.lower():
          fallback_results.append(rep)
      results = fallback_results

    print("search_reports_client: using", len(results), "result(s)")
    transformed_results = []
    for rep in results:
      if rep is None:
        continue
      transformed_results.append({
        'id': safe_value(rep, 'id', ""),
        'file_name': safe_value(rep, 'file_name', "Untitled"),
        'name': safe_value(rep, 'name', ""),
        'statut': safe_value(rep, 'statut', "Not specified"),
        'report_rich': safe_value(rep, 'report_rich', ""),
        'last_modified': safe_value(rep, 'last_modified', "")
      })
    print("search_reports_client: number of transformed results:", len(transformed_results))
    self.call_js("populateReports", transformed_results)

  def search_users_relay(self, search_input, **event_args):
    """Used by the Vet-add modal to search for users."""
    try:
      return anvil.server.call("search_users", search_input)
    except Exception as e:
      print("Error in search_users_relay:", e)
      return []

  def add_authorized_vet_relay(self, structure_id, user_email, **event_args):
    """Adds a vet to the affiliated list via server call."""
    try:
      result = anvil.server.call("add_authorized_vet", structure_id, user_email)
      self.affiliated_vets = anvil.server.call("pick_structure", self.structure, "affiliated_vets")
      self.call_js("setAffiliatedVets", self.affiliated_vets)
      return result
    except Exception as e:
      print("Error in add_authorized_vet_relay:", e)
      return None

  # ----------------------------------------------------------
  # Method to handle deletion of a report from the client side
  # ----------------------------------------------------------
  def delete_report_client_side(self, report_rich, **event_args):
    """Called from JS when the trash icon is clicked. Confirms, then calls 'delete_report' on the server."""
    confirm_result = confirm("Are you sure you want to delete this report?")
    if confirm_result:
      try:
        result = anvil.server.call('delete_report', report_rich)
        if result:
          print(f"Successfully deleted report with report_rich='{report_rich}' on the server.")
          # Remove the deleted report from self.reports
          self.reports = [r for r in self.reports if safe_value(r, 'report_rich', '') != report_rich]
          # Refresh the UI
          self.call_js("populateReports", self.reports)
      except Exception as e:
        print("Error during report deletion:", e)
        alert("An error occurred while deleting the report.")
