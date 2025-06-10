import os
import sys
import time
import math

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QWidget


class PhysicsSettings:
    gravity = 500.0  # pixels per second squared
    friction = 300  # per second
    air_resistance = 0.95 # per second
    bounce_damping = 0.5


class CharacterWindow(QWidget):
    def __init__(self, character_name, character_height):
        super().__init__()
        self.character_name = character_name
        self.character_height = character_height
        self.current_sprite = "sprite.png"  # Default sprite

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # Prevents taskbar icon
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Load character image
        self.label = QLabel(self)
        self.loadSprite(self.current_sprite)

        # Physics variables
        # TODO: set position to window's position on the start
        self.position_x = 300.0
        self.position_y = 300.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        # Drag tracking
        self.drag_position = QPoint()
        self.is_dragging = False
        self.last_mouse_pos = QPoint()
        self.last_time = time.time()
        self.drag_history = []  # Store recent positions for velocity calculation

        # Physics timer
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.start(16)  # ~60 FPS
        self.last_physics_time = time.time()

        # Make it draggable
        self.label.mousePressEvent = self.mousePressEvent
        self.label.mouseMoveEvent = self.mouseMoveEvent
        self.label.mouseReleaseEvent = self.mouseReleaseEvent

        self.show()

    def getWindowPosition(self):
        return self.frameGeometry().topLeft()

    def setWindowPositionToCharacterPosition(self):
        self.move(int(self.position_x), int(self.position_y))

    def setCharacterPositionToWindowPosition(self):
        window_pos = self.getWindowPosition()
        self.position_x = float(window_pos.x())
        self.position_y = float(window_pos.y())

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
        self.drag_position = event.globalPos() - self.getWindowPosition()
        self.last_mouse_pos = event.globalPos()
        self.last_time = time.time()
        self.drag_history = []
        # Stop current physics movement
        self.velocity_x = 0
        self.velocity_y = 0

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton or not self.is_dragging:
            return

        current_time = time.time()
        current_pos = event.globalPos()

        # Move the window
        self.move(current_pos - self.drag_position)

        # Track movement history for velocity calculation
        if current_time - self.last_time <= 0:
            return

        self.drag_history.append({
            'pos': current_pos,
            'time': current_time
        })

        # Keep only recent history (last 100ms)
        self.drag_history = [h for h in self.drag_history if current_time - h['time'] < 0.1]

        self.last_mouse_pos = current_pos
        self.last_time = current_time

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

        dx = recent['pos'].x() - older['pos'].x()
        dy = recent['pos'].y() - older['pos'].y()

        # Scale velocity (pixels per second)
        self.velocity_x = (dx / time_diff)
        self.velocity_y = (dy / time_diff)

    def update_physics(self):
        if self.is_dragging:
            self.last_physics_time = time.time()
            self.setCharacterPositionToWindowPosition()
            return

        # Calculate delta time
        current_time = time.time()
        dt = current_time - self.last_physics_time
        self.last_physics_time = current_time

        # Skip if delta time is too large (e.g., window was paused)
        if dt > 0.1:
            return

        # Get screen dimensions
        screen = QApplication.primaryScreen().geometry()

        # Apply gravity
        self.velocity_y += PhysicsSettings.gravity * dt

        # Apply air resistance
        # friction_factor = PhysicsSettings.friction ** dt
        # self.velocity_x *= friction_factor
        # self.velocity_y *= friction_factor

        # Get current position
        current_rect = self.geometry()
        self.position_x += self.velocity_x * dt
        self.position_y += self.velocity_y * dt

        # Bounce off screen edges
        if self.position_x <= 0.0:
            self.position_x = 0.0
            self.velocity_x = abs(self.velocity_x) * PhysicsSettings.bounce_damping
        elif self.position_x + current_rect.width() >= screen.width():
            self.position_x = screen.width() - current_rect.width()
            self.velocity_x = -abs(self.velocity_x) * PhysicsSettings.bounce_damping

        if self.position_y <= 0.0:
            self.position_y = 0.0
            self.velocity_y = abs(self.velocity_y) * PhysicsSettings.bounce_damping
        elif self.position_y + current_rect.height() >= screen.height():
            self.position_y = screen.height() - current_rect.height()
            self.velocity_y = -abs(self.velocity_y) * PhysicsSettings.bounce_damping

            # friction
            friction_force = PhysicsSettings.friction * dt
            if abs(self.velocity_x) < friction_force:
                self.velocity_x = 0.0
            else:
                self.velocity_x -= math.copysign(friction_force, self.velocity_x)

        # Stop very small movements to prevent jitter
        if abs(self.velocity_x) < 1.0:
            self.velocity_x = 0.0
        if abs(self.velocity_y) < 1.0:
            self.velocity_y = 0.0

        # Update position
        self.setWindowPositionToCharacterPosition()

    def closeEvent(self, event):
        """Clean up when closing"""
        self.physics_timer.stop()
        event.accept()


class DesktopPetManager:
    """Manager class to handle multiple pets"""

    def __init__(self):
        self.pets = []

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


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create pet manager
    manager = DesktopPetManager()

    # Add a pet (you can add multiple)
    pet1 = manager.addPet("Sans", 128)

    # Ensure app exits when all windows are closed
    app.setQuitOnLastWindowClosed(True)

    sys.exit(app.exec_())
