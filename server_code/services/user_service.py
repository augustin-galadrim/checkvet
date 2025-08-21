import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from ..logging_server import get_logger

logger = get_logger(__name__)

#################### CONFIRMATION EMAIL SECTION #################


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


#################### CUSTOM PDF SECTION #################


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
  """Update a user by ID with the provided fields"""
  try:
    user_row = app_tables.users.get_by_id(user_id)
    if not user_row:
      print(f"DEBUG: No user found with ID {user_id}")
      return False

      # Handle structure separately
    if "structure" in kwargs:
      structure_value = kwargs.pop("structure")
      if structure_value and structure_value != "Indépendant":
        # Set to a structure row
        structure_row = app_tables.structures.get(name=structure_value)
        if structure_row:
          user_row["structure"] = structure_row
        else:
          print(f"DEBUG: Structure not found: {structure_value}")
          return False
      else:
        # For "Indépendant", set structure to None
        user_row["structure"] = None

        # Update all other fields
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
