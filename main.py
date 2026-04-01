import sys

from PySide6.QtWidgets import QApplication

from controllers.main_controller import MainController
from views.main_window import VMainWindow


def main():
    app = QApplication(sys.argv)
    window = VMainWindow()
    controller = MainController(window, app)
    controller.view.show()

    # load the application
    sys.exit(app.exec())

if __name__ == '__main__':
    main()