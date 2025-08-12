from ._anvil_designer import AudioManagerEditTemplate
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.users
import json


def safe_value(report, key, default_value):
  """Retourne la valeur associée à 'key' dans 'report', ou 'default_value' si elle est manquante ou None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val


class AudioManagerEdit(AudioManagerEditTemplate):
  def __init__(
    self, report=None, clicked_value=None, initial_content=None, **properties
  ):
    """
    Ce formulaire est utilisé pour modifier un rapport existant.

    Il accepte soit :
      - un dictionnaire de rapport complet via le paramètre 'report', ou
      - des paramètres séparés (clicked_value et initial_content) à partir desquels un rapport minimal
        est construit.

    Le dictionnaire de rapport doit contenir :
      - id : l'ID unique du rapport (utilisé pour la mise à jour)
      - file_name : le nom du fichier du rapport
      - report_rich : le contenu existant au format riche
      - statut : le statut actuel du rapport
      - name : le nom du patient/animal associé au rapport
      - transcript : le texte de transcription associé au rapport
    """
    anvil.users.login_with_form()
    print("Rapport reçu dans AudioManagerEditSecretariat :", report)
    self.init_components(**properties)
    self.recording_widget_1.set_event_handler(
      "recording_complete", self.handle_recording
    )
    # Construire un dictionnaire de rapport s'il n'est pas fourni.
    if report is None:
      if clicked_value is not None or initial_content is not None:
        report = {
          "id": clicked_value or "",
          "report_rich": initial_content or "",
          "file_name": "Sans nom",
          "statut": "Non spécifié",
          "name": "",
          "transcript": "",
        }
      else:
        alert("Aucun rapport fourni. Redirection vers Archives.")
        open_form("Archives.Archives")
        return

    # Utiliser safe_value pour s'assurer que chaque champ est défini.
    self.report = {
      "id": safe_value(report, "id", ""),
      "file_name": safe_value(report, "file_name", "Sans nom"),
      "report_rich": safe_value(report, "report_rich", ""),
      "statut": safe_value(report, "statut", "Non spécifié"),
      "name": safe_value(report, "name", ""),
      "transcript": safe_value(report, "transcript", ""),
    }
    self.report_id = self.report.get("id")
    self.file_name = self.report.get("file_name")
    self.initial_content = self.report.get("report_rich")
    self.statut = self.report.get("statut")
    self.animal_name = self.report.get("name")
    self.transcript = self.report.get("transcript")

    # Masquer la barre de navigation (si présente) et afficher la barre Retour.
    if hasattr(self, "retour_bar"):
      self.retour_bar.visible = True
    if hasattr(self, "nav_tabs"):
      self.nav_tabs.visible = False

    # Attacher l'événement show du formulaire pour peupler l'éditeur plus tard
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Lors de l'affichage du formulaire, s'assurer que l'éditeur affiche le contenu actuel du rapport."""
    if self.initial_content:
      self.text_editor_1.html_content = self.initial_content

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def handle_recording(self, audio_blob, **event_args):
    """This event handler is called by the RecordingWidget."""
    self.process_recording(audio_blob)

  def process_recording(self, audio_blob, **event_args):
    """
    Traite le blob audio : transcrit l'audio, puis appelle le nouveau server function edit_report()
    pour modifier le rapport existant selon les instructions orales.
    """
    print("process_recording() appelé avec un blob audio en mode édition.")
    try:
      transcription = anvil.server.call("process_audio_whisper", audio_blob)
      current_content = self.text_editor_1.get_content()
      edited_report = anvil.server.call("edit_report", transcription, current_content)
      self.text_editor_1.html_content = edited_report
      return "OK"

    except Exception as e:
      alert(f"Erreur lors du traitement de l'enregistrement : {str(e)}")

  def relaunch_ai(self, **event_args):
    print("relaunch_ai() appelé avec transcript:", self.transcript)
    try:
      current_content = self.text_editor_1.get_content()
      edited_report = anvil.server.call("edit_report", self.transcript, current_content)
      self.text_editor_1.html_content = edited_report
      self.call_js("displayBanner", "Rapport mis à jour avec succès", "success")
    except Exception as e:
      alert("Erreur lors du relancement de l'IA : " + str(e))

  def report_footer_1_status_clicked(self, **event_args):
    print("[DEBUG] report_footer_1_status_clicked called")
    status_options = anvil.server.call("get_status_options")

    buttons = [(opt.replace("_", " ").title(), opt) for opt in status_options]
    buttons.append(("Cancel", None))

    choice = alert("Choose status:", buttons=buttons)

    if choice:
      self.selected_statut = choice
      self.report_footer_1.update_status_display(choice)
      self.call_js(
        "displayBanner", f"Status chosen: {choice.replace('_', ' ').title()}", "success"
      )
    return choice

  def report_footer_1_save_clicked(
    self, ignored_file_name, content_json, images, **event_args
  ):
    """
    Appelé lorsque l'utilisateur clique sur "Archiver". Met à jour l'enregistrement
    existant du rapport en appelant la fonction serveur write_report.
    """
    print("update_report() appelé depuis JS en mode édition")
    try:
      html_content = self.text_editor_1.get_content()
      print(f"Longueur du contenu HTML : {len(html_content)}")
      print(f"Nombre d'images : {len(images)}")
      statut = self.statut or "not_specified"
      file_name_to_use = self.file_name

      result = anvil.server.call(
        "write_report",
        file_name_to_use,
        self.animal_name,
        None,
        None,
        html_content,
        statut,
      )

      if result:
        self.call_js("displayBanner", "Rapport mis à jour avec succès", "success")
        open_form("Archives.Archives")
      else:
        alert("Échec de la mise à jour du rapport. Veuillez réessayer.")
    except Exception as e:
      print("Exception dans update_report :", e)
      alert("Erreur lors de la mise à jour du rapport : " + str(e))
    return True
