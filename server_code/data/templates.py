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
  templates = app_tables.custom_templates.search(owner=current_user)
  # Return dictionaries with the new schema: id, name, html, display
  result = [
    {"id": t["id"], "name": t["name"], "html": t["html"], "display": t["display"]}
    for t in templates
  ]
  return result


@anvil.server.callable
def write_template(
  template_id=None,
  name=None,
  html=None,
  display=None,
):
  print(
    f"writing template with the following args : name={name}, html={html}, id={template_id}"
  )
  current_user = anvil.users.get_user()

  if template_id:
    print("writing template : entered EDIT mode")
    template_row = app_tables.custom_templates.get(id=template_id)
    print(template_row)
    if not template_row or template_row["owner"] != current_user:
      raise anvil.server.PermissionDenied(
        "You do not have permission to edit this template or it does not exist."
      )
  else:
    # CREATE mode
    print("writing template : entered CREATE mode")
    template_row = app_tables.custom_templates.add_row(
      id=str(uuid.uuid4()), owner=current_user
    )

  # Update the row's properties (works for both edit and create)
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
