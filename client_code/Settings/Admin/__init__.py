from ._anvil_designer import AdminTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Admin(AdminTemplate):
  def __init__(self, **properties):
    print("Debug: Initialisation du formulaire Admin...")
    self.init_components(**properties)
    print("Debug: Composants du formulaire initialisés.")

    # Current state
    self.current_structure_id = None
    self.current_user_id = None
    self.current_template_name = None  # Added for template management
    self.current_template_id = None

    # Add show event handler
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    """
    S'exécute après que le formulaire est visible.
    """
    print("Debug: Le formulaire Admin est maintenant visible.")
    self.load_structures()
    self.load_users()
    self.load_templates()  # Added to load templates

  def refresh_session_relay(self, **event_args):
    """Relay method for refreshing the session when called from JS"""
    try:
      return anvil.server.call_s("check_and_refresh_session")
    except anvil.server.SessionExpiredError:
      anvil.server.reset_session()
      return anvil.server.call_s("check_and_refresh_session")
    except Exception as e:
      print(f"[DEBUG] Error in refresh_session_relay: {str(e)}")
      return False

  # ----- Structure Management -----

  def load_structures(self):
    """
    Charge la liste des structures depuis le serveur.
    """
    try:
      structures = relay_read_structures()
      print(f"Debug: Structures récupérées: {structures}")
      self.call_js("populateStructures", structures)
    except Exception as e:
      print(f"Debug: Erreur lors du chargement des structures: {str(e)}")
      alert(f"Une erreur est survenue lors du chargement des structures: {str(e)}")

  def get_structure_details(self, structure_name, **event_args):
    """
    Récupère les détails d'une structure et les affiche dans le formulaire.
    """
    try:
      structures = relay_read_structures()
      structure = next(
        (s for s in structures if s["structure"] == structure_name), None
      )

      if structure:
        self.current_structure_id = structure_name
        self.call_js("displayStructureDetails", structure)
      else:
        alert(f"Structure '{structure_name}' non trouvée.")
    except Exception as e:
      print(
        f"Debug: Erreur lors de la récupération des détails de la structure: {str(e)}"
      )
      alert(f"Une erreur est survenue: {str(e)}")

  def new_structure(self, **event_args):
    """
    Prépare le formulaire pour créer une nouvelle structure.
    """
    self.current_structure_id = None
    self.call_js("clearStructureForm")
    self.call_js("showStructureForm", True)

  def save_structure(self, structure_data, **event_args):
    """
    Sauvegarde les données d'une structure (nouvelle ou modifiée).
    """
    try:
      print(f"Debug: Sauvegarde de la structure: {structure_data}")

      name = structure_data.get("name")
      phone = structure_data.get("phone")
      email = structure_data.get("email")
      address = structure_data.get("address")

      if not name:
        alert("Le nom de la structure est obligatoire.")
        return False

      success = relay_write_structure(
        name=name, phone=phone, email=email, address=address
      )

      if success:
        alert("Structure sauvegardée avec succès!")
        self.load_structures()
        return True
      else:
        alert("Erreur lors de la sauvegarde de la structure.")
        return False
    except Exception as e:
      print(f"Debug: Erreur lors de la sauvegarde de la structure: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")
      return False

  # ----- User Management -----

  def load_users(self):
    """
    Charge la liste des utilisateurs depuis le serveur.
    """
    try:
      users = relay_search_users(
        ""
      )  # Recherche sans filtres pour obtenir tous les utilisateurs
      print(f"Debug: Utilisateurs récupérés: {len(users) if users else 0}")
      self.call_js("populateUsers", users)
    except Exception as e:
      print(f"Debug: Erreur lors du chargement des utilisateurs: {str(e)}")
      alert(f"Une erreur est survenue lors du chargement des utilisateurs: {str(e)}")

  def get_user_details(self, user_id, **event_args):
    """
    Récupère les détails d'un utilisateur et les affiche dans le formulaire.
    """
    try:
      users = relay_search_users("")
      user = next((u for u in users if u["id"] == user_id), None)

      if user:
        self.current_user_id = user_id

        # Get the list of structures for the dropdown
        structures = relay_read_structures()
        structure_names = ["Indépendant"] + [s["structure"] for s in structures]

        # Create a modified user object with the correct structure name
        modified_user = dict(user)

        # Handle structure - LiveObjectProxy uses dict-like access with []
        if user.get("structure"):
          try:
            # Try to get the structure name using dict-like access
            structure_obj = user.get("structure")

            # Try different possible attribute names one by one
            try:
              structure_name = structure_obj["name"]
              modified_user["structure"] = structure_name
              print(
                f"DEBUG: Set structure name to {structure_name} from 'name' attribute"
              )
            except (KeyError, TypeError):
              try:
                structure_name = structure_obj["structure"]
                modified_user["structure"] = structure_name
                print(
                  f"DEBUG: Set structure name to {structure_name} from 'structure' attribute"
                )
              except (KeyError, TypeError):
                print("DEBUG: Could not find structure name in structure object")
                modified_user["structure"] = "Indépendant"
          except Exception as e:
            print(f"DEBUG: General error extracting structure name: {str(e)}")
            modified_user["structure"] = "Indépendant"
        else:
          modified_user["structure"] = "Indépendant"
          print(f"DEBUG: No structure found, defaulting to Indépendant")

          # Send the modified user data to JavaScript
        self.call_js("displayUserDetails", modified_user, structure_names)
      else:
        alert(f"Utilisateur avec ID '{user_id}' non trouvé.")
    except Exception as e:
      print(
        f"Debug: Erreur lors de la récupération des détails de l'utilisateur: {str(e)}"
      )
      alert(f"Une erreur est survenue: {str(e)}")

  def new_user(self, **event_args):
    """
    Prépare le formulaire pour créer un nouvel utilisateur.
    """
    try:
      self.current_user_id = None

      # Get the list of structures for the dropdown
      structures = relay_read_structures()
      structure_names = ["Indépendant"] + [s["structure"] for s in structures]

      self.call_js("clearUserForm")
      self.call_js("showUserForm", True, structure_names)
    except Exception as e:
      print(
        f"Debug: Erreur lors de la préparation du formulaire d'utilisateur: {str(e)}"
      )
      alert(f"Une erreur est survenue: {str(e)}")

  def save_user(self, user_data, **event_args):
    """
    Sauvegarde les données d'un utilisateur (nouveau ou modifié).
    """
    try:
      print(f"Debug: Sauvegarde de l'utilisateur: {user_data}")

      # Required fields
      email = user_data.get("email")
      name = user_data.get("name")

      if not email or not name:
        alert("L'email et le nom sont obligatoires.")
        return False

        # If it's a new user, we need to create it first
      if not self.current_user_id:
        # Create a new user using a server function specifically for creating users
        try:
          # Call a different server function for creating users
          user_created = relay_create_user(email=email, name=name)
          if not user_created:
            alert("Erreur lors de la création de l'utilisateur.")
            return False
            # After creating, we need to get the user to update it
          self.current_user_id = (
            user_created  # Assuming relay_create_user returns the new user ID
          )
        except Exception as e:
          print(f"Debug: Erreur lors de la création de l'utilisateur: {str(e)}")
          alert(f"Une erreur est survenue lors de la création: {str(e)}")
          return False

          # Now update the user with all provided data
          # You need a different server function for updating users by admin
      success = relay_update_user(
        user_id=self.current_user_id,  # Use the user ID instead of email
        name=name,
        phone=user_data.get("phone"),
        structure=user_data.get("structure"),
        supervisor=user_data.get("supervisor", False),
        favorite_language=user_data.get("favorite_language", "en"),
      )

      if success:
        alert("Utilisateur sauvegardé avec succès!")
        self.load_users()
        return True
      else:
        alert("Erreur lors de la sauvegarde de l'utilisateur.")
        return False
    except Exception as e:
      print(f"Debug: Erreur lors de la sauvegarde de l'utilisateur: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")
      return False

  def add_vet_to_structure(self, user_email, **event_args):
    """
    Ajoute un vétérinaire à la structure actuelle comme utilisateur autorisé.
    """
    try:
      if not self.current_structure_id:
        alert("Aucune structure sélectionnée.")
        return False

      success = ...
      if success:
        alert(f"Utilisateur {user_email} ajouté avec succès à la structure.")
        return True
      else:
        alert("Erreur lors de l'ajout de l'utilisateur à la structure.")
        return False
    except Exception as e:
      print(f"Debug: Erreur lors de l'ajout du vétérinaire à la structure: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")
      return False

  # ----- Template Management -----

  def load_templates(self):
    """
    Charge la liste des templates depuis le serveur.
    """
    try:
      templates = relay_read_templates()
      print(f"Debug: Templates récupérés: {len(templates) if templates else 0}")
      self.call_js("populateTemplates", templates)
    except Exception as e:
      print(f"Debug: Erreur lors du chargement des templates: {str(e)}")
      alert(f"Une erreur est survenue lors du chargement des templates: {str(e)}")

  def get_template_details(self, template_id, **event_args):
    """
    Récupère les détails d'un template et les affiche dans le formulaire.
    """
    try:
      templates = relay_read_templates()
      template = next((t for t in templates if t["id"] == template_id), None)

      if template:
        self.current_template_id = template_id

        # Get users for assignment
        users = relay_search_users("")

        self.call_js("displayTemplateDetails", template, users)
      else:
        alert(f"Template '{template_id}' non trouvé.")
    except Exception as e:
      print(f"Debug: Erreur lors de la récupération des détails du template: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")

  def new_template(self, **event_args):
    """
    Prépare le formulaire pour créer un nouveau template.
    """
    self.current_template_id = None

    # Get users for assignment
    users = relay_search_users("")

    self.call_js("clearTemplateForm")
    self.call_js("showTemplateForm", True, users)

  def save_template(self, template_data, **event_args):
    """
    Sauvegarde les données d'un template (nouveau ou modifié).
    """
    try:
      print(f"Debug: Sauvegarde du template: {template_data}")

      name = template_data.get("name")
      html = template_data.get("html")
      display = template_data.get("display")

      if not name:
        alert("Le nom du template est obligatoire.")
        return False

      success = relay_write_template(
        template_id=self.current_template_id,
        name=name,
        html=html,
        display=display,
      )

      if success:
        alert("Template sauvegardé avec succès!")
        self.load_templates()
        return True
      else:
        alert("Erreur lors de la sauvegarde du template.")
        return False
    except Exception as e:
      print(f"Debug: Erreur lors de la sauvegarde du template: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")
      return False

  def assign_template_to_users(self, template_id, user_ids, **event_args):
    """
    Assigne un template à plusieurs utilisateurs.
    """
    try:
      if not template_id:
        alert("Aucun template sélectionné.")
        return False

      success = relay_assign_template(template_id, user_ids)
      if success:
        alert("Template assigné avec succès aux utilisateurs sélectionnés.")
        return True
      else:
        alert("Erreur lors de l'assignation du template.")
        return False
    except Exception as e:
      print(f"Debug: Erreur lors de l'assignation du template: {str(e)}")
      alert(f"Une erreur est survenue: {str(e)}")
      return False

  # ----- Navigation -----

  def back_to_home(self, **event_args):
    """
    Retourne à la page d'accueil/dashboard.
    """
    open_form("StartupForm")


