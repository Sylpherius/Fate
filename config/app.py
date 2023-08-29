import copy
import heapq
import json

import pygame
from collections import namedtuple

from pygame import Surface

from config import constants
from config.button import Button
from config.tile import Tile
from config.ui import UI, InterfaceLocation
from config.unit import Unit, MovingUnit
from typing import List, Dict, Optional, Tuple

SelectedTile = namedtuple('SelectedTile', ['row', 'col', 'tile_info'])
SelectedUnit = namedtuple('SelectedUnit', ['row', 'col', 'unit_info'])
XYTile = namedtuple('XYTile', ['x', 'y', 'tile'])
XYUnit = namedtuple('XYUnit', ['x', 'y', 'unit'])
Position = namedtuple('Position', ['row', 'col'])


class App:
    def __init__(self):
        self.ui_list: Dict[str, UI] = {constants.UI_DEFAULT: UI(self)}
        self.ui_removal_list: List[str] = []
        self.game_map: List[List[XYTile]] = []
        self.unit_map: List[List[XYUnit]] = []
        self.tile_offset_x = constants.TILE_SIZE * 1.5
        self.tile_offset_y = constants.TILE_SIZE * 0.425
        self.tile_info: Dict[str, Tile] = {}
        self.unit_info: Dict[str, Unit] = {}
        self.start_tile: Optional[SelectedTile] = None
        self.start_unit: Optional[SelectedUnit] = None
        self.shortest_path: List[SelectedTile] = []
        self.moving_sprites = pygame.sprite.Group()
        self.rows = 26
        self.cols = 10
        self.alignments = constants.ALIGNMENTS
        self.turn = 0

        # six directions to adjacent tiles
        # on even going left is the issue, on odd going right is the issue
        self.directions_even = [(-2, 0), (-1, 1), (1, 1), (2, 0), (1, 0), (-1, 0)]
        self.directions_odd = [(-2, 0), (-1, 0), (1, 0), (2, 0), (1, -1), (-1, -1)]

    def test_function(self, tile: Position, speed: int):
        self.unit_map[tile.row][tile.col].unit.set_speed(speed)

    def initialize(self) -> None:
        self.load_tiles_and_units()
        self.initialize_maps()
        default_ui = self.ui_list[constants.UI_DEFAULT]
        default_ui.add_button(Button(constants.BUTTON_END_TURN, default_ui,
                                     (1400, 1000), default_ui.end_turn, 200, 200))

    def load_tiles_and_units(self) -> None:
        """
        Loads in the information of all tiles and units in the game
        """
        # load tiles
        with open("info/tile_info.json") as f:
            data = json.load(f)
        for tile in data["tile_info"]:
            self.tile_info[tile["name"]] = Tile(tile["name"], tile["desc"], tile["traits"])

        # load units
        with open("info/unit_info.json") as f:
            data = json.load(f)
        for unit in data["unit_info"]:
            self.unit_info[unit["name"]] = Unit(unit["name"], unit["desc"], unit["traits"], unit["health"],
                                                unit["attacks"], unit["speed"], unit["scale_size"], unit["offset_x"],
                                                unit["offset_y"], unit["ring_offset_x"], unit["ring_offset_y"],
                                                unit["alpha"])

    def initialize_maps(self) -> None:
        """
        Initializes any map presets in the game
        """
        for i in range(self.rows):
            row = []
            unit_row = []
            for j in range(self.cols):
                tile_x = j * self.tile_offset_x
                tile_y = i * self.tile_offset_y
                if i % 2 == 1:
                    tile_x += self.tile_offset_x / 2
                tile = self.get_tile(constants.TILE_BLANK)
                row.append(XYTile(tile_x, tile_y, tile))
                unit_row.append(XYUnit(tile_x, tile_y, None))
            self.game_map.append(row)
            self.unit_map.append(unit_row)

        for neighbor, direction in self.get_neighbors(Position(5, 5)):
            tile_name = constants.TILE_DIFFICULT
            self.update_tile([Position(neighbor.row, neighbor.col)], tile_name)

    def update(self, screen, hovered_tile: SelectedTile):
        # update tile info
        self.update_tile_alignments()

        # draw the tiles
        for row in self.game_map:
            for tile_x, tile_y, tile in row:
                screen.blit(tile.image, (tile_x, tile_y))

        # draw the units
        self.moving_sprites.update()
        self.moving_sprites.draw(screen)
        for row in range(self.rows):
            for col in range(self.cols):
                unit_x, unit_y, unit = self.unit_map[row][col]
                if unit is not None:
                    if unit.health <= 0:
                        self.unit_map[row][col] = XYUnit(unit_x, unit_y, None)
                        unit.destroy()
                    unit.update(screen, unit_x, unit_y)

        # draw tile overlay
        if self.start_unit is None and hovered_tile is not None:
            self.overlay([Position(hovered_tile.row, hovered_tile.col)], self.tile_info[constants.TILE_CHOSEN].image,
                         screen)

        # draw ui interfaces/buttons
        for ui in self.ui_list.values():
            ui.draw_interfaces(screen)
            ui.draw_buttons(screen)

    def handle_event(self, event) -> None:
        """
        Handles all events in the app

        :param event: event
        """
        for ui in self.ui_list.values():
            ui.handle_event(event)

        for ui_name in self.ui_removal_list:
            self.ui_list.pop(ui_name)
        self.ui_removal_list.clear()

    # Get Shortest Path ================================================================
    def get_shortest_path(self, start: SelectedTile, end: SelectedTile, unit: Unit) -> List[SelectedTile]:
        """
        Returns the shortest path with weights on difficult terrain and moving in the same direction

        :param start: beginning tile of path
        :param end: ending tile of path
        :param unit: unit that is moving across path
        :return: a list of tiles, from beginning to end of path
        """
        # initialize data structures
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        last_direction = {start: -1}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == end:
                # Reconstruct the path when the goal is reached
                path = []
                while current in came_from:
                    path.insert(0, current)
                    current = came_from[current]
                path.insert(0, start)
                return path

            for neighbor, direction in self.get_neighbors(Position(current.row, current.col)):
                row, col, tile = neighbor
                tentative_g_score = g_score[current] + self.get_move_cost(tile, unit)
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    # Update g_score and add the neighbor to the open set
                    g_score[neighbor] = tentative_g_score
                    last_direction[neighbor] = direction

                    # f_score adds a small weight if travelling in same direction
                    f_add = 0.5 if last_direction[current] == direction else 0
                    f_score = tentative_g_score + f_add
                    heapq.heappush(open_set, (f_score, neighbor))
                    came_from[neighbor] = current

        return []

    def get_neighbors(self, pos: Position) -> List[Tuple[SelectedTile, int]]:
        """
        Gets the neighbors of the input tile

        :param pos: position of target tile surrounded by neighbors
        :return: a list of tile neighbors as well as their direction from the original
        """
        neighbors = []
        direction = 0
        for dx, dy in get_directions(pos.row):
            nx, ny = pos.row + dx, pos.col + dy
            if 0 <= nx < self.rows and 0 <= ny < self.cols:
                neighbors.append((SelectedTile(nx, ny, self.game_map[nx][ny].tile), direction))
            direction += 1
        return neighbors

    def get_move_cost(self, tile: Tile, unit: Unit, count_hidden=False) -> int:
        """
        Gets the weighted move cost of moving a specific unit onto a specific tile

        :param tile: tile being moved onto
        :param unit: unit moving onto tile
        :param count_hidden: decides whether invisible units' alignments should be taken into account
        :return: move cost of moving the unit onto tile
        """
        move_cost = 1
        if "difficult" in tile.traits:
            move_cost = 2
        for alignment in tile.alignments:
            if alignment != unit.alignment:
                move_cost = unit.speed
        if count_hidden:
            for alignment in tile.hidden_alignments:
                if alignment != unit.alignment:
                    move_cost = unit.speed

        return move_cost

    # =====================================================================================
    # Combat Functions ====================================================================
    def start_battle(self, unit1: Unit, unit2: Unit) -> None:
        """
        Starts the battle

        :param unit1: the attacking unit
        :param unit2: the enemy unit
        """
        ui_battle_image = pygame.image.load("assets/ui_" + constants.UI_BATTLE + ".png")
        ui_battle_image = pygame.transform.scale(ui_battle_image,
                                                 (constants.UI_BATTLE_WIDTH, constants.UI_BATTLE_HEIGHT))

        ui_x = (constants.SCREEN_WIDTH - ui_battle_image.get_width()) // 2
        ui_y = (constants.SCREEN_HEIGHT - ui_battle_image.get_height()) // 2
        ui_mid_x = (ui_x + constants.UI_BATTLE_WIDTH) // 2
        ui_mid_y = (ui_y + constants.UI_BATTLE_HEIGHT) // 2
        battle_ui = UI(self)
        battle_ui.add_interface(InterfaceLocation(ui_x, ui_y, ui_battle_image))
        self.ui_list[constants.UI_BATTLE] = battle_ui

        margin_x = (constants.UI_BATTLE_WIDTH - 2 * constants.BUTTON_ATTACK_WIDTH) // 4
        # adding the ally unit's attacks
        num_attack = 0
        unit1.set_selected_attack("")
        for attack, attack_info in unit1.attacks.items():
            if not unit1.selected_attack:
                unit1.set_selected_attack(attack)

            # create the text to be shown on the attack
            text_list, text_xy_list = generate_attack_text(attack, attack_info)

            text_surface = constants.FONT_BATTLE.render(attack, True, (0, 0, 0))
            attack_x = ui_x + margin_x
            attack_y = ui_mid_y + num_attack * 1.5 * constants.BUTTON_ATTACK_HEIGHT
            battle_ui.add_button(Button(constants.BUTTON_ATTACK, battle_ui, (attack_x, attack_y),
                                        lambda unit=unit1, atk=attack: battle_ui.select_attack(unit, atk),
                                        constants.BUTTON_ATTACK_WIDTH, constants.BUTTON_ATTACK_HEIGHT,
                                        text=text_list, text_xy=text_xy_list, has_selected=True, btype="unit1"))
            num_attack += 1

        # adding the enemy unit's attacks
        num_attack = 0
        unit2.set_selected_attack("")
        for attack, attack_info in unit2.attacks.items():
            # select first attack as initial attack choice
            if not unit2.selected_attack:
                unit2.set_selected_attack(attack)

            # create the text to be shown on the attack
            text_list, text_xy_list = generate_attack_text(attack, attack_info)

            # calculate where to place the button
            attack_x = ui_x + constants.BUTTON_ATTACK_WIDTH + 3 * margin_x
            attack_y = ui_mid_y + num_attack * 1.5 * constants.BUTTON_ATTACK_HEIGHT
            battle_ui.add_button(Button(constants.BUTTON_ATTACK, battle_ui, (attack_x, attack_y),
                                        lambda unit=unit2, atk=attack: battle_ui.select_attack(unit, atk),
                                        constants.BUTTON_ATTACK_WIDTH, constants.BUTTON_ATTACK_HEIGHT,
                                        text=text_list, text_xy=text_xy_list, has_selected=True, btype="unit2"))
            num_attack += 1

        # adding the attack confirm/cancel buttons
        attack_option_margin = constants.BUTTON_ATTACK_OPTION_HEIGHT // 2
        attack_option_y = ui_y + constants.UI_BATTLE_HEIGHT - 2 * constants.BUTTON_ATTACK_OPTION_HEIGHT
        attack_option_confirm_x = ui_mid_x - attack_option_margin
        attack_option_cancel_x = ui_mid_x + constants.BUTTON_ATTACK_OPTION_WIDTH + attack_option_margin
        battle_ui.add_button(Button(constants.BUTTON_ATTACK_CONFIRM, battle_ui,
                                    (attack_option_confirm_x, attack_option_y),
                                    lambda unit_1=unit1, unit_2=unit2: battle_ui.attack_confirm(unit_1, unit_2),
                                    constants.BUTTON_ATTACK_OPTION_WIDTH, constants.BUTTON_ATTACK_OPTION_HEIGHT))
        battle_ui.add_button(Button(constants.BUTTON_ATTACK_CANCEL, battle_ui,
                                    (attack_option_cancel_x, attack_option_y),
                                    battle_ui.attack_cancel, constants.BUTTON_ATTACK_OPTION_WIDTH,
                                    constants.BUTTON_ATTACK_OPTION_HEIGHT))

    # =====================================================================================
    def update_tile_alignments(self) -> None:
        """
        Figures out what units are around a tile and adds their alignments to it.
        TODO: also add hidden alignments, in the case of invisible units
        """
        for row in range(self.rows):
            for col in range(self.cols):
                self.game_map[row][col].tile.alignments = set()

        for row in range(self.rows):
            for col in range(self.cols):
                unit = self.unit_map[row][col].unit
                if unit is not None:
                    for d in get_directions(row):
                        new_row = row + d[0]
                        new_col = col + d[1]
                        if 0 <= new_row < self.rows and 0 <= new_col < self.cols:
                            tile = self.game_map[new_row][new_col].tile
                            tile.alignments.add(unit.alignment)

    def update_tile(self, tiles: List[Position], tile_name: str) -> None:
        """
        Updates all given positions with the given tile

        :param tiles: list of positions to override
        :param tile_name: name of tile being created
        """
        for t in tiles:
            x, y, tile = self.game_map[t.row][t.col]
            new_tile = self.get_tile(tile_name)
            self.game_map[t.row][t.col] = XYTile(x, y, new_tile)

    def get_tile(self, tile: str) -> Tile:
        """
        Get a copy of a tile of given type

        :param tile: name of tile
        :return: copy of tile
        """
        return copy.copy(self.tile_info[tile])

    def spawn_unit(self, tile: Position, unit: Unit, alignment: str) -> None:
        """
        Spawn a unit on the given tile with an alignment

        :param tile: name of tile
        :param unit: name of unit
        :param alignment: alignment of unit
        """
        x, y, old_unit = self.unit_map[tile.row][tile.col]
        unit_copy = copy.copy(unit)
        unit_copy.set_original_alignment(alignment)
        self.unit_map[tile.row][tile.col] = XYUnit(x, y, unit_copy)

    def move_unit(self, unit: SelectedUnit, target_tile: SelectedTile,
                  path: List[SelectedTile], location, is_attacking=False,
                  new_unit_info=None) -> None:
        """
        Moves a unit across the map through a given path

        :param unit: unit being moved
        :param target_tile: tile unit is attempting to move towards
        :param path: shortest path from the unit to the tile
        :param location: tracks where along the path the unit is
        :param is_attacking: tracks whether this path ends in a fight
        """
        can_move = True
        if path:
            start_x, start_y, start_unit_info = self.unit_map[unit.row][unit.col]
            max_movement = min(len(path) - 1, unit.unit_info.movement)
            # if no movement then check if they are attacking
            if max_movement == 0 and len(path) == 2 and unit.unit_info.can_attack:
                new_x, new_y, new_unit_info = self.unit_map[path[1].row][path[1].col]
                if new_unit_info is not None and new_unit_info.alignment != unit.unit_info.alignment and \
                        unit.unit_info.can_attack:
                    is_attacking = True

            if not new_unit_info:
                new_x, new_y, new_unit_info = self.unit_map[path[max_movement].row][path[max_movement].col]

            if location == 0:
                if new_unit_info is not None:
                    if new_unit_info.alignment != unit.unit_info.alignment and unit.unit_info.can_attack:
                        is_attacking = True
                        self.unit_map[unit.row][unit.col] = XYUnit(start_x, start_y, None)
                    else:
                        can_move = False
                else:
                    self.unit_map[unit.row][unit.col] = XYUnit(start_x, start_y, None)

            if can_move:
                cur_x, cur_y, temp = self.unit_map[path[location].row][path[location].col]
                end_point = len(path) - 2 if is_attacking else len(path) - 1
                if max_movement > 0 and location < end_point:
                    row, col, temp = path[location]
                    target_row, target_col, next_tile = path[location + 1]
                    x, y, temp = self.unit_map[row][col]
                    target_x, target_y, temp = self.unit_map[target_row][target_col]
                    offset_x = unit.unit_info.offset_x
                    offset_y = unit.unit_info.offset_y
                    duration = constants.UNIT_MOVE_DURATION
                    image = unit.unit_info.image
                    sprite = MovingUnit(image, x + offset_x, y + offset_y, target_x + offset_x, target_y + offset_y,
                                        duration, unit, target_tile, path, location + 1, is_attacking, new_unit_info,
                                        self)

                    unit.unit_info.movement = max(0, unit.unit_info.movement -
                                                  self.get_move_cost(next_tile, unit.unit_info, True))
                    self.moving_sprites.add(sprite)
                else:
                    self.unit_map[path[location].row][path[location].col] = XYUnit(cur_x, cur_y, unit.unit_info)
                    if is_attacking:
                        self.start_battle(unit.unit_info, new_unit_info)
            elif is_attacking:
                self.start_battle(unit.unit_info, new_unit_info)

    def overlay(self, tiles: List[Position], overlay_image, screen) -> None:
        """
        Overlays an image over the entire mlap

        :param tiles: list of tile positions to be overlayed
        :param overlay_image: image
        :param screen: screen object
        """
        for tile in tiles:
            tile_info = self.game_map[tile.row][tile.col]
            screen.blit(overlay_image, (tile_info.x, tile_info.y))

    def set_start_tile(self, tile: SelectedTile) -> None:
        """
        Set the start tile

        :param tile: start tile
        """
        self.start_tile = tile
        self.set_start_unit(tile)

    def set_start_unit(self, tile: SelectedTile) -> None:
        """
        Set the start unit based on tile

        :param tile: name of tile start unit is on
        """
        unit = self.unit_map[tile.row][tile.col].unit
        if unit is not None and unit.alignment == self.alignments[self.turn]:
            self.start_unit = SelectedUnit(tile.row, tile.col, unit)

    def is_mouse_on_tile(self, mouse_position: Tuple[int, int]) -> SelectedTile:
        """
        Checks if mouse is hovering over the tile

        :param mouse_position: x, y position of mouse
        :return: tile that mouse is hovering over, None if no tiles
        """
        x, y = mouse_position
        for i in range(len(self.game_map)):
            for j in range(len(self.game_map[0])):
                tile_x, tile_y, tile = self.game_map[i][j]
                tile_rect = tile.image.get_rect(topleft=(tile_x, tile_y))
                if tile_rect.collidepoint(x, y):
                    local_x, local_y = x - tile_rect.x, y - tile_rect.y
                    if tile.image.get_at((local_x, local_y)).a > 0:
                        return SelectedTile(i, j, tile)

    def get_active_units(self) -> List[Unit]:
        """
        Gets all current units on the map

        :return: List of units
        """
        active_units = []
        for row in self.unit_map:
            for xyunit in row:
                if xyunit.unit is not None:
                    active_units.append(xyunit.unit)

        return active_units

    def increment_turn(self):
        """
        Increase the turn
         * resets all unit attack + movement
        """
        self.turn = (self.turn + 1) % len(self.alignments)
        for unit in self.get_active_units():
            unit.set_can_attack(True)
            unit.set_movement(unit.speed)
            unit.take_damage(2)


