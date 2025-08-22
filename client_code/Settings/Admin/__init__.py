from ._anvil_designer import AdminTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Admin(AdminTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.current_structure_name = None
    self.current_user_id = None
    self.current_template_id = None
    self.all_structures = []
    self.all_users = []
    self.all_templates = []
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    self.load_structures()
    self.load_users()
    self.load_templates()

  # ----- Structure Management -----
  def load_structures(self):
    try:
      self.all_structures = anvil.server.call_s("read_structures")
      self.call_js("populateStructures", self.all_structures)
    except Exception as e:
      alert(f"An error occurred while loading structures: {e}")

  def get_structure_details(self, structure_name, **event_args):
    structure = next(
      (s for s in self.all_structures if s["structure"] == structure_name), None
    )
    if structure:
      self.current_structure_name = structure_name
      self.call_js("displayStructureDetails", structure)
      # Also load and display affiliated vets
      vets = anvil.server.call_s("get_vets_in_structure", structure_name)
      # This part needs a new JS function `displayAffiliatedVets`
      # For now, we will just log it, assuming it will be a new feature.
      print(f"Vets for {structure_name}: {vets}")
    else:
      alert(f"Structure '{structure_name}' not found.")

  def new_structure(self, **event_args):
    self.current_structure_name = None
    self.call_js("clearStructureForm")
    self.call_js("showStructureForm", True)

  def save_structure(self, structure_data, **event_args):
    try:
      name = structure_data.get("name")
      if not name:
        alert("Structure name is required.")
        return False
      anvil.server.call_s("admin_write_structure", **structure_data)
      alert("Structure saved successfully!")
      self.load_structures()
      self.call_js("showStructureForm", False)
      return True
    except Exception as e:
      alert(f"Error saving structure: {e}")
      return False

  # ----- User Management -----
  def load_users(self):
    try:
      self.all_users = anvil.server.call_s("admin_get_all_users")
      self.call_js("populateUsers", self.all_users)
    except Exception as e:
      alert(f"An error occurred while loading users: {e}")

  def get_user_details(self, user_id, **event_args):
    user = next((u for u in self.all_users if u["id"] == user_id), None)
    if user:
      self.current_user_id = user_id
      structure_names = ["Indépendant"] + [s["structure"] for s in self.all_structures]
      self.call_js("displayUserDetails", user, structure_names)
    else:
      alert(f"User with ID '{user_id}' not found.")

  def new_user(self, **event_args):
    self.current_user_id = None
    structure_names = ["Indépendant"] + [s["structure"] for s in self.all_structures]
    self.call_js("clearUserForm")
    self.call_js("showUserForm", True, structure_names)

  def save_user(self, user_data, **event_args):
    try:
      email = user_data.get("email")
      name = user_data.get("name")
      if not email or not name:
        alert("Email and name are required.")
        return False

      if not self.current_user_id:  # It's a new user
        self.current_user_id = anvil.server.call_s(
          "admin_create_user", email=email, name=name
        )
        if not self.current_user_id:
          alert("Failed to create the user. They may already exist.")
          self.current_user_id = None  # Reset
          return False

      # Now update the user with all data
      anvil.server.call_s(
        "admin_update_user", user_id=self.current_user_id, **user_data
      )
      alert("User saved successfully!")
      self.load_users()
      self.call_js("showUserForm", False)
      return True
    except Exception as e:
      alert(f"Error saving user: {e}")
      self.current_user_id = None  # Reset on failure
      return False

  # ----- Template Management -----
  def load_templates(self):
    try:
      self.all_templates = anvil.server.call_s("admin_get_all_templates")
      self.call_js("populateTemplates", self.all_templates)
    except Exception as e:
      alert(f"An error occurred while loading templates: {e}")

  def get_template_details(self, template_id, **event_args):
    template = next((t for t in self.all_templates if t["id"] == template_id), None)
    if template:
      self.current_template_id = template_id
      # For assignment, we need all users
      self.call_js("displayTemplateDetails", template, self.all_users)
    else:
      alert(f"Template '{template_id}' not found.")

  def new_template(self, **event_args):
    self.current_template_id = None
    self.call_js("clearTemplateForm")
    # We need all users to be available for assignment
    self.call_js("showTemplateForm", True, self.all_users)

  def save_template(self, template_data, selected_user_ids, **event_args):
    try:
      if not template_data.get("name"):
        alert("Template name is required.")
        return False

        # Add the current template ID for updates
      template_data["template_id"] = self.current_template_id

      # If it's a new template, we must assign an owner.
      # This UI doesn't support selecting an owner, so we will assign it to the admin.
      if not self.current_template_id:
        admin_user = anvil.users.get_user()
        admin_user_row = app_tables.users.get(email=admin_user["email"])
        template_data["owner_id"] = admin_user_row.get_id()

        # Save the template details
      anvil.server.call_s("admin_write_template", **template_data)

      # Handle assignment if there are selected users
      if selected_user_ids:
        # We need the ID of the template we just saved
        # For simplicity, we reload templates to get the latest state
        self.load_templates()
        saved_template = next(
          (t for t in self.all_templates if t["name"] == template_data["name"]), None
        )
        if saved_template:
          anvil.server.call_s(
            "assign_template_to_users", saved_template["id"], selected_user_ids
          )

      alert("Template saved successfully!")
      self.load_templates()
      self.call_js("showTemplateForm", False)
      return True
    except Exception as e:
      alert(f"Error saving template: {e}")
      return False

  def back_to_home(self, **event_args):
    open_form("Settings.Settings")