# ----- Relay Methods for Server Calls -----


def relay_read_structures():
  """Relay method for read_structures server function"""
  try:
    return anvil.server.call_s("read_structures")
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("read_structures")


def relay_write_structure(**kwargs):
  """Relay method for write_structure server function"""
  try:
    return anvil.server.call_s("write_structure", **kwargs)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("write_structure", **kwargs)


def relay_search_users(search_term):
  """Relay method for search_users server function"""
  try:
    return anvil.server.call_s("search_users", search_term)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("search_users", search_term)


def relay_write_user(**kwargs):
  """Relay method for write_user server function"""
  try:
    # Handle structure separately
    if "email" in kwargs:
      # We need to get user by email first
      email = kwargs.pop("email")
      users = anvil.server.call_s("search_users", "")
      user = next((u for u in users if u["email"] == email), None)

      if not user:
        print(f"Debug: User with email {email} not found")
        return False

        # Handle structure field
      if "structure" in kwargs:
        structure_value = kwargs.pop("structure")
        if structure_value == "Indépendant":
          kwargs["structure"] = None

          # Now use the existing write_user function with the correct parameters
      return anvil.server.call_s("write_user", **kwargs)
    else:
      return anvil.server.call_s("write_user", **kwargs)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("write_user", **kwargs)
  except Exception as e:
    print(f"DEBUG: Error in relay_write_user: {str(e)}")
    return False


def relay_create_user(**kwargs):
  """Relay method for create_user server function"""
  try:
    return anvil.server.call_s("create_user", **kwargs)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("create_user", **kwargs)


def relay_update_user(**kwargs):
  """Relay method for update_user server function"""
  try:
    return anvil.server.call_s("update_user", **kwargs)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("update_user", **kwargs)


def relay_read_templates():
  """Relay method for read_templates server function"""
  try:
    return anvil.server.call_s("read_templates")
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("read_templates")


def relay_write_template(**kwargs):
  """Relay method for write_template server function"""
  try:
    return anvil.server.call_s("write_template", **kwargs)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("write_template", **kwargs)


def relay_assign_template(template_id, user_ids):
  """Relay method for assign_template server function"""
  try:
    return anvil.server.call_s("assign_template_to_users", template_id, user_ids)
  except anvil.server.SessionExpiredError:
    anvil.server.reset_session()
    return anvil.server.call_s("assign_template_to_users", template_id, user_ids)
