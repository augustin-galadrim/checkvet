import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server


@anvil.server.callable(require_user=True)
def EN_read_templates():
  current_user = anvil.users.get_user()
  print(f"Reading templates for user: {current_user}")

  # Retrieve all templates from the table.
  all_templates = list(app_tables.custom_templates.search())
  print(f"Found {len(all_templates)} total templates")

  result = []
  # Filter templates based on the owner's email.
  for template in all_templates:
    owner = template["owner"]
    if owner is not None:
      # Direct access to the owner's email property.
      owner_email = owner["email"]
      if owner_email in [current_user["email"], "en_su@checkvet.com"]:
        print(
          f"Processing template: {template['template_name']} (Owner: {owner_email})"
        )
        template_dict = {
          "template_name": template["template_name"],
          "owner": owner,
          "prompt": template["prompt"],
          "human_readable": template["human_readable"],
        }
        result.append(template_dict)

  print(f"Returning {len(result)} templates")
  return result


@anvil.server.callable
def EN_search_templates(search_input):
  try:
    if not isinstance(search_input, str):
      raise ValueError("Search input must be a string")

    # Get the current user
    current_user = anvil.users.get_user()
    if not current_user:
      raise Exception("No current user is logged in.")

    # Get the en_su user row from the users table
    en_su_user = next(
      (
        user
        for user in app_tables.users.search()
        if user["email"] == "en_su@checkvet.com"
      ),
      None,
    )

    search_term = search_input.strip()

    if not search_term:
      # If no search term, return all templates owned by current user or en_su
      rows = [
        r
        for r in app_tables.custom_templates.search()
        if r["owner"] == current_user or (en_su_user and r["owner"] == en_su_user)
      ]
    else:
      # Search for term within template_name, limited to records owned by current user or en_su
      rows = [
        r
        for r in app_tables.custom_templates.search()
        if search_term.lower() in r["template_name"].lower()
        and (r["owner"] == current_user or (en_su_user and r["owner"] == en_su_user))
      ]

    # Build the return structure
    return [
      {
        "id": r.get_id(),
        "template_name": r["template_name"],
        "owner": r["owner"],  # Link to the users' row
        "prompt": r["prompt"],
        "human_readable": r["human_readable"],
      }
      for r in rows
    ]

  except Exception as e:
    print(f"Search error: {str(e)}")
    return []


@anvil.server.callable
def EN_pick_template(template_name, header):
  """
  Updated debug version of pick_template.
  We retrieve the Data Tables row, iterate over the items (which return [key, value] pairs),
  then build a list of just the keys. Finally, we check if `header` is in that list.
  """
  print(f"DEBUG: pick_template() -> template_name='{template_name}', header='{header}'")
  try:
    current_user = anvil.users.get_user()
    print(f"Current user: {current_user}")

    # Get the en_su user row
    en_su_user = next(
      (
        user
        for user in app_tables.users.search()
        if user["email"] == "en_su@checkvet.com"
      ),
      None,
    )
    print(f"EN_SU user: {en_su_user}")

    # Search for template owned by either current user or en_su
    template = next(
      (
        t
        for t in app_tables.custom_templates.search(template_name=template_name)
        if t["owner"] == current_user or (en_su_user and t["owner"] == en_su_user)
      ),
      None,
    )

    print(f"Retrieved template: {template}")
    if not template:
      print("No template found - returning None")
      return None

    # Attempt to iterate over the row items,
    # which appear as [key, value] pairs in your logs.
    column_pairs = []
    for item in template:
      # item should be something like ["prompt", "...text..."]
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
