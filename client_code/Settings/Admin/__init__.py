from ._anvil_designer import AdminTemplate
from anvil import *
import anvil.server
import anvil.users


class Admin(AdminTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.current_structure_id = None
    self.current_structure_name = None
    self.current_user_id = None
    self.current_template_id = None
    self.add_event_handler("show", self.on_form_show)

  def on_form_show(self, **event_args):
    try:
      all_structures = anvil.server.call_s("read_structures")
      self.call_js("admin_initializeData", "structures", all_structures)

      all_users = anvil.server.call_s("admin_get_all_users")
      self.call_js("admin_initializeData", "users", all_users)

      all_base_templates = anvil.server.call_s("admin_get_all_base_templates")
      self.call_js("admin_initializeData", "templates", all_base_templates)
    except Exception as e:
      self.call_js("displayBanner", f"An error occurred while loading initial data: {e}", "error")

  # ----- Structure Management -----
  def get_structure_details(self, structure_id, **event_args):
    self.current_structure_id = structure_id
    structure = self.call_js("admin_findDataById", "structures", structure_id)

    if structure:
      self.current_structure_name = structure.get('structure')
      self.call_js("admin_displayStructureDetails", structure)
      # Fetch and display affiliated vets
      vets = anvil.server.call_s("get_vets_in_structure", self.current_structure_name)
      self.call_js("admin_displayAffiliatedVets", vets)
    else:
      self.call_js("displayBanner", f"Structure with ID '{structure_id}' not found.", "error")

  def new_structure(self, **event_args):
    self.current_structure_id = None
    self.current_structure_name = None
    self.call_js("admin_clearStructureForm")
    self.call_js("admin_showStructureForm", True)

  def save_structure(self, structure_data, **event_args):
    try:
      name = structure_data.get("name")
      if not name:
        self.call_js("displayBanner", "Structure name is required.", "error")
        return False
      structure_data['id'] = self.current_structure_id
      anvil.server.call_s("admin_write_structure", structure_data)
      self.call_js("displayBanner", "Structure saved successfully!", "success")
      # Reload all data after save
      self.on_form_show()
      self.call_js("admin_showStructureForm", False)
      return True
    except Exception as e:
      self.call_js("displayBanner", f"Error saving structure: {e}", "error")
      return False

  def add_vet_to_structure(self, vet_email, **event_args):
    """Called from JS to add a vet to the current structure."""
    if not self.current_structure_id:
      self.call_js("displayBanner", "No structure selected. Please select a structure to modify first.", "error")
      return
    if not vet_email:
      self.call_js("displayBanner", "Please enter the veterinarian's email address.", "error")
      return

    try:
      success = anvil.server.call_s(
        "admin_add_vet_to_structure", self.current_structure_name, vet_email
      )
      if success:
        self.call_js("displayBanner", f"Successfully added {vet_email} to {self.current_structure_name}.", "success")
        # Refresh the details view to show the new vet
        self.on_form_show()
        self.get_structure_details(self.current_structure_id)
      else:
        # The server function returns False on specific failures (e.g., user not found)
        self.call_js("displayBanner", f"Failed to add vet. Please check the email address and that the user exists.", "error")
    except Exception as e:
      self.call_js("displayBanner", f"An error occurred while adding the vet: {e}", "error")

  def remove_vet_from_structure(self, user_id, **event_args):
    """Called from JS to remove a vet from the current structure."""
    if not user_id:
      self.call_js("displayBanner", "User ID is missing.", "error")
      return
    try:
      success = anvil.server.call_s("admin_remove_vet_from_structure", user_id)
      if success:
        self.call_js("displayBanner", "Vet removed from structure successfully.", "success")
        # Refresh the details view
        self.on_form_show()
        self.get_structure_details(self.current_structure_id)
      else:
        self.call_js("displayBanner", "Failed to remove vet from structure.", "error")
    except Exception as e:
      self.call_js("displayBanner", f"An error occurred while removing the vet: {e}", "error")

  # ----- User Management -----
  def get_user_details(self, user_id, **event_args):
    user = self.call_js("admin_findDataById", "users", user_id)
    if user:
      self.current_user_id = user_id
      all_structures = self.call_js("admin_getAllData", "structures")
      user_templates = anvil.server.call_s("admin_get_templates_for_user", user_id)
      self.call_js("admin_displayUserDetails", user, all_structures, user_templates)
    else:
      self.call_js("displayBanner", f"User with ID '{user_id}' not found.", "error")

  def new_user(self, **event_args):
    self.current_user_id = None
    all_structures = self.call_js("admin_getAllData", "structures")
    self.call_js("admin_clearUserForm")
    self.call_js("admin_showUserForm", True, all_structures)

  def save_user(self, user_data, **event_args):
    try:
      email = user_data.get("email")
      name = user_data.get("name")
      if not email or not name:
        self.call_js("displayBanner", "Email and name are required.", "error")
        return False

      if not self.current_user_id:
        # This is a NEW user, call the enhanced create function
        self.current_user_id = anvil.server.call_s(
          "admin_create_user",
          email=email,
          name=name,
          phone=user_data.get("phone"),
          supervisor=user_data.get("supervisor"),
          favorite_language=user_data.get("favorite_language"),
          structure_name=user_data.get("structure")
        )
        if not self.current_user_id:
          self.call_js("displayBanner", "Failed to create user. The email may already be in use.", "error")
          return False
      else:
        # This is an EXISTING user, call the update function
        update_data = {k: v for k, v in user_data.items() if k not in ["email"]}
        anvil.server.call_s(
          "admin_update_user", user_id=self.current_user_id, **update_data
        )

      self.call_js("displayBanner", "User saved successfully!", "success")
      self.on_form_show()
      self.call_js("admin_showUserForm", False)
      return True

    except Exception as e:
      self.call_js("displayBanner", f"Error saving user: {e}", "error")
      self.current_user_id = None # Reset ID on failure
      return False

  # ----- Template Management -----
  def get_template_details(self, template_id, **event_args):
    template = self.call_js("admin_findDataById", "templates", template_id)
    if template:
      self.current_template_id = template_id
      all_users = self.call_js("admin_getAllData", "users")
      self.call_js("admin_displayTemplateDetails", template, all_users, "base")
    else:
      self.call_js("displayBanner", f"Base Template '{template_id}' not found.", "error")

  def edit_user_template(self, template_id, **event_args):
    """Gets a custom user template and displays it in the editor within the User Tab."""
    try:
      template_data = anvil.server.call_s("admin_get_custom_template", template_id)
      if template_data:
        self.current_template_id = template_id
        # New JS function to populate the editor in the user tab
        self.call_js("admin_displayUserTemplateEditor", template_data)
      else:
        self.call_js("displayBanner", "Could not load the selected template.", "error")
    except Exception as e:
      self.call_js("displayBanner", f"Error loading template: {e}", "error")

  def new_template(self, **event_args):
    self.current_template_id = None
    self.call_js("admin_clearTemplateForm")
    # The last argument 'False' tells JS to hide the assignment section for new templates
    self.call_js("admin_showTemplateForm", True, [], False)

  def save_base_template(self, template_data, **event_args):
    try:
      if not template_data.get("name"):
        self.call_js("displayBanner", "Template name is required.", "error")
        return False
      template_data["template_id"] = (
        self.current_template_id
        if self.call_js("admin_getCurrentEditingMode") == "base"
        else None
      )
      anvil.server.call_s("admin_write_base_template", **template_data)
      self.call_js("displayBanner", "Base template saved successfully!", "success")
      self.on_form_show()
      self.call_js("admin_showTemplateForm", False)
      return True
    except Exception as e:
      self.call_js("displayBanner", f"Error saving base template: {e}", "error")
      return False

  def save_custom_template(self, template_data, **event_args):
    """Saves changes to a custom (user-owned) template."""
    try:
      if not template_data.get("name") or not self.current_template_id:
        self.call_js("displayBanner", "Template name and ID are required.", "error")
        return False

      anvil.server.call_s(
        "admin_write_template",
        template_id=self.current_template_id,
        name=template_data.get("name"),
        html=template_data.get("html"),
        language=template_data.get("language"),
      )
      self.call_js("displayBanner", "User template saved successfully!", "success")
      self.call_js("admin_showTemplateForm", False)
      # Hide user template editor and refresh the user details to see the updated template list
      self.call_js("admin_hideUserTemplateEditor")
      self.get_user_details(self.current_user_id)
      return True
    except Exception as e:
      self.call_js("displayBanner", f"Error saving user template: {e}", "error")
      return False

  def assign_template_to_users(self, template_id, user_ids, **event_args):
    try:
      if not template_id or not user_ids:
        self.call_js("displayBanner", "Template and at least one user must be selected for assignment.", "error")
        return False
      success = anvil.server.call_s(
        "admin_assign_base_template_to_users", template_id, user_ids
      )
      if success:
        self.call_js("displayBanner", f"Template successfully assigned to {len(user_ids)} user(s).", "success")
        return True
      else:
        self.call_js("displayBanner", "An error occurred during template assignment.", "error")
        return False
    except Exception as e:
      self.call_js("displayBanner", f"Error assigning template: {e}", "error")
      return False

  def back_to_home(self, **event_args):
    open_form("Settings.Settings")