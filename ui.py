import dataclasses
import functools
from pathlib import Path

import pygame
from pygame import Vector2 as Vec2, Color
from pygame import FRect, Rect as IRect

from factoryMechanics import Factory, CopperMineBasic, Copper, Iron

ORE_TEXT_COLOR = 'white'

MAIN_AREA = IRect((0, 0), (1600, 900))
MENU_AREA = IRect((0, 900), (1600, 100))
SC_SIZE = Vec2(MAIN_AREA.union(MENU_AREA).size)
BASE_PLAYER_AREA = MAIN_AREA.scale_by(0.5, 0.5).move_to(topleft=(0, 0))
PLAYER_ORES_AREA = BASE_PLAYER_AREA.scale_by(0.15, 1).move_to(topleft=(0, 0))  # 10%?
PLAYER_BUILDINGS_AREA = BASE_PLAYER_AREA.scale_by(0.85, 1).move_to(top=0, left=PLAYER_ORES_AREA.right)


def clamped_subsurf(s: pygame.Surface, r: IRect | FRect):
    return s.subsurface(r.clamp(s.get_rect()))


@functools.cache
def load_from_fontspec(*fontspec: str):
    for f in fontspec:
        if '/' in f or '\\' in f and Path(f).is_file():  # Filename
            p = Path(f)
        else:
            p = pygame.font.match_font(f)
        if p:
            fnt = pygame.font.Font(p)
            # May segfault, so segfault early:
            _ = fnt.name
            return fnt


@dataclasses.dataclass
class Player:
    color: pygame.Color
    factory: Factory

    def render_factories(self, dest: pygame.Surface):
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
            # TODO: textures and such: modify this below
            #  and w = ..., h = ... above
            pygame.draw.rect(dest, b.ore.colour, IRect(x, y, w, h))
            x += w + 5
            h_max = max(h_max, h)

    def render_ores(self, dest: pygame.Surface):
        # Alphabetical consistent order
        ores = sorted(self.factory.ores, key=lambda i: i.type)
        font = load_from_fontspec('Helvetica', 'sans-serif')
        text = '\n'.join(f'{o.type}: {round(o.amount, 3)}' for o in ores)

        rendered = font.render(text, antialias=True, color=ORE_TEXT_COLOR,
                               wraplength=dest.width - 5)  # 2, 3
        dest.blit(rendered, (3, 2))  # PAdding: 2 above, 3 left

    def render_area(self, dest: pygame.Surface):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), 0.8))
        self.render_factories(clamped_subsurf(dest, PLAYER_BUILDINGS_AREA))
        self.render_ores(clamped_subsurf(dest, PLAYER_ORES_AREA))


def render_player_area(dest: pygame.Surface, data):  # TODO: get the data!
    dest.fill(data)


def render_players_screen(screen: pygame.Surface, players: list[Player]):
    players[0].render_area(screen.subsurface(BASE_PLAYER_AREA))
    players[1].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(left=MAIN_AREA.w / 2)))
    players[2].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(top=MAIN_AREA.h / 2)))
    players[3].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(topleft=Vec2(MAIN_AREA.size) / 2)))


def demo_factory():
    factory1 = Factory([CopperMineBasic()], [Copper(2), Iron(0)])
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

    i = 0
    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        i += 1

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")

        # RENDER YOUR GAME HERE
        if (i + 1) % 60 == 0:
            for p in players:
                p.factory.mineLoop(collecting=True)
        render_players_screen(screen, players)

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    pygame.quit()


if __name__ == '__main__':
    main()
