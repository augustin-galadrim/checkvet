from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64


from ._anvil_designer import TemplatesTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import base64


class Templates(TemplatesTemplate):
  def __init__(self, **properties):
    print("Initialisation du formulaire Templates...")
    # Initialiser les composants du formulaire
    self.init_components(**properties)
    print("Composants du formulaire initialisés.")

    # Attacher le gestionnaire d'événement "show"
    self.add_event_handler("show", self.form_show)

  def form_show(self, **event_args):
    """Une fois le formulaire affiché, lire les modèles depuis le serveur et remplir la liste HTML."""
    print("Déclenchement de form_show du formulaire Templates.")
    templates = anvil.server.call("read_templates")
    print(f"Le serveur a renvoyé {len(templates)} modèles.")
    # Pousser la liste des modèles dans le code JavaScript
    self.call_js("populateTemplates", templates)

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  # --------------------
  # Ouverture de l'éditeur de template
  # --------------------
  def open_template_editor(self, template_id=None, **event_args):
    """
    Ouvre le formulaire TemplateEditor avec les paramètres appropriés.
    Si template_id est fourni, cherche le template correspondant par son id.
    Sinon, crée un nouveau template.
    """
    print(f"open_template_editor appelé avec template_id={template_id}")

    if template_id:
      # Mode édition - Rechercher le template par id
      templates = anvil.server.call("read_templates")
      found_template = next((t for t in templates if t.get("id") == template_id), None)

      if not found_template:
        alert(f"Template avec ID {template_id} introuvable.")
        return

      print(f"Ouverture de l'éditeur de template pour éditer: {found_template['name']}")
      open_form("Templates.TemplateEditor", template=found_template)
    else:
      # Mode création
      print("Ouverture de l'éditeur de template pour créer un nouveau template")
      open_form("Templates.TemplateEditor")

  # --------------------------------------
  # Logique du modal pour "Créer" => Transformation PDF en template
  # --------------------------------------
  def show_pdf_modal(self, **event_args):
    """
    Appelé depuis JS lors du clic sur le bouton "+ Créer".
    Affiche le modal de téléchargement PDF.
    """
    print("Affichage du modal PDF...")
    self.call_js("openPdfModal")

  def transform_pdf_to_template(self, base64_pdf, template_name, **event_args):
    """
    1) Convertir base64_pdf en anvil.BlobMedia
    2) Traiter le PDF avec un premier prompt puis retraiter avec un second prompt
    3) Enregistrer le résultat final dans la base de données
    4) Afficher une bannière de succès
    """
    print(f"Appel de transform_pdf_to_template avec template_name={template_name}")

    # 1) Convertir la chaîne Base64 en BlobMedia PDF
    pdf_bytes = base64.b64decode(base64_pdf)
    pdf_file = anvil.BlobMedia(
      content_type="application/pdf", content=pdf_bytes, name="uploaded.pdf"
    )

    # 2) Définir les prompts
    first_prompt = anvil.server.call("get_prompt", "pdf_structure", "fr")
    second_prompt = anvil.server.call("get_prompt", "pdf_system_prompt", "fr")
    try:
      # Traiter le texte du PDF avec le premier prompt
      initial_result = anvil.server.call("process_pdf", first_prompt, pdf_file)
      print("Résultat du premier traitement (tronqué) :", initial_result[:100])

      # Retraiter avec le second prompt
      final_result = anvil.server.call(
        "reprocess_output_with_prompt", initial_result, second_prompt
      )

      # 3) Enregistrer le résultat final dans la base de données
      anvil.server.call("store_final_output_in_db", final_result, template_name)
    except Exception as e:
      print("Erreur lors de la transformation du PDF en template :", e)
      alert(f"Erreur : {str(e)}")
      return

    # 4) Afficher la bannière de succès dans le modal
    self.call_js("showSuccessBanner")

  # ----------------------
  # Nouveau : Fonctionnalité de recherche
  # ----------------------
  def search_templates_client(self, query, **event_args):
    print(f"search_templates_client() appelé avec la requête : {query}")
    if not query:
      print("Requête vide ; renvoi des modèles initiaux.")
      templates = anvil.server.call("read_templates")
      self.call_js("populateTemplates", templates)
      return
    try:
      results = anvil.server.call("search_templates", query)
      print(f"La recherche a renvoyé {len(results)} résultats.")
      self.call_js("populateTemplates", results)
    except Exception as e:
      print("Échec de la recherche :", e)

  def delete_template(self, template_id, **event_args):
    """Called from JavaScript when a user clicks the delete icon."""
    # Show a confirmation dialog to the user.
    if confirm(f"Are you sure you want to delete this template?"):
      try:
        # Call the server function to delete the template.
        success = anvil.server.call("delete_template", template_id)
        if success:
          # If deletion was successful, refresh the template list.
          self.form_show()
        else:
          alert("Could not delete the template. It may have already been removed.")
      except Exception as e:
        alert(f"An error occurred while deleting the template: {e}")
