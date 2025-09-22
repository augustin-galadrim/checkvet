import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from ..logging_server import get_logger

logger = get_logger(__name__)


@anvil.server.callable
def leg_read_reports():
  current_user = anvil.users.get_user()
  reports = app_tables.reports.search(
    tables.order_by("last_modified", ascending=False), vet=current_user
  )

  result = []
  for report in reports:
    animal_row = report["animal"]
    animal_name = animal_row["name"] if animal_row else None
    # --- MODIFIED: Add the animal's Row ID for client-side filtering ---
    animal_id = animal_row.get_id() if animal_row else None

    dt_str = (
      report["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
      if report["last_modified"]
      else None
    )

    report_dict = {
      "id": report.get_id(),
      "file_name": report["file_name"],
      "name": animal_name,
      "animal_id": animal_id,  # <-- ADDED
      "vet": report["vet"],
      "last_modified": dt_str,
      "report_rich": report["report_rich"],
      "statut": report["statut"],
      "transcript": report["transcript"],
    }
    result.append(report_dict)

  return result


@anvil.server.callable
def leg_write_report(
  file_name,
  animal_name=None,
  vet=None,
  last_modified=None,
  report_rich=None,
  statut=None,
):
  # Log the start of the function
  print(
    f"[DEBUG] Starting write_report with file_name={file_name}, "
    f"animal_name={animal_name}, vet={vet}, last_modified={last_modified}, "
    f"rapport_rich={report_rich}"
  )

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
    report_row["animal"] = animal_row
    print(f"[DEBUG] Updated report_row['animal']: {report_row['animal']}")

  # Update other fields if provided
  if last_modified is not None:
    print(f"[DEBUG] Updating last_modified to {last_modified}")
    report_row["last_modified"] = last_modified

  if report_rich is not None:
    print(f"[DEBUG] Updating rapport_text to {report_rich}")
    report_row["report_rich"] = report_rich

  if statut is not None:
    print(f"[DEBUG] Updating rapport_text to {statut}")
    report_row["statut"] = statut

  # Always update the last_modified field to the current server time
  current_time = datetime.now().date()  # Convert datetime to date
  report_row["last_modified"] = current_time
  print(
    f"[DEBUG] Updated report_row['last_modified'] to current server time: {current_time}"
  )

  # Final state of the report_row
  print(f"[DEBUG] Final report_row: {report_row}")
  return True


@anvil.server.callable
def leg_write_report_first_time(
  animal_name=None,
  vet=None,
  last_modified=None,
  report_rich=None,
  statut=None,
  animal_id=None,
  transcript=None,
  language=None,
):
  # Get the current date string for file name generation
  current_date_str = datetime.now().strftime("%Y%m%d")

  # Generate file_name by concatenating animal_name and the current date string.
  # If animal_name is None, use "unknown" as a placeholder.
  file_name_part = animal_name if animal_name is not None else "unknown"
  file_name = f"{file_name_part}_{current_date_str}"
  print(f"[DEBUG] Generated file_name: {file_name}")

  # Log the start of the function with the generated file_name
  print(
    f"[DEBUG] Starting write_report_first_time with generated file_name={file_name}, "
    f"animal_name={animal_name}, vet={vet}, last_modified={last_modified}, "
    f"report_rich={report_rich}, statut={statut}, animal_id={animal_id}"
  )

  # Get the current user (we use this as the vet)
  current_user = anvil.users.get_user()
  print(f"[DEBUG] Current user: {current_user}")

  # Always create a new report row unconditionally with the generated file_name
  print("[DEBUG] Creating a new report row...")
  report_row = app_tables.reports.add_row(file_name=file_name, vet=current_user)
  print(f"[DEBUG] New report_row created: {report_row}")

  # Handle the animal field: find the animal by its Anvil ID and assign it to the report row.
  if animal_id is not None:
    print(f"[DEBUG] Attempting to find animal with id '{animal_id}'...")

    animal_row = app_tables.animals.get_by_id(animal_id)
    if animal_row is None:
      print(f"[ERROR] No animal found with id '{animal_id}'")
      raise ValueError(f"No animal found with id '{animal_id}'")
    print(f"[DEBUG] Found animal_row: {animal_row}")
    report_row["animal"] = animal_row
    print(f"[DEBUG] Updated report_row['animal']: {report_row['animal']}")

  # Update additional fields if provided.
  if last_modified is not None:
    print(f"[DEBUG] Updating last_modified to {last_modified}")
    report_row["last_modified"] = last_modified

  if report_rich is not None:
    print(f"[DEBUG] Updating report_rich to {report_rich}")
    report_row["report_rich"] = report_rich

  if statut is not None:
    print(f"[DEBUG] Updating statut to {statut}")
    report_row["statut"] = statut

  if transcript is not None:
    print(f"[DEBUG] Updating transcript to {transcript}")
    report_row["transcript"] = transcript

  if language is not None:
    report_row["language"] = language

  # Always update the last_modified field to the current server time.
  current_time = datetime.now().date()  # Converting to date if needed.
  report_row["last_modified"] = current_time
  print(
    f"[DEBUG] Updated report_row['last_modified'] to current server time: {current_time}"
  )

  # Final state of the report_row for debugging.
  print(f"[DEBUG] Final report_row: {report_row}")
  return True


@anvil.server.callable
def leg_delete_report(
  report_id,
):
  print(f"[DEBUG] Starting delete_report with report_id={report_id}")
  current_user = anvil.users.get_user()

  report_row = app_tables.reports.get_by_id(report_id)

  if report_row is None or report_row["vet"] != current_user:
    print(
      f"[ERROR] No report found with id '{report_id}' for user {current_user['email']}"
    )
    return False

  report_row.delete()
  print(f"[DEBUG] Successfully deleted report with id '{report_id}'")

  return True


@anvil.server.callable(require_user=True)
def leg_update_report(report_id, new_html_content, new_status):
  """
  Updates the content and status of a specific, existing report.
  This is the dedicated function for saving edits from AudioManagerEdit.
  """
  print(f"[INFO] Attempting to update report with ID: {report_id}")
  current_user = anvil.users.get_user()

  report_row = app_tables.reports.get_by_id(report_id)

  if not report_row:
    logger.warning(f"[SECURITY] Edit failed. Report ID '{report_id}' not found.")
    return False

  report_owner = report_row["vet"]

  is_author = report_owner == current_user

  is_supervisor_in_structure = False
  if current_user["supervisor"] and report_owner["structure"]:
    if current_user["structure"] == report_owner["structure"]:
      is_supervisor_in_structure = True

  if not (is_author or is_supervisor_in_structure):
    logger.error(
      f"[SECURITY] User '{current_user['email']}' attempted to edit report ID '{report_id}' without permission."
    )
    return False

  try:
    report_row.update(
      report_rich=new_html_content,
      statut=new_status,
      last_modified=datetime.now().date(),
    )
    print(f"[SUCCESS] Report ID '{report_id}' was updated successfully.")
    return True
  except Exception as e:
    print(
      f"[ERROR] An unexpected error occurred while updating report ID '{report_id}': {e}"
    )
    return False
