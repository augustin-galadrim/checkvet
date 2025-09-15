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


def _is_user_independent(user_row):
  return user_row["structure"]["is_personal"] if user_row["structure"] else True


@anvil.server.callable(require_user=True)
def read_user():
  """
  Retrieves a dictionary of all relevant data for the currently logged-in user.
  This is the primary function for fetching user session information.
  """
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])
  if user_row is None:
    logger.error(f"No user row found for email: {current_user['email']}")
    return None

  is_independent = _is_user_independent(user_row)
  structure_name = user_row["structure"]["name"] if user_row["structure"] else None

  join_code = None
  # A user can only see a join code if they are a supervisor of a non-personal structure.
  if user_row["structure"] and user_row["supervisor"] and not is_independent:
    join_code = user_row["structure"]["join_code"]

  return {
    "email": user_row["email"],
    "name": user_row["name"],
    "phone": user_row["phone"],
    "enabled": user_row["enabled"],
    "supervisor": user_row["supervisor"],
    "structure": structure_name,
    "additional_info": user_row["additional_info"],
    "favorite_language": user_row["favorite_language"],
    "mobile_installation": user_row["mobile_installation"],
    "join_code": join_code,
    "is_independent": is_independent,
  }


@anvil.server.callable(require_user=True)
def join_structure_as_vet(join_code):
  """
  Allows a user to join a new structure. If the user is currently independent,
  this function archives their personal structure and branding assets before
  re-linking them to the new clinic.
  """
  user = anvil.users.get_user(allow_remembered=True)
  if not join_code or not isinstance(join_code, str):
    return {"success": False, "message": "A valid join code must be provided."}

  logger.info(
    f"User '{user['email']}' attempting to join structure with code: '{join_code}'."
  )

  target_structure = app_tables.structures.get(join_code=join_code.upper())
  if not target_structure:
    logger.warning(
      f"Join failed for user '{user['email']}': No structure found with code '{join_code}'."
    )
    return {"success": False, "message": "Invalid join code."}

  # Check if the user is currently independent.
  is_independent = _is_user_independent(user)

  if is_independent:
    # --- Archive & Re-link Workflow for Independent Users ---
    logger.info(
      f"User '{user['email']}' is independent. Archiving personal assets and structure."
    )
    personal_structure = user["structure"]

    if personal_structure:
      # 1. Archive all assets owned by the personal structure.
      personal_assets = app_tables.assets.search(owner_structure=personal_structure)
      for asset in personal_assets:
        asset["is_archived"] = True

      # 2. Archive the personal structure itself.
      personal_structure["is_archived"] = True
      logger.info(
        f"Archived personal structure '{personal_structure['name']}' and its assets."
      )

  # 3. Re-link the user to the new target structure.
  user["structure"] = target_structure
  user["supervisor"] = (
    False  # Users joining a structure are never supervisors by default.
  )

  structure_name = target_structure["name"]
  logger.info(f"User '{user['email']}' successfully joined '{structure_name}'.")
  return {"success": True, "message": f"Successfully joined {structure_name}."}


@anvil.server.callable(require_user=True)
def write_user(**kwargs):
  """
  Updates the record of the currently logged-in user for simple fields.
  Structure changes are handled by dedicated functions.
  """
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])
  if not user_row:
    return False

  # Prevent modification of critical fields like 'structure' through this general function.
  kwargs.pop("structure", None)
  kwargs.pop("email", None)

  for key, value in kwargs.items():
    user_row[key] = value
  return True


@anvil.server.callable(require_user=True)
def get_vets_in_structure(structure_name):
  """Retrieves the name and email for all users linked to a specific structure."""
  if not structure_name:
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
    elif choice == "independent":
      logger.info(
        f"Registering independent user '{user['email']}'. Creating personal structure."
      )
      personal_structure_name = f"Practice of {user['name']}"

      if app_tables.structures.get(name=personal_structure_name):
        personal_structure_name = f"Personal Structure - User ID: {user.get_id()}"

      new_structure = app_tables.structures.add_row(
        name=personal_structure_name, owner=user, is_personal=True
      )
      user["structure"] = new_structure
      logger.info(f"Personal structure '{new_structure['name']}' created and linked.")

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
  A one-time migration script to find all users with no linked structure,
  create a personal structure for each one, and set the 'is_personal' flag.
  """
  logger.info("MIGRATION SCRIPT: Starting migration of independent users.")

  # Find all users where the 'structure' column is empty (None)
  independent_users = app_tables.users.search(structure=None)

  migrated_count = 0
  skipped_count = 0

  users_to_migrate = list(independent_users)
  total_users = len(users_to_migrate)
  logger.info(f"MIGRATION SCRIPT: Found {total_users} user(s) to migrate.")

  for user_row in users_to_migrate:
    try:
      # Safety check: ensure we don't accidentally overwrite an existing link.
      if user_row["structure"] is not None:
        logger.warning(
          f"MIGRATION SCRIPT: Skipping user '{user_row['email']}' as they already have a structure."
        )
        skipped_count += 1
        continue

        # ======================= KEY CHANGES =======================
        # 1. Use a programmatic, unique name for the structure.
        # This makes it clear it's a system-managed entity.
      personal_structure_name = f"Personal Structure - User ID: {user_row.get_id()}"

      new_structure = app_tables.structures.add_row(
        name=personal_structure_name,
        owner=user_row,
        join_code=structures._generate_unique_join_code(),
        # 2. Set the new flag to True to identify this structure's purpose.
        is_personal=True,
      )
      # ==========================================================

      # Link the user to their new personal structure
      user_row["structure"] = new_structure

      logger.info(
        f"MIGRATION SCRIPT: Successfully migrated user '{user_row['email']}'. Created personal structure '{new_structure['name']}'."
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


@admin_required
@anvil.server.callable
def admin_get_all_users():
  """
  Admin function to retrieve a formatted list of all users for the admin panel.
  """
  logger.info("Admin request to get all users.")
  all_users = app_tables.users.search()

  result_list = []
  for user_row in all_users:
    is_independent = _is_user_independent(user_row)
    structure_name = (
      "Independent"
      if is_independent
      else (user_row["structure"]["name"] if user_row["structure"] else None)
    )

    result_list.append({
      "id": user_row.get_id(),
      "name": user_row["name"],
      "email": user_row["email"],
      "phone": user_row["phone"],
      "supervisor": user_row["supervisor"],
      "structure": structure_name,
      "is_independent": is_independent,
    })

  logger.info(f"Returning {len(result_list)} users to the admin panel.")
  return result_list
