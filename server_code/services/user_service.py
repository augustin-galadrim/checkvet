import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from ..logging_server import get_logger
from ..auth import admin_required
from ..data.structures import generate_unique_join_code
from ..data import structures, base_templates, users

logger = get_logger(__name__)


@anvil.server.callable
def custom_confirm_email(email, confirmation_key):
  user = app_tables.users.get(email=email, confirmation_key=confirmation_key)
  if user:
    anvil.users.force_login(user)
    user["confirmed_email"] = True
    user["confirmation_key"] = None
    return True
  return False


@anvil.server.callable
def mark_additional_info_completed(user):
  user["additional_info_completed"] = True


@admin_required
@anvil.server.callable
def admin_make_user_independent(user_id):
  """
  Safely removes a user from their current structure by creating and assigning
  them to a new, personal structure. This is the correct way to make a user independent.
  """
  logger.info(f"Admin request to make user ID '{user_id}' independent.")
  user_to_update = app_tables.users.get_by_id(user_id)

  if not user_to_update:
    logger.error(
      f"admin_make_user_independent failed: User with ID '{user_id}' not found."
    )
    raise ValueError(f"User with ID '{user_id}' not found.")

  # Create a unique name for the new personal structure.
  personal_structure_name = f"Personal Structure - User ID: {user_to_update.get_id()}"

  new_personal_structure = app_tables.structures.add_row(
    name=personal_structure_name,
    owner=user_to_update,
    is_personal=True,
    join_code=generate_unique_join_code(),
  )

  # Re-link the user and ensure they are no longer a supervisor.
  user_to_update.update(structure=new_personal_structure, supervisor=False)

  logger.info(f"Successfully made user '{user_to_update['email']}' independent.")
  return True


@anvil.server.callable
def get_full_user_info():
  user = anvil.users.get_user()
  if not user:
    return None

  user_row = app_tables.users.get(email=user["email"])
  if not user_row:
    return None

  return {
    "signature_image": user_row["signature_image"],
    "report_header_image": user_row["report_header_image"],
    "report_footer_image": user_row["report_footer_image"],
  }


@anvil.server.callable
def pick_user_email(user, header):
  print("DEBUG: Entering pick_user_info function.")
  print(f"DEBUG: Requested header: {header}")

  user_row = app_tables.users.get(name=user)
  print(f"DEBUG: Retrieved user_row: {user_row}")
  if user_row is None:
    print("DEBUG: No user row found for the current user.")
    return None

  return user_row["email"]


@anvil.server.callable
def create_user(email, name):
  """Create a new user with basic information"""
  try:
    # Check if user already exists
    existing_user = app_tables.users.get(email=email)
    if existing_user:
      print(f"DEBUG: User with email {email} already exists")
      return False

      # Create a new user row
    new_user = app_tables.users.add_row(
      email=email,
      name=name,
      enabled=True,
      confirmed_email=True,
      supervisor=False,
      signed_up=datetime.now(),
    )

    return new_user.get_id()  # Return the new user ID
  except Exception as e:
    print(f"ERROR: Failed to create user: {str(e)}")
    return False


@anvil.server.callable
def update_user(user_id, **kwargs):
  """
  Update a user by ID. Can only assign users to real, non-personal structures.
  Making a user independent is handled by 'admin_make_user_independent'.
  """
  try:
    user_row = app_tables.users.get_by_id(user_id)
    if not user_row:
      print(f"DEBUG: No user found with ID {user_id}")
      return False

    if "structure" in kwargs:
      structure_value = kwargs.pop("structure")
      if structure_value:
        # Ensure we only link to real, non-personal clinics.
        structure_row = app_tables.structures.get(
          name=structure_value, is_personal=False
        )
        if structure_row:
          user_row["structure"] = structure_row
        else:
          print(f"DEBUG: Non-personal structure not found: {structure_value}")
          return False
      # If structure_value is empty, this block is skipped, preserving the user's current structure.

    for key, value in kwargs.items():
      user_row[key] = value

    return True
  except Exception as e:
    print(f"ERROR: Failed to update user: {str(e)}")
    return False


