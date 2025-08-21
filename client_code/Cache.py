import time


# --- Reports Cache ---
class ReportCache:
  """A dedicated object for managing the caching of reports."""

  def __init__(self, lifetime_seconds=300):
    self.lifetime_seconds = lifetime_seconds
    self._my_reports = None
    self._structure_reports = None
    self._has_structure = None
    self._structure_name = None
    self._affiliated_vets = None
    self._last_fetched = 0

  def is_valid(self):
    if self._my_reports is None:
      return False
    age = time.time() - self._last_fetched
    return age < self.lifetime_seconds

  def get(self):
    if self.is_valid():
      return (
        self._my_reports,
        self._structure_reports,
        self._has_structure,
        self._structure_name,
        self._affiliated_vets,
      )
    return (None, None, None, None, None)

  def set(
    self, my_reports, structure_reports, has_structure, structure_name, affiliated_vets
  ):
    self._my_reports = my_reports
    self._structure_reports = structure_reports
    self._has_structure = has_structure
    self._structure_name = structure_name
    self._affiliated_vets = affiliated_vets
    self._last_fetched = time.time()

  def invalidate(self):
    print("Reports cache invalidated.")
    self._my_reports = None
    self._structure_reports = None
    self._has_structure = None
    self._structure_name = None
    self._affiliated_vets = None
    self._last_fetched = 0


reports_cache_manager = ReportCache()


# --- Templates Cache ---
class TemplateCache:
  """A dedicated object for managing the caching of templates."""

  def __init__(self, lifetime_seconds=300):
    self.lifetime_seconds = lifetime_seconds
    self._templates = None
    self._last_fetched = 0

  def is_valid(self):
    if self._templates is None:
      return False
    age = time.time() - self._last_fetched
    return age < self.lifetime_seconds

  def get(self):
    if self.is_valid():
      return self._templates
    return None

  def set(self, templates):
    self._templates = templates
    self._last_fetched = time.time()

  def invalidate(self):
    print("Template cache invalidated.")
    self._templates = None
    self._last_fetched = 0


template_cache_manager = TemplateCache()

user_settings_cache = {
  "language": None,
  "additional_info": None,
  "mobile_installation": None,
}
