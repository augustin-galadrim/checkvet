from ._anvil_designer import ArchivesSecretariatTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

def safe_value(report, key, default_value):
  """Retourne la valeur associée à 'key' dans 'report', ou 'default_value' si elle est manquante ou None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class ArchivesSecretariat(ArchivesSecretariatTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.add_event_handler("show", self.form_show)

    # Variables d'état.
    self.reports = []                # liste complète des rapports
    self.current_status_filter = "Afficher tout"
    self.selected_vets = []          # liste des noms de vétérinaires sélectionnés

    try:
      self.struture = anvil.server.call("pick_user_info", "structure")
      self.affiliated_vets = anvil.server.call("pick_structure", self.struture, "affiliated_vets")
    except Exception as e:
      print("Erreur lors de la récupération de la structure ou des vétérinaires affiliés :", e)
      self.struture = None
      self.affiliated_vets = []

  def form_show(self, **event_args):
    try:
      raw_reports = anvil.server.call("get_reports_by_structure", self.struture)
      # Exclure les entrées None.
      self.reports = [r for r in raw_reports if r is not None]
    except Exception as e:
      print("Erreur lors de la récupération des rapports :", e)
      self.reports = []

    try:
      self.call_js("setAffiliatedVets", self.affiliated_vets)
      self.call_js("setStructure", self.struture)
    except Exception as e:
      print("Erreur lors de l'envoi des données de structure/vétérinaires au JS :", e)

    self._apply_combined_filters()

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def _apply_combined_filters(self):
    """Combine le filtre par statut et la sélection des vétérinaires."""
    try:
      # 1) Filtrer par statut.
      if self.current_status_filter == "Afficher tout":
        subset_status = self.reports
      else:
        subset_status = [
          r for r in self.reports
          if safe_value(r, 'statut', "Non spécifié") == self.current_status_filter
        ]

      # 2) Filtrer par vétérinaires sélectionnés (self.selected_vets).
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

      self.call_js("populateReports", [r for r in final_subset if r is not None])
    except Exception as e:
      print("Erreur lors de l'application des filtres combinés :", e)

  def open_audio_manager_form(self, report, **event_args):
    try:
      safe_report = {
        'id': safe_value(report, 'id', ""),
        'file_name': safe_value(report, 'file_name', "Sans nom"),
        'report_rich': safe_value(report, 'report_rich', ""),
        'statut': safe_value(report, 'statut', "Non spécifié"),
        'name': safe_value(report, 'name', "")
      }
      open_form("Archives.AudioManagerEditSecretariat", report=safe_report)
    except Exception as e:
      print("Erreur lors de l'ouverture du formulaire de gestion audio :", e)
      alert("Erreur lors de l'ouverture du rapport. Redirection vers ArchivesSecretariat.")
      open_form("Archives.ArchivesSecretariat")

  def open_production_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def open_templates_form(self, **event_args):
    open_form("Templates.Templates")

  def open_settings_form(self, **event_args):
    open_form("Settings.Settings")

  def open_create_form(self, **event_args):
    open_form("Production.AudioManagerForm")

  def filter_reports_client(self, filter_val, **event_args):
    self.current_status_filter = filter_val
    self._apply_combined_filters()

  def filter_reports_vets(self, vets_list, **event_args):
    self.selected_vets = vets_list
    self._apply_combined_filters()

  def search_reports_client(self, query, **event_args):
    print("search_reports_client appelé avec la requête :", query)
    if not query:
      self._apply_combined_filters()
      return

    try:
      results = anvil.server.call('search_reports_for_all_vets_in_structure', query)
    except Exception as e:
      print("Erreur de recherche depuis le serveur :", e)
      results = None

    # Si l'appel serveur échoue ou renvoie une valeur inattendue, fallback en local.
    if not isinstance(results, list):
      fallback_results = []
      for rep in self.reports:
        file_name = rep.get('file_name') or ""
        animal = rep.get('animal') or {}
        animal_name = animal.get('name', "")
        if query.lower() in file_name.lower() or query.lower() in animal_name.lower():
          fallback_results.append(rep)
      results = fallback_results

    print("search_reports_client : utilisation de", len(results), "résultat(s)")
    transformed_results = []
    for rep in results:
      if rep is None:
        continue
      transformed_results.append({
        'id': safe_value(rep, 'id', ""),
        'file_name': safe_value(rep, 'file_name', "Sans nom"),
        'name': safe_value(rep, 'name', ""),
        'statut': safe_value(rep, 'statut', "Non spécifié"),
        'report_rich': safe_value(rep, 'report_rich', ""),
        'last_modified': safe_value(rep, 'last_modified', "")
      })
    print("search_reports_client : nombre de résultats transformés :", len(transformed_results))
    self.call_js("populateReports", transformed_results)

  def search_users_relay(self, search_input, **event_args):
    try:
      return anvil.server.call("search_users", search_input)
    except Exception as e:
      print("Erreur dans search_users_relay :", e)
      return []

  def add_authorized_vet_relay(self, structure_id, user_email, **event_args):
    try:
      result = anvil.server.call("add_authorized_vet", structure_id, user_email)
      self.affiliated_vets = anvil.server.call("pick_structure", self.struture, "affiliated_vets")
      self.call_js("setAffiliatedVets", self.affiliated_vets)
      return result
    except Exception as e:
      print("Erreur dans add_authorized_vet_relay :", e)
      return None

  # -------------------------------------------------------------------------
  # Handling the trash-icon click from the client side
  # -------------------------------------------------------------------------
  def delete_report_client_side(self, report_rich, **event_args):
    confirm_result = confirm("Are you sure you want to delete this report?")
    if confirm_result:
      try:
        result = anvil.server.call('delete_report', report_rich)
        if result:
          print(f"Successfully deleted report with report_rich='{report_rich}' on server.")
          # Remove the deleted item from self.reports
          self.reports = [r for r in self.reports if safe_value(r, 'report_rich', '') != report_rich]
          # Refresh the front-end
          self.call_js("populateReports", self.reports)
      except Exception as e:
        print("Error during report deletion:", e)
        alert("An error occurred while deleting the report.")