@anvil.server.callable(require_user=True)
def set_default_template(template_id):
  """
  Sets the default template for the current user.
  """
  user = anvil.users.get_user()
  if not user:
    raise anvil.server.PermissionDenied(
      "You must be logged in to set a default template."
    )

  # Correctly fetch the template by its unique Anvil Row ID
  template_to_set = app_tables.custom_templates.get_by_id(template_id)

  # Verify the template exists and is owned by the current user
  if not template_to_set or template_to_set["owner"] != user:
    raise anvil.server.PermissionDenied(
      "Template not found or you do not have permission to access it."
    )

  try:
    # Set the 'default_template' link in the users table
    user["default_template"] = template_to_set
    print(
      f"User '{user['email']}' set default template to '{template_to_set['name']}'."
    )
    return True
  except Exception as e:
    print(f"Error setting default template for user '{user['email']}': {e}")
    return False


@admin_required
@anvil.server.callable
def admin_create_user(
  email, name, phone, supervisor, favorite_language, structure_name
):
  """
  Admin function to create a new user with all necessary details, including structure assignment.
  This function is called when creating a new user from the admin panel.
  """
  logger.info(f"Admin request to create new user: '{email}'.")
  if not email or not name:
    raise ValueError("Email and Name are required to create a new user.")

  if app_tables.users.get(email=email):
    logger.warning(f"User creation failed: Email '{email}' already exists.")
    return None  # Indicate failure

  try:
    # Determine the structure to assign
    assigned_structure = None
    is_independent = structure_name == "independent" or not structure_name

    if not is_independent:
      assigned_structure = app_tables.structures.get(
        name=structure_name, is_personal=False
      )
      if not assigned_structure:
        raise ValueError(
          f"Could not find a non-personal structure named '{structure_name}'."
        )

        # Create the new user
    new_user = app_tables.users.add_row(
      email=email,
      name=name,
      phone=phone,
      enabled=True,
      confirmed_email=True,  # Admins can create confirmed users directly
      supervisor=False if is_independent else supervisor,
      favorite_language=favorite_language,
      signed_up=datetime.now(),
      additional_info=True,  # Assume admin-created users have their info filled
    )

    # Handle structure assignment after user is created
    if is_independent:
      personal_structure = app_tables.structures.add_row(
        name=f"Practice of {name}", owner=new_user, is_personal=True
      )
      new_user["structure"] = personal_structure
    else:
      new_user["structure"] = assigned_structure

      # Assign all base templates to the new user
    base_templates.assign_all_base_templates(new_user)

    logger.info(f"Successfully created and configured user '{email}'.")
    return new_user.get_id()

  except Exception as e:
    logger.error(
      f"Failed to execute admin_create_user for '{email}': {e}", exc_info=True
    )
    # Clean up partial user creation if it occurred
    user_to_delete = app_tables.users.get(email=email)
    if user_to_delete:
      user_to_delete.delete()
    raise e


@admin_required
@anvil.server.callable
def admin_update_user(user_id, **kwargs):
  """
  Admin function to update a user by ID. Handles structure changes correctly.
  """
  logger.info(f"Admin request to update user ID: {user_id}")
  try:
    user_row = app_tables.users.get_by_id(user_id)
    if not user_row:
      logger.error(f"Update failed: No user found with ID {user_id}")
      return False

    if "structure" in kwargs:
      structure_value = kwargs.pop("structure")
      if structure_value == "independent":
        # If the user is already independent, do nothing. Otherwise, make them independent.
        if not users._is_user_independent(user_row):
          admin_make_user_independent(user_id)  # Re-use the safe function
      else:
        # Assigning to a real, non-personal structure
        structure_row = app_tables.structures.get(
          name=structure_value, is_personal=False
        )
        if structure_row:
          user_row["structure"] = structure_row
        else:
          logger.warning(
            f"Update failed: Non-personal structure '{structure_value}' not found."
          )
          # Do not change the structure if the new one is not found

    # Update supervisor status, but only if they are not independent
    if not users._is_user_independent(user_row) and "supervisor" in kwargs:
      user_row["supervisor"] = kwargs.pop("supervisor")
    else:
      # Ensure independent users are never supervisors
      user_row["supervisor"] = False

    # Update any remaining simple fields
    for key, value in kwargs.items():
      if key not in ["email", "structure", "supervisor"]:  # Protect critical fields
        user_row[key] = value

    logger.info(f"Successfully updated user '{user_row['email']}'.")
    return True
  except Exception as e:
    logger.error(
      f"ERROR: Failed to execute admin_update_user for ID {user_id}: {e}", exc_info=True
    )
    return False
