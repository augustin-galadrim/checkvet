import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime

@anvil.server.callable
def read_reports():
  current_user = anvil.users.get_user()
  print(f"Reading reports for user: {current_user}")

  reports = app_tables.reports.search(vet=current_user)
  print(f"Found {len(reports)} reports")

  result = []
  for report in reports:
    animal_row = report['animal']
    animal_name = animal_row['name'] if animal_row else None
    dt_str = report['last_modified'].strftime("%Y-%m-%d %H:%M:%S") if report['last_modified'] else None
    print(f"Processing report: {report['file_name']} (animal: {animal_name})")

    report_dict = {
        'file_name': report['file_name'],
        'name': animal_name,
        'vet': report['vet'],
        'last_modified': dt_str,
        'report_rich': report['report_rich'],
        'statut': report['statut'],
        'transcript': report['transcript']
    }
    result.append(report_dict)

  print(f"Returning {len(result)} reports")
  return result


############################################ WRITING LOGIC ##################################################

@anvil.server.callable
def write_report(file_name, animal_name=None, vet=None, last_modified=None, report_rich=None, statut=None):
  # Log the start of the function
  print(f"[DEBUG] Starting write_report with file_name={file_name}, "
        f"animal_name={animal_name}, vet={vet}, last_modified={last_modified}, "
        f"rapport_rich={report_rich}")

  # Get the current user
  current_user = anvil.users.get_user()
  print(f"[DEBUG] Current user: {current_user}")

  # Check if a report row already exists
  report_row = app_tables.reports.get(file_name=file_name, vet=current_user)
  print(f"[DEBUG] Existing report_row: {report_row}")

  # If no existing report, create a new one
  if report_row is None:
    print("[DEBUG] No existing report found. Creating a new row...")
    report_row = app_tables.reports.add_row(file_name=file_name, vet=current_user)
    print(f"[DEBUG] New report_row created: {report_row}")

  # Handle the animal field
  if animal_name is not None:
    print(f"[DEBUG] Attempting to find animal with name '{animal_name}'...")
    animal_row = app_tables.animals.get(name=animal_name)
    if animal_row is None:
      print(f"[ERROR] No animal found with name '{animal_name}'")
      raise ValueError(f"No animal found with name '{animal_name}'")
    print(f"[DEBUG] Found animal_row: {animal_row}")
    report_row['animal'] = animal_row
    print(f"[DEBUG] Updated report_row['animal']: {report_row['animal']}")

  # Update other fields if provided
  if last_modified is not None:
    print(f"[DEBUG] Updating last_modified to {last_modified}")
    report_row['last_modified'] = last_modified

  if report_rich is not None:
    print(f"[DEBUG] Updating rapport_text to {report_rich}")
    report_row['report_rich'] = report_rich

  if statut is not None:
    print(f"[DEBUG] Updating rapport_text to {statut}")
    report_row['statut'] = statut

  # Always update the last_modified field to the current server time
  current_time = datetime.now().date()  # Convert datetime to date
  report_row['last_modified'] = current_time
  print(f"[DEBUG] Updated report_row['last_modified'] to current server time: {current_time}")

  # Final state of the report_row
  print(f"[DEBUG] Final report_row: {report_row}")
  return True

