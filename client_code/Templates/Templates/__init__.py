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
