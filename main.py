import math
import os
import sys
import time

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QVector2D
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from PhysicsObject import PhysicsObject, DesktopInteractionManager


class CharacterWindow(QWidget):
    def __init__(self, character_name, character_height):
        super().__init__()
        self.character_name = character_name
        self.character_height = character_height
        self.current_sprite = "sprite.png"  # Default sprite

        self.initWindow()
        self.initSprite()

        # Drag tracking
        self.is_dragging = False
        self.drag_position = QPoint()
        self.last_mouse_pos = QPoint()
        self.last_dragging_time = time.time()
        self.drag_history = []  # Store recent positions for velocity calculation

        # Update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateFrame)
        self.timer.start(16)  # ~60 FPS

        # Show window
        self.show()

        # Physics
        self.physics = PhysicsObject(position=self.frameGeometry().topLeft(),
                                     size=(self.size().width(), self.size().height()))
        self.last_physics_time = time.time()

    def initWindow(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

    def initSprite(self):
        self.label = QLabel(self)
        self.loadSprite(self.current_sprite)
        self.label.mousePressEvent = self.mousePressEvent
        self.label.mouseMoveEvent = self.mouseMoveEvent
        self.label.mouseReleaseEvent = self.mouseReleaseEvent

    def loadSprite(self, sprite_name):
        """Load a sprite for the character"""
        sprite_path = f"Characters/{self.character_name}/{sprite_name}"
        if os.path.exists(sprite_path):
            pixmap = QPixmap(sprite_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaledToHeight(self.character_height, Qt.FastTransformation)
                self.label.setPixmap(scaled_pixmap)
                self.resize(scaled_pixmap.size())
                return True

        # Create a placeholder if no image found
        placeholder = QPixmap(self.character_height, self.character_height)
        placeholder.fill(Qt.red)
        self.label.setPixmap(placeholder)
        self.resize(self.character_height, self.character_height)
        return False

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        self.is_dragging = True
        self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        self.last_mouse_pos = event.globalPos()
        self.last_dragging_time = time.time()
        self.drag_history = []
        self.physics.velocity = QVector2D(0.0, 0.0)

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton or not self.is_dragging:
            return

        current_time = time.time()
        current_pos = event.globalPos()

        # Move the window
        self.move(current_pos - self.drag_position)

        # Track movement history for velocity calculation
        if current_time - self.last_dragging_time <= 0:
            return

        self.drag_history.append({
            'pos': current_pos,
            'time': current_time
        })

        # Keep only recent history (last 100ms)
        self.drag_history = [h for h in self.drag_history if current_time - h['time'] < 0.1]

        self.last_mouse_pos = current_pos
        self.last_dragging_time = current_time

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self.is_dragging:
            return

        self.is_dragging = False

        # Keep only recent history (last 100ms)
        current_time = time.time()
        self.drag_history = [h for h in self.drag_history if current_time - h['time'] < 0.1]

        # Calculate release velocity based on recent movement
        if len(self.drag_history) < 2:
            return

        recent = self.drag_history[-1]
        older = self.drag_history[0]
        time_diff = recent['time'] - older['time']

        if time_diff <= 0:
            return

        pos_diff = recent['pos'] - older['pos']
        self.physics.velocity = QVector2D(pos_diff) / time_diff

    def closeEvent(self, event):
        """Clean up when closing"""
        self.physics_timer.stop()
        event.accept()

    def updateFrame(self):
        if self.is_dragging:
            self.physics.position = QVector2D(self.frameGeometry().topLeft())
            self.last_physics_time = time.time()
            return

        dt = time.time() - self.last_physics_time
        self.last_physics_time = time.time()
        if dt > 0.1:
            return

        screen = QApplication.primaryScreen().geometry()
        self.physics.applyPhysics(dt, screen)
        self.move(self.physics.position.toPoint())


class DesktopPetManager:
    """Manager class to handle multiple pets"""

    def __init__(self):
        self.pets = []

        # Debug timer setup
        self.debug_timer = QTimer()
        self.debug_timer.timeout.connect(self.debugTick)
        self.debug_timer.start(1000)

    def addPet(self, character_name, character_height=128):
        """Add a new pet to the desktop"""
        pet = CharacterWindow(character_name, character_height)
        self.pets.append(pet)
        return pet

    def removePet(self, pet):
        """Remove a pet from the desktop"""
        if pet in self.pets:
            pet.close()
            self.pets.remove(pet)

    def closeAllPets(self):
        """Close all pets"""
        for pet in self.pets:
            pet.close()
        self.pets.clear()

    def debugTick(self):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create pet manager
    manager = DesktopPetManager()

    # Add a pet (you can add multiple)
    pet1 = manager.addPet("Sans", 128)

    # Ensure app exits when all windows are closed
    app.setQuitOnLastWindowClosed(True)

    sys.exit(app.exec_())
