import dataclasses
import functools
from collections import Counter
from pathlib import Path

import pygame
from pygame import Vector2 as Vec2, Color
from pygame import FRect, Rect as IRect

import factoryMechanics as backend
from factoryMechanics import Factory, CopperMineBasic, Copper, Iron, Building

ORE_TEXT_COLOR = 'white'
BUILDING_TEXT_COLOR = 'white'

MAIN_AREA = IRect((0, 0), (1600, 900))
MENU_AREA = IRect((0, 900), (1600, 100))
SC_SIZE = Vec2(MAIN_AREA.union(MENU_AREA).size)
BASE_PLAYER_AREA = MAIN_AREA.scale_by(0.5, 0.5).move_to(topleft=(0, 0))
PLAYER_ORES_AREA = BASE_PLAYER_AREA.scale_by(0.15, 1).move_to(topleft=BASE_PLAYER_AREA.topleft)
PLAYER_RIGHT_AREA = BASE_PLAYER_AREA.scale_by(0.85, 1).move_to(topleft=PLAYER_ORES_AREA.topright)
PLAYER_BUILDINGS_AREA = PLAYER_RIGHT_AREA.scale_by(1, 0.6).move_to(topleft=PLAYER_RIGHT_AREA.topleft)
PLAYER_BUY_AREA = PLAYER_RIGHT_AREA.scale_by(1, 0.4).move_to(topleft=PLAYER_BUILDINGS_AREA.bottomleft)


def clamped_subsurf(s: pygame.Surface, r: IRect | FRect):
    return s.subsurface(r.clamp(s.get_rect()))


@functools.cache
def load_from_fontspec(*fontspec: str, size=20):
    for f in fontspec:
        if '/' in f or '\\' in f and Path(f).is_file():  # Filename
            p = Path(f)
        else:
            p = pygame.font.match_font(f)
        if p:
            fnt = pygame.font.Font(p, size)
            # May segfault, so segfault early:
            _ = fnt.name
            return fnt


def render_building(b: Building):
    dest = pygame.Surface((40, 40))
    pygame.draw.rect(dest, b.ore.colour, IRect(0, 0, 40, 40))
    font = load_from_fontspec('Helvetica', 'sans-serif')
    tex = font.render(abbreviate(b.name), True, BUILDING_TEXT_COLOR)
    tex_area = tex.get_rect(center=dest.get_rect().center)
    dest.blit(tex, tex_area)
    return dest


def abbreviate(s: str):
    return ''.join(w[0] for w in s.split())


@dataclasses.dataclass
class Player:
    color: pygame.Color
    factory: Factory
    area: IRect

    def render_factories(self, dest: pygame.Surface):
        x = 5
        y = 5
        h_max = 1
        for b in self.factory.buildings:
            tex = render_building(b)
            w, h = tex.size
            if x + w > dest.width:
                x = 5
                y += h_max + 5  # Next 'line'
                h_max = 1
            dest.blit(tex, (x, y))
            x += w + 5
            h_max = max(h_max, h)

    def render_ores(self, dest: pygame.Surface):
        # Alphabetical consistent order
        ores = sorted(self.factory.ores, key=lambda i: i.type)
        font = load_from_fontspec('Helvetica', 'sans-serif')
        text = '\n'.join(f'{o.type}: {round(o.amount, 3)}' for o in ores)

        rendered = font.render(text, antialias=True, color=ORE_TEXT_COLOR,
                               wraplength=dest.width - 5)  # 2, 3
        dest.blit(rendered, (3, 2))  # Padding: 2 above, 3 left

    def render_buy_buttons(self, dest: pygame.Surface):
        font = load_from_fontspec('Helvetica', 'sans-serif')
        y = 0
        buttons: list[tuple[IRect, str]] = []
        for m_id, cls in backend.MINE_CLASSES.items():
            costs = sorted(cls.cost, key=lambda cost: cost[1])
            cost_str = (f'{abbreviate(cls.name)}: {cls.productionRate} '
                        f'{cls.produces.name}/sec (COST: '
                        + ', '.join(f'{n} {ore_s}' for n, ore_s in costs)
                        + ')')
            tex = font.render(cost_str, True, 'white')
            btn_rect = pygame.draw.rect(dest, (50, 50, 50), IRect(5, y, tex.width + 10, tex.height + 10))
            dest.blit(tex, (5 + 5, y + 5))
            y += tex.height + 15
            btn_rect_outer = btn_rect.move(Vec2(PLAYER_BUY_AREA.topleft) - Vec2(0, 0))
            buttons.append((btn_rect_outer, m_id))
        return buttons

    def render_area(self, dest: pygame.Surface):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), 0.9))
        self.render_factories(clamped_subsurf(dest, PLAYER_BUILDINGS_AREA))
        self.render_ores(clamped_subsurf(dest, PLAYER_ORES_AREA))
        self.buttons = self.render_buy_buttons(clamped_subsurf(dest, PLAYER_BUY_AREA))

    def onclick(self, pos: Vec2):
        print('Recv onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, s = self.buttons[c_idx]
        self.factory.createBuilding(s)


def render_player_area(dest: pygame.Surface, data):  # TODO: get the data!
    dest.fill(data)


def render_players_screen(screen: pygame.Surface, players: list[Player]):
    players[0].render_area(screen.subsurface(BASE_PLAYER_AREA))
    players[1].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(left=MAIN_AREA.w / 2)))
    players[2].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(top=MAIN_AREA.h / 2)))
    players[3].render_area(screen.subsurface(BASE_PLAYER_AREA.move_to(topleft=Vec2(MAIN_AREA.size) / 2)))


def demo_factory():
    factory1 = Factory([CopperMineBasic()], [Copper(2), Iron(0)], 10)
    return factory1


def main():
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode(SC_SIZE)
    clock = pygame.time.Clock()
    running = True

    p1 = Player(pygame.Color("red"), demo_factory(),
                BASE_PLAYER_AREA)
    p2 = Player(pygame.Color("yellow"), demo_factory(),
                BASE_PLAYER_AREA.move_to(left=MAIN_AREA.w / 2))
    p3 = Player(pygame.Color("green"), demo_factory(),
                BASE_PLAYER_AREA.move_to(top=MAIN_AREA.h / 2))
    p4 = Player(pygame.Color("blue"), demo_factory(),
                BASE_PLAYER_AREA.move_to(topleft=Vec2(MAIN_AREA.size) / 2))
    players = [p1, p2, p3, p4]

    i = 0
    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONUP:
                pos = Vec2(event.pos)
                for pl in players:
                    if pl.area.collidepoint(pos):
                        pl.onclick(pos - pl.area.topleft)
        i += 1

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("purple")

        # RENDER YOUR GAME HERE
        if (i + 1) % 10 == 0:
            for p in players:
                p.factory.mineLoop(collecting=True)
        render_players_screen(screen, players)

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    pygame.quit()


if __name__ == '__main__':
    main()
