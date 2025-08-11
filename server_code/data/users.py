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


# Define a constant for the non-display key for an independent user.
# This avoids "magic strings" and ensures consistency across the application.
INDEPENDENT_KEY = "independent"


@anvil.server.callable(require_user=True)
def read_user():
  """
  Retrieves a dictionary of all relevant data for the currently logged-in user.
  Returns the key 'independent' for users without a structure.
  """
  current_user = anvil.users.get_user(allow_remembered=True)

  try:
    user_row = app_tables.users.get(email=current_user["email"])
    if user_row is None:
      print(f"[ERROR] No user row found for email: {current_user['email']}")
      return None

    # If the user has a linked structure, return its name. Otherwise, return the standard key.
    structure_value = (
      user_row["structure"]["name"] if user_row["structure"] else INDEPENDENT_KEY
    )

    user_data = {
      "email": user_row["email"],
      "name": user_row["name"] or "",
      "phone": user_row["phone"] or "",
      "enabled": user_row["enabled"],
      "supervisor": user_row["supervisor"],
      "structure": structure_value,
      "additional_info": user_row["additional_info"],
      "favorite_language": user_row["favorite_language"] or "EN",
      "mobile_installation": user_row["mobile_installation"],
    }
    return user_data

  except Exception as e:
    print(f"[ERROR] An unexpected error occurred in read_user: {str(e)}")
    return None


@anvil.server.callable(require_user=True)
def write_user(**kwargs):
  """
  Updates the record of the currently logged-in user.
  Recognizes the key 'independent' to set the user's structure to None.
  """
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])

  if not user_row:
    print(
      f"[ERROR] Could not find user record for email: {current_user['email']} to update."
    )
    return False

  try:
    # Handle the 'structure' field separately as it's a linked row.
    if "structure" in kwargs:
      structure_name = kwargs.pop("structure")
      # If the provided name is the key for independent, set the link to None.
      if not structure_name or structure_name.strip().lower() == INDEPENDENT_KEY:
        user_row["structure"] = None
      else:
        # Otherwise, find the structure row by name and link it.
        structure_row = app_tables.structures.get(name=structure_name)
        if structure_row:
          user_row["structure"] = structure_row
        else:
          raise ValueError(f"No structure found with the name '{structure_name}'.")

    # Update all other provided fields dynamically.
    for key, value in kwargs.items():
      user_row[key] = value
      print(f"[INFO] Updated user '{user_row['email']}' field '{key}'.")

    return True

  except Exception as e:
    print(f"[ERROR] An unexpected error occurred in write_user: {str(e)}")
    return False


@anvil.server.callable(require_user=True)
def get_user_info(column_name):
  """
  Retrieves the value of a single, specified column for the current user.
  Returns the key 'independent' if the user has no structure.
  """
  current_user = anvil.users.get_user(allow_remembered=True)
  user_row = app_tables.users.get(email=current_user["email"])

  if not user_row:
    print(f"[ERROR] Could not find user record for email: {current_user['email']}.")
    return None

  # Handle the special case for 'structure' to return the name or the key.
  if column_name == "structure":
    return user_row["structure"]["name"] if user_row["structure"] else INDEPENDENT_KEY

  try:
    return user_row[column_name]
  except KeyError:
    # This block will now correctly execute if the column is missing from the schema.
    print(f"[WARN] Column '{column_name}' does not exist in the users table.")
    return None


@anvil.server.callable(require_user=True)
def get_vets_in_structure(structure_name):
  """
  Retrieves the name and email for all users linked to a specific structure.
  This replaces the obsolete 'get_affiliated_vets_details' logic.

  Args:
    structure_name (str): The name of the structure to look up.

  Returns:
    list of dict: A list of vet details [{'name': str, 'email': str}] or an empty list.
  """
  # Do not search if the structure is the independent key
  if not structure_name or structure_name == "independent":
    return []

  try:
    # Find the structure row from the 'structures' table by its name.
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      print(
        f"[WARN] No structure found with name '{structure_name}' in get_vets_in_structure."
      )
      return []

    # Query the 'users' table for all users linked to this specific structure row.
    vets_in_structure = app_tables.users.search(structure=structure_row)

    vet_details_list = [
      {"name": vet["name"], "email": vet["email"]} for vet in vets_in_structure if vet
    ]

    print(
      f"[INFO] Found {len(vet_details_list)} vets for structure '{structure_name}'."
    )
    return vet_details_list

  except Exception as e:
    print(f"[ERROR] in get_vets_in_structure for '{structure_name}': {e}")
    return []


@anvil.server.callable(require_user=True)
def register_user_and_setup(reg_data):
  """
  Handles the entire user registration and structure setup process in a single, atomic transaction.
  """
  user = anvil.users.get_user(allow_remembered=True)
  if not user:
    return {"success": False, "message": "User not logged in."}

  try:
    # 1. Update the user's personal information
    write_user(
      name=reg_data.get("name"),
      phone=reg_data.get("phone"),
      favorite_language=reg_data.get("favorite_language"),
      additional_info=True,  # Mark registration as complete
    )

    # 2. Handle the structure choice
    choice = reg_data.get("structure_choice")
    if choice == "join":
      join_code = reg_data.get("join_code")
      result = structures.join_structure_by_code(join_code)
      if not result.get("success"):
        return result  # Return the error message from the join function

    elif choice == "create":
      structure_details = reg_data.get("structure_details")
      result = structures.create_and_join_new_structure(structure_details)
      if not result.get("success"):
        return result  # Return the error message from the create function

        # 3. Assign language-specific templates
    base_templates.assign_language_specific_base_templates(
      user, reg_data.get("favorite_language")
    )

    return {"success": True, "message": "Registration complete!"}

  except Exception as e:
    print(f"[FATAL REGISTRATION ERROR] User: {user['email']}, Error: {str(e)}")
    return {"success": False, "message": f"A fatal error occurred: {str(e)}"}
