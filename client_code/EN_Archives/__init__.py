from ._anvil_designer import EN_ArchivesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

def safe_value(report, key, default_value):
  """Returns the value associated with key in report, or default_value if missing or None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class EN_Archives(EN_ArchivesTemplate):
  def __init__(self, **properties):
    print("Initializing EN_Archives form...")
    self.init_components(**properties)
    print("Form components initialized.")
    self.add_event_handler("show", self.form_show)
    self.reports = []  # complete list of reports

  def form_show(self, **event_args):
    print("EN_Archives form_show triggered.")
    try:
      self.reports = anvil.server.call("read_reports")
      print(f"Received {len(self.reports)} reports from server.")
    except Exception as e:
      print("Error calling read_reports:", e)
      self.reports = []

    # Display reports for debugging
    for i, rep in enumerate(self.reports):
      print(f"Report {i} : {rep}")

    try:
      self.call_js("populateReports", self.reports)
      print("JS populateReports call succeeded.")
    except Exception as e:
      print("Error calling populateReports:", e)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def open_audio_manager_form(self, report, **event_args):
    print("open_audio_manager_form() called with report:", report)
    try:
      safe_report = {
        'id': safe_value(report, 'id', ""),
        'file_name': safe_value(report, 'file_name', "No name"),
        'report_rich': safe_value(report, 'report_rich', ""),
        'statut': safe_value(report, 'statut', "Not specified"),
        'name': safe_value(report, 'name', "(None)")
      }
      print("Safe report constructed:", safe_report)
      open_form("EN_AudioManagerEdit", report=safe_report)
      print("EN_AudioManagerEdit form opened successfully.")
    except Exception as e:
      print("Error in open_audio_manager_form:", e)
      alert("Error opening report. Redirecting to EN_Archives.")
      open_form("EN_Archives")

  def open_production_form(self, **event_args):
    print("open_production_form() called.")
    open_form("AudioManagerForm")

  def open_templates_form(self, **event_args):
    print("open_templates_form() called.")
    open_form("EN_Templates")

  def open_settings_form(self, **event_args):
    print("open_settings_form() called.")
    open_form("EN_Settings")

  def open_create_form(self, **event_args):
    print("open_create_form() called.")
    open_form("AudioManagerForm")

  def filter_reports_client(self, filter_val, **event_args):
    print(f"Filtering reports by status = '{filter_val}'")
    try:
      if filter_val == "Show all":
        filtered = self.reports
      else:
        filtered = [r for r in self.reports if safe_value(r, 'statut', "Not specified") == filter_val]
      print(f"Number of filtered reports: {len(filtered)}")
      self.call_js("populateReports", filtered)
    except Exception as e:
      print("Error filtering reports:", e)

  def search_reports_client(self, query, **event_args):
    print(f"search_reports_client() called with query: {query}")
    if not query:
      print("Empty query; returning initial reports.")
      self.call_js("populateReports", self.reports)
      return
    try:
      results = anvil.server.call('search_reports', query)
      print(f"Search returned {len(results)} results.")
      transformed_results = []
      for rep in results:
        transformed_results.append({
          'id': safe_value(rep, 'id', ""),
          'file_name': safe_value(rep, 'file_name', "No name"),
          'name': safe_value(rep, 'name', "(None)"),
          'statut': safe_value(rep, 'statut', "Not specified"),
          'report_rich': safe_value(rep, 'report_rich', ""),
          'last_modified': safe_value(rep, 'last_modified', "")
        })
      self.call_js("populateReports", transformed_results)
      print("populateReports called for search results.")
    except Exception as e:
      print("Search failed:", e)

  # -------------------------------------------------------------------------
  # New method for handling the trash icon click from the client side
  # -------------------------------------------------------------------------
  def delete_report_client_side(self, report_rich, **event_args):
    """Confirm, then call the server function to delete a specific report."""
    confirm_result = confirm("Are you sure you want to delete this report?")
    if confirm_result:
      try:
        result = anvil.server.call('delete_report', report_rich)
        if result:
          print(f"Successfully deleted report with report_rich='{report_rich}' on the server.")
          # Remove the deleted item from self.reports
          self.reports = [r for r in self.reports if safe_value(r, 'report_rich', '') != report_rich]
          # Update the front-end list
          self.call_js("populateReports", self.reports)
      except Exception as e:
        print("Error during report deletion:", e)
        alert("An error occurred while deleting the report.")
