import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime


@anvil.server.callable
def read_structures():
  current_user = anvil.users.get_user()
  print(f"Reading cliniques for user: {current_user}")

  structures = app_tables.structures.search(owner=current_user)
  print(f"Found {len(structures)} structure")

  result = []
  for structure in structures:
    print(f"Processing structure: {structure['name']}")
    structure_dict = {
        'structure': structure['name'],
        'phone': structure['phone'],  # This will return a list of user rows
        'email': structure['email'],
        'affiliated_vets': structure['affiliated_vets'],
        'authorized_vets': structure['authorized_vets'],
        'owner': structure['owner']
    }
    print(f"Number of vets in clinique: {len(structure['affiliated_vets']) if structure['affiliated_vets'] else 0}")
    result.append(structure_dict)

  print(f"Returning {len(result)} structures")
  return result

@anvil.server.callable
def write_structure(name=None, phone=None, email=None, address=None, affiliated_vets=None):
  current_user = anvil.users.get_user()
  print(f"Writing structure '{name}' for user: {current_user}")

  # Search for clinique rows where the current user is the owner
  structure_row = app_tables.structures.get(name=name, owner=current_user)
  print(f"Existing structure found: {structure_row is not None}")

  if structure_row is None:
    print("Creating new clinique record")
    structure_row = app_tables.structures.add_row(name=name, owner=current_user)

  # Update only the fields that were provided
  updates = []
  if phone is not None:
    structure_row['phone'] = phone
    updates.append('phone')
  if email is not None:
    structure_row['email'] = email
    updates.append('email')
  if address is not None:
    structure_row['address'] = address
    updates.append('address')
  if affiliated_vets is not None:
    structure_row['affiliated_vets'] = affiliated_vets
    updates.append('affiliated_vets')

  print(f"Updated fields: {', '.join(updates)}")
  return True

@anvil.server.callable
def pick_structure(structure_name, header):
  current_user = anvil.users.get_user()
  print(f"Picking '{header}' from structure '{structure_name}' (user: {current_user})")

  # Fetch row from the 'structures' table
  structure = app_tables.structures.get(name=structure_name)
  print(f"Structure found: {structure is not None}")
  print('test')
  print(structure['affiliated_vets'])
  # Assuming structure['affiliated_vets'] contains a list of Anvil Row objects
  list_of_dicts = [dict(row) for row in structure['affiliated_vets']]
  # Assuming `list_of_dicts` is already defined and contains the list of dictionaries
  names_list = [d['name'] for d in list_of_dicts if 'name' in d]
  #print(names_list)
  # Output the result
  return names_list




"""
# To read all cliniques for the current user (as owner)
cliniques = anvil.server.call('read_structures')

# To write or update a clinique's information
anvil.server.call('write_structure', 'VetCare Clinic', phone='123456789', email='contact@vetcare.com')

# To pick a specific value from a clinique's information
email = anvil.server.call('pick_structure', 'VetCare Clinic', 'email')
"""
