import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def read_animals():
  current_user = anvil.users.get_user()
  print(f"Reading animals for user: {current_user}")

  animals = app_tables.animals.search(vet=current_user)
  print(f"Found {len(animals)} animals")

  result = []
  for animal in animals:
    animal_dict = {
        'type': animal['type'],
        'name': animal['name'],
        'proprietaire': animal['proprietaire'],
        'vet': animal['vet']
    }
    print(f"Processing animal: {animal_dict['name']}")
    result.append(animal_dict)

  print(f"Returning {len(result)} animals")
  return result

@anvil.server.callable
def write_animal(name, type=None, proprietaire=None):
  current_user = anvil.users.get_user()
  print(f"Writing animal '{name}' for user: {current_user}")

  animal_row = app_tables.animals.get(name=name, vet=current_user)
  print(f"Existing animal found: {animal_row is not None}")

  if animal_row is None:
    print("Creating new animal record")

    # 1. Search all rows sorted by unique_id descending
    search_result = app_tables.animals.search(
        tables.order_by("unique_id", ascending=False)
    )
    # 2. Convert to a list so we can index or check length
    search_result = list(search_result)

    # 3. Find the largest unique_id if any rows exist
    if len(search_result) > 0:
      highest_unique_id = search_result[0]['unique_id']
    else:
      highest_unique_id = 0

    # 4. Increment for the new row
    new_unique_id = highest_unique_id + 1

    # 5. Create the new row with that unique_id
    animal_row = app_tables.animals.add_row(
        name=name,
        vet=current_user,
        unique_id=new_unique_id
    )
    print(f"Assigned unique_id = {new_unique_id}")

  # Update only provided fields
  updates = []
  if type is not None:
    animal_row['type'] = type
    updates.append('type')
  if proprietaire is not None:
    animal_row['proprietaire'] = proprietaire
    updates.append('proprietaire')

  print(f"Updated fields: {', '.join(updates)}")
  return True

@anvil.server.callable
def write_animal_first_time(name, type=None, proprietaire=None):
  current_user = anvil.users.get_user()
  print(f"Writing animal '{name}' for user: {current_user}")

  animal_row = app_tables.animals.get(name=name, vet=current_user)
  print(f"Existing animal found: {animal_row is not None}")

  if animal_row is None:
    print("Creating new animal record")

    # 1. Search all rows sorted by unique_id descending
    search_result = app_tables.animals.search(
        tables.order_by("unique_id", ascending=False)
    )
    # 2. Convert to a list so we can index or check length
    search_result = list(search_result)

    # 3. Find the largest unique_id if any rows exist
    if len(search_result) > 0:
      highest_unique_id = search_result[0]['unique_id']
    else:
      highest_unique_id = 0

    # 4. Increment for the new row
    new_unique_id = highest_unique_id + 1

    # 5. Create the new row with that unique_id
    animal_row = app_tables.animals.add_row(
        name=name,
        vet=current_user,
        unique_id=new_unique_id
    )
    print(f"Assigned unique_id = {new_unique_id}")

  # Update only provided fields
  updates = []
  if type is not None:
    animal_row['type'] = type
    updates.append('type')
  if proprietaire is not None:
    animal_row['proprietaire'] = proprietaire
    updates.append('proprietaire')

  print(f"Updated fields: {', '.join(updates)}")
  return new_unique_id

@anvil.server.callable
def pick_animal(nom, header):
  current_user = anvil.users.get_user()
  print(f"Picking '{header}' for animal '{nom}' (user: {current_user})")

  animal = app_tables.animals.get(name=nom, vet=current_user)
  print(f"Animal found: {animal is not None}")

  if animal is None:
    print("No animal found")
    return None

  if header in animal:
    value = animal[header]
    print(f"Returning value: {value}")
    return value
  else:
    print(f"Header '{header}' not found")
    return None


"""
# To read all animals for the current veterinarian
animals = anvil.server.call('read_animals')

# To write or update an animal's information
anvil.server.call('write_animal', 'Bella', espece='Dog', age=5, proprietaire='Jane Doe', informations='Friendly')

# To pick a specific value from an animal's information
owner = anvil.server.call('pick_animal', 'Bella', 'proprietaire')
"""
