from collections import namedtuple
from typing import List

from config import constants
from config.button import Button
from config.unit import Unit

InterfaceLocation = namedtuple('InterfaceLocation', ['x', 'y', 'interface'])


class UI:
    def __init__(self, app):
        self.buttons: List[Button] = []
        self.interfaces: List[InterfaceLocation] = []
        self.app = app

    def draw_interfaces(self, screen):
        """
        Draws interfaces on the screen

        :param screen: main surface
        """
        for x, y, interface in self.interfaces:
            screen.blit(interface, (x, y))

    def draw_buttons(self, screen):
        """
        Draws buttons on the screen

        :param screen: main surface
        """
        for button in self.buttons:
            button.update(screen)

    def handle_event(self, event) -> None:
        """
        Handles all events for buttons in the ui

        :param event: event
        """
        for button in self.buttons:
            button.handle_event(event)

    def add_button(self, button) -> None:
        """
        Adds interface to the screen
        """
        self.buttons.append(button)

    def add_interface(self, interface: InterfaceLocation) -> None:
        """
        Adds interface to the screen
        """
        self.interfaces.append(interface)

    def deselect_buttons_of_type(self, btype):
        for button in self.buttons:
            if button.btype == btype and button.selected:
                button.toggle_selected()

    def end_turn(self) -> None:
        """
        Triggers the end turn sequence.
        """
        self.app.increment_turn()

    @staticmethod
    def select_attack(unit, attack) -> None:
        """
        Selects attack for a unit in combat

        :param unit: unit whose attack is being selected
        :param attack: string of the attack
        """
        unit.set_selected_attack(attack)

    def attack_confirm(self, unit1, unit2) -> None:
        """
        Confirms the attack choices

        :param unit1: First unit
        :param unit2: Second unit
        """
        self.attack_execute(unit1, unit2)
        self.app.ui_removal_list.append(constants.UI_BATTLE)

    def attack_execute(self, unit1: Unit, unit2: Unit):
        """
        Executes the attack between 2 units

        :param unit1: First unit
        :param unit2: Second unit
        """
        unit1_attack = unit1.get_attack()
        unit2_attack = unit2.get_attack()

        unit1_dmg = unit1_attack.damage * unit1_attack.count
        unit2_dmg = unit2_attack.damage * unit2_attack.count

        unit1.take_damage(unit2_dmg)
        unit2.take_damage(unit1_dmg)

        unit1.can_attack = False
        unit1.movement = 0

    def attack_cancel(self) -> None:
        """
        Cancels an attack and closes UI
        """
        self.app.ui_removal_list.append(constants.UI_BATTLE)
