import pygame

from config import constants


class HealthBar(pygame.sprite.Sprite):
    def __init__(self, unit):
        super().__init__()
        self.width = constants.TILE_SIZE * 0.7 * (unit.max_health / constants.HEALTH_BAR_RATIO)
        self.height = constants.TILE_SIZE * 0.07
        self.image = pygame.Surface((self.width, self.height))
        self.rect = self.image.get_rect()
        self.unit = unit

    def update(self, screen, health, max_health):
        # calculate the current width of the health bar based on the unit's health
        health_ratio = health / max_health
        self.rect.width = int(self.width * health_ratio)
        self.image = pygame.transform.scale(self.image, (self.rect.width, self.height))

        if health_ratio > 0.6:
            color = constants.HEALTH_GREEN
        elif health_ratio > 0.4:
            color = constants.HEALTH_YELLOW
        elif health_ratio > 0.2:
            color = constants.HEALTH_ORANGE
        else:
            color = constants.HEALTH_RED
        self.image.fill(color)

        self.rect.midbottom = self.unit.rect.midtop
        self.rect.y += self.unit.visible_height * 0.7

        screen.blit(self.image, self.rect)

    def destroy(self):
        del self


