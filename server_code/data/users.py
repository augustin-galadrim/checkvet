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


# ======================= NEW CORE LOGIC =======================
def _is_user_independent(user_row):
  """
  Checks if a user is independent.

  Domain Logic: An independent user is defined as a user who is the owner
  of the structure they belong to. This provides a single, reliable source of truth
  and supports the "personal structure" model.
  """
  if not user_row or not user_row["structure"]:
    return False

  # The user is independent if their structure's owner is the user themselves.
  return user_row["structure"]["owner"] == user_row


# =============================================================


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
def admin_create_user(
  email, name, phone=None, supervisor=False, favorite_language="en", structure_name=None
):
  """Admin function to create a new user."""
  logger.info(f"Admin request to create user: Email='{email}'")
  if not email or not name:
    logger.error("admin_create_user failed: Email and name are required.")
    raise ValueError("Email and name are required.")
  if app_tables.users.get(email=email):
    logger.warning(f"User with email '{email}' already exists. Creation aborted.")
    raise ValueError(f"A user with the email '{email}' already exists.")

  logger.info(f"Creating new user: {email}")

  structure_row = None
  if structure_name and structure_name.lower() != INDEPENDENT_KEY:
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      logger.error(f"admin_create_user failed: Structure '{structure_name}' not found.")
      raise ValueError(f"Structure '{structure_name}' not found.")

  user_data = {
    "email": email,
    "name": name,
    "phone": phone,
    "enabled": True,
    "confirmed_email": True,
    "supervisor": supervisor,
    "additional_info": True,
    "favorite_language": favorite_language,
    "structure": structure_row,
  }

  new_user = app_tables.users.add_row(**user_data)

  # Assign all base templates to the new user
  base_templates.assign_all_base_templates(new_user)

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

  update_dict = {}

  if "structure" in kwargs:
    structure_name = kwargs.pop("structure")
    if not structure_name or structure_name.lower() == INDEPENDENT_KEY:
      update_dict["structure"] = None
      logger.debug(f"Set user '{user_row['email']}' structure to None (Independent).")
    else:
      structure_row = app_tables.structures.get(name=structure_name)
      if not structure_row:
        logger.error(
          f"admin_update_user failed: Structure '{structure_name}' not found."
        )
        raise ValueError(f"Structure '{structure_name}' not found.")
      update_dict["structure"] = structure_row
      logger.debug(
        f"Linked user '{user_row['email']}' to structure '{structure_name}'."
      )

  # Add remaining kwargs to the update dictionary
  for key, value in kwargs.items():
    update_dict[key] = value

  # Perform a single update operation
  if update_dict:
    user_row.update(**update_dict)
    logger.info(
      f"Successfully updated user ID '{user_id}' with fields: {list(update_dict.keys())}."
    )
  else:
    logger.info(f"No fields to update for user ID '{user_id}'.")

  return True


@admin_required
@anvil.server.callable
def admin_add_vet_to_structure(structure_name, vet_email):
  """Admin function to add an existing user to a structure."""
  logger.info(
    f"Admin request to add user '{vet_email}' to structure '{structure_name}'."
  )

  if not structure_name or not vet_email:
    logger.error(
      "admin_add_vet_to_structure failed: Missing structure name or vet email."
    )
    return False

  structure_row = app_tables.structures.get(name=structure_name)
  if not structure_row:
    logger.error(
      f"admin_add_vet_to_structure failed: Structure '{structure_name}' not found."
    )
    return False

  user_to_add = app_tables.users.get(email=vet_email)
  if not user_to_add:
    logger.error(
      f"admin_add_vet_to_structure failed: User with email '{vet_email}' not found."
    )
    return False

  try:
    user_to_add["structure"] = structure_row
    logger.info(
      f"Successfully added user '{vet_email}' to structure '{structure_name}'."
    )
    return True
  except Exception as e:
    logger.error(
      f"Exception while adding user '{vet_email}' to structure '{structure_name}': {e}",
      exc_info=True,
    )
    return False


