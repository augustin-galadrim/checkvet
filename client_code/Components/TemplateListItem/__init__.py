from ._anvil_designer import TemplateListItemTemplate
from anvil import *
import anvil.server


class TemplateListItem(TemplateListItemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # self.item is automatically populated by the RepeatingPanel.
    # We use Data Bindings to link UI components to this data.
    # In the IDE, bind:
    # - self.label_template_name.text to self.item['template_name']
    # - self.switch_display.checked to self.item['display_template'] (with writeback enabled)

  def switch_display_change(self, **event_args):
    """This method is called when the switch is toggled."""
    # The 'writeback' on the data binding has already updated self.item['display_template']
    anvil.server.call(
      "update_template_visibility",
      self.item["template_name"],
      self.item["display_template"],
    )

  def link_edit_click(self, **event_args):
    """This method is called when the 'Edit' link is clicked."""
    # Raise a custom event to notify the parent form (Templates/Templates)
    # that this item should be edited.
    self.parent.raise_event("x-edit-template", template=self.item)
