import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from ..data import (
  structures,
  base_templates,
)
from ..logging_server import get_logger
from ..auth import admin_required

logger = get_logger(__name__)

INDEPENDENT_KEY = "independent"


@admin_required
@anvil.server.callable
def admin_get_all_users():
  """Admin function to retrieve all users."""
  logger.info("Admin request to get all users.")
  all_users = app_tables.users.search()
  result = [
    {
      "id": user.get_id(),
      "name": user["name"],
      "email": user["email"],
      "phone": user["phone"],
      "supervisor": user["supervisor"],
      "structure": user["structure"]["name"] if user["structure"] else INDEPENDENT_KEY,
      "favorite_language": user["favorite_language"],
    }
    for user in all_users
  ]
  logger.info(f"Returning {len(result)} users.")
  return result


@admin_required
@anvil.server.callable
def admin_create_user(email, name):
  """Admin function to create a new user."""
  logger.info(f"Admin request to create user: Email='{email}'")
  if not email or not name:
    logger.error("admin_create_user failed: Email and name are required.")
    raise ValueError("Email and name are required.")
  if app_tables.users.get(email=email):
    logger.warning(f"User with email '{email}' already exists. Creation aborted.")
    raise ValueError(f"A user with the email '{email}' already exists.")

  logger.info(f"Creating new user: {email}")
  new_user = app_tables.users.add_row(
    email=email,
    name=name,
    enabled=True,
    confirmed_email=True,
    supervisor=False,
    additional_info=True,
  )
  return new_user.get_id()


@admin_required
@anvil.server.callable
def admin_update_user(user_id, **kwargs):
  """Admin function to update a user by ID."""
  logger.info(f"Admin request to update user ID '{user_id}' with data: {kwargs}")
  user_row = app_tables.users.get_by_id(user_id)
  if not user_row:
    logger.error(f"admin_update_user failed: No user found with ID '{user_id}'.")
    raise ValueError(f"No user found with ID '{user_id}'.")

  if "structure" in kwargs:
    structure_name = kwargs.pop("structure")
    if not structure_name or structure_name.lower() == INDEPENDENT_KEY:
      user_row["structure"] = None
      logger.debug(f"Set user '{user_row['email']}' structure to None (Independent).")
    else:
      structure_row = app_tables.structures.get(name=structure_name)
      if not structure_row:
        logger.error(
          f"admin_update_user failed: Structure '{structure_name}' not found."
        )
        raise ValueError(f"Structure '{structure_name}' not found.")
      user_row["structure"] = structure_row
      logger.debug(
        f"Linked user '{user_row['email']}' to structure '{structure_name}'."
      )

  for key, value in kwargs.items():
    user_row[key] = value

  logger.info(f"Successfully updated user ID '{user_id}'.")
  return True


@anvil.server.callable(require_user=True)
def read_user():
  """Retrieves a dictionary of all relevant data for the currently logged-in user."""
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])
  if user_row is None:
    logger.error(f"No user row found for email: {current_user['email']}")
    return None

  structure_value = (
    user_row["structure"]["name"] if user_row["structure"] else INDEPENDENT_KEY
  )
  join_code = (
    user_row["structure"]["join_code"]
    if user_row["structure"] and user_row["supervisor"]
    else None
  )

  return {
    "email": user_row["email"],
    "name": user_row["name"],
    "phone": user_row["phone"],
    "enabled": user_row["enabled"],
    "supervisor": user_row["supervisor"],
    "structure": structure_value,
    "additional_info": user_row["additional_info"],
    "favorite_language": user_row["favorite_language"],
    "mobile_installation": user_row["mobile_installation"],
    "join_code": join_code,
  }


@anvil.server.callable(require_user=True)
def join_structure_as_vet(join_code):
  """Allows the current user to join a structure using a join code."""
  user = anvil.users.get_user(allow_remembered=True)
  result = structures.join_structure_by_code(join_code)
  if result.get("success"):
    user["supervisor"] = False
  return result


@anvil.server.callable(require_user=True)
def write_user(**kwargs):
  """Updates the record of the currently logged-in user."""
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])
  if not user_row:
    return False

  if "structure" in kwargs:
    structure_name = kwargs.pop("structure")
    if not structure_name or structure_name.strip().lower() == INDEPENDENT_KEY:
      user_row["structure"] = None
    else:
      structure_row = app_tables.structures.get(name=structure_name)
      if structure_row:
        user_row["structure"] = structure_row
      else:
        raise ValueError(f"No structure found with name '{structure_name}'.")

  for key, value in kwargs.items():
    user_row[key] = value
  return True


@anvil.server.callable(require_user=True)
def get_user_info(column_name):
  """
  MODIFIED: Retrieves a single column for the current user, now robustly handling missing user rows.
  """
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])

  if not user_row:
    logger.critical(
      f"CRITICAL: User '{current_user['email']}' is logged in but has no record in the 'users' table."
    )
    return None

  if column_name == "structure":
    return user_row["structure"]["name"] if user_row["structure"] else INDEPENDENT_KEY

  try:
    return user_row[column_name]
  except KeyError:
    logger.warning(f"Column '{column_name}' does not exist in the users table.")
    return None


@anvil.server.callable(require_user=True)
def get_vets_in_structure(structure_name):
  """Retrieves the name and email for all users linked to a specific structure."""
  if not structure_name or structure_name == "independent":
    return []
  structure_row = app_tables.structures.get(name=structure_name)
  if not structure_row:
    return []
  vets = app_tables.users.search(structure=structure_row)
  return [{"name": v["name"], "email": v["email"]} for v in vets if v]


@anvil.server.callable(require_user=True)
def register_user_and_setup(reg_data):
  """Handles the entire user registration and structure setup process."""
  user = anvil.users.get_user(allow_remembered=True)
  if not user:
    return {"success": False, "message": "User not logged in."}

  try:
    write_user(
      name=reg_data.get("name"),
      phone=reg_data.get("phone"),
      favorite_language=reg_data.get("favorite_language"),
      additional_info=True,
    )
    choice = reg_data.get("structure_choice")
    if choice == "join":
      result = structures.join_structure_by_code(reg_data.get("join_code"))
      if not result.get("success"):
        return result
    elif choice == "create":
      result = structures.create_and_join_new_structure(
        reg_data.get("structure_details")
      )
      if not result.get("success"):
        return result

    base_templates.assign_language_specific_base_templates(
      user, reg_data.get("favorite_language")
    )
    return {"success": True, "message": "Registration complete!"}
  except Exception as e:
    logger.error(
      f"FATAL REGISTRATION ERROR User: {user['email']}, Error: {e}", exc_info=True
    )
    return {"success": False, "message": f"A fatal error occurred: {e}"}
