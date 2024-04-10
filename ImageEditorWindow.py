from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QPushButton, QLabel, QListWidget, QListWidgetItem, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout, QMenu
from PyQt6.QtGui import QPixmap, QIcon, QMouseEvent
from PyQt6.QtCore import pyqtSlot, pyqtSignal, Qt, QSize
from ImageViewer import ImageViewer
from HoverButton import HoverButton
from CropWindow import CropWindow


class ImageEditor_ButtonLayout(QWidget):
    
    # Define signals for different button actions
    button_crop_clicked = pyqtSignal()
    button_brightness_clicked = pyqtSignal()
    button_colors_clicked = pyqtSignal()
    button_edit_image_clicked = pyqtSignal()
    button_effects_clicked = pyqtSignal()
    button_de_noise_clicked = pyqtSignal()
    button_histogram_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        self.button_size = 60  # Button size
        self.icon_size = 40  # Icon size inside the button

        # Create a layout for buttons
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # Aligns widgets at the top within the layout
        self.setLayout(layout)

        # Create and add buttons for each action
        self.add_button("icons/crop.png", "Adjust Cropping", self.button_crop_clicked)
        self.add_button("icons/brightness.png", "Adjust Lighting", self.button_brightness_clicked)
        self.add_button("icons/colors.png", "Adjust Colors", self.button_colors_clicked)
        self.add_button("icons/edit-image.png", "Adjust Levels", self.button_edit_image_clicked)
        self.add_button("icons/button_effects.png", "Sharpness", self.button_effects_clicked)
        # Assuming the "De-Noise" button should have a unique action, use `button_de_noise_clicked` signal
        self.add_button("icons/button_effects.png", "De-Noise", self.button_de_noise_clicked)
        self.add_button("icons/histogram.png", "Histogram", self.button_histogram_clicked)
        

    def add_button(self, icon, tooltip, signal):
        # Assuming HoverButton is a custom button class that supports `setToolTip` and `clicked` signal
        new_button = HoverButton(self, icon=icon, button_size=self.button_size, icon_size=self.icon_size)
        new_button.setToolTip(tooltip)  # Set tooltip for the button
        new_button.clicked.connect(signal.emit)  # Connect button click to the respective signal
        self.layout().addWidget(new_button)  # Add button to the layout

class HistoryWidget(QWidget):
    show_image_requested = pyqtSignal(QPixmap)
    delete_image_requested = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        self.label = QLabel("Editing History")
        layout.addWidget(self.label)

        self.history_list_widget = QListWidget()
        self.history_list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.history_list_widget.setIconSize(QSize(300, 100))
        self.history_list_widget.setWordWrap(True)
        self.history_list_widget.setSpacing(10)

        layout.addWidget(self.history_list_widget)
        self.original_pixmaps = []  # List to store original pixmaps
        # Connect the itemDoubleClicked signal to a slot
        self.history_list_widget.itemDoubleClicked.connect(self.onItemDoubleClicked)
    
    def clearHistory(self):
        self.history_list_widget.clear()
        for pix in self.original_pixmaps:
            del pix # Also remove the pixmap reference
        self.original_pixmaps = []

    def update_history_list(self, pixmap, description=""):
        self.original_pixmaps.append(pixmap)  # Store the original pixmap
        # icon = QIcon(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))  # Scale for display
        # item = QListWidgetItem(icon, description)
        item = QListWidgetItem(QIcon(pixmap), description)
        item.setToolTip(description)
        item.setSizeHint(QSize(200, 120))
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.history_list_widget.addItem(item)
            
    def onItemDoubleClicked(self, item):
        row = self.history_list_widget.row(item)
        if row != -1:
            self.show_image_requested.emit(self.original_pixmaps[row])

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        show_action = context_menu.addAction("Show Image")
        delete_action = context_menu.addAction("Delete Image")
        
        # Get the row of the item right-clicked on
        row = self.history_list_widget.indexAt(self.history_list_widget.mapFromGlobal(event.globalPos())).row()

        # Only add the delete option if the item is not the first one
        # Assuming the first item (index 0) is the original image
        if row < 1:
            delete_action.setDisabled(True)

        action = context_menu.exec(event.globalPos())

        if action == show_action:
            if row != -1:
                self.show_image_requested.emit(self.original_pixmaps[row])
        elif action == delete_action:
            if row != -1:
                self.delete_image_requested.emit(row)
                self.history_list_widget.takeItem(row)
                del self.original_pixmaps[row]  # Also remove the pixmap reference
                if row < self.history_list_widget.count(): 
                    self.show_image_requested.emit(self.original_pixmaps[row])
                else:
                    self.show_image_requested.emit(self.original_pixmaps[row-1])

class ImageViewerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Viewer Window")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.image_viewer = ImageViewer()
        self.history_widget = HistoryWidget()  # Create instance of HistoryWidget
        self.buttons_layer = ImageEditor_ButtonLayout()
        
        self.cropWindow = CropWindow()
        self.cropWindow.crop_confirmed.connect(self.cropping_confirmed)
        
        main_layout = QGridLayout(central_widget)

        image_layout = QVBoxLayout()
        image_layout.addWidget(self.image_viewer)

        main_layout.addWidget(self.buttons_layer, 0, 0)
        main_layout.addLayout(image_layout, 0, 1)
        main_layout.addWidget(self.history_widget, 0, 2)
        
        # Set column stretch to achieve desired proportions
        main_layout.setColumnStretch(0, 0)  
        main_layout.setColumnStretch(1, 10)  
        main_layout.setColumnStretch(2, 0)  

        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        # Adjust window size to half of the screen size
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        half_screen_size = screen_size / 2
        self.resize(half_screen_size)

        # Connect button signal to slot
        self.buttons_layer.button_crop_clicked.connect(self.crop_button_clicked)
        self.history_widget.show_image_requested.connect(self.show_image_from_history)
        self.history_widget.delete_image_requested.connect(self.delete_image_from_history)

    def show_image_from_history(self, pixmap):
        self.image_viewer.load_new_pixmap(pixmap)  # Assuming your ImageViewer widget has a method to set a QPixmap

    def delete_image_from_history(self, index):
        # Handle the deletion of an image from the history
        print(f"Image at index {index} has been requested to delete")

    def show_new_image(self,image_path):
        self.history_widget.clearHistory()
        self.image_viewer.open_new_image(image_path) 
        self.history_widget.update_history_list(self.image_viewer.get_current_pixmap(), "Original Image")

    def crop_button_clicked(self):
        self.cropWindow.show()
        self.cropWindow.set_image(self.image_viewer.get_current_pixmap())
        # Handle edit button click event
        print("Crop Window event.")
        pass  # Placeholder, put your code here to handle the edit button click
    
    def cropping_confirmed(self, pixmap):
        print("Cropping confirmed!")
        self.image_viewer.load_new_pixmap(pixmap)
        self.history_widget.update_history_list(pixmap,"Crop and rotate.")

        # print(f"Rectangle Coordinates: Top Left ({rect.topLeft().x()}, {rect.topLeft().y()}) - Bottom Right ({rect.bottomRight().x()}, {rect.bottomRight().y()})")
        # print(f"Rectangle Size: Width {rect.width()} - Height {rect.height()}")