def generate_attack_text(attack, attack_info) -> Tuple[List[Surface], List[Tuple[int, int]]]:
    """
    Generates the text for an attack

    :param attack: string of the attack
    :param attack_info: all the info about the attack
    :return: A list of the different string lines as well as their positions
    """
    text_list = []
    text_xy_list = []
    text = attack
    text_list.append(constants.FONT_BATTLE.render(text, True, (0, 0, 0)))
    text_xy_list.append((10, 10))
    text = str(attack_info.damage) + " - " + str(attack_info.count)
    text_list.append(constants.FONT_BATTLE.render(text, True, (0, 0, 0)))
    text_xy_list.append((10, 50))

    return text_list, text_xy_list


def get_directions(row: int) -> List[Tuple[int, int]]:
    """
    Gets the directions depending on the row, since even and odd rows need different index mathing

    :param row: row of tile
    :return: List of all the directions around tile
    """
    directions_even = [(-2, 0), (-1, 0), (1, 0), (2, 0), (1, -1), (-1, -1)]
    directions_odd = [(-2, 0), (-1, 1), (1, 1), (2, 0), (1, 0), (-1, 0)]
    if row % 2 == 0:
        return directions_even
    else:
        return directions_odd


def is_closer(start: Position, end: Position, new: Position) -> bool:
    """
    Checks if the new position is closer than the start position

    :param start: starting position
    :param end: ending position
    :param new: new tile that is compared to starting tile
    :return: True if new position is closer than start
    """
    start_row_dist = abs(end.row - start.row)
    new_row_dist = abs(end.row - new.row)
    start_col_dist = abs(end.col - start.col)
    new_col_dist = abs(end.col - new.col)

    if start_row_dist > new_row_dist:
        row_change = 1
    elif start_row_dist == new_row_dist:
        row_change = 0
    else:
        row_change = -1

    if start_col_dist > new_col_dist:
        col_change = 1
    elif start_col_dist == new_col_dist:
        col_change = 0
    else:
        col_change = -1

    return row_change + col_change > 0
