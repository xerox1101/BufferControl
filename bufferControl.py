# This SublimeText 3 plugin adds some new functionality for managing the open
# buffers. It lets you switch between open buffers only, kill open buffers, and
# open new buffers from the command line. A lot of this is inspired from how I
# was used to using emacs.
#
# Commands:
#  - switch_buffer: Open a quick panel to select a different already open view
#    to switch to.
#    Arguments:
#      - active_group: Set whether the switch command is limited to the active
#        group or all groups in this window (defaults to True).
#      - sort_by_recent: Set whether the buffers in the list will be sorted by
#        which one was most recently used (defaults to True).
#
#  - kill_buffer: Open a quick panel to select a view to close.
#    Arguments:
#      - active_group: Set whether the command is limited to the active group
#        or all groups in this window (defaults to True).
#      - sort_by_recent: Set whether the buffers in the list will be sorted by
#        which one was most recently used (defaults to True).
#      - auto_index: Automatically select a specific index in the list and close
#        it without opening the window.
#      - recent_on_kill: Determine whether we switch to the most recently used
#        view in the group after killing a view or if we use ST3's default
#        behavior (defaults to True).
#

import sublime, sublime_plugin
import os

# List of all views by which was last opened
activeViewList = []

class BufferControlEventListener(sublime_plugin.EventListener):
  # When we activate a view either add it to the list or bump it up to the
  # beginning since it's now the most recent
  def on_activated(self, view):
    # If this is already in the list then remove it
    if view in activeViewList:
      activeViewList.remove(view)

    # Always put the newest view on the end
    activeViewList.append(view)

  # When a veiw is closed remove the view's ID from our history list
  def on_close(self, view):
    # Since we've just closed this view remove it from the history
    if view in activeViewList:
      activeViewList.remove(view)

# This utility can be passed to the sort function to sort a list of views by
# which one was last used
def sort_views_by_recent(views):
  # Helper function for sorting
  def sort_helper(view):
    if view in activeViewList:
      return activeViewList.index(view)
    else:
      return -1
  return sorted(views, key=sort_helper, reverse=True)

# Implements the switch_buffer command
class SwitchBufferCommand(sublime_plugin.WindowCommand):
  def run(self, **kwargs):
    activeGroup = kwargs.get("active_group", True)
    sortByRecent = kwargs.get("sort_by_recent", True)

    # Create a selector object to help manage the selection process
    selector = BufferSelector(self.window, self.action, activeGroup,
                              sortByRecent, currentFirst=False)
    # Open and run the selector
    selector.choose_view()

  def action(self, view):
    self.window.focus_view(view)

# Implements the kill_buffer command
class KillBufferCommand(sublime_plugin.WindowCommand):
  def run(self, **kwargs):
    activeGroup = kwargs.get("active_group", True)
    sortByRecent = kwargs.get("sort_by_recent", True)
    index = kwargs.get("auto_index", None)
    self.recentOnKill = kwargs.get("recent_on_kill", True)

    # Create a selector object to help manage the selection process
    selector = BufferSelector(self.window, self.action, activeGroup,
                              sortByRecent, currentFirst=True)
    # Open and run the selector
    selector.choose_view(index)

  def action(self, view):
    startGroup = self.window.active_group()

    # Switch to the group with the view we're closing
    for group in range(self.window.num_groups()):
      if view in self.window.views_in_group(group):
        self.window.focus_group(group)
        break

    # If we want to switch to the most recent tab on kill then make sure we
    # figure out what that tab is here.
    if self.recentOnKill:
      # We only need to do anything here if this is the active view in the group
      # it's in (which we swtiched to above) since killing an inactive view
      # won't impact things
      if view == self.window.active_view():
        # Switch the active view in this group to the next one
        viewsInGroup = self.window.views_in_group(self.window.active_group())
        viewsInGroup = sort_views_by_recent(viewsInGroup)
        viewsInGroup.remove(view)
        if len(viewsInGroup) > 0:
          self.window.focus_view(viewsInGroup[0])

    # Store the current view so that we can switch back to it after closing
    startView = self.window.active_view()

    # Close the requested view by switching to it and issuing a command
    self.window.focus_view(view)
    self.window.run_command("close_file")

    # Switch back to the correct new view and the group we started in
    if startView != view:
      self.window.focus_view(startView)
    self.window.focus_group(startGroup)

# Helper routine for buffer selection from a quick panel. This is used by the
# switch_buffer and kill_buffer commands to create the list of files.
class BufferSelector(object):
  def __init__(self, window, callback=None, activeGroup=True, sortByRecent=True,
               currentFirst=False):
    self.window = window
    self.callback = callback

    # Get the set of views we want to select between
    if activeGroup:
      views = self.window.views_in_group(self.window.active_group())
    else:
      views = self.window.views()

    # Sort the views using the activeViewList if requested
    if sortByRecent:
      views = sort_views_by_recent(views)

    # We don't want to show the current view first in certain cases so
    # move it to the end here
    if not currentFirst:
      if len(views) > 0 and views[0] == window.active_view():
        firstView = views[0]
        views.remove(firstView)
        views.append(firstView)

    # Store the views and items for reference later
    self.views = views

  def choose_view(self, index=None):
    # Auto select the specified index without showing the panel
    if index != None and abs(index) < len(self.views):
      self.select(index)
      return

    # Create the items to show the user and prompt them with a quick panel
    items = [[self.__get_display_name(view),self.__get_path(view)]
             for view in self.views]
    self.window.show_quick_panel(items, self.select)

  def select(self, index):
    if index != -1 and self.callback != None:
      self.callback(self.views[index])

  def __get_display_name(self, view):
      mod_star = '*' if view.is_dirty() else ''

      if view.name() != None and view.name() != '':
        disp_name = view.name()
      elif view.file_name() is not None:
        disp_name = os.path.basename(view.file_name())
      else:
        disp_name = 'untitled'

      return '%s%s' % (disp_name, mod_star)

  def __get_path(self, view):
    if view.is_scratch():
      return ''

    if not view.file_name():
      return '<unsaved>'

    folders = self.window.folders()

    for folder in folders:
      if os.path.commonprefix([folder, view.file_name()]) == folder:
        relpath = os.path.relpath(view.file_name(), folder)

        if len(folders) > 1:
          return os.path.join(os.path.basename(folder), relpath)

        return relpath

    return view.file_name()
