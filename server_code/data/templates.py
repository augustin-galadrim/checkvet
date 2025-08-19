import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import uuid


@anvil.server.callable
def read_templates():
  current_user = anvil.users.get_user()
  if not current_user:
    return {"templates": [], "default_template_id": None}

  default_template_id = None
  try:
    default_template_link = current_user["default_template"]
    if default_template_link:
      default_template_id = default_template_link.get_id()
  except Exception as e:
    print(
      f"WARN: Could not retrieve default template for user {current_user['email']}. Error: {e}"
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

  return {"templates": result_list, "default_template_id": default_template_id}


@anvil.server.callable
def write_template(template_id=None, name=None, html=None, display=None, language=None):
  current_user = anvil.users.get_user()
  if template_id:
    template_row = app_tables.custom_templates.get_by_id(template_id)
    if not template_row or template_row["owner"] != current_user:
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

  return True


@anvil.server.callable
def pick_template(template_id, header):
  print(f"DEBUG: pick_template() -> template_id='{template_id}', header='{header}'")
  try:
    current_user = anvil.users.get_user()
    template = app_tables.custom_templates.get_by_id(template_id)

    if not template or template["owner"] != current_user:
      print("No template found or permission denied - returning None")
      return None

    if header in template:
      value = template[header]
      print(f"Found header '{header}' in row. Returning value.")
      return value
    else:
      print(f"Header '{header}' not found in row. Returning None.")
      return None

  except Exception as e:
    print(f"Exception in pick_template: {e}")
    raise


@anvil.server.callable
def delete_template(template_id):
  current_user = anvil.users.get_user()
  if not current_user:
    raise anvil.users.AuthenticationFailed(
      "You must be logged in to delete a template."
    )

  template_row = app_tables.custom_templates.get_by_id(template_id)

  if template_row and template_row["owner"] == current_user:
    template_row.delete()
    print(
      f"Template with id '{template_id}' deleted successfully for user '{current_user['email']}'."
    )
    return True
  else:
    print(
      f"Template with id '{template_id}' not found for user '{current_user['email']}'."
    )
    return False