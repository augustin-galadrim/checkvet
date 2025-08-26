import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import uuid
from ..logging_server import get_logger
from ..auth import admin_required

logger = get_logger(__name__)


@admin_required
@anvil.server.callable
def admin_assign_base_template_to_users(template_id, user_ids):
  """
  Admin function to assign a BASE template to multiple users by unconditionally
  creating a new copy for each.
  """
  logger.info(
    f"Admin request to assign base template ID '{template_id}' to {len(user_ids)} users."
  )
  if not template_id or not user_ids:
    logger.warning("Assignment failed: template_id or user_ids not provided.")
    return False

  try:
    base_template = app_tables.base_templates.get_by_id(template_id)
    if not base_template:
      logger.error(
        f"Assignment failed: Base template with ID '{template_id}' not found."
      )
      return False

    for user_id in user_ids:
      try:
        user = app_tables.users.get_by_id(user_id)
        if user:
          # Unconditionally create a copy of the base template.
          app_tables.custom_templates.add_row(
            name=base_template["name"],
            owner=user,
            html=base_template["html"],
            display=True,
            language=base_template["language"],
          )
          logger.debug(
            f"Assigned template '{base_template['name']}' ({base_template['language']}) to user '{user['email']}'."
          )
      except Exception as e:
        logger.error(f"Error assigning template to user {user_id}: {str(e)}")

    logger.info(f"Finished assignment for base template ID '{template_id}'.")
    return True
  except Exception as e:
    logger.error(f"Critical error in admin_assign_base_template_to_users: {str(e)}")
    return False


@admin_required
@anvil.server.callable
def admin_get_templates_for_user(user_id):
  """Admin function to retrieve all custom templates for a specific user ID."""
  if not user_id:
    return []

  user = app_tables.users.get_by_id(user_id)
  if not user:
    logger.warning(
      f"Admin request for templates failed: User ID '{user_id}' not found."
    )
    return []

  logger.info(f"Admin request for templates owned by user '{user['email']}'.")
  user_templates = app_tables.custom_templates.search(owner=user)

  result = [
    {
      "id": t.get_id(),
      "name": t["name"],
      "language": t["language"],
    }
    for t in user_templates
  ]

  logger.info(f"Found {len(result)} templates for user '{user['email']}'.")
  return result


@admin_required
@anvil.server.callable
def admin_get_custom_template(template_id):
  """Admin function to retrieve a single custom template by its ID."""
  logger.info(f"Admin request for custom template details. ID: {template_id}")
  if not template_id:
    return None

  template = app_tables.custom_templates.get_by_id(template_id)
  if not template:
    logger.warning(f"No custom template found for ID: {template_id}")
    return None

  return {
    "id": template.get_id(),
    "name": template["name"],
    "html": template["html"],
    "language": template["language"],
  }


@admin_required
@anvil.server.callable
def admin_write_template(
  template_id=None, name=None, html=None, display=None, language=None, owner_id=None
):
  """Admin function to create or update any template."""
  logger.info(f"Admin request to write template. ID: {template_id}, Name: {name}")
  try:
    if template_id:
      template_row = app_tables.custom_templates.get_by_id(template_id)
      if not template_row:
        logger.error(
          f"admin_write_template failed: Template with ID '{template_id}' not found."
        )
        raise ValueError(f"Template with ID '{template_id}' not found.")
      logger.debug(f"Updating template ID: {template_id}")
    else:
      if not owner_id:
        logger.error(
          "admin_write_template failed: Owner ID is required to create a new template."
        )
        raise ValueError("An owner is required to create a new template.")
      owner = app_tables.users.get_by_id(owner_id)
      if not owner:
        logger.error(
          f"admin_write_template failed: Owner with ID '{owner_id}' not found."
        )
        raise ValueError(f"Owner with ID '{owner_id}' not found.")
      template_row = app_tables.custom_templates.add_row(owner=owner)
      logger.debug(f"Creating new template for owner: {owner['email']}")

    if name is not None:
      template_row["name"] = name
    if html is not None:
      template_row["html"] = html
    if display is not None:
      template_row["display"] = display
    if language is not None:
      template_row["language"] = language

    logger.info(f"Successfully wrote template '{name}'.")
    return True
  except Exception as e:
    logger.error(f"Exception in admin_write_template: {e}", exc_info=True)
    raise


@anvil.server.callable
def read_templates():
  """Fetches templates for the current user."""
  current_user = anvil.users.get_user()
  if not current_user:
    return {"templates": [], "default_template_id": None}
  logger.info(f"Reading templates for user '{current_user['email']}'.")

  default_template_id = None
  try:
    default_template_link = current_user["default_template"]
    if default_template_link:
      default_template_id = default_template_link.get_id()
  except Exception as e:
    logger.warning(
      f"Could not retrieve default template for user {current_user['email']}. Error: {e}"
    )

  templates = app_tables.custom_templates.search(owner=current_user)
  result_list = [
    {
      "id": t.get_id(),
      "name": t["name"],
      "html": t["html"],
      "display": t["display"],
      "language": t["language"],
    }
    for t in templates
  ]
  logger.debug(
    f"Found {len(result_list)} templates for user '{current_user['email']}'."
  )
  return {"templates": result_list, "default_template_id": default_template_id}


@anvil.server.callable
def write_template(template_id=None, name=None, html=None, display=None, language=None):
  """Writes a template for the current user."""
  current_user = anvil.users.get_user()
  logger.info(
    f"User '{current_user['email']}' writing template. ID: {template_id}, Name: {name}"
  )
  if template_id:
    template_row = app_tables.custom_templates.get_by_id(template_id)
    if not template_row or template_row["owner"] != current_user:
      logger.error(
        f"Permission denied for user '{current_user['email']}' to edit template ID '{template_id}'."
      )
      raise anvil.server.PermissionDenied("Permission denied.")
  else:
    template_row = app_tables.custom_templates.add_row(owner=current_user)

  if name is not None:
    template_row["name"] = name
  if html is not None:
    template_row["html"] = html
  if display is not None:
    template_row["display"] = display
  if language is not None:
    template_row["language"] = language
  logger.info(
    f"Successfully wrote template '{name}' for user '{current_user['email']}'."
  )
  return True


@anvil.server.callable
def delete_template(template_id):
  """Deletes a template for the current user."""
  current_user = anvil.users.get_user()
  if not current_user:
    raise anvil.users.AuthenticationFailed("You must be logged in.")

  template_row = app_tables.custom_templates.get_by_id(template_id)
  if template_row and template_row["owner"] == current_user:
    template_row.delete()
    logger.info(
      f"Template ID '{template_id}' deleted by owner '{current_user['email']}'."
    )
    return True
  else:
    logger.warning(
      f"Failed delete attempt: Template ID '{template_id}' not found or not owned by '{current_user['email']}'."
    )
    return False


# The pick_template function remains unchanged as it is not directly used by the admin panel logic.
@anvil.server.callable
def pick_template(template_id, header):
  current_user = anvil.users.get_user()
  template = app_tables.custom_templates.get_by_id(template_id)
  if not template or template["owner"] != current_user:
    return None
  return template.get(header)
