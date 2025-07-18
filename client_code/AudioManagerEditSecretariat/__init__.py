from ._anvil_designer import AudioManagerEditSecretariatTemplate
from anvil import *
import anvil.server
import anvil.users
import json

def safe_value(report, key, default_value):
  """Retourne la valeur associée à 'key' dans 'report', ou 'default_value' si elle est manquante ou None."""
  if report is None:
    return default_value
  val = report.get(key)
  return default_value if val is None else val

class AudioManagerEditSecretariat(AudioManagerEditSecretariatTemplate):
  def __init__(self, report=None, clicked_value=None, initial_content=None, **properties):
    """
    Ce formulaire est utilisé pour modifier un rapport existant.

    Il accepte soit :
      - un dictionnaire de rapport complet via le paramètre 'report', ou
      - des paramètres séparés (clicked_value et initial_content) à partir desquels un rapport minimal est construit.

    Le dictionnaire de rapport est censé contenir :
      - id : l'ID unique du rapport (utilisé pour la mise à jour)
      - file_name : le nom du fichier du rapport
      - report_rich : le contenu existant au format riche
      - statut : le statut actuel du rapport
      - name : le nom du patient/animal associé au rapport
      - (optionnel) transcript : le texte de transcription associé au rapport
    """
    anvil.users.login_with_form()
    self.init_components(**properties)
    print("Rapport reçu dans AudioManagerEditSecretariat :", report)

    # Construire un dictionnaire de rapport s'il n'est pas fourni.
    if report is None:
      if clicked_value is not None or initial_content is not None:
        report = {
          'id': clicked_value or "",
          'report_rich': initial_content or "",
          'file_name': 'Sans nom',
          'statut': 'Non spécifié',
          'name': '',
          'transcript': ''
        }
      else:
        alert("Aucun rapport fourni. Redirection vers Archives.")
        open_form("ArchivesSecretariat")
        return

    # Utiliser safe_value pour s'assurer que chaque champ est défini.
    self.report = {
      'id': safe_value(report, 'id', ""),
      'file_name': safe_value(report, 'file_name', "Sans nom"),
      'report_rich': safe_value(report, 'report_rich', ""),
      'statut': safe_value(report, 'statut', "Non spécifié"),
      'name': safe_value(report, 'name', ""),
      'transcript': safe_value(report, 'transcript', "")
    }
    self.report_id = self.report.get('id')
    self.file_name = self.report.get('file_name')
    self.initial_content = self.report.get('report_rich')
    self.statut = self.report.get('statut')
    self.animal_name = self.report.get('name')
    self.transcript = self.report.get('transcript')  # Charger la transcription

    # Masquer la barre de navigation (si présente) et afficher la barre Retour.
    if hasattr(self, 'retour_bar'):
      self.retour_bar.visible = True
    if hasattr(self, 'nav_tabs'):
      self.nav_tabs.visible = False

    # Ne pas définir le contenu de l'éditeur immédiatement (éviter d'appeler JS avant que le DOM soit prêt)
    # self.editor_content = self.initial_content

    # Attacher l'événement "show" du formulaire.
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Lors de l'affichage du formulaire, s'assurer que l'éditeur affiche le contenu actuel du rapport."""
    if self.initial_content:
      self.editor_content = self.initial_content

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  # --------------------------
  # Méthodes d'enregistrement audio
  # --------------------------
  def start_recording(self, **event_args):
    print("start_recording() appelé (mode édition).")

  def pause_recording(self, **event_args):
    print("pause_recording() appelé (mode édition).")

  def stop_recording(self, **event_args):
    print("stop_recording() appelé (mode édition).")

  def process_recording(self, audio_blob, **event_args):
    """
    Traite le blob audio : transcrit l'audio, puis appelle la fonction serveur edit_report()
    pour modifier le rapport existant selon les instructions orales.
    """
    print("process_recording() appelé avec un blob audio en mode édition.")
    try:
      # 1) Transcrire l'audio
      transcription = anvil.server.call("process_audio_whisper", audio_blob)

      # 2) Appeler la nouvelle fonction 'edit_report',
      #    en fournissant la transcription et le contenu actuel de l'éditeur
      edited_report = anvil.server.call("edit_report", transcription, self.editor_content)

      # 3) Mettre à jour l'éditeur avec le rapport édité
      self.editor_content = edited_report

      return "OK"
    except Exception as e:
      alert(f"Erreur lors du traitement de l'enregistrement : {str(e)}")

  # --------------------------
  # Nouvelle méthode pour relancer l'IA à partir du transcript
  # --------------------------
  def relaunch_ai(self, **event_args):
    print("relaunch_ai() appelé avec transcript:", self.transcript)
    try:
      # Réutiliser le même concept : edit_report
      edited_report = anvil.server.call("edit_report", self.transcript, self.editor_content)
      self.editor_content = edited_report
      self.call_js("displayBanner", "Rapport mis à jour avec succès", "success")
    except Exception as e:
      alert("Erreur lors du relancement de l'IA : " + str(e))

  # --------------------------
  # Propriété de l'éditeur
  # --------------------------
  @property
  def editor_content(self):
    try:
      return self.call_js("getEditorContent")
    except Exception as e:
      print("ERREUR lors de la récupération du contenu de l'éditeur :", e)
      return None

  @editor_content.setter
  def editor_content(self, value):
    try:
      self.call_js("setEditorContent", value)
    except Exception as e:
      print("ERREUR lors de la définition du contenu de l'éditeur :", e)

  # --------------------------
  # Sélection du Statut
  # --------------------------
  def on_statut_clicked(self, **event_args):
    """Invite l'utilisateur à sélectionner un nouveau statut pour le rapport."""
    choice = alert("Choisir le statut :", buttons=["à corriger", "validé", "envoyé", "Annuler"])
    if choice in ["à corriger", "validé", "envoyé"]:
      self.statut = choice
      self.call_js("displayBanner", f"Statut sélectionné : {choice}", "success")
      return choice
    else:
      return None

  # --------------------------
  # Mise à jour du rapport (Sauvegarder)
  # --------------------------
  def update_report(self, ignored_file_name, content_json, images, **event_args):
    """
    Appelé lorsque l'utilisateur clique sur "Archiver". Cette méthode met à jour l'enregistrement existant du rapport
    en appelant la fonction serveur write_report avec les paramètres dans l'ordre attendu :
      file_name, animal_name, vet, last_modified, report_rich, statut

    Remarque : Le paramètre file_name est ignoré et self.file_name est utilisé afin de conserver le nom de fichier inchangé.
    """
    print("update_report() appelé depuis JS en mode édition")
    try:
      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"Longueur du contenu HTML : {len(html_content)}")
      print(f"Nombre d'images : {len(images)}")
      statut = self.statut or "Non spécifié"
      file_name_to_use = self.file_name

      result = anvil.server.call(
          "write_report",
          file_name_to_use,
          self.animal_name,
          None,
          None,
          html_content,
          statut
      )
      if result:
        self.call_js("displayBanner", "Rapport mis à jour avec succès", "success")
        open_form("ArchivesSecretariat")
      else:
        alert("Échec de la mise à jour du rapport. Veuillez réessayer.")
    except Exception as e:
      print("Exception dans update_report :", e)
      alert("Erreur lors de la mise à jour du rapport : " + str(e))
    return True

  # --------------------------
  # Partager le rapport (Export PDF)
  # --------------------------
  def build_report_pdf_relay(self, placeholders, images):
    print("build_report_pdf_relay appelé en mode édition avec placeholders :", placeholders, "et images :", images)
    pdf_base64 = anvil.server.call("build_report_pdf_base64", placeholders, images)
    return pdf_base64

  def get_media_url_relay(self, pdf_media):
    import anvil
    return anvil.get_url(pdf_media)

  # --------------------------
  # Bouton Retour
  # --------------------------
  def retour_clicked(self, **event_args):
    """Retourner à la page Archives sans confirmation."""
    open_form("ArchivesSecretariat")
