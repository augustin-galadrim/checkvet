import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

@anvil.server.callable
def add_authorized_vet(structure_id_unused, user_email):
  """
  Adds the user with user_email as an authorized veterinarian to the current user's
  structure. The structure is determined by retrieving the 'structure' value from
  the current user's record in the users table.

  Only the supervisor of the structure is allowed to perform this action.
  """

  print("Starting add_authorized_vet...")
  print("User email to add:", user_email)

  # Validate that user_email is a string.
  if not isinstance(user_email, str):
    msg = f"Expected user_email to be a string but got {user_email} (type {type(user_email)})."
    print("Error:", msg)
    raise Exception(msg)

  # Get the current user (supervisor)
  supervisor = anvil.users.get_user()
  print('tentative de recup des droits')
  print(supervisor['supervisor'])
  print("Retrieved supervisor:", supervisor)
  if not supervisor:
    print("Error: User not logged in.")
    raise Exception("User not logged in.")

  # Retrieve the current user's record from the users table using the supervisor's email.
  current_users = list(app_tables.users.search(email=supervisor['email']))
  print("Current user search results:", current_users)
  if not current_users:
    print("Error: Current user record not found.")
    raise Exception("Current user record not found.")
  current_user = current_users[0]

  # Retrieve the structure row from the current user's record.
  structure_row = current_user['structure']
  print("Structure row from current user record:", structure_row)
  if not structure_row:
    print("Error: No structure found for the current user.")
    raise Exception("No structure found for the current user.")

  # Extract the structure's name from the structure row using dictionary indexing.
  try:
    structure_name = structure_row['name']
  except Exception as e:
    print("Error: Structure name not found in the current user's record.", e)
    raise Exception("Structure name not found in the current user's record.")
  print("Extracted structure name:", structure_name)

  # Search for the structure record in the structures table using the extracted name.
  structures = list(app_tables.structures.search(name=structure_name))
  print("Search result for structure:", structures)
  if not structures:
    print("Error: Structure not found.")
    raise Exception("Structure not found.")
  structure = structures[0]
  print("Structure record found:", structure)

  # Retrieve the target user (new veterinarian) from the users table using email.
  new_vet_search = list(app_tables.users.search(email=user_email))
  print("Search result for new veterinarian:", new_vet_search)
  if not new_vet_search:
    msg = f"Error: User to add not found. Verify that the email exists in the Users table: {user_email}"
    print(msg)
    raise Exception(msg)
  new_vet = new_vet_search[0]
  print("New veterinarian record found:", new_vet)

  # Verify that the current user is allowed to modify the structure.
  print('tentative de recup des droits juste avant la vérification')
  print(supervisor['supervisor'])
  if not supervisor['supervisor']:
    print("Error: Not authorized to modify this structure.")
    raise Exception("Not authorized to modify this structure.")
  print("Authorization check passed for supervisor.")

  # Retrieve the current list of authorized veterinarians.
  if "authorized_vets" in structure and structure["authorized_vets"] is not None:
    current_vets = structure["authorized_vets"]
    print("Current authorized vets:", current_vets)
  else:
    current_vets = []
    print("No authorized vets found. Initializing empty list.")

  # Check if the new vet is already authorized.
  if new_vet in current_vets:
    print("User is already authorized as a vet.")
    return "User already authorized."

  # Add the new vet and update the structure record.
  current_vets.append(new_vet)
  structure["authorized_vets"] = current_vets
  print("Updated authorized vets:", structure["authorized_vets"])

  print("User successfully added as an authorized vet.")
  return "User successfully added."





@anvil.server.callable
def check_vet_authorization(structure_name):
  # Get the current user
  current_user = anvil.users.get_user()
  if not current_user:
    return False

  # Search for the structure row (assuming the table column is named 'structure')
  rows = list(app_tables.structures.search(name=structure_name))
  if not rows:
    return False

  structure_row = rows[0]

  # Use dictionary indexing to retrieve the 'authorized_vets' column
  authorized_vets = structure_row['authorized_vets']
  return current_user in authorized_vets
