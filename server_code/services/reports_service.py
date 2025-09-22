import anvil.secrets
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import json
import openai
from ..logging_server import get_logger

logger = get_logger(__name__)


@anvil.server.callable
def get_status_options():
  """
  Returns the list of valid, English-keyed report statuses.
  This acts as a single source of truth for the application.
  """
  return ["pending_correction", "validated", "sent", "not_specified"]


@anvil.server.callable
def get_user_reports():
  current_user = anvil.users.get_user()
  if not current_user:
    raise Exception("User not authenticated")

  reports = app_tables.reports.search(owner=current_user)

  # Log each row's fileName and report values
  for row in reports:
    print(f"DEBUG: Row: {row}, fileName: {row['fileName']}, report: {row['report']}")

  valid_reports = []
  for row in reports:
    file_name = row["fileName"] if row["fileName"] else "Unnamed Report"
    report_data = row["report"] if row["report"] else {}
    valid_reports.append({"fileName": file_name, "Report": report_data})

  return valid_reports


@anvil.server.callable
def get_reports_by_structure(structure_name):
  print(
    f"DEBUG: Entering get_reports_by_structure with structure_name='{structure_name}'"
  )
  try:
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      return []

    users_in_structure = app_tables.users.search(structure=structure_row)
    user_rows = list(users_in_structure)
    if not user_rows:
      return []

    reports_query = app_tables.reports.search(
      tables.order_by("last_modified", ascending=False), vet=q.any_of(*user_rows)
    )

    results = []
    for report_row in reports_query:
      animal_row = report_row["animal"]
      animal_name = animal_row["name"] if animal_row else None
      dt_str = (
        report_row["last_modified"].strftime("%Y-%m-%d %H:%M:%S")
        if report_row["last_modified"]
        else None
      )
      vet_display_name = "Unknown Vet"
      vet_row = report_row["vet"]
      if vet_row:
        vet_display_name = vet_row["name"] or vet_row["email"]

      results.append({
        "id": report_row.get_id(),  # --- MODIFIED: Return Anvil's unique Row ID
        "file_name": report_row["file_name"],
        "name": animal_name,
        "last_modified": dt_str,
        "owner_email": report_row["vet"]["email"] if report_row["vet"] else None,
        "report_rich": report_row["report_rich"],
        "statut": report_row["statut"],
        "vet_display_name": vet_display_name,
      })

    print(f"DEBUG: Returning {len(results)} report(s) for structure '{structure_name}'")
    return results
  except Exception as e:
    print(f"ERROR: Unexpected error in get_reports_by_structure: {e}")
    return []


@anvil.server.callable(require_user=True)
def save_new_report_with_images(report_details, image_list):
  user = anvil.users.get_user(allow_remembered=True)
  logger.info(
    f"User '{user['email']}' saving new report for animal ID '{report_details.get('animal_id')}' with {len(image_list)} images."
  )

  new_report_row = None
  created_image_rows = []

  try:
    animal_row = app_tables.animals.get_by_id(report_details.get("animal_id"))
    if not animal_row:
      raise ValueError("Animal record not found.")

    current_date_str = datetime.now().strftime("%Y%m%d")
    file_name = f"{animal_row['name']}_{current_date_str}"

    new_report_row = app_tables.reports.add_row(
      file_name=file_name,
      animal=animal_row,
      vet=user,
      last_modified=datetime.now().date(),
      report_rich=report_details.get("html_content"),
      statut=report_details.get("status", "not_specified"),
      transcript=report_details.get("transcript"),
      language=report_details.get("language"),
    )
    new_report_id = new_report_row.get_id()

    for image_data in image_list:
      img_row = app_tables.embedded_images.add_row(
        owner=user,
        report_id=new_report_row,
        media=image_data.get("file"),
        reference_id=image_data.get("reference_id"),
        created_date=datetime.now(),
      )
      created_image_rows.append(img_row)

    logger.info(f"Successfully saved new report ID '{new_report_id}'.")
    return {"success": True, "report_id": new_report_id}

  except Exception as e:
    logger.error(
      f"Failed to save new report for user '{user['email']}': {e}", exc_info=True
    )
    if new_report_row:
      new_report_row.delete()
    for img_row in created_image_rows:
      img_row.delete()
    return {"success": False, "error": str(e)}


@anvil.server.callable(require_user=True)
def update_report_with_images(report_id, report_details, new_image_list):
  user = anvil.users.get_user(allow_remembered=True)
  logger.info(
    f"User '{user['email']}' updating report ID '{report_id}' with {len(new_image_list)} new images."
  )

  report_row = app_tables.reports.get_by_id(report_id)

  if not report_row:
    logger.error(f"Update failed: Report ID '{report_id}' not found.")
    return {"success": False, "error": "Report not found."}

  is_owner = report_row["vet"] == user
  is_supervisor = (
    user["supervisor"]
    and user["structure"]
    and user["structure"] == report_row["vet"]["structure"]
  )

  if not (is_owner or is_supervisor):
    logger.error(
      f"SECURITY: User '{user['email']}' permission denied to edit report ID '{report_id}'."
    )
    return {"success": False, "error": "Permission denied."}

  try:
    report_row.update(
      report_rich=report_details.get("html_content"),
      statut=report_details.get("status"),
      last_modified=datetime.now().date(),
    )

    for image_data in new_image_list:
      app_tables.embedded_images.add_row(
        owner=user,
        report_id=report_row,
        media=image_data.get("file"),
        reference_id=image_data.get("reference_id"),
        created_date=datetime.now(),
      )

    logger.info(f"Successfully updated report ID '{report_id}'.")
    return {"success": True}

  except Exception as e:
    logger.error(f"Failed to update report ID '{report_id}': {e}", exc_info=True)
    return {"success": False, "error": str(e)}
