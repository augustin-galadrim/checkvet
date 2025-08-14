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

  # --- MODIFIED: Use a try-except block for safety ---
  default_template_id = None
  try:
    # Fetch the user's default template link
    default_template_link = current_user["default_template"]
    if default_template_link:
      # --- MODIFIED: Use the reliable get_id() method ---
      default_template_id = default_template_link.get_id()
  except Exception as e:
    print(
      f"WARN: Could not retrieve default template for user {current_user['email']}. Error: {e}"
    )
    # This can happen if the 'default_template' column doesn't exist or is empty.

  # Fetch all templates owned by the user
  templates = app_tables.custom_templates.search(owner=current_user)

  result_list = [
    # --- MODIFIED: Use t.get_id() for each template in the list ---
    {"id": t.get_id(), "name": t["name"], "html": t["html"], "display": t["display"]}
    for t in templates
  ]

  # Return a dictionary containing both the list and the default ID
  return {"templates": result_list, "default_template_id": default_template_id}


# --- The write_template function should also be corrected to use Anvil's ID ---
@anvil.server.callable
def write_template(template_id=None, name=None, html=None, display=None):
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

  return True


@anvil.server.callable
def pick_template(template_id, header):
  """
  Updated debug version of pick_template.
  We retrieve the Data Tables row by id.
  """
  print(f"DEBUG: pick_template() -> template_id='{template_id}', header='{header}'")
  try:
    current_user = anvil.users.get_user()
    print(f"Current user: {current_user}")

    template = app_tables.custom_templates.get_by_id(template_id)

    if not template or template["owner"] != current_user:
      # Fallback for old templates that might be searched by name, though we are moving away from this.
      template = app_tables.custom_templates.get(name=template_id, owner=current_user)

    print(f"Retrieved template: {template}")

    if not template:
      print("No template found - returning None")
      return None

    # Attempt to iterate over the row items,
    # which appear as [key, value] pairs in your logs.
    column_pairs = []
    for item in template:
      # item should be something like ["html", "...text..."]
      column_pairs.append(item)

    print(f"Discovered pairs in row: {column_pairs}")

    # Now extract just the keys
    column_names = [pair[0] for pair in column_pairs]
    print(f"Extracted column names: {column_names}")

    # Check if the requested header is one of these names
    if header in column_names:
      value = template[header]
      print(f"Found header '{header}' in row. Returning value: {value}")
      return value
    else:
      print(f"Header '{header}' not found in row. Returning None.")
      return None

  except Exception as e:
    print(f"Exception in pick_template: {e}")
    raise


@anvil.server.callable
def delete_template(template_id):
  """
  Deletes a template for the currently logged-in user.
  """
  current_user = anvil.users.get_user()
  if not current_user:
    raise anvil.users.AuthenticationFailed(
      "You must be logged in to delete a template."
    )

  # Find the template that matches the id and is owned by the current user.
  template_row = app_tables.custom_templates.get(id=template_id)

  if template_row and template_row["owner"] == current_user:
    # If the template is found, delete it.
    template_row.delete()
    print(
      f"Template with id '{template_id}' deleted successfully for user '{current_user['email']}'."
    )
    return True
  else:
    # If no template is found for this user, do nothing and report failure.
    print(
      f"Template with id '{template_id}' not found for user '{current_user['email']}'."
    )
    return False
