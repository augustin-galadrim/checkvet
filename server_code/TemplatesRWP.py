import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def read_templates():
  current_user = anvil.users.get_user()
  print(f"Reading templates for user: {current_user}")

  templates = app_tables.custom_templates.search(owner=current_user)
  print(f"Found {len(templates)} templates")

  result = []
  for template in templates:
    print(f"Processing template: {template['template_name']}")
    template_dict = {
      'template_name': template['template_name'],
      'owner': template['owner'],
      'prompt': template['prompt'],
      'human_readable': template['human_readable'],
      'priority': template['priority'],
      'display_template': template['display_template'],
      'text_to_display': template['text_to_display'],
      'prompt_fr': template['prompt_fr'],  # Added French prompt
      'prompt_en': template['prompt_en']   # Added English prompt
    }
    result.append(template_dict)

  print(f"Returning {len(result)} templates")
  return result

@anvil.server.callable
def write_template(template_name, prompt=None, human_readable=None, priority=None, text_to_display=None, display_template=None, prompt_fr=None, prompt_en=None):
  current_user = anvil.users.get_user()
  print(f"Writing template '{template_name}' for user: {current_user}")

  template_row = app_tables.custom_templates.get(template_name=template_name, owner=current_user)
  print(f"Existing template found: {template_row is not None}")

  if template_row is None:
    print("Creating new template record")
    # Default lorem ipsum values for new templates
    default_prompt_fr = """Tu es un assistant IA expert dans l'édition de rapports vétérinaires selon les commandes orales du vétérinaire utilisateur.
Accomplis la demande du vétérinaire utilisateur en respectant la précision de la médecine vétérinaire et l'orthographe des termes techniques. Assure-toi que ton output inclue toujours l'intégralité du rapport.

Exemples:
- Si le vétérinaire demande des ajouts, renvoie le compte rendu entier avec les ajouts
- Si le vétérinaire demande des modifications, renvoie le compte rendu entier avec les modifications
- Si le vétérinaire demande des suppressions, renvoie le compte rendu entier sans les éléments à supprimer"""
    default_prompt_en = """You are an AI assistant specialized in editing veterinary reports according to the verbal commands of the veterinary user.
Complete the veterinary user's request while maintaining accuracy in veterinary medicine and correct spelling of technical terms. Make sure your output always includes the entire report.
Examples:

If the veterinarian requests additions, return the entire report with the additions
If the veterinarian requests modifications, return the entire report with the modifications
If the veterinarian requests deletions, return the entire report without the elements to be deleted"""

    template_row = app_tables.custom_templates.add_row(
      template_name=template_name,
      owner=current_user,
      priority=0,  # Default priority to 0
      prompt_fr=default_prompt_fr,  # Set default lorem ipsum for French
      prompt_en=default_prompt_en   # Set default lorem ipsum for English
    )

  # Update only the fields that were provided
  updates = []
  if human_readable is not None:
    template_row['human_readable'] = human_readable
    updates.append('human_readable')
  if prompt is not None:
    template_row['prompt'] = prompt
    updates.append('prompt')
  if priority is not None:
    template_row['priority'] = priority
    updates.append('priority')
  if text_to_display is not None:
    template_row['text_to_display'] = text_to_display
    updates.append('text_to_display')
  if display_template is not None:
    template_row['display_template'] = display_template
    updates.append('display_template')
  if prompt_fr is not None:
    template_row['prompt_fr'] = prompt_fr
    updates.append('prompt_fr')
  if prompt_en is not None:
    template_row['prompt_en'] = prompt_en
    updates.append('prompt_en')

  print(f"Updated fields: {', '.join(updates)}")
  return True

@anvil.server.callable
def pick_template(template_name, header):
  """
    Updated debug version of pick_template.
    We retrieve the Data Tables row, iterate over the items (which return [key, value] pairs),
    then build a list of just the keys. Finally, we check if `header` is in that list.
    """
  print(f"DEBUG: pick_template() -> template_name='{template_name}', header='{header}'")
  try:
    current_user = anvil.users.get_user()
    print(f"Current user: {current_user}")

    template = app_tables.custom_templates.get(
      template_name=template_name,
      owner=current_user
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

@anvil.server.callable
def set_priority(template_name, new_priority):
  """
  Updates the priority value (0, 1, or 2) for the template with the given template_name
  for the current user.
  Enforces:
    - Only one template can have priority 2 (green).
    - At most two templates can have priority 1 (yellow).
  """
  # Get the current user
  current_user = anvil.users.get_user()
  if not current_user:
    raise Exception("User not logged in.")
  # Get the template row from the custom_templates table for the current user.
  row = app_tables.custom_templates.get(template_name=template_name, owner=current_user)
  if not row:
    raise Exception("Template not found for current user.")
  # For priority 2, automatically demote any other template that is green for the current user.
  if new_priority == 2:
    for r in app_tables.custom_templates.search(owner=current_user, priority=2):
      if r['template_name'] != template_name:
        r['priority'] = 0
  # For priority 1, enforce a maximum of two yellow templates for the current user.
  if new_priority == 1:
    yellow_templates = [r for r in app_tables.custom_templates.search(owner=current_user, priority=1)
                        if r['template_name'] != template_name]
    if len(yellow_templates) >= 2:
      raise Exception("Maximum yellow favorites reached.")
  # Update the row's priority
  row['priority'] = new_priority
  return "OK"

@anvil.server.callable
def assign_template_to_users(template_name, user_ids):
  """
    Assigns a template to multiple users.

    Args:
        template_name: The name of the template to assign
        user_ids: A list of user IDs to assign the template to

    Returns:
        Boolean indicating success
    """
  try:
    # Get the current user (admin)
    admin_user = anvil.users.get_user()
    if not admin_user:
      return False
      # Get the template
    template = app_tables.custom_templates.get(template_name=template_name, owner=admin_user)
    if not template:
      return False
      # Process each user ID
    for user_id in user_ids:
      try:
        user = app_tables.users.get_by_id(user_id)
        if user:
          # Check if user already has this template
          existing_template = app_tables.custom_templates.get(
            template_name=template_name,
            owner=user
          )
          if not existing_template:
            # Create a copy of the template for this user
            app_tables.custom_templates.add_row(
              template_name=template_name,
              owner=user,
              prompt=template['prompt'],
              human_readable=template['human_readable'],
              priority=template['priority'],
              display_template=template['display_template'],
              text_to_display=template['text_to_display'],
              prompt_fr=template['prompt_fr'],  # Copy French prompt
              prompt_en=template['prompt_en']   # Copy English prompt
            )
      except Exception as e:
        print(f"Error assigning template to user {user_id}: {str(e)}")
    return True
  except Exception as e:
    print(f"Error in assign_template_to_users: {str(e)}")
    return False
