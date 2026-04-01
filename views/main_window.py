from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QPushButton, QProgressBar, QToolBar

from views.gl_widget import GLWidget


class VMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.glWidget = GLWidget()
        self.loadBtn = QPushButton("Load music")
        self.progressBar = QProgressBar(self)

        self.startBtn = QPushButton("Start")
        self.stopBtn = QPushButton("Stop")

        actionToolbar = QToolBar(self)
        actionToolbar.addWidget(self.loadBtn)
        actionToolbar.addSeparator()
        actionToolbar.addWidget(self.startBtn)
        actionToolbar.addWidget(self.stopBtn)

        layout = QVBoxLayout()
        layout.addWidget(self.progressBar)
        layout.addWidget(self.glWidget)
        layout.addWidget(actionToolbar)

        central_widget = QWidget()
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)
