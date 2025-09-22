import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from ..logging_server import get_logger

logger = get_logger(__name__)


@anvil.server.callable
def get_status_options():
  return ["pending_correction", "validated", "sent", "not_specified"]


@anvil.server.callable(require_user=True)
def read_reports():
  current_user = anvil.users.get_user(allow_remembered=True)
  reports = app_tables.reports.search(
    tables.order_by("last_updated_at", ascending=False), vet=current_user
  )

  result = []
  for report in reports:
    animal_row = report["animal"]
    animal_name = animal_row["name"] if animal_row else "No Patient"
    animal_id = animal_row.get_id() if animal_row else None

    report_dict = {
      "id": report.get_id(),
      "name": animal_name,
      "animal_id": animal_id,
      "vet": report["vet"],
      "created_at": report["created_at"].strftime("%Y-%m-%d %H:%M:%S")
      if report["created_at"]
      else None,
      "last_updated_at": report["last_updated_at"].strftime("%Y-%m-%d %H:%M:%S")
      if report["last_updated_at"]
      else None,
      "report_rich": report["report_rich"],
      "statut": report["statut"],
      "transcript": report["transcript"],
    }
    result.append(report_dict)

  return result


@anvil.server.callable(require_user=True)
def get_reports_by_structure(structure_name):
  try:
    structure_row = app_tables.structures.get(name=structure_name)
    if not structure_row:
      return []

    users_in_structure = app_tables.users.search(structure=structure_row)
    user_rows = list(users_in_structure)
    if not user_rows:
      return []

    reports_query = app_tables.reports.search(
      tables.order_by("last_updated_at", ascending=False), vet=q.any_of(*user_rows)
    )

    results = []
    for report_row in reports_query:
      animal_row = report_row["animal"]
      animal_name = animal_row["name"] if animal_row else "No Patient"
      vet_display_name = "Unknown Vet"
      vet_row = report_row["vet"]
      if vet_row:
        vet_display_name = vet_row["name"] or vet_row["email"]

      results.append({
        "id": report_row.get_id(),
        "name": animal_name,
        "created_at": report_row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        if report_row["created_at"]
        else None,
        "last_updated_at": report_row["last_updated_at"].strftime("%Y-%m-%d %H:%M:%S")
        if report_row["last_updated_at"]
        else None,
        "owner_email": report_row["vet"]["email"] if report_row["vet"] else None,
        "report_rich": report_row["report_rich"],
        "statut": report_row["statut"],
        "vet_display_name": vet_display_name,
      })

    return results
  except Exception as e:
    logger.error(f"Unexpected error in get_reports_by_structure: {e}")
    return []


@anvil.server.callable(require_user=True)
def save_report(report_details, image_list):
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

    now = datetime.now()

    new_report_row = app_tables.reports.add_row(
      animal=animal_row,
      vet=user,
      created_at=now,
      last_updated_at=now,
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
        created_date=now,
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
def update_report(report_id, report_details, new_image_list):
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
      last_updated_at=datetime.now(),
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


@anvil.server.callable(require_user=True)
def delete_report(report_id):
  user = anvil.users.get_user(allow_remembered=True)
  report_row = app_tables.reports.get_by_id(report_id)

  if report_row is None:
    logger.warning(f"Delete failed: Report ID '{report_id}' not found.")
    return False

  is_owner = report_row["vet"] == user
  is_supervisor = (
    user["supervisor"]
    and user["structure"]
    and user["structure"] == report_row["vet"]["structure"]
  )

  if not (is_owner or is_supervisor):
    logger.error(
      f"SECURITY: User '{user['email']}' permission denied to delete report ID '{report_id}'."
    )
    return False

  try:
    associated_images = app_tables.embedded_images.search(report_id=report_row)

    image_count = 0
    for image_row in associated_images:
      image_row.delete()
      image_count += 1

    if image_count > 0:
      logger.info(
        f"Deleted {image_count} associated image(s) for report ID '{report_id}'."
      )

    report_row.delete()
    logger.info(f"Successfully deleted report ID '{report_id}'.")

    return True

  except Exception as e:
    logger.error(
      f"An error occurred while deleting report ID '{report_id}': {e}", exc_info=True
    )
    return False


@anvil.server.callable(require_user=True)
def get_report_for_editing(report_id):
  user = anvil.users.get_user(allow_remembered=True)
  logger.info(f"User '{user['email']}' requesting report ID '{report_id}' for editing.")

  report_row = app_tables.reports.get_by_id(report_id)

  if not report_row:
    logger.error(f"get_report_for_editing failed: Report ID '{report_id}' not found.")
    return None

  is_owner = report_row["vet"] == user
  is_supervisor = (
    user["supervisor"]
    and user["structure"]
    and user["structure"] == report_row["vet"]["structure"]
  )

  if not (is_owner or is_supervisor):
    logger.error(
      f"SECURITY: User '{user['email']}' permission denied to access report ID '{report_id}'."
    )
    raise anvil.server.PermissionDenied(
      "You do not have permission to edit this report."
    )

  images = app_tables.embedded_images.search(report_id=report_row)

  image_list = []
  for img_row in images:
    image_list.append({
      "reference_id": img_row["reference_id"],
      "file": img_row["media"],
    })

  report_data = {
    "id": report_row.get_id(),
    "name": report_row["animal"]["name"] if report_row["animal"] else "No Patient",
    "report_rich": report_row["report_rich"],
    "statut": report_row["statut"],
    "images": image_list,
  }

  return report_data
