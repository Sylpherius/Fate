import pygame
import sys
from config import constants
from config.app import App, Position

# initialize game
pygame.init()
pygame.mixer.init()

# background music
pygame.mixer.music.load("audio/" + constants.SOUND_WELP)
pygame.mixer.music.set_volume(0)
pygame.mixer.music.play(-1)

# set screen
screen_dimensions = (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
screen = pygame.display.set_mode(screen_dimensions)

# set the title of the window
pygame.display.set_caption("Fate")

# set up the clock
clock = pygame.time.Clock()

# main game loop
app = App()
app.initialize()
left_click_handled = False
right_click_handled = False
app.spawn_unit(Position(1, 1), app.unit_info[constants.UNIT_SLIME], 'white')
app.spawn_unit(Position(4, 4), app.unit_info[constants.UNIT_SLIME], 'blue')
app.spawn_unit(Position(5, 4), app.unit_info[constants.UNIT_SLIME], 'blue')
while True:
    screen.fill('black')

    # check if mouse is hovering over a tile
    mouse_position = pygame.mouse.get_pos()
    hovered_tile = app.is_mouse_on_tile(mouse_position)

    app.update(screen, hovered_tile)

    # highlight path if a unit has been clicked
    if app.start_unit is not None and app.start_tile is not None and hovered_tile is not None:
        app.shortest_path = app.get_shortest_path(app.start_tile, hovered_tile, app.start_unit.unit_info)
    else:
        app.shortest_path = []

    for row, col, tile in app.shortest_path:
        app.overlay([Position(row, col)], app.tile_info[constants.TILE_CHOSEN].image, screen)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and not left_click_handled:
                # left mouse button clicked
                left_click_handled = True

                if hovered_tile:
                    if not app.start_unit:
                        app.set_start_tile(hovered_tile)
                        app.set_start_unit(hovered_tile)
                    else:
                        app.start_tile = None
                        if app.start_unit is not None:
                            app.move_unit(app.start_unit, hovered_tile, app.shortest_path, 0)
                        app.start_unit = None
                        app.shortest_path = []
            elif event.button == 3 and not right_click_handled:
                # right mouse button clicked
                right_click_handled = True

                if hovered_tile:
                    if not app.unit_map[hovered_tile.row][hovered_tile.col].unit:
                        app.spawn_unit(Position(hovered_tile.row, hovered_tile.col),
                                       app.unit_info[constants.UNIT_SLIME], 'white')
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                left_click_handled = False
            elif event.button == 3:
                right_click_handled = False

        app.handle_event(event)

    # update the screen
    pygame.display.flip()

    # limit frame rate
    clock.tick(constants.FRAME_RATE)
