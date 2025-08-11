import anvil.secrets
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid


@anvil.server.callable
def assign_language_specific_base_templates(user, language_code):
  """
  Finds all base templates matching a specific language and assigns them to a new user.

  This is the primary function called at the end of the new user registration process.

  Args:
    user (Row): The user row from the 'users' table.
    language_code (str): The two-letter language code (e.g., "fr", "en") chosen by the user.

  Returns:
    int: The number of templates that were successfully assigned to the user.
  """
  if not user or not language_code:
    print(
      "[ERROR] assign_language_specific_base_templates: Called with invalid user or language_code."
    )
    return 0

  print(
    f"[INFO] Starting template assignment for user '{user['email']}' with language '{language_code}'."
  )

  try:
    # Find all base templates that match the user's chosen language.
    language_templates = app_tables.base_templates.search(language=language_code)

    templates_to_assign = list(language_templates)

    if not templates_to_assign:
      print(f"[WARN] No base templates found for language code: '{language_code}'.")
      return 0

    print(
      f"[INFO] Found {len(templates_to_assign)} templates to assign for language '{language_code}'."
    )

    assigned_count = 0
    for base_template in templates_to_assign:
      # Call the helper function to create a copy for the user.
      success = _create_custom_template_from_base(base_template, user)
      if success:
        assigned_count += 1

    print(
      f"[INFO] Successfully assigned {assigned_count} templates to user '{user['email']}'."
    )
    return assigned_count

  except Exception as e:
    print(f"[ERROR] An unexpected error occurred during template assignment: {str(e)}")
    return 0


def _create_custom_template_from_base(base_template, user):
  """
  Helper function to create a new row in custom_templates for a specific user,
  derived from a base template.

  This function now copies the necessary data (name, html) and sets the owner.

  Args:
    base_template (Row): The row from the 'base_templates' table to copy.
    user (Row): The user who will own the new custom template.

  Returns:
    bool: True if the template was created, False if it already existed.
  """
  try:
    template_name = base_template["name"]
    template_html = base_template["html"]

    # Check if a custom template with the same name already exists for this user to avoid duplicates.
    is_existing = app_tables.custom_templates.get(owner=user, name=template_name)

    if is_existing:
      print(
        f"[INFO] User '{user['email']}' already has template '{template_name}'. Skipping."
      )
      return False

    # Create the new row in the custom_templates table.
    app_tables.custom_templates.add_row(
      id=str(uuid.uuid4()),  # Generate a new unique ID
      name=template_name,
      html=template_html,
      owner=user,
      display=True,  # Default to being displayable
    )

    print(
      f"[INFO] Created custom template '{template_name}' for user '{user['email']}'."
    )
    return True

  except Exception as e:
    template_name_for_error = base_template["name"] if base_template else "N/A"
    print(
      f"[ERROR] Failed to create custom template '{template_name_for_error}' for user '{user['email']}': {str(e)}"
    )
    return False
