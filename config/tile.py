from typing import Set

import pygame
from config import constants


class Tile:
    def __init__(self, name, desc, traits):
        self.name = name
        tile_image = pygame.image.load("assets/tile_" + name + ".png")
        tile_image = pygame.transform.scale(tile_image, (constants.TILE_SIZE, constants.TILE_SIZE)).convert_alpha()
        self.image = tile_image
        self.desc = desc
        self.traits = traits
        self.alignments: Set[str] = set()
        self.hidden_alignments: Set[str] = set()
