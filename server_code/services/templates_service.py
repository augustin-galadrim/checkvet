import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.users

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
              display_template=template['display_template'],
              text_to_display=template['text_to_display']
            )
      except Exception as e:
        print(f"Error assigning template to user {user_id}: {str(e)}")

    return True
  except Exception as e:
    print(f"Error in assign_template_to_users: {str(e)}")
    return False
