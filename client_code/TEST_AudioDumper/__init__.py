from ._anvil_designer import TEST_AudioDumperTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
import anvil.users

def safe_value(item, key, default_value):
  """Retourne la valeur associée à 'key' dans 'item', ou 'default_value' si la clé est manquante ou None."""
  if item is None:
    return default_value
  val = item.get(key)
  return default_value if val is None else val

class TEST_AudioDumper(TEST_AudioDumperTemplate):
  def __init__(
    self,
    clicked_value=None,
    template_name=None,
    initial_content=None,
    prompt=None,
    **properties,
  ):
    print("[DEBUG] Initialisation du formulaire FR_AudioManager")
    print(f"[DEBUG] Paramètres __init__: clicked_value={clicked_value}, template_name={template_name}, initial_content={initial_content}, prompt={prompt}")
    self.init_components(**properties)

    # Stocker les paramètres fournis par l'utilisateur
    self.clicked_value = clicked_value
    self.template_name = template_name
    self.initial_content = initial_content
    self.prompt = prompt

    # Stockage pour la transcription brute
    self.raw_transcription = None

    # État de l'enregistrement
    self.recording_state = "idle"

    # Le statut sélectionné par l'utilisateur sera stocké ici
    self.selected_statut = None

    def silent_error_handler(err):
      print(f"[DEBUG] Gestionnaire d'erreur silencieux: {err}")
      # Optionnel: Ajoutez du logging ici
      pass
    set_default_error_handling(silent_error_handler)

    # Lors de l'affichage du formulaire, exécuter form_show
    self.add_event_handler("show", self.form_show)
    print("[DEBUG] __init__ terminé.")

  def form_show(self, **event_args):
    print("[DEBUG] Démarrage de form_show dans FR_AudioManager")
    # Vérifier si l'utilisateur a fourni des infos supplémentaires
    additional_info = anvil.server.call("pick_user_info", "additional_info")
    print(f"[DEBUG] additional_info depuis pick_user_info: {additional_info}")
    if not additional_info:
      print("[DEBUG] Pas d'additional_info, ouverture du flux d'inscription en français (RegistrationFlow)")
      open_form("FR_RegistrationFlow")
      return

    mobile_installation = anvil.server.call("pick_user_info2", "mobile_installation")
    print(f"[DEBUG] mobile_installation depuis pick_user_info2: {mobile_installation}")
    if not mobile_installation:
      print("[DEBUG] Pas d'installation mobile renseignée, ouverture du flux d'installation mobile en français")
      open_form("FR_MobileInstallationFlow")
      return

    # Charger les modèles en base et filtrer sur les favoris (priorité 1 ou 2)
    templates = anvil.server.call("read_templates")  # renvoie une liste de dictionnaires
    filtered_templates = [t for t in templates if t.get('priority') in (1, 2)]
    self.call_js("populateTemplateModal", filtered_templates)

    # Charger un contenu initial dans l'éditeur, si fourni
    if self.initial_content:
      print("[DEBUG] Chargement du contenu initial dans l'éditeur.")
      self.editor_content = self.initial_content
    else:
      if self.clicked_value is not None:
        print("[DEBUG] clicked_value fourni, chargement du contenu du rapport.")
        self.load_report_content()

    # Recréer le champ de recherche de patient (comme dans la modal d'archives).
    print("[DEBUG] Reconstruire le champ de recherche patient.")
    self.call_js("rebuildPatientSearchInput")

    print("[DEBUG] form_show terminé.")

  def refresh_session_relay(self, **event_args):
    """Appelé lorsque l'application redevient en ligne ou que l'onglet revient au premier plan, pour garder la session utilisateur active."""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Erreur dans refresh_session_relay: {str(e)}")
      return False

  def load_report_content(self):
    print(f"[DEBUG] Chargement du contenu du rapport pour clicked_value: {self.clicked_value}")
    try:
      content, error = anvil.server.call("load_report_content", self.clicked_value)
      print(f"[DEBUG] Résultat de load_report_content: content={content}, error={error}")
      if error:
        alert(error)
      elif content:
        self.editor_content = content
      else:
        alert("Erreur inattendue : aucun contenu renvoyé.")
    except Exception as e:
      print(f"[ERROR] Exception dans load_report_content: {e}")

  # -------------------------
  # Méthodes d'enregistrement
  # -------------------------
  def start_recording(self, **event_args):
    self.recording_state = "recording"
    print("[DEBUG] start_recording() appelé. État d'enregistrement défini sur 'recording'.")

  def pause_recording(self, **event_args):
    self.recording_state = "paused"
    print("[DEBUG] pause_recording() appelé. État d'enregistrement défini sur 'paused'.")

  def stop_recording(self, **event_args):
    self.recording_state = "stopped"
    print("[DEBUG] stop_recording() appelé. État d'enregistrement défini sur 'stopped'.")

  def show_error(self, error_message, **event_args):
    print(f"[DEBUG] show_error() appelé avec le message: {error_message}")
    alert(error_message)

  # -------------------------
  # Nouvelle méthode pour traiter les fichiers audio uploadés
  # -------------------------
  def process_uploaded_audio(self, audio_blob, **event_args):
    """
    Traite un fichier audio uploadé (particulièrement pour les Voice Memos iOS)
    """
    print("[DEBUG] process_uploaded_audio() appelé avec un audio blob.")
    try:
        # Exécuter le traitement de l'audio une fois le fichier reçu
      return self.process_recording(audio_blob)
    except Exception as e:
      print(f"[ERROR] Exception dans process_uploaded_audio: {e}")
      alert(f"Erreur lors du traitement du fichier audio: {str(e)}")
      return None

  # -------------------------
  # Détection de la langue
  # -------------------------
  def get_selected_language(self):
    """
    Récupère la langue actuellement sélectionnée en se basant sur l'émoji du drapeau
    dans le dropdown de langue.
    Retourne: 'FR' ou 'EN'
    """
    try:
      language_emoji = self.call_js("getDropdownSelectedValue", "langueDropdown")
      print(f"[DEBUG] Émoji de langue sélectionné: {language_emoji}")
      if language_emoji == "🇫🇷":
        return "FR"
      elif language_emoji == "🇬🇧":
        return "EN"
      else:
        # Par défaut, on retourne FR si on ne sait pas
        print(f"[DEBUG] Émoji de langue inconnu: {language_emoji}, on retourne FR par défaut")
        return "FR"
    except Exception as e:
      print(f"[ERROR] Erreur en récupérant la langue sélectionnée: {e}")
      return "FR"

  # -------------------------
  # Traitement de l'audio
  # -------------------------
  def process_recording(self, audio_blob, **event_args):
    """
    Traite un enregistrement audio pour générer un rapport vétérinaire.

    Étapes:
      1. Récupère le nom du modèle et la langue sélectionnés
      2. Récupère le prompt correspondant à cette langue
      3. Transcrit l'audio via l'API Whisper
      4. Génère le rapport via GPT-4
      5. Formate le rapport selon la langue
      6. Met à jour l'éditeur avec le rapport final
    """
    print("[DEBUG] process_recording() appelé avec un audio blob.")
    try:
      #---------- SÉLECTION DU MODÈLE ----------#
      selected_template_with_star = self.call_js("getDropdownSelectedValue", "templateSelectBtn")
      print(f"[DEBUG] Modèle brut sélectionné: {selected_template_with_star}")
      selected_template = selected_template_with_star.split(" [")[0]
      print(f"[DEBUG] Nom du modèle nettoyé: {selected_template}")
      if not selected_template or selected_template.startswith("Sélection"):
        alert("Aucun modèle sélectionné. Veuillez choisir un modèle dans la fenêtre modale.")
        return

      #---------- DÉTECTION DE LANGUE ----------#
      selected_language = self.get_selected_language()
      print(f"[DEBUG] Langue choisie pour le template/prompt: {selected_language}")

      #---------- SÉLECTION DE LA COLONNE PROMPT ----------#
      prompt_header = "prompt_fr" if selected_language == "FR" else "prompt_en"
      print(f"[DEBUG] Colonne de prompt utilisée: {prompt_header}")

      #---------- RÉCUPÉRATION DU PROMPT ----------#
      template_prompt = anvil.server.call("pick_template", selected_template, prompt_header)
      print(f"[DEBUG] Prompt pour le modèle '{selected_template}' ({prompt_header}): {template_prompt}")
      if not template_prompt:
        print(f"[DEBUG] Pas de {prompt_header}, tentative du prompt par défaut.")
        template_prompt = anvil.server.call("pick_template", selected_template, "prompt")
        if not template_prompt:
          alert(f"Aucun prompt trouvé pour le modèle '{selected_template}'")
          return
      self.template_name = selected_template
      self.prompt = template_prompt

      #---------- TRANSCRIPTION AUDIO ----------#
      print("[DEBUG] Appel à Whisper pour la transcription")
      if selected_language == "EN":
        transcription = anvil.server.call("EN_process_audio_whisper", audio_blob)
      else:
        transcription = anvil.server.call("process_audio_whisper", audio_blob)
      print(f"[DEBUG] Transcription reçue: {transcription}")
      self.raw_transcription = transcription

      #---------- GÉNÉRATION DU RAPPORT (GPT-4) ----------#
      print("[DEBUG] Appel à generate_report")
      report_content = anvil.server.call("generate_report", self.prompt, transcription)
      print(f"[DEBUG] Contenu du rapport généré: {report_content}")

      #---------- FORMATAGE DU RAPPORT ----------#
      print("[DEBUG] Appel à format_report")
      if selected_language == "FR":
        report_final = anvil.server.call("format_report", report_content)
      else:
        report_final = anvil.server.call("EN_format_report", report_content)
      print(f"[DEBUG] Rapport final formaté: {report_final}")

      #---------- MISE À JOUR DE L'ÉDITEUR ----------#
      self.editor_content = report_final
      print("[DEBUG] process_recording() terminé avec succès.")
      return "OK"

    except Exception as e:
      print(f"[ERROR] Exception dans process_recording: {e}")
      alert(f"Erreur lors du traitement de l'enregistrement: {str(e)}")

  # -------------------------
  # Traitement des formats iOS
  # -------------------------
  def convert_audio_format_if_needed(self, audio_blob, file_name, **event_args):
    """
    Vérifie si le format audio est compatible (notamment pour iOS Voice Memos) et le convertit si nécessaire.
    iOS Voice Memos utilise généralement le format .m4a, qui est compatible avec notre traitement.
    """
    print(f"[DEBUG] Vérification du format audio pour: {file_name}")

    try:
      # Vérifier l'extension du fichier
      file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''

      if file_extension in ['m4a', 'mp3', 'wav', 'aac']:
        # Formats déjà compatibles avec notre système
        print(f"[DEBUG] Format audio compatible: {file_extension}")
        return audio_blob
      else:
        # On pourrait implémenter la conversion ici
        # Pour l'instant, on alerte simplement l'utilisateur
        print(f"[DEBUG] Format audio non optimal: {file_extension}")
        if file_extension not in ['m4a']:
          alert(f"Note: Le format {file_extension} n'est pas optimisé pour iOS Voice Memos (qui utilise m4a).")
        return audio_blob

    except Exception as e:
      print(f"[ERROR] Erreur lors de la vérification du format audio: {e}")
      return audio_blob  # On retourne le blob original en cas d'erreur

  # -------------------------
  # Propriété pour l'éditeur
  # -------------------------
  @property
  def editor_content(self):
    try:
      content = self.call_js("getEditorContent")
      print(f"[DEBUG] Contenu de l'éditeur récupéré: {content}")
      return content
    except Exception as e:
      print(f"[ERROR] ERREUR en récupérant le contenu de l'éditeur: {e}")
      return None

  @editor_content.setter
  def editor_content(self, value):
    try:
      print(f"[DEBUG] Mise à jour du contenu de l'éditeur: {value}")
      self.call_js("setEditorContent", value)
    except Exception as e:
      print(f"[ERROR] ERREUR en définissant le contenu de l'éditeur: {e}")

  # -------------------------
  # Méthode pour le bouton "Statut"
  # -------------------------
  def on_statut_clicked(self, **event_args):
    print("[DEBUG] on_statut_clicked() appelé")
    choice = alert(
      "Choisir le statut :",
      buttons=["à corriger", "validé", "envoyé", "Annuler"]
    )
    print(f"[DEBUG] Statut sélectionné: {choice}")
    if choice in ["à corriger", "validé", "envoyé"]:
      self.selected_statut = choice
      self.call_js("displayBanner", f"Statut choisi: {choice}", "success")
      return choice
    else:
      return None

  # -------------------------
  # Sauvegarde et génération PDF
  # -------------------------
  def save_report(self, content_json, images, selected_patient, **event_args):
    print("[DEBUG] save_report() appelé depuis le JS")
    try:
        # Vérifier que selected_patient est un dict
      if not isinstance(selected_patient, dict):
        print(f"[DEBUG] selected_patient n'est pas un dict. Recherche du patient : {selected_patient}")
        matches = self.search_patients_relay(selected_patient)
        if len(matches) == 1:
          selected_patient = matches[0]
          print(f"[DEBUG] Patient trouvé: {selected_patient}")
        elif len(matches) > 1:
          alert("Plusieurs patients trouvés. Veuillez en sélectionner un dans la liste.")
          return
        else:
          alert("Aucun patient trouvé avec ce nom.")
          return

      animal_name = selected_patient.get("name")
      unique_id = selected_patient.get("unique_id")
      print(f"[DEBUG] Extraction du patient: animal_name={animal_name}, unique_id={unique_id}")

      if unique_id is None:
        print("[DEBUG] Nouveau patient détecté, création via write_animal_first_time")
        details = selected_patient.get("details", {})
        type_val = details.get("type")
        proprietaire_val = details.get("proprietaire")
        new_unique_id = anvil.server.call("write_animal_first_time", animal_name, type=type_val, proprietaire=proprietaire_val)
        print(f"[DEBUG] write_animal_first_time a renvoyé unique_id: {new_unique_id}")
        unique_id = new_unique_id
      else:
        print("[DEBUG] Patient existant sélectionné, réutilisation des infos.")

      parsed = json.loads(content_json)
      html_content = parsed.get("content", "")
      print(f"[DEBUG] Longueur du contenu HTML: {len(html_content)}")
      print(f"[DEBUG] Nombre d'images: {len(images)}")

      statut = self.selected_statut or "Non spécifié"
      print(f"[DEBUG] Statut utilisé: {statut}")

      print("[DEBUG] Appel de write_report_first_time avec unique_id.")
      result = anvil.server.call(
          "write_report_first_time",
          animal_name=animal_name,
          report_rich=html_content,
          statut=statut,
          unique_id=unique_id,
          transcript=self.raw_transcription
      )
      print(f"[DEBUG] Retour de write_report_first_time : {result}")

      if result:
        self.call_js("displayBanner", "Rapport enregistré avec succès", "success")
      else:
        alert("Échec de l'enregistrement du rapport. Veuillez réessayer.")

    except Exception as e:
      print(f"[ERROR] Exception dans save_report: {e}")
      raise

    print("[DEBUG] save_report() terminé avec succès.")
    return True

  def get_new_patient_details(self):
    print("[DEBUG] get_new_patient_details() appelé")
    form_content = ColumnPanel(spacing=10)
    form_content.add_component(TextBox(placeholder="Nom"))
    form_content.add_component(TextBox(placeholder="Espèce"))
    form_content.add_component(TextBox(placeholder="Propriétaire"))
    result = alert(
      content=form_content, title="Entrer les détails du nouveau patient", buttons=["OK", "Annuler"]
    )
    print(f"[DEBUG] Résultat get_new_patient_details: {result}")
    if result == "OK":
      components = form_content.get_components()
      details = {
        "name": components[0].text,
        "type": components[1].text,
        "proprietaire": components[2].text,
      }
      print(f"[DEBUG] Détails du nouveau patient: {details}")
      return details
    else:
      print("[DEBUG] get_new_patient_details annulé par l'utilisateur.")
      return None

  def build_report_pdf_relay(self, placeholders, images):
    print("[DEBUG] build_report_pdf_relay appelé")
    print(f"[DEBUG] Placeholders: {placeholders}, Nombre d'images: {len(images)}")
    pdf_base64 = anvil.server.call("build_report_pdf_base64", placeholders, images)
    print(f"[DEBUG] pdf_base64 reçu du serveur. Longueur: {len(pdf_base64)}")
    return pdf_base64

  def get_media_url_relay(self, pdf_media):
    print("[DEBUG] get_media_url_relay appelé")
    import anvil
    url = anvil.get_url(pdf_media)
    print(f"[DEBUG] URL générée: {url}")
    return url

  # -------------------------
  # Navigation depuis les onglets du haut
  # -------------------------
  def open_production_form(self, **event_args):
    print("[DEBUG] Ouverture du formulaire FR_Production")
    open_form("Production")

  def open_templates_form(self, **event_args):
    print("[DEBUG] Ouverture du formulaire FR_Templates")
    open_form("Templates")

  def open_archives_form(self, **event_args):
    print("[DEBUG] Ouverture du formulaire FR_Archives")
    current_user = anvil.users.get_user()
    if current_user['supervisor']:
      open_form("ArchivesSecretariat")
    else:
      open_form("Archives")

  def open_settings_form(self, **event_args):
    print("[DEBUG] Ouverture du formulaire FR_Parametres")
    open_form("Settings")

  # -------------------------
  # Relay front-end pour la recherche de patients
  # -------------------------
  def search_patients_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_patients_relay appelé avec search_term: {search_term}")
    try:
      results = anvil.server.call("search_patients", search_term)
      print(f"[DEBUG] Résultats de search_patients_relay: {results}")
      return results
    except Exception as e:
      print(f"[ERROR] Erreur dans search_patients_relay: {e}")
      return []

  # -------------------------
  # Relay front-end pour la recherche de modèles
  # -------------------------
  def search_template_relay(self, search_term, **event_args):
    print(f"[DEBUG] search_template_relay appelé avec search_term: {search_term}")
    try:
      results = anvil.server.call("EN_search_templates", search_term)
      if results is None:
        results = []
      transformed_results = []
      for template in results:
        if template is None:
          continue
        transformed_result = {
          "id": safe_value(template, "id", ""),
          "template_name": safe_value(template, "template_name", "Modèle sans nom"),
          "priority": safe_value(template, "priority", 0)
        }
        transformed_results.append(transformed_result)
      print(f"[DEBUG] Résultats de modèles transformés: {transformed_results}")
      return transformed_results
    except Exception as e:
      print(f"[ERROR] Erreur dans search_template_relay: {e}")
      return []
