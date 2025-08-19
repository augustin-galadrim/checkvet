import anvil.secrets
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
      "type": animal["type"],
      "name": animal["name"],
      "proprietaire": animal["proprietaire"],
      "vet": animal["vet"],
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
    animal_row = app_tables.animals.add_row(name=name, vet=current_user)

  # Update only provided fields
  updates = []
  if type is not None:
    animal_row["type"] = type
    updates.append("type")
  if proprietaire is not None:
    animal_row["proprietaire"] = proprietaire
    updates.append("proprietaire")

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
    animal_row = app_tables.animals.add_row(
      name=name,
      vet=current_user,
    )

  # Update only provided fields
  updates = []
  if type is not None:
    animal_row["type"] = type
    updates.append("type")
  if proprietaire is not None:
    animal_row["proprietaire"] = proprietaire
    updates.append("proprietaire")

  print(f"Updated fields: {', '.join(updates)}")
  # Return the new row's Anvil ID
  return animal_row.get_id()


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


@anvil.server.callable
def get_my_patients_for_filtering():
  """
  Retrieves a simple list of patient names and IDs for the current user.
  Used to populate filter dropdowns/modals.
  """
  current_user = anvil.users.get_user()
  if not current_user:
    return []

    # Fetch all animals for the current vet, ordered by name
  patient_rows = app_tables.animals.search(
    tables.order_by("name", ascending=True), vet=current_user
  )

  # Return a list of simple dictionaries containing the Row ID and name
  return [{"id": p.get_id(), "name": p["name"]} for p in patient_rows]
