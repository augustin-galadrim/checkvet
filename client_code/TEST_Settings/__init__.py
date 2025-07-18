from ._anvil_designer import TEST_SettingsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class TEST_Settings(TEST_SettingsTemplate):
  def __init__(self, **properties):
    print("Debug: Initialisation du formulaire Settings...")
    # Initialiser les composants du formulaire
    self.init_components(**properties)
    print("Debug: Composants du formulaire initialisés.")

    # Attacher un gestionnaire d'événement lors de l'affichage du formulaire
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    """
    S'exécute après que le formulaire est visible. Nous allons récupérer les données utilisateur,
    remplir les champs via self.call_js(...), et charger les modaux.
    """
    print(
      "Debug: Le formulaire Settings est maintenant visible. Chargement des données du vétérinaire..."
    )
    self.load_vet_data()
    print("Debug: Données du vétérinaire chargées dans le formulaire.")
    print("Debug: Chargement des données du modal de structure...")
    self.load_structure_modal()
    print("Debug: Données du modal de structure chargées.")
    print("Debug: Chargement des données du modal de langue préférée...")
    self.load_favorite_language_modal()
    print("Debug: Données du modal de langue préférée chargées.")

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  def load_vet_data(self):
    """
    Récupère les données utilisateur depuis le serveur et remplit les champs
    dans le formulaire HTML via self.call_js(...).
    """
    try:
      current_user = anvil.users.get_user()
      if not current_user:
        print("Debug: Aucun utilisateur connecté.")
        alert("Aucun utilisateur n'est actuellement connecté.")
        return

      print(f"Debug: Utilisateur courant récupéré : {current_user}")
      user_data = anvil.server.call(
        "read_user"
      )  # ex. { name, email, phone, structure, signature_image, ... }
      print(f"Debug: Données utilisateur depuis le serveur : {user_data}")

      if user_data:
        # Pour les champs de texte :
        self.call_js("setValueById", "name", user_data.get("name", ""))
        self.call_js("setValueById", "email", user_data.get("email", ""))
        self.call_js("setValueById", "phone", user_data.get("phone", ""))
        # Définir la structure : mettre à jour l'input caché et le bouton d'affichage
        structure = user_data.get("structure")
        if not structure:
          structure = "Indépendant"
        self.call_js("setValueById", "structure", structure)
        self.call_js("setButtonTextById", "structure-button", structure)

        # Définir la langue préférée : mettre à jour l'input caché et le bouton d'affichage.
        # La valeur dans la base de données est attendue comme FR, EN, ES ou DE.
        favorite_language = user_data.get("favorite_language")
        if not favorite_language:
          favorite_language = "EN"
        mapping = {"FR": "Français", "EN": "Anglais", "ES": "Español", "DE": "Deutsch"}
        display_text = mapping.get(favorite_language, "Anglais")
        self.call_js("setValueById", "favorite-language", favorite_language)
        self.call_js("setButtonTextById", "favorite-language-button", display_text)

        # Pour la case à cocher
        self.call_js("setCheckedById", "supervisor", user_data.get("supervisor", False))

        # Libellés de fichiers pour les images existantes
        if user_data.get("signature_image"):
          self.call_js(
            "setFileNameById", "signature", user_data["signature_image"].name
          )
        if user_data.get("report_header_image"):
          self.call_js(
            "setFileNameById", "report-header", user_data["report_header_image"].name
          )
        if user_data.get("report_footer_image"):
          self.call_js(
            "setFileNameById", "report-footer", user_data["report_footer_image"].name
          )
      else:
        alert(
          "Impossible de récupérer les données utilisateur. Veuillez contacter le support."
        )
    except Exception as e:
      print(f"Debug: Erreur dans load_vet_data : {str(e)}")
      alert(f"Une erreur est survenue lors du chargement des données : {str(e)}")

  def load_structure_modal(self):
    """
    Utilise la fonction relais pour récupérer les structures depuis le serveur et
    remplit le modal avec les noms des structures.
    """
    try:
      structures = relay_read_structures()
      print(f"Debug: Structures récupérées : {structures}")
      # Extraire le nom de la structure pour chaque structure
      options = [s["structure"] for s in structures]
      # S'assurer que "Indépendant" est toujours disponible
      if "Indépendant" not in options:
        options.append("Indépendant")
      # Récupérer la structure actuelle de l'utilisateur, ou utiliser "Indépendant" par défaut
      user_data = anvil.server.call("read_user")
      current_structure = (
        user_data.get("structure")
        if user_data and user_data.get("structure")
        else "Indépendant"
      )
      # Mettre à jour l'input caché et le bouton de structure
      self.call_js("setValueById", "structure", current_structure)
      self.call_js("setButtonTextById", "structure-button", current_structure)
      # Remplir le modal avec les options et mettre en évidence la valeur actuelle
      self.call_js("populateStructureModal", options, current_structure)
    except Exception as e:
      print(f"Debug: Erreur lors du chargement du modal de structure : {str(e)}")
      alert(f"Une erreur est survenue lors du chargement des structures : {str(e)}")

  def load_favorite_language_modal(self):
    """
    Remplit le modal de langue préférée avec des options prédéfinies.
    L'interface affichera les noms des langues dans leur propre langue,
    tandis que la valeur sous-jacente sera FR, EN, ES ou DE.
    """
    try:
      options = [
        {"display": "Français", "value": "FR"},
        {"display": "Anglais", "value": "EN"},
        {"display": "Español", "value": "ES"},
        {"display": "Deutsch", "value": "DE"},
      ]
      user_data = anvil.server.call("read_user")
      current_fav = (
        user_data.get("favorite_language")
        if user_data and user_data.get("favorite_language")
        else "EN"
      )
      mapping = {"FR": "Français", "EN": "Anglais", "ES": "Español", "DE": "Deutsch"}
      display_text = mapping.get(current_fav, "Anglais")
      self.call_js("setValueById", "favorite-language", current_fav)
      self.call_js("setButtonTextById", "favorite-language-button", display_text)
      self.call_js("populateFavoriteLanguageModal", options, current_fav)
    except Exception as e:
      print(f"Debug: Erreur lors du chargement du modal de langue préférée : {str(e)}")
      alert(
        f"Une erreur est survenue lors du chargement des langues préférées : {str(e)}"
      )

  def submit_click(self, **event_args):
    """
    Appelé lorsque l'utilisateur clique sur "Mettre à jour les paramètres" (depuis le JS via anvil.call).
    """
    try:
      print(
        "Debug: Bouton de soumission cliqué. Récupération des données du formulaire..."
      )

      form_data = {
        "name": self.call_js("getValueById", "name"),
        "phone": self.call_js("getValueById", "phone"),
        "structure": self.call_js("getValueById", "structure"),
        "supervisor": self.call_js("getCheckedById", "supervisor"),
        "favorite_language": self.call_js("getValueById", "favorite-language"),
      }

      # Récupérer les données de fichier pour chaque champ si un fichier a été sélectionné
      signature_file = self.get_file_data("signature")
      if signature_file:
        form_data["signature_image"] = signature_file

      report_header_file = self.get_file_data("report-header")
      if report_header_file:
        form_data["report_header_image"] = report_header_file

      report_footer_file = self.get_file_data("report-footer")
      if report_footer_file:
        form_data["report_footer_image"] = report_footer_file

      print(f"Debug: Données du formulaire récupérées : {form_data}")

      # Appeler le serveur pour mettre à jour l'enregistrement de l'utilisateur
      success = anvil.server.call("write_user", **form_data)
      print(f"Debug: Réponse du serveur pour la mise à jour : {success}")

      if success:
        self.call_js(
          "displayBanner",
          "Les paramètres du vétérinaire ont été mis à jour avec succès !",
          "success",
        )
        open_form("StartupForm")
      else:
        alert(
          "Échec de la mise à jour des paramètres du vétérinaire. Veuillez réessayer."
        )
    except Exception as e:
      print(f"Debug: Erreur lors de la soumission : {str(e)}")
      alert(f"Une erreur est survenue lors de la soumission : {str(e)}")

  def cancel_click(self, **event_args):
    """
    Appelé lorsque l'utilisateur clique sur "Annuler" (depuis le JS via anvil.call).
    """
    open_form("TEST_AudioManager")

  def logout_click(self, **event_args):
    """
    Appelé lorsque l'utilisateur clique sur "Déconnexion" (depuis le JS via anvil.call).
    """
    anvil.users.logout()
    open_form("StartupForm")

  def get_file_data(self, input_id):
    """
    Fonction utilitaire pour récupérer les données d'un fichier depuis JavaScript. Si un fichier est sélectionné,
    nous créons un BlobMedia à partir des données retournées.
    """
    file_data_promise = self.call_js("getFileData", input_id)
    if file_data_promise:
      try:
        file_data = file_data_promise
        return anvil.BlobMedia(
          content_type=file_data["content_type"],
          content=file_data["content"],
          name=file_data["name"],
        )
      except Exception as e:
        print(
          f"Debug: Erreur lors de la lecture des données du fichier pour {input_id} : {e}"
        )
    return None

  def openProduction(self, **event_args):
    """Appelé depuis l'onglet supérieur 'Production'"""
    open_form("TEST_AudioManagerUltimate35")

  def openTemplates(self, **event_args):
    """Appelé depuis l'onglet supérieur 'Modèles/IA'"""
    open_form("TEST_Templates")

  def openArchives(self, **event_args):
    """Appelé depuis l'onglet supérieur 'Archives'"""
    current_user = anvil.users.get_user()
    if current_user["supervisor"]:
      open_form("TEST_ArchivesSecretariat")
    else:
      open_form("TEST_Archives")

  def openMicrophoneTest(self, **event_args):
    """Appelé depuis le bouton 'Tester mon micro' pour ouvrir le formulaire MicrophoneTest."""
    open_form("MicrophoneTest")

  def check_structure_authorization(self, structure, **event_args):
    """
    Appelé depuis JavaScript pour vérifier si l'utilisateur courant est autorisé pour la structure donnée.
    Utilise une fonction relais pour appeler la fonction serveur.
    """
    return relay_check_vet_authorization(structure)


# Fonction relais dans le front py pour appeler la fonction serveur "read_structures"
def relay_read_structures():
  return anvil.server.call("read_structures")


# Fonction relais dans le front py pour appeler la fonction serveur "check_vet_authorization"
def relay_check_vet_authorization(structure):
  return anvil.server.call("check_vet_authorization", structure)
