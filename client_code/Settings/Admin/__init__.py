from ._anvil_designer import AdminTemplate
from anvil import *
import anvil.server
import anvil.users


class Admin(AdminTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.current_structure_name = None
    self.current_user_id = None
    self.current_template_id = None
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    # Load all data and pass it to Javascript for client-side searching and rendering
    try:
      all_structures = anvil.server.call_s("read_structures")
      self.call_js("initializeData", "structures", all_structures)

      all_users = anvil.server.call_s("admin_get_all_users")
      self.call_js("initializeData", "users", all_users)

      all_base_templates = anvil.server.call_s("admin_get_all_base_templates")
      self.call_js("initializeData", "templates", all_base_templates)
    except Exception as e:
      alert(f"An error occurred while loading initial data: {e}")

  # ----- Structure Management -----
  def get_structure_details(self, structure_name, **event_args):
    self.current_structure_name = structure_name
    # Data is already on the client, just find it
    structure = self.call_js("findDataById", "structures", structure_name)

    if structure:
      self.call_js("displayStructureDetails", structure)
      # Fetch and display affiliated vets
      vets = anvil.server.call_s("get_vets_in_structure", structure_name)
      self.call_js("displayAffiliatedVets", vets)
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
      # Reload all data after save
      self.on_form_show()
      self.call_js("showStructureForm", False)
      return True
    except Exception as e:
      alert(f"Error saving structure: {e}")
      return False

  def remove_vet_from_structure(self, user_id, **event_args):
    """Called from JS to remove a vet from the current structure."""
    if not user_id:
      alert("User ID is missing.")
      return
    try:
      success = anvil.server.call_s("admin_remove_vet_from_structure", user_id)
      if success:
        alert("Vet removed from structure successfully.")
        # Refresh the details view
        self.get_structure_details(self.current_structure_name)
      else:
        alert("Failed to remove vet from structure.")
    except Exception as e:
      alert(f"An error occurred while removing the vet: {e}")

  # ----- User Management -----
  def get_user_details(self, user_id, **event_args):
    user = self.call_js("findDataById", "users", user_id)
    if user:
      self.current_user_id = user_id
      all_structures = self.call_js("getAllData", "structures")
      user_templates = anvil.server.call_s("admin_get_templates_for_user", user_id)
      self.call_js("displayUserDetails", user, all_structures, user_templates)
    else:
      alert(f"User with ID '{user_id}' not found.")

  def new_user(self, **event_args):
    self.current_user_id = None
    all_structures = self.call_js("getAllData", "structures")
    self.call_js("clearUserForm")
    self.call_js("showUserForm", True, all_structures)

  def save_user(self, user_data, **event_args):
    try:
      email = user_data.get("email")
      name = user_data.get("name")
      if not email or not name:
        alert("Email and name are required.")
        return False

        # Handle new user creation if no ID is set
      if not self.current_user_id:
        self.current_user_id = anvil.server.call_s(
          "admin_create_user", email=email, name=name
        )
        if not self.current_user_id:
          alert("Failed to create user. The email may already be in use.")
          return False

        # Update the user with the rest of the data (for both new and existing users)
      update_data = {k: v for k, v in user_data.items() if k != "email"}
      anvil.server.call_s(
        "admin_update_user", user_id=self.current_user_id, **update_data
      )

      alert("User saved successfully!")
      self.on_form_show()
      self.call_js("showUserForm", False)
      return True

    except Exception as e:
      alert(f"Error saving user: {e}")
      # Reset the ID in case of a failure during the creation step
      self.current_user_id = None
      return False

  # ----- Template Management -----
  def get_template_details(self, template_id, **event_args):
    template = self.call_js("findDataById", "templates", template_id)
    if template:
      self.current_template_id = template_id
      all_users = self.call_js("getAllData", "users")
      self.call_js("displayTemplateDetails", template, all_users, "base")
    else:
      alert(f"Base Template '{template_id}' not found.")

  def edit_user_template(self, template_id, **event_args):
    """Gets a custom user template and displays it in the editor within the User Tab."""
    try:
      template_data = anvil.server.call_s("admin_get_custom_template", template_id)
      if template_data:
        self.current_template_id = template_id
        # New JS function to populate the editor in the user tab
        self.call_js("displayUserTemplateEditor", template_data)
      else:
        alert("Could not load the selected template.")
    except Exception as e:
      alert(f"Error loading template: {e}")

  def new_template(self, **event_args):
    self.current_template_id = None
    self.call_js("clearTemplateForm")
    # The last argument 'False' tells JS to hide the assignment section for new templates
    self.call_js("showTemplateForm", True, [], False)

  def save_base_template(self, template_data, **event_args):
    try:
      if not template_data.get("name"):
        alert("Template name is required.")
        return False
      template_data["template_id"] = (
        self.current_template_id
        if self.call_js("getCurrentEditingMode") == "base"
        else None
      )
      anvil.server.call_s("admin_write_base_template", **template_data)
      alert("Base template saved successfully!")
      self.on_form_show()
      self.call_js("showTemplateForm", False)
      return True
    except Exception as e:
      alert(f"Error saving base template: {e}")
      return False

  def save_custom_template(self, template_data, **event_args):
    """Saves changes to a custom (user-owned) template."""
    try:
      if not template_data.get("name") or not self.current_template_id:
        alert("Template name and ID are required.")
        return False

      anvil.server.call_s(
        "admin_write_template",
        template_id=self.current_template_id,
        name=template_data.get("name"),
        html=template_data.get("html"),
        language=template_data.get("language"),
      )
      alert("User template saved successfully!")
      self.call_js("showTemplateForm", False)
      # Hide user template editor and refresh the user details to see the updated template list
      self.call_js("hideUserTemplateEditor")
      self.get_user_details(self.current_user_id)
      return True
    except Exception as e:
      alert(f"Error saving user template: {e}")
      return False

  def assign_template_to_users(self, template_id, user_ids, **event_args):
    try:
      if not template_id or not user_ids:
        alert("Template and at least one user must be selected for assignment.")
        return False
      success = anvil.server.call_s(
        "admin_assign_base_template_to_users", template_id, user_ids
      )
      if success:
        alert(f"Template successfully assigned to {len(user_ids)} user(s).")
        return True
      else:
        alert("An error occurred during template assignment.")
        return False
    except Exception as e:
      alert(f"Error assigning template: {e}")
      return False

  def back_to_home(self, **event_args):
    open_form("Settings.Settings")
