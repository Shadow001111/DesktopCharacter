import math
import os
import sys
import time

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QVector2D
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from DesktopInteractionManager import DesktopInteractionManager


class PhysicsSettings:
    gravity = 5000.0  # pixels per second squared
    friction = 2000.0  # per second
    air_resistance = 0.001
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

        # Drag tracking
        self.drag_position = QPoint()
        self.is_dragging = False
        self.last_mouse_pos = QPoint()
        self.last_time = time.time()
        self.drag_history = []  # Store recent positions for velocity calculation

        # Physics timer
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self.updatePhysics)
        self.physics_timer.start(16)  # ~60 FPS
        self.last_physics_time = time.time()

        # Make it draggable
        self.label.mousePressEvent = self.mousePressEvent
        self.label.mouseMoveEvent = self.mouseMoveEvent
        self.label.mouseReleaseEvent = self.mouseReleaseEvent

        # Show window
        self.show()

        # Physics variables
        self.position = QVector2D(0.0, 0.0)
        self.velocity = QVector2D(0.0, 0.0)
        self.setCharacterPositionToWindowPosition()

    def getWindowPosition(self):
        return self.frameGeometry().topLeft()

    def setWindowPositionToCharacterPosition(self):
        self.move(self.position.toPoint())

    def setCharacterPositionToWindowPosition(self):
        window_pos = self.getWindowPosition()
        self.position = QVector2D(window_pos)

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
        self.velocity.setX(0.0)
        self.velocity.setY(0.0)

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

        pos_diff = recent['pos'] - older['pos']
        self.velocity = QVector2D(pos_diff) / time_diff

    def updatePhysics(self):
        if self.is_dragging:
            self.last_physics_time = time.time()
            self.setCharacterPositionToWindowPosition()
            return

        # Calculate delta time
        current_time = time.time()
        dt = current_time - self.last_physics_time
        self.last_physics_time = current_time
        dt = min(dt, 0.05)

        # Get screen dimensions
        screen = QApplication.primaryScreen().geometry()

        # Apply gravity
        gravity_force = QVector2D(0.0, PhysicsSettings.gravity * dt)
        self.velocity += gravity_force

        # Apply air resistance
        speed_squared = self.velocity.lengthSquared()
        speed = math.sqrt(speed_squared)
        air_resistance_force = speed_squared * PhysicsSettings.air_resistance * dt
        if speed < air_resistance_force:
            self.velocity.setX(0.0)
            self.velocity.setY(0.0)
        else:
            self.velocity -= self.velocity.normalized() * air_resistance_force

        # Get current position
        current_rect = self.geometry()
        self.position += self.velocity * dt

        # Bounce off screen edges
        if self.position.x() <= 0.0:
            self.position.setX(0.0)
            self.velocity.setX(abs(self.velocity.x()) * PhysicsSettings.bounce_damping)
        elif self.position.x() + current_rect.width() >= screen.width():
            self.position.setX(screen.width() - current_rect.width())
            self.velocity.setX(-abs(self.velocity.x()) * PhysicsSettings.bounce_damping)

        if self.position.y() <= 0.0:
            self.position.setY(0.0)
            self.velocity.setY(abs(self.velocity.y()) * PhysicsSettings.bounce_damping)
        elif self.position.y() + current_rect.height() >= screen.height():
            self.position.setY(screen.height() - current_rect.height())
            self.velocity.setY(-abs(self.velocity.y()) * PhysicsSettings.bounce_damping)

            # friction
            friction_force = PhysicsSettings.friction * dt
            if abs(self.velocity.x()) < friction_force:
                self.velocity.setX(0.0)
            else:
                self.velocity.setX(self.velocity.x() - math.copysign(friction_force, self.velocity.x()))

        # Stop very small movements to prevent jitter
        if abs(self.velocity.x()) < 1.0:
            self.velocity.setX(0.0)
        if abs(self.velocity.y()) < 1.0:
            self.velocity.setY(0.0)

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
        DesktopInteractionManager.updateAllWindowsList()

        print(f"[DEBUG] Windows on Desktop:")
        for window in DesktopInteractionManager.windows:
            print(window)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create pet manager
    manager = DesktopPetManager()

    # Add a pet (you can add multiple)
    pet1 = manager.addPet("Sans", 128)

    # Ensure app exits when all windows are closed
    app.setQuitOnLastWindowClosed(True)

    sys.exit(app.exec_())
