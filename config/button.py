from typing import List, Tuple

import pygame
from pygame import Surface


class Button:
    def __init__(self, image_name, ui, pos, action, width, height, text=None, text_xy=None,
                 has_selected=False, btype=None):
        if text is None:
            text = []
        self.image = pygame.image.load("assets/button_" + image_name + ".png")
        self.image = pygame.transform.scale(self.image, (width, height)).convert_alpha()
        self.image_selected = self.image
        self.ui = ui
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        self.action = action
        self.text: List[Surface] = text
        self.text_xy: List[Tuple[int, int]] = text_xy
        self.selected = False
        self.btype = btype

        if has_selected:
            self.image_selected = pygame.image.load("assets/button_" + image_name + "_selected.png")
            self.image_selected = pygame.transform.scale(self.image_selected, (width, height)).convert_alpha()

    def update(self, surface):
        """
        Update button image

        :param surface:
        """
        image = self.image_selected if self.selected else self.image
        surface.blit(image, self.rect.topleft)
        for i in range(len(self.text)):
            image.blit(self.text[i], self.text_xy[i])

    def toggle_selected(self):
        """
        Toggle whether button is selected- if it has a btype then deselect all other buttons of same btype
        """
        self.selected = not self.selected

    def handle_event(self, event):
        """
        Handle event

        :param event: event
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            local_x, local_y = mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y
            if self.rect.collidepoint(mouse_pos) and self.image.get_at((local_x, local_y)).a > 0:
                self.action()
                if self.btype:
                    self.ui.deselect_buttons_of_type(self.btype)
                self.toggle_selected()
