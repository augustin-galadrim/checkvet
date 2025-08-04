import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.users

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

  # Update the row’s priority
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
              text_to_display=template['text_to_display']
            )
      except Exception as e:
        print(f"Error assigning template to user {user_id}: {str(e)}")

    return True
  except Exception as e:
    print(f"Error in assign_template_to_users: {str(e)}")
    return False