@admin_required
@anvil.server.callable
def admin_remove_vet_from_structure(user_id):
  """Admin function to remove a user from their current structure."""
  logger.info(f"Admin request to remove user ID '{user_id}' from their structure.")

  user_to_update = app_tables.users.get_by_id(user_id)
  if not user_to_update:
    logger.error(
      f"admin_remove_vet_from_structure failed: User with ID '{user_id}' not found."
    )
    return False

  try:
    user_to_update["structure"] = None
    logger.info(
      f"Successfully removed user '{user_to_update['email']}' from their structure."
    )
    return True
  except Exception as e:
    logger.error(
      f"Exception while removing user ID '{user_id}' from structure: {e}", exc_info=True
    )
    return False


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
  return [{"id": v.get_id(), "name": v["name"], "email": v["email"]} for v in vets if v]


@anvil.server.callable(require_user=True)
def register_user_and_setup(reg_data):
  """Handles the entire user registration and structure setup process."""
  user = anvil.users.get_user(allow_remembered=True)
  if not user:
    return {"success": False, "message": "User not logged in."}

  try:
    choice = reg_data.get("structure_choice")

    # Update user with basic info first
    user.update(
      name=reg_data.get("name"),
      phone=reg_data.get("phone"),
      favorite_language=reg_data.get("favorite_language"),
      additional_info=True,
      supervisor=(choice == "create"),
    )

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
    # ======================= MODIFIED LOGIC =======================
    elif choice == "independent":
      # Domain Logic: Create a personal, single-member structure for this user.
      # This ensures that every user in the system has a structure, simplifying
      # all downstream logic for asset management.
      logger.info(
        f"Registering independent user '{user['email']}'. Creating personal structure."
      )
      personal_structure_name = f"Practice of {user['name']}"

      # Check for name collision, though unlikely
      if app_tables.structures.get(name=personal_structure_name):
        personal_structure_name = f"Practice of {user['name']} ({user.get_id()[:4]})"

      new_structure = app_tables.structures.add_row(
        name=personal_structure_name,
        owner=user,
        join_code=structures._generate_unique_join_code(),
      )
      user["structure"] = new_structure
      logger.info(f"Personal structure '{new_structure['name']}' created and linked.")
    # =============================================================

    # Assign all base templates to the user, regardless of language
    base_templates.assign_all_base_templates(user)

    return {"success": True, "message": "Registration complete!"}
  except Exception as e:
    logger.error(
      f"FATAL REGISTRATION ERROR User: {user['email']}, Error: {e}", exc_info=True
    )
    return {"success": False, "message": f"A fatal error occurred: {e}"}


@admin_required
@anvil.server.callable
def migrate_independent_users_to_personal_structures():
  """
  A one-time migration script to find all users with no linked structure
  and create a personal structure for each of them.
  """
  logger.info("MIGRATION SCRIPT: Starting migration of independent users.")

  independent_users = app_tables.users.search(structure=None)

  migrated_count = 0
  skipped_count = 0

  users_to_migrate = list(independent_users)
  total_users = len(users_to_migrate)
  logger.info(f"MIGRATION SCRIPT: Found {total_users} user(s) to migrate.")

  for user_row in users_to_migrate:
    try:
      if user_row["structure"] is not None:
        logger.warning(
          f"MIGRATION SCRIPT: Skipping user '{user_row['email']}' as they already have a structure."
        )
        skipped_count += 1
        continue

      personal_structure_name = f"Practice of {user_row['name']}"

      if app_tables.structures.get(name=personal_structure_name):
        unique_id = user_row.get_id().split("-")[0]
        personal_structure_name = f"Practice of {user_row['name']} ({unique_id})"

      new_structure = app_tables.structures.add_row(
        name=personal_structure_name,
        owner=user_row,
        join_code=structures._generate_unique_join_code(),
      )

      user_row["structure"] = new_structure

      logger.info(
        f"MIGRATION SCRIPT: Successfully migrated user '{user_row['email']}'. Created structure '{new_structure['name']}'."
      )
      migrated_count += 1

    except Exception as e:
      logger.error(
        f"MIGRATION SCRIPT: FAILED to migrate user '{user_row['email']}'. Error: {e}",
        exc_info=True,
      )

  summary = f"MIGRATION SCRIPT: Finished. Migrated: {migrated_count}, Skipped: {skipped_count}, Total Found: {total_users}."
  logger.info(summary)
  return summary
