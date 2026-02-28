import dataclasses

import pygame
from pygame import Vector2 as Vec2, Color
from pygame import FRect, Rect as IRect

from factoryMechanics import Factory

MAIN_AREA = IRect((0, 0), (1600, 900))
MENU_AREA = IRect((0, 900), (1600, 100))
SC_SIZE = Vec2(MAIN_AREA.union(MENU_AREA).size)

# TODO: this is temp.
ORE_TO_COLOR = {
    "ore1": Color(180, 180, 255),
    "ore2": Color(255, 210, 180),
    "ore3": Color(100, 255, 100),
}


@dataclasses.dataclass
class Player:
    color: pygame.Color
    factory: Factory

    def render_area(self, dest: pygame.Surface):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), 0.5))
        x = 5
        y = 5
        h_max = 1
        for b in self.factory.buildings:
            w = 40
            h = 40  # TODO?
            if x + w > dest.width:
                x = 5
                y += h_max + 5  # Next 'line'
                h_max = 1
            pygame.draw.rect(dest, ORE_TO_COLOR[b.ore.type], IRect(x, y, w, h))
            x += w + 5
            h_max = max(h_max, h)


def render_player_area(dest: pygame.Surface, data):  # TODO: get the data!
    dest.fill(data)


def render_players_screen(screen: pygame.Surface, players: list[Player]):
    base_area_rect = MAIN_AREA.scale_by(0.5, 0.5).move_to(topleft=(0, 0))

    players[0].render_area(screen.subsurface(base_area_rect))
    players[1].render_area(screen.subsurface(base_area_rect.move_to(left=MAIN_AREA.w / 2)))
    players[2].render_area(screen.subsurface(base_area_rect.move_to(top=MAIN_AREA.h / 2)))
    players[3].render_area(screen.subsurface(base_area_rect.move_to(topleft=Vec2(MAIN_AREA.size) / 2)))


def demo_factory():
    factory1 = Factory([])

    factory1.createBuilding("building1", "ore1", 1)
    factory1.createBuilding("building2", "ore2", 2)
    factory1.createBuilding("building3", "ore1", 3)

    return factory1


def main():
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode(SC_SIZE)
    clock = pygame.time.Clock()
    running = True

    p1 = Player(pygame.Color("red"), demo_factory())
    p2 = Player(pygame.Color("yellow"), demo_factory())
    p3 = Player(pygame.Color("green"), demo_factory())
    p4 = Player(pygame.Color("blue"), demo_factory())
    players = [p1, p2, p3, p4]

    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")

        # RENDER YOUR GAME HERE
        render_players_screen(screen, players)

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    pygame.quit()


if __name__ == '__main__':
    main()
