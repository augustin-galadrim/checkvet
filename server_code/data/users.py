import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

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
      "signature_image": user_row["signature_image"],
      "report_header_image": user_row["report_header_image"],
      "report_footer_image": user_row["report_footer_image"],
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
      if key in user_row:
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

  if column_name in user_row:
    return user_row[column_name]
  else:
    print(f"[WARN] Column '{column_name}' does not exist in the users table.")
    return None
