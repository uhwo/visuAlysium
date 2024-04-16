import os
import sys
from PyQt6.QtCore import Qt, QDir, QStandardPaths, QSize, QThreadPool, QRunnable, QObject, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtGui import QPixmap, QIcon, QAction, QPalette, QColor, QFileSystemModel
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView, QHBoxLayout, QWidget, QListWidget, QListWidgetItem, QSplitter, QMenu, QMenuBar, QMessageBox, QFileDialog
from ImageEditorWindow import ImageViewerWindow

# Worker signals class for communicating between threads
class WorkerSignals(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object, object)

# Worker class that encapsulates a task to be run in a separate thread
class Worker(QRunnable):
    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            # Try executing the function with the provided arguments
            result1, result2 = self.function(*self.args, **self.kwargs)
            self.signals.result.emit(result1, result2)
        except Exception as e:
            # Emit the results as None if an error occurs
            self.signals.result.emit(None, None)
        finally:
            # Always emit finished signal
            self.signals.finished.emit()

# Function to load thumbnail for images
def load_thumbnail(image_path):
    try:
        pixmap = QPixmap(image_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon = QIcon(pixmap)
        return icon, image_path
    except Exception as e:
        return None, image_path

# Thread class to load images from a directory
class ImageLoaderThread(QThread):
    image_loaded = pyqtSignal(QIcon, str)

    def __init__(self, folder_path, thread_pool):
        super().__init__()
        self.folder_path = folder_path
        self.thread_pool = thread_pool

    @pyqtSlot()
    def run(self):
        image_files = [file for file in os.listdir(self.folder_path) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        for image_file in image_files:
            image_path = os.path.join(self.folder_path, image_file)
            runnable = Worker(load_thumbnail, image_path)
            runnable.signals.result.connect(self.image_loaded.emit)
            self.thread_pool.start(runnable)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisuAlysium - Image Editor")
        self.initUI()

    def initUI(self):
        # Create a menu bar
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Create a "File" menu and add it to the menu bar
        file_menu = QMenu("&File", self)
        menu_bar.addMenu(file_menu)

        self.image_viewer = ImageViewerWindow()

        # Create actions for the "File" menu
        open_folder_action = QAction("Open Folder", self)
        open_image_action = QAction("Open Image", self)
        about_action = QAction("About", self)

        # Add actions to the "File" menu
        file_menu.addAction(open_folder_action)
        file_menu.addAction(open_image_action)
        file_menu.addAction(about_action)

        # Connect actions to methods
        open_folder_action.triggered.connect(self.open_folder)
        open_image_action.triggered.connect(self.open_image)
        about_action.triggered.connect(self.about)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        # Left panel: Folder tree view
        self.folder_model = QFileSystemModel()
        self.folder_model.setRootPath(QDir.rootPath())
        self.folder_tree_view = QTreeView()
        self.folder_tree_view.setModel(self.folder_model)
        self.folder_tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree_view.customContextMenuRequested.connect(self.open_menu)
        self.folder_tree_view.setRootIndex(self.folder_model.index(''))  # Set the root index to root directory
        
        desktop_path = QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DownloadLocation)[0]
        desktop_index = self.folder_model.index(desktop_path)
        self.folder_tree_view.setCurrentIndex(desktop_index)

        self.image_list_widget = QListWidget()
        self.image_list_widget.setViewMode(QListWidget.ViewMode.IconMode)  # Set the view mode to IconMode
        self.image_list_widget.setIconSize(QSize(100, 100))  # Set the icon size to 100x100 pixels
        self.image_list_widget.setWordWrap(False)  # Enable word wrap
        self.image_list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)  # Set text elide mode to elide right
        self.image_list_widget.setUniformItemSizes(True)  # Enable uniform item sizes
        self.image_list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)  # Set resize mode to Adjust
        self.image_list_widget.setSpacing(10)  # Set spacing between items
        
        self.image_list_widget.itemDoubleClicked.connect(self.image_double_clicked)
        self.image_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.image_list_widget.customContextMenuRequested.connect(self.open_image_menu)
        
        # Add widgets to layout
        splitter = QSplitter()
        splitter.addWidget(self.folder_tree_view)
        splitter.addWidget(self.image_list_widget)
        splitter.setStretchFactor(0, 0)  # Prevent the folder view from stretching
        splitter.setStretchFactor(1, 1)  # Allow the image view to stretch

        # Set default sizes for the left and right panels
        splitter.setSizes([400, 600])

        self.layout.addWidget(splitter)
        self.folder_tree_view.setColumnWidth(0, 250)  # Set the width of the "Name" column

    def open_image_menu(self, position):
        menu = QMenu()
        open_image_action = QAction("Show Image", self)
        open_image_action.triggered.connect(lambda: self.image_double_clicked(self.image_list_widget.currentItem()))
        menu.addAction(open_image_action)
        menu.exec(self.image_list_widget.viewport().mapToGlobal(position))
        
    def open_menu(self, position):
        menu = QMenu()
        show_images_action = QAction("Show Images", self)
        show_images_action.triggered.connect(lambda: self.folder_selected(self.folder_tree_view.currentIndex()))
        menu.addAction(show_images_action)
        menu.exec(self.folder_tree_view.viewport().mapToGlobal(position))

    def folder_selected(self, index):
        folder_path = self.folder_model.filePath(index)
        self.load_images(folder_path)

    def load_images(self, folder_path):
        self.image_list_widget.clear()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(8)
        self.image_loader_thread = ImageLoaderThread(folder_path, self.thread_pool)
        self.image_loader_thread.image_loaded.connect(self.add_thumbnail)
        self.image_loader_thread.run()

    def add_thumbnail(self, icon, image_path):
        image_file = os.path.basename(image_path)
        item = QListWidgetItem(icon, image_file)
        item.setToolTip(image_path)  # Set tooltip to display full file name
        item.setSizeHint(QSize(100, 120))  # Set a fixed size for the items
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)  # Center align text
        self.image_list_widget.addItem(item)
    
    def image_double_clicked(self, item):
        image_path = item.toolTip()
        self.image_viewer.show()
        self.image_viewer.show_new_image(image_path)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.load_images(folder_path)

    def open_image(self):
        file_dialog = QFileDialog()
        image_path, _ = file_dialog.getOpenFileName(self, "Open Image", QDir.homePath(), "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if image_path:
            self.image_viewer.show()
            self.image_viewer.show_new_image(image_path)

    def about(self):
        # Create a QMessageBox
        msg_box = QMessageBox()
        msg_box.setWindowTitle("About")
        msg_box.setIcon(QMessageBox.Icon.Information)

        # Set text and customize appearance
        msg_box.setText(
            "p>This is an experimental Python-based image visualizer and editor.</p>"
            "<p>Copyright (c) 2024 VisuAlysium</p>"
            "<p>This program is free software: you can redistribute it and/or modify it under the terms of the "
            "GNU General Public License as published by the Free Software Foundation, either version 3 of the License, "
            "or (at your option) any later version.</p>"
            "<p>This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without "
            "even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General "
            "Public License for more details.</p>"
            "<p>You should have received a copy of the GNU General Public License along with this program. If not, "
            "see <a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses/</a>.</p>"
      
        )

        # # Customize appearance
        # msg_box.setStyleSheet("QLabel{min-width: 600px;}")
        
        # Set fixed size
        msg_box.setFixedSize(800, 400)

        # Display the message box
        msg_box.exec()


from PyQt6.QtGui import QPalette, QColor

def main():
    
    # This bit gets the taskbar icon working properly in Windows
    if sys.platform.startswith('win'):
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'Visualysium.ExImaVi.ImageVisualizer.0.01') # Arbitrary string

    app = QApplication(sys.argv)
    
    # Set the application style to Fusion
    app.setStyle("Fusion")

    # Create a dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)

    # Change some style settings
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
        # Set application icon

    window = MainWindow()

    # Get the screen dimensions
    screen_rect = app.primaryScreen().availableGeometry()

    # Calculate the dimensions for the window (50% of screen dimensions)
    window_width = screen_rect.width() * 0.5
    window_height = screen_rect.height() * 0.75

    # Calculate the position for the window to be centered
    window_x = (screen_rect.width() - window_width) / 2
    window_y = (screen_rect.height() - window_height) / 2

    # Set the geometry of the window
    window.setGeometry(int(window_x), int(window_y), int(window_width), int(window_height))

    window.show()
    icon_path = "icons/main_icon.png"
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    app.setApplicationName("VisuAlysium")
    app.setApplicationDisplayName("VisuAlysium")
    

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
