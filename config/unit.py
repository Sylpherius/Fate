import math
from collections import namedtuple
from typing import Set, Dict

import pygame
from config import constants
from config.health_bar import HealthBar

AttackInfo = namedtuple('AttackInfo', ['damage', 'count', 'effects'])


class Unit:
    def __init__(self, name, desc, traits, health, attacks, speed, scale_size, offset_x, offset_y,
                 ring_offset_x, ring_offset_y, alpha):
        self.name: str = name
        self.desc: str = desc
        self.traits: Set = set(traits.split(','))
        self.health: int = health
        self.max_health: int = health
        self.attacks: Dict[str, AttackInfo] = {}
        for attack_name, attack_info in attacks.items():
            self.attacks[attack_name] = AttackInfo(attack_info["damage"], attack_info["count"], attack_info["effects"])
        self.selected_attack: str = ""
        self.speed: int = speed
        self.movement: int = speed
        self.offset_x = offset_x * constants.TILE_SIZE
        self.offset_y = offset_y * constants.TILE_SIZE
        self.ring_offset_x = ring_offset_x
        self.ring_offset_y = ring_offset_y

        self.original_alignment: str = ""
        self.alignment: str = ""
        self.ring = None
        self.statuses: Set = set()
        self.healthbar = HealthBar(self)
        self.can_attack = True

        scale_size *= constants.TILE_SIZE
        image = pygame.image.load("assets/unit_" + name + ".png")
        image = pygame.transform.scale(image, (scale_size, scale_size))
        image.set_alpha(alpha)

        self.image = image
        self.rect = self.image.get_rect()
        self.visible_height = 0
        for y in range(self.image.get_height()):
            if any(self.image.get_at((x, y)).a != 0 for x in range(self.image.get_width())):
                self.visible_height = y
                break

    def update(self, screen, unit_x, unit_y):
        self.rect.x = unit_x + self.offset_x
        self.rect.y = unit_y + self.offset_y
        if self.ring:
            screen.blit(self.ring, (unit_x + self.ring_offset_x, unit_y + self.ring_offset_y))
        screen.blit(self.image, self.rect.topleft)
        self.healthbar.update(screen, self.health, self.max_health)

    def destroy(self):
        self.healthbar.destroy()

        del self

    def is_poisoned(self):
        return True if constants.STATUS_POISON in self.statuses else False

    def remove_status(self, status):
        if status in self.statuses:
            self.statuses.remove(status)

    def set_selected_attack(self, attack):
        self.selected_attack = attack

    def set_can_attack(self, can_attack):
        self.can_attack = can_attack

    def get_attack(self):
        return self.attacks[self.selected_attack]

    def set_speed(self, speed):
        self.speed = speed

    def get_speed(self):
        return self.speed

    def set_movement(self, movement):
        self.movement = movement

    def get_movement(self):
        return self.movement

    def set_original_alignment(self, alignment):
        self.set_alignment(alignment)
        self.original_alignment = alignment

    def get_original_alignment(self, alignment):
        return self.original_alignment

    def set_alignment(self, alignment):
        self.alignment = alignment
        self.ring = pygame.image.load("assets/ring_" + alignment + ".png")
        self.ring = pygame.transform.scale(self.ring, (constants.TILE_SIZE, constants.TILE_SIZE))

    def get_alignment(self, alignment):
        return self.alignment

    def take_damage(self, damage):
        self.health -= damage

    def recover_health(self, health, cure=False):
        max_health_recovered = min(self.max_health, self.health + health)
        if self.is_poisoned():
            if cure:
                self.remove_status(constants.STATUS_POISON)
        else:
            self.health = max_health_recovered

    def get_health(self):
        return self.health


def lerp(start, end, fraction):
    return start + (end - start) * fraction


class MovingUnit(pygame.sprite.Sprite):
    def __init__(self, image, x, y, target_x, target_y, duration, input_unit,
                 input_target_tile, input_path, input_location, is_attacking, new_unit_info, app):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.original_x = x
        self.original_y = y
        self.target_x = target_x
        self.target_y = target_y
        self.duration = duration
        self.distance = math.sqrt((target_x - x) ** 2 + (target_y - y) ** 2)
        self.input_unit = input_unit
        self.input_target_tile = input_target_tile
        self.input_path = input_path
        self.input_location = input_location
        self.is_attacking = is_attacking
        self.new_unit_info = new_unit_info
        self.app = app
        self.frame_count = 1

    def update(self):
        fraction = min(self.frame_count / self.duration, 1.0)

        self.rect.x = lerp(self.original_x, self.target_x, fraction)
        self.rect.y = lerp(self.original_y, self.target_y, fraction)

        self.frame_count += 1

        if fraction >= 1.0:
            self.kill()
            self.app.move_unit(self.input_unit, self.input_target_tile, self.input_path,
                               self.input_location, self.is_attacking, self.new_unit_info)
