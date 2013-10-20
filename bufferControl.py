import sublime, sublime_plugin
import os

activeViewList = []

class SwitchBufferCommand(sublime_plugin.WindowCommand):
  def run(self):
    views = self.window.views_in_group(self.window.active_group())
    # Create a selector object to help figure out what view to operate on
    selector = BufferSelector(self.window, views, currentFirst=False)
    view = selector.choose_view(self.action)

  def action(self, view):
    self.window.focus_view(view)

class KillBufferCommand(sublime_plugin.WindowCommand):
  def run(self):
    views = self.window.views_in_group(self.window.active_group())
    # Create a selector object to help figure out what view to operate on
    selector = BufferSelector(self.window, views, currentFirst=True)
    view = selector.choose_view(self.action)

  def action(self, view):
    self.window.focus_view(view)
    self.window.run_command("close_file")

class BufferSelector(object):
    def __init__(self, window, views, currentFirst=False):
        self.window = window
        self.views = views
        self.callback = None
        self.currentFirst = currentFirst

        # Sort the views using the activeViewList
        self.views = sorted(views, key=self.sort_helper, reverse=True)
        self.items = [
            [
                "\t" + self.__get_display_name(view),
                "\t" + self.__get_path(view)
            ] for view in self.views
        ]

    def sort_helper(self, view):
      if not self.currentFirst and self.window.active_view().id() == view.id():
        return -1
      if view.id() in activeViewList:
        return activeViewList.index(view.id())
      else:
        return -1

    def choose_view(self, callback):
      self.callback = callback
      self.window.show_quick_panel(self.items, self.select)

    def select(self, index):
      if index != -1 and self.callback != None:
        self.callback(self.views[index])

    def __get_display_name(self, view):
        mod_star = '*' if view.is_dirty() else ''

        if view.is_scratch() or not view.file_name():
            disp_name = view.name() if len(view.name()) > 0 else 'untitled'
        else:
            disp_name = os.path.basename(view.file_name())

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


class BufferControlEventListener(sublime_plugin.EventListener):
  # When we activate a view either add it to the list or bump it up to the
  # beginning since it's now the most recent
  def on_activated(self, view):
    # If this is already in the list then remove it
    if view.id() in activeViewList:
      activeViewList.remove(view.id())

    # Always put the newest view on the end
    activeViewList.append(view.id())

  # When a veiw is closed remove the view's ID from our history list
  def on_close(self, view):
    # Since we've just closed this view remove it from the history
    if view.id() in activeViewList:
      activeViewList.remove(view.id())