@anvil.server.callable
def write_report_first_time(animal_name=None, vet=None, last_modified=None, report_rich=None, statut=None, unique_id=None, transcript=None):
  from datetime import datetime

  # Get the current date string for file name generation
  current_date_str = datetime.now().strftime("%Y%m%d")

  # Generate file_name by concatenating animal_name and the current date string.
  # If animal_name is None, use "unknown" as a placeholder.
  file_name_part = animal_name if animal_name is not None else "unknown"
  file_name = f"{file_name_part}_{current_date_str}"
  print(f"[DEBUG] Generated file_name: {file_name}")

  # Log the start of the function with the generated file_name
  print(f"[DEBUG] Starting write_report_first_time with generated file_name={file_name}, "
        f"animal_name={animal_name}, vet={vet}, last_modified={last_modified}, "
        f"report_rich={report_rich}, statut={statut}, unique_id={unique_id}")

  # Get the current user (we use this as the vet)
  current_user = anvil.users.get_user()
  print(f"[DEBUG] Current user: {current_user}")

  # Always create a new report row unconditionally with the generated file_name
  print("[DEBUG] Creating a new report row...")
  report_row = app_tables.reports.add_row(file_name=file_name, vet=current_user)
  print(f"[DEBUG] New report_row created: {report_row}")

  # Handle the animal field: find the animal by its name and assign it to the report row.
  if animal_name is not None:
    print(f"[DEBUG] Attempting to find animal with name '{animal_name}'...")
    print(f"[DEBUG] Received unique_id: {unique_id} (type: {type(unique_id)})")

    # If unique_id is a list or tuple, take the first element
    if isinstance(unique_id, (list, tuple)):
      print(f"[DEBUG] unique_id is a list/tuple: {unique_id}")
      unique_id = unique_id[0]
      print(f"[DEBUG] Using first element of unique_id: {unique_id} (type: {type(unique_id)})")

    # If unique_id is a string, attempt to convert it to int
    elif isinstance(unique_id, str):
      print(f"[DEBUG] unique_id is a string: '{unique_id}'")
      try:
        unique_id = int(unique_id)
        print(f"[DEBUG] Converted unique_id to int: {unique_id} (type: {type(unique_id)})")
      except Exception as e:
        print(f"[ERROR] Could not convert unique_id '{unique_id}' to int: {e}")

    print(f"[DEBUG] Final unique_id used for search: {unique_id} (type: {type(unique_id)})")
    animal_row = app_tables.animals.get(name=animal_name, unique_id=unique_id)
    if animal_row is None:
      print(f"[ERROR] No animal found with name '{animal_name}' and unique_id {unique_id}")
      raise ValueError(f"No animal found with name '{animal_name}'")
    print(f"[DEBUG] Found animal_row: {animal_row}")
    report_row['animal'] = animal_row
    print(f"[DEBUG] Updated report_row['animal']: {report_row['animal']}")

  # Update additional fields if provided.
  if last_modified is not None:
    print(f"[DEBUG] Updating last_modified to {last_modified}")
    report_row['last_modified'] = last_modified

  if report_rich is not None:
    print(f"[DEBUG] Updating report_rich to {report_rich}")
    report_row['report_rich'] = report_rich

  if statut is not None:
    print(f"[DEBUG] Updating statut to {statut}")
    report_row['statut'] = statut

  if transcript is not None:
    print(f"[DEBUG] Updating statut to {transcript}")
    report_row['transcript'] = transcript

  # Always update the last_modified field to the current server time.
  current_time = datetime.now().date()  # Converting to date if needed.
  report_row['last_modified'] = current_time
  print(f"[DEBUG] Updated report_row['last_modified'] to current server time: {current_time}")

  # Final state of the report_row for debugging.
  print(f"[DEBUG] Final report_row: {report_row}")
  return True






@anvil.server.callable
def pick_report(file_name, header):
  print(f"Picking '{header}' from report '{file_name}'")

  report = app_tables.reports.get(file_name=file_name)
  print(f"Report found: {report is not None}")

  if report is None:
    print("No report found")
    return None

  if header in report:
    if header == "animal":
      # Return the 'nom' value of the animal row
      animal_row = report['animal']
      print(f"Animal row exists: {animal_row is not None}")
      value = animal_row['nom'] if animal_row else None
      print(f"Returning animal name: {value}")
      return value

    value = report[header]
    print(f"Returning value: {value}")
    return value
  else:
    print(f"Header '{header}' not found")
    return None

"""
# To read all reports for the current vet
reports = anvil.server.call('read_reports')

# To write or update a report
anvil.server.call('write_report', 'report1.txt', animal='Dog', last_modified=datetime.now(), rapport_text='Detailed report')

# To pick a specific value from a report
rapport_text = anvil.server.call('pick_report', 'report1.txt', 'rapport_text')
"""


# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#


@anvil.server.callable
def delete_report(report_rich):
  # Log the start of the function
  print(f"[DEBUG] Starting delete_report with report_rich={report_rich}")

  # Get the current user
  current_user = anvil.users.get_user()
  print(f"[DEBUG] Current user: {current_user}")

  # Find the report with matching report_rich value and current user
  report_row = app_tables.reports.get(report_rich=report_rich, vet=current_user)
  print(f"[DEBUG] Found report_row: {report_row}")

  # Check if report exists
  if report_row is None:
    print(f"[ERROR] No report found with report_rich '{report_rich}'")
    raise ValueError(f"No report found with report_rich '{report_rich}'")

  # Delete the report
  report_row.delete()
  print(f"[DEBUG] Successfully deleted report with report_rich '{report_rich}'")

  return True
