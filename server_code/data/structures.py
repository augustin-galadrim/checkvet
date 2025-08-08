import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import random
import string


def _generate_unique_join_code(length=6):
  """
  Generates a unique, random alphanumeric code to join a structure.

  Ensures the generated code is not already in use in the database.

  Args:
    length (int): The desired length of the code.

  Returns:
    str: A unique join code.
  """
  chars = string.ascii_uppercase + string.digits
  while True:
    join_code = "".join(random.choice(chars) for _ in range(length))
    # Check if this code already exists in the table.
    if not app_tables.structures.get(join_code=join_code):
      return join_code


@anvil.server.callable(require_user=True)
def create_and_join_new_structure(structure_details):
  """
  Creates a new structure, sets the current user as its owner,
  and automatically links the user to this new structure.

  Args:
    structure_details (dict): A dictionary containing the new structure's information,
                              e.g., {'name': 'My Vet Clinic', 'phone': '12345', 'email': 'contact@vet.com'}.

  Returns:
    dict: A dictionary indicating success and containing the new structure's details.
  """
  user = anvil.users.get_user(allow_remembered=True)

  # Validate input
  if not isinstance(structure_details, dict) or not structure_details.get("name"):
    raise anvil.server.NoServerFunctionError(
      "Valid structure details, including a name, must be provided."
    )

  structure_name = structure_details["name"]

  # Prevent duplicate structure names
  if app_tables.structures.get(name=structure_name):
    return {
      "success": False,
      "message": f"A structure with the name '{structure_name}' already exists.",
    }

  print(
    f"[INFO] User '{user['email']}' is creating a new structure: '{structure_name}'."
  )

  try:
    # Generate a unique code for this new structure
    new_join_code = _generate_unique_join_code()

    # Create the new row in the 'structures' table
    new_structure = app_tables.structures.add_row(
      name=structure_name,
      phone=structure_details.get("phone"),
      email=structure_details.get("email"),
      address=structure_details.get("address"),
      owner=user,
      join_code=new_join_code,
    )

    # Automatically link the creator's user record to this new structure
    user["structure"] = new_structure

    print(
      f"[SUCCESS] Structure '{structure_name}' created with join code '{new_join_code}'."
    )

    return {
      "success": True,
      "message": "Structure created and joined successfully.",
      "structure_name": new_structure["name"],
      "join_code": new_structure["join_code"],
    }

  except Exception as e:
    print(
      f"[ERROR] Failed to create new structure for user '{user['email']}': {str(e)}"
    )
    return {
      "success": False,
      "message": "An unexpected error occurred while creating the structure.",
    }


@anvil.server.callable(require_user=True)
def join_structure_by_code(join_code):
  """
  Links a user to an existing structure using a unique join code.

  Args:
    join_code (str): The unique code for the structure the user wants to join.

  Returns:
    dict: A dictionary indicating success or failure and providing a user-friendly message.
  """
  user = anvil.users.get_user(allow_remembered=True)

  # Validate input
  if not join_code or not isinstance(join_code, str):
    return {"success": False, "message": "A valid join code must be provided."}

  print(
    f"[INFO] User '{user['email']}' is attempting to join a structure with code: '{join_code}'."
  )

  try:
    # Find the structure that corresponds to the provided join code.
    structure_to_join = app_tables.structures.get(join_code=join_code.upper())

    if not structure_to_join:
      print(f"[FAIL] No structure found with join code '{join_code}'.")
      return {
        "success": False,
        "message": "Invalid join code. Please check the code and try again.",
      }

    # If a structure is found, update the user's 'structure' column to link them to it.
    user["structure"] = structure_to_join

    structure_name = structure_to_join["name"]
    print(
      f"[SUCCESS] User '{user['email']}' has successfully joined structure '{structure_name}'."
    )

    return {
      "success": True,
      "message": f"You have successfully joined the structure: {structure_name}.",
      "structure_name": structure_name,
    }

  except Exception as e:
    print(
      f"[ERROR] An error occurred while user '{user['email']}' attempted to join with code '{join_code}': {str(e)}"
    )
    return {
      "success": False,
      "message": "An unexpected error occurred. Please try again later.",
    }
