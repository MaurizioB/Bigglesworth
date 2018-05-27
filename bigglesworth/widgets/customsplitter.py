from Qt import QtCore, QtWidgets

class Handle(QtWidgets.QSplitterHandle):
    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitterHandle.__init__(self, *args, **kwargs)
        if self.orientation() == QtCore.Qt.Horizontal:
            self.mouseMoveEvent = self.mouseMoveEventHor
        else:
            self.mouseMoveEvent = self.mouseMoveEventVer

    def mouseMoveEventHor(self, event):
        QtWidgets.QSplitterHandle.mouseMoveEvent(self, event)
        self.splitter().moved.emit(self.mapToParent(event.pos()).x())

    def mouseMoveEventVer(self, event):
        QtWidgets.QSplitterHandle.mouseMoveEvent(self, event)
        self.splitter().moved.emit(self.mapToParent(event.pos()).y())

class CustomSplitter(QtWidgets.QSplitter):
    moved = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        QtWidgets.QSplitter.__init__(self, *args, **kwargs)

    def createHandle(self):
        return Handle(self.orientation(), self)
