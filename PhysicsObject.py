import math
from dataclasses import dataclass

from PyQt5.QtGui import QVector2D

from DesktopInteractionManager import DesktopInteractionManager


# TODO: Using pyqt5 vector must be slow, so maybe use numpy or something

class PhysicsSettings:
    gravity = 5000.0  # pixels per second squared
    friction = 2000.0  # per second
    air_resistance = 0.001
    bounce_damping = 0.5
    min_velocity = 1.0


@dataclass
class CollisionBorder:
    x: float
    y: float
    x2: float


@dataclass
class CollisionBordersGroup:
    x_s: list[tuple[float, float]]
    y: float


def subtractIntervals(base_start: float, base_end: float, subtracts: list[tuple[float, float]]):
    intervals = [(base_start, base_end)]
    for sx, ex in subtracts:
        new_intervals = []
        for ix, iy in intervals:
            # No overlap
            if ex <= ix or sx >= iy:
                new_intervals.append((ix, iy))
            else:
                # Left side remains
                if sx > ix:
                    new_intervals.append((ix, sx))
                # Right side remains
                if ex < iy:
                    new_intervals.append((ex, iy))
        intervals = new_intervals
    return intervals


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
        previous_y = self.position.y()
        self.position += self.velocity * dt

        # Bounce and clamp
        applyFriction = self.screenBordersCollision(screen_rect)
        if not applyFriction and self.velocity.y() > 0:  # Character didn't hit the bottom and they are falling
            applyFriction = self.windowsCollision(previous_y)

        # Friction
        if applyFriction:
            friction = PhysicsSettings.friction * dt
            if abs(self.velocity.x()) < friction:
                self.velocity.setX(0.0)
            else:
                self.velocity.setX(self.velocity.x() - math.copysign(friction, self.velocity.x()))

        # Stop very small movement
        if abs(self.velocity.x()) < PhysicsSettings.min_velocity:
            self.velocity.setX(0.0)
        if abs(self.velocity.y()) < PhysicsSettings.min_velocity:
            self.velocity.setY(0.0)

    def screenBordersCollision(self, screen_rect) -> bool:
        apply_friction = False
        x, y = self.position.x(), self.position.y()
        vx, vy = self.velocity.x(), self.velocity.y()
        w, h = self.size.x(), self.size.y()

        if x < 0:
            self.position.setX(0)
            vx *= -PhysicsSettings.bounce_damping
        elif x + w > screen_rect.width():
            self.position.setX(screen_rect.width() - w)
            vx *= -PhysicsSettings.bounce_damping

        if y < 0:
            self.position.setY(0)
            vy *= -PhysicsSettings.bounce_damping
        elif y + h > screen_rect.height():
            self.position.setY(screen_rect.height() - h)
            vy *= -PhysicsSettings.bounce_damping
            apply_friction = True

        self.velocity.setX(vx)
        self.velocity.setY(vy)
        return apply_friction

    @staticmethod
    def getCollisionBordersGroups() -> list[CollisionBordersGroup]:
        bordersGroups = []
        DesktopInteractionManager.updateAllWindowsList()

        # Collect all visible borders
        # TODO: Store CharacterMax_YMinusH(max_y_minus_height from all characters) and if window.y is above it, then don't include the top border
        for windowInfo in DesktopInteractionManager.windows:
            border = CollisionBorder(
                x=windowInfo.position[0],
                y=windowInfo.position[1],
                x2=windowInfo.position[0] + windowInfo.size[0]
            )

            covering_intervals = []

            # Find intersecting rectangles
            # TODO: 'windows' list is sorted by 'z' in ascending order, so we can use index and use list slices to skip all unnecessary windows
            for windowInfo2 in DesktopInteractionManager.windows:
                if windowInfo.z < windowInfo2.z:  # if out segment is in front of window
                    continue
                if windowInfo is windowInfo2:
                    continue
                r_top = windowInfo2.position[1]
                r_bottom = windowInfo2.position[1] + windowInfo2.size[1]
                if r_top <= border.y < r_bottom:
                    r_left = windowInfo2.position[0]
                    r_right = windowInfo2.position[0] + windowInfo2.size[0]
                    covering_intervals.append((r_left, r_right))

            #
            bordersGroup = CollisionBordersGroup(x_s=[], y=border.y)
            visible_segments = subtractIntervals(border.x, border.x2, covering_intervals)
            for seg_x1, seg_x2 in visible_segments:
                bordersGroup.x_s.append((seg_x1, seg_x2))
            bordersGroups.append(bordersGroup)

        return bordersGroups

    def windowsCollision(self, previous_y) -> bool:
        x, y = self.position.x(), self.position.y()
        w, h = self.size.x(), self.size.y()
        char_left = x
        char_right = x + w

        # TODO: Update windows info rarely and not per character

        bordersGroups = PhysicsObject.getCollisionBordersGroups()

        for bordersGroup in bordersGroups:
            if not (y + h > bordersGroup.y >= previous_y + h):
                continue

            for border_x1, border_x2 in bordersGroup.x_s:
                collision = char_right > border_x1 and border_x2 > char_left
                if not collision:
                    continue

                self.position.setY(bordersGroup.y - h)
                self.velocity.setY(self.velocity.y() * -PhysicsSettings.bounce_damping)
                return True
        return False
