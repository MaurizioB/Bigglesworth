from Qt import QtWidgets

#this class is a workaround for context menus not updating the status bar
class ContextMenu(QtWidgets.QMenu):
    def mouseMoveEvent(self, event):
        QtWidgets.QMenu.mouseMoveEvent(self, event)
        action = self.actionAt(event.pos())
        try:
            if action and action.statusTip():
                self.parent().window().statusBar().showMessage(action.statusTip(), 0)
            else:
                self.parent().window().statusBar().clearMessage()
        except Exception as e:
            print(e)

    def hideEvent(self, event):
        QtWidgets.QMenu.hideEvent(self, event)
        self.parent().window().statusBar().clearMessage()

    def leaveEvent(self, event):
        QtWidgets.QMenu.leaveEvent(self, event)
        self.parent().window().statusBar().clearMessage()
