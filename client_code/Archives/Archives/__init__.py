from ._anvil_designer import ArchivesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

def safe_value(report, key, default_value):
  """Retourne la valeur associée à la clé dans report, ou default_value si elle est manquante ou None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class Archives(ArchivesTemplate):
  def __init__(self, **properties):
    print("Initialisation du formulaire Archives...")
    self.init_components(**properties)
    print("Composants du formulaire initialisés.")
    self.add_event_handler("show", self.form_show)
    self.reports = []  # liste complète des rapports

  def form_show(self, **event_args):
    print("Déclenchement de form_show du formulaire Archives.")
    try:
      self.reports = anvil.server.call("read_reports")
      print(f"Reçu {len(self.reports)} rapports du serveur.")
    except Exception as e:
      print("Erreur lors de l'appel de read_reports :", e)
      self.reports = []

    # Affichage des rapports pour le débogage
    for i, rep in enumerate(self.reports):
      print(f"Rapport {i} : {rep}")

    try:
      self.call_js("populateReports", self.reports)
      print("Appel JS populateReports réussi.")
    except Exception as e:
      print("Erreur lors de l'appel de populateReports :", e)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def open_audio_manager_form(self, report, **event_args):
    print("open_audio_manager_form() appelé avec le rapport :", report)
    try:
      safe_report = {
        'id': safe_value(report, 'id', ""),
        'file_name': safe_value(report, 'file_name', "Sans nom"),
        'report_rich': safe_value(report, 'report_rich', ""),
        'statut': safe_value(report, 'statut', "Non spécifié"),
        'name': safe_value(report, 'name', "")
      }
      print("Rapport sécurisé construit :", safe_report)
      open_form("AudioManager.AudioManagerEdit", report=safe_report)
      print("Formulaire AudioManagerEdit ouvert avec succès.")
    except Exception as e:
      print("Erreur dans open_audio_manager_form :", e)
      alert("Erreur lors de l'ouverture du rapport. Redirection vers Archives.")
      open_form("Archives.Archives")

  def open_production_form(self, **event_args):
    print("open_production_form() appelé.")
    open_form("AudioManager.AudioManagerForm")

  def open_templates_form(self, **event_args):
    print("open_templates_form() appelé.")
    open_form("Templates.Templates")

  def open_settings_form(self, **event_args):
    print("open_settings_form() appelé.")
    open_form("Settings.Settings")

  def open_create_form(self, **event_args):
    print("open_create_form() appelé.")
    open_form("AudioManager.AudioManagerForm")

  def filter_reports_client(self, filter_val, **event_args):
    print(f"Filtrage des rapports par statut = '{filter_val}'")
    try:
      if filter_val == "Afficher tout":
        filtered = self.reports
      else:
        filtered = [r for r in self.reports if safe_value(r, 'statut', "Non spécifié") == filter_val]
      print(f"Nombre de rapports filtrés : {len(filtered)}")
      self.call_js("populateReports", filtered)
    except Exception as e:
      print("Erreur lors du filtrage des rapports :", e)

  def search_reports_client(self, query, **event_args):
    print(f"search_reports_client() appelé avec la requête : {query}")
    if not query:
      print("Requête vide ; renvoi des rapports initiaux.")
      self.call_js("populateReports", self.reports)
      return
    try:
      results = anvil.server.call('search_reports', query)
      print(f"La recherche a renvoyé {len(results)} résultats.")
      transformed_results = []
      for rep in results:
        transformed_results.append({
          'id': safe_value(rep, 'id', ""),
          'file_name': safe_value(rep, 'file_name', "Sans nom"),
          'name': safe_value(rep, 'name', ""),  # Utilisation de 'name' pour le patient
          'statut': safe_value(rep, 'statut', "Non spécifié"),
          'report_rich': safe_value(rep, 'report_rich', ""),
          'last_modified': safe_value(rep, 'last_modified', "")
        })
      self.call_js("populateReports", transformed_results)
      print("populateReports appelé pour les résultats de recherche.")
    except Exception as e:
      print("La recherche a échoué :", e)

  # -------------------------------------------------------
  # New method to handle deletion from the client side
  # -------------------------------------------------------
  def delete_report_client_side(self, report_rich, **event_args):
    """Confirm, then call the server function to delete a specific report."""
    confirm_result = confirm("Are you sure you want to delete this report?")
    if confirm_result:
      try:
        result = anvil.server.call('delete_report', report_rich)
        if result:
          print(f"Successfully deleted report with report_rich='{report_rich}' on server.")
          # Remove the deleted item from self.reports
          self.reports = [r for r in self.reports if safe_value(r, 'report_rich', "") != report_rich]
          # Update the front-end list
          self.call_js("populateReports", self.reports)
      except Exception as e:
        print("Error during report deletion:", e)
        alert("An error occurred while deleting the report.")
