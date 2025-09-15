import anvil.secrets
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
import random
import string
from ..logging_server import get_logger
from ..auth import admin_required

logger = get_logger(__name__)


def _generate_unique_join_code(length=6):
  """Generates a unique, random alphanumeric code to join a structure."""
  chars = string.ascii_uppercase + string.digits
  while True:
    join_code = "".join(random.choice(chars) for _ in range(length))
    if not app_tables.structures.get(join_code=join_code):
      return join_code


@anvil.server.callable(require_user=True)
def read_structures():
  """
  REFACTORED: Retrieves all non-personal structures and includes a count of affiliated vets.
  """
  logger.info("Reading all non-personal structures from the database for admin panel.")
  # This query now explicitly excludes personal structures from the results.
  all_structures = app_tables.structures.search(is_personal=False)
  result = []
  for structure_row in all_structures:
    try:
      vet_count = len(list(app_tables.users.search(structure=structure_row)))
      logger.debug(f"Found {vet_count} vets for structure '{structure_row['name']}'.")
    except Exception as e:
      logger.error(
        f"Could not count vets for structure '{structure_row['name']}': {e}",
        exc_info=True,
      )
      vet_count = 0

    structure_dict = {
      "id": structure_row.get_id(),
      "structure": structure_row["name"],
      "phone": structure_row["phone"],
      "email": structure_row["email"],
      "address": structure_row["address"],
      "affiliated_vets": vet_count,
    }
    result.append(structure_dict)
  logger.info(f"Returning {len(result)} non-personal structures.")
  return result


@admin_required
@anvil.server.callable
def admin_write_structure(structure_data):
  """Admin function to create or update a structure."""
  name = structure_data.get("name")
  structure_id = structure_data.get("id")
  logger.info(f"Admin request to write structure: ID='{structure_id}', Name='{name}'")
  if not name or not name.strip():
    logger.error("admin_write_structure failed: Structure name cannot be empty.")
    raise ValueError("Structure name cannot be empty.")

  try:
    if structure_id:
      structure_row = app_tables.structures.get_by_id(structure_id)
      if not structure_row:
        raise ValueError(f"Structure with ID '{structure_id}' not found.")
      logger.info(f"Updating existing structure: '{name}'")
      structure_row.update(
        name=name,
        phone=structure_data.get("phone"),
        email=structure_data.get("email"),
        address=structure_data.get("address"),
      )
    else:
      # Prevent creating a new structure if one with the same name already exists
      if app_tables.structures.get(name=name):
        raise ValueError(f"A structure with the name '{name}' already exists.")
      logger.info(f"Creating new structure: '{name}'")
      app_tables.structures.add_row(
        name=name,
        phone=structure_data.get("phone"),
        email=structure_data.get("email"),
        address=structure_data.get("address"),
        join_code=_generate_unique_join_code(),
      )
    logger.info(f"Successfully wrote structure '{name}'.")
    return True
  except Exception as e:
    logger.error(
      f"Exception in admin_write_structure for name '{name}': {e}", exc_info=True
    )
    raise


@anvil.server.callable(require_user=True)
def create_and_join_new_structure(structure_details):
  """Creates a new structure and links the current user to it."""
  user = anvil.users.get_user(allow_remembered=True)
  if not isinstance(structure_details, dict) or not structure_details.get("name"):
    logger.error(
      "create_and_join_new_structure call failed: invalid structure_details."
    )
    raise anvil.server.NoServerFunctionError(
      "Valid structure details, including a name, must be provided."
    )

  structure_name = structure_details["name"]
  logger.info(f"User '{user['email']}' is creating new structure: '{structure_name}'.")
  if app_tables.structures.get(name=structure_name):
    logger.warning(f"Structure '{structure_name}' already exists. Creation aborted.")
    return {
      "success": False,
      "message": f"A structure with the name '{structure_name}' already exists.",
    }

  try:
    new_join_code = _generate_unique_join_code()
    new_structure = app_tables.structures.add_row(
      name=structure_name,
      phone=structure_details.get("phone"),
      email=structure_details.get("email"),
      address=structure_details.get("address"),
      owner=user,
      join_code=new_join_code,
      is_personal=False,
    )
    user["structure"] = new_structure
    logger.info(
      f"Successfully created structure '{structure_name}' with code '{new_join_code}'."
    )
    return {"success": True, "message": "Structure created and joined successfully."}
  except Exception as e:
    logger.error(
      f"Failed to create new structure for user '{user['email']}': {e}", exc_info=True
    )
    return {"success": False, "message": "An unexpected error occurred."}


@anvil.server.callable(require_user=True)
def join_structure_by_code(join_code):
  """Links a user to a structure via a join code."""
  user = anvil.users.get_user(allow_remembered=True)
  if not join_code or not isinstance(join_code, str):
    return {"success": False, "message": "A valid join code must be provided."}

  logger.info(f"User '{user['email']}' attempting to join with code: '{join_code}'.")
  try:
    structure_to_join = app_tables.structures.get(join_code=join_code.upper())
    if not structure_to_join:
      logger.warning(f"Join failed: No structure found with code '{join_code}'.")
      return {"success": False, "message": "Invalid join code."}

    user["structure"] = structure_to_join
    structure_name = structure_to_join["name"]
    logger.info(f"User '{user['email']}' successfully joined '{structure_name}'.")
    return {"success": True, "message": f"Successfully joined {structure_name}."}
  except Exception as e:
    logger.error(
      f"Exception during join_structure_by_code for user '{user['email']}': {e}",
      exc_info=True,
    )
    return {"success": False, "message": "An unexpected error occurred."}
