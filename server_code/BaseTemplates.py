import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime

@anvil.server.callable
def get_base_template(template_name):
  """
  Retrieves a base template by name using search instead of get.
  """
  try:
    print(f"[DEBUG] Searching for base template with name: '{template_name}'")
    results = list(app_tables.base_templates.search(template_name=template_name))

    print(f"[DEBUG] Search results count: {len(results)}")
    if results and len(results) > 0:
      template = results[0]
      print(f"[DEBUG] Template found: {template}")
      print(f"[DEBUG] Template type: {type(template)}")

      # Print all available columns
      print("[DEBUG] Template columns:")
      for col in template:
        print(f"[DEBUG]   - Column: {col[0]}, Value type: {type(col[1])}")

      return template

    print(f"[DEBUG] No template found with name '{template_name}'")
    return None
  except Exception as e:
    print(f"[DEBUG] Error in get_base_template: {str(e)}")
    import traceback
    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
    return None

@anvil.server.callable
def affect_base_template(base_template, user):
  """
  Creates a new row in custom_templates derived from a base template for a specific user,
  using dictionary-style column access.
  """
  import traceback

  try:
    print("[DEBUG] ===== affect_base_template started =====")

    # Validate inputs
    print(f"[DEBUG] base_template: {base_template}")
    print(f"[DEBUG] base_template type: {type(base_template)}")
    print(f"[DEBUG] user: {user}")

    if not base_template:
      print("[DEBUG] Error: Base template is None or invalid")
      raise Exception("Base template is None or invalid")

    # Identify template_name via dictionary style
    try:
      template_name = base_template['template_name']
      print(f"[DEBUG] template_name found via dict access: '{template_name}'")
    except Exception as e:
      template_name = "Unnamed Template"
      print(f"[DEBUG] Could not find template_name: {str(e)}. Fallback: '{template_name}'")

    print(f"[DEBUG] Final template_name: '{template_name}'")
    print(f"[DEBUG] Creating custom template from base template '{template_name}' for user: {user['email']}")

    # Debug: Inspect base_template columns by iterating
    try:
      row_id = base_template.get_id()
      print(f"[DEBUG] base_template row_id: {row_id}")
    except Exception as e:
      print(f"[DEBUG] Could not get base_template.get_id(): {str(e)}")

    print("[DEBUG] base_template columns discovered via iteration:")
    for col_name, col_val in base_template:
      # Show a limited preview if it's a long string
      if isinstance(col_val, str) and len(col_val) > 50:
        preview = col_val[:50] + "..."
      else:
        preview = col_val
      print(f"[DEBUG]   '{col_name}': type={type(col_val)}, value={preview}")

    # Check if template already exists for this user
    existing_templates = list(app_tables.custom_templates.search(
        owner=user,
        base_template=base_template
    ))

    if existing_templates:
      print(f"[DEBUG] User already has this template, returning existing row")
      return existing_templates[0]

    # Safely extract fields with defaults using dictionary access
    try:
      prompt = base_template['prompt']
      print(f"[DEBUG] Found prompt, length: {len(prompt)}")
    except Exception as e:
      prompt = ""
      print(f"[DEBUG] Could not read 'prompt': {str(e)} -> defaulting to empty")

    try:
      prompt_fr = base_template['prompt_fr']
      print(f"[DEBUG] Found prompt_fr, length: {len(prompt_fr)}")
    except Exception as e:
      prompt_fr = ""
      print(f"[DEBUG] Could not read 'prompt_fr': {str(e)} -> defaulting to empty")

    try:
      prompt_en = base_template['prompt_en']
      print(f"[DEBUG] Found prompt_en, length: {len(prompt_en)}")
    except Exception as e:
      prompt_en = ""
      print(f"[DEBUG] Could not read 'prompt_en': {str(e)} -> defaulting to empty")

    try:
      human_readable = base_template['human_readable']
      print(f"[DEBUG] Found human_readable: {human_readable}")
    except Exception as e:
      human_readable = ""
      print(f"[DEBUG] Could not read 'human_readable': {str(e)} -> defaulting to empty")

    print(f"[DEBUG] Creating new row in custom_templates...")
    new_template = app_tables.custom_templates.add_row(
        template_name=template_name,
        owner=user,
        prompt=prompt,
        prompt_fr=prompt_fr,
        prompt_en=prompt_en,
        base_template=base_template,
        priority=2,
        human_readable=human_readable
    )

    print("[DEBUG] Successfully created custom template derived from base template")
    return new_template

  except Exception as e:
    error_tb = traceback.format_exc()
    print(f"[DEBUG] Error in affect_base_template: {str(e)}")
    print(f"[DEBUG] Traceback: {error_tb}")
    raise Exception(f"Failed to create template: {str(e)}")




@anvil.server.callable
def update_base_template(base_template):
  """
  Updates all custom templates derived from a specific base template.

  Args:
      base_template: Row object from the base_templates table that has been updated

  Returns:
      The number of custom templates that were updated
  """
  try:
    print(f"Debug: Updating derived templates for base template: {base_template['template_name']}")

    # Find all custom templates linked to this base template
    derived_templates = app_tables.custom_templates.search(
        base_template=base_template
    )

    # Count for return value
    update_count = 0

    # Update each derived template
    for template in derived_templates:
      # Update the multilingual prompts
      template['prompt'] = base_template['prompt']

      # Only update these if they exist in the base template
      if 'prompt_fr' in base_template:
        template['prompt_fr'] = base_template['prompt_fr']

      if 'prompt_en' in base_template:
        template['prompt_en'] = base_template['prompt_en']

      # If human_readable needs to be updated as well
      if 'human_readable' in base_template:
        template['human_readable'] = base_template['human_readable']

      update_count += 1

    print(f"Debug: Updated {update_count} derived templates")
    return update_count

  except Exception as e:
    print(f"Debug: Error in update_base_template: {str(e)}")
    raise Exception(f"Failed to update derived templates: {str(e)}")

@anvil.server.callable
def list_base_templates():
  """
  Returns a list of all base templates
  """
  try:
    print("Debug: Fetching list of base templates")
    templates = app_tables.base_templates.search()
    result = []

    for template in templates:
      template_dict = {
          'id': template.get_id(),  # Added row ID
          'template_name': template['template_name'],
          'prompt': template['prompt'],
          # Include other fields as needed
      }
      result.append(template_dict)

    print(f"Debug: Returning {len(result)} base templates")
    return result
  except Exception as e:
    print(f"Debug: Error in list_base_templates: {str(e)}")
    raise Exception(f"Failed to list base templates: {str(e)}")

@anvil.server.callable
def assign_template_to_all_users(base_template_name):
  """
  Assigns a base template to all existing users
  """
  try:
    print(f"Debug: Assigning template '{base_template_name}' to all users")
    # Get the base template
    base_template = app_tables.base_templates.get(template_name=base_template_name)
    if not base_template:
      print(f"Debug: Base template '{base_template_name}' not found")
      raise Exception(f"Base template '{base_template_name}' not found")

    # Get all users
    users = app_tables.users.search()
    count = 0

    # Assign template to each user
    for user in users:
      affect_base_template(base_template, user)
      count += 1

    print(f"Debug: Successfully assigned template to {count} users")
    return f"Assigned template to {count} users"
  except Exception as e:
    print(f"Debug: Error in assign_template_to_all_users: {str(e)}")
    raise Exception(f"Failed to assign templates: {str(e)}")
