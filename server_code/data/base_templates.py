import anvil.secrets
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid
from ..auth import admin_required
from ..logging_server import get_logger

logger = get_logger(__name__)


@admin_required
@anvil.server.callable
def admin_get_all_base_templates():
  """Admin function to retrieve all templates from the base_templates table."""
  logger.info("Admin request to get all base templates.")
  all_base_templates = app_tables.base_templates.search()

  result = [
    {"id": t.get_id(), "name": t["name"], "html": t["html"], "language": t["language"]}
    for t in all_base_templates
  ]

  logger.info(f"Returning {len(result)} base templates.")
  return result


@anvil.server.callable
def assign_all_base_templates(user):
  """
  Finds all base templates and assigns them to a new user.

  Args:
    user (Row): The user row from the 'users' table.

  Returns:
    int: The number of templates that were successfully assigned to the user.
  """
  if not user:
    logger.error("assign_all_base_templates: Called with an invalid user.")
    return 0

  logger.info(f"Starting template assignment for user '{user['email']}'.")

  try:
    # Find all base templates.
    all_base_templates = app_tables.base_templates.search()

    templates_to_assign = list(all_base_templates)

    if not templates_to_assign:
      logger.warning("No base templates found in the database.")
      return 0

    logger.info(f"Found {len(templates_to_assign)} total base templates to assign.")

    assigned_count = 0
    for base_template in templates_to_assign:
      # Call the helper function to create a copy for the user.
      success = _create_custom_template_from_base(base_template, user)
      if success:
        assigned_count += 1

    logger.info(
      f"Successfully assigned {assigned_count} templates to user '{user['email']}'."
    )
    return assigned_count

  except Exception as e:
    logger.error(
      f"An unexpected error occurred during template assignment for user '{user['email']}': {e}",
      exc_info=True,
    )
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
      name=template_name,
      html=template_html,
      owner=user,
      display=True,
      language=base_template["language"],
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