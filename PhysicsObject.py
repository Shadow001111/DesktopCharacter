from PyQt5.QtGui import QVector2D
import math


class PhysicsSettings:
    gravity = 5000.0  # pixels per second squared
    friction = 2000.0  # per second
    air_resistance = 0.001
    bounce_damping = 0.5


class PhysicsObject:
    def __init__(self, position, size):
        self.position = QVector2D(position)
        self.velocity = QVector2D(0.0, 0.0)
        self.size = QVector2D(*size)

    def applyPhysics(self, dt, screen_rect):
        # Gravity
        self.velocity += QVector2D(0.0, PhysicsSettings.gravity * dt)

        # Air resistance
        speed_squared = self.velocity.lengthSquared()
        if speed_squared > 0:
            air_force = speed_squared * PhysicsSettings.air_resistance * dt
            self.velocity -= self.velocity.normalized() * min(air_force, self.velocity.length())

        # Update position
        self.position += self.velocity * dt

        # Bounce and clamp
        x, y = self.position.x(), self.position.y()
        w, h = self.size.x(), self.size.y()

        if x < 0:
            self.position.setX(0)
            self.velocity.setX(abs(self.velocity.x()) * PhysicsSettings.bounce_damping)
        elif x + w > screen_rect.width():
            self.position.setX(screen_rect.width() - w)
            self.velocity.setX(-abs(self.velocity.x()) * PhysicsSettings.bounce_damping)

        if y < 0:
            self.position.setY(0)
            self.velocity.setY(abs(self.velocity.y()) * PhysicsSettings.bounce_damping)
        elif y + h > screen_rect.height():
            self.position.setY(screen_rect.height() - h)
            self.velocity.setY(-abs(self.velocity.y()) * PhysicsSettings.bounce_damping)

            # Ground friction
            friction = PhysicsSettings.friction * dt
            if abs(self.velocity.x()) < friction:
                self.velocity.setX(0.0)
            else:
                self.velocity.setX(self.velocity.x() - math.copysign(friction, self.velocity.x()))

        # Stop very small movement
        if abs(self.velocity.x()) < 1.0:
            self.velocity.setX(0.0)
        if abs(self.velocity.y()) < 1.0:
            self.velocity.setY(0.0)
