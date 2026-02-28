import dataclasses
import functools
from pathlib import Path
from typing import Callable

import pygame
from pygame import Vector2 as Vec2
from pygame import FRect, Rect as IRect

import factoryMechanics as backend
from factoryMechanics import Factory, CopperMineBasic, Copper, Iron, Building, Contract

ORE_TEXT_COLOR = 'white'
BUILDING_TEXT_COLOR = 'white'


class ScreenInfo:
    def from_sc_size(self, sc_size: Vec2):
        self.sc_size = sc_size
        self.sc_rect = IRect((0, 0), sc_size)
        self.main_area = self.sc_rect.scale_by(1, 0.9).move_to(topleft=(0, 0))
        self.menu_area = self.sc_rect.scale_by(1, 0.1).move_to(topleft=self.main_area.bottomleft)
        self.base_player_area = self.main_area.scale_by(0.5, 0.5).move_to(topleft=(0, 0))
        self.player_ores_area = self.base_player_area.scale_by(0.15, 1).move_to(
            topleft=self.base_player_area.topleft)
        self.player_right_area = self.base_player_area.scale_by(0.85, 1).move_to(
            topleft=self.player_ores_area.topright)
        self.player_buildings_area = self.player_right_area.scale_by(1, 0.6).move_to(
            topleft=self.player_right_area.topleft)
        self.player_buy_area = self.player_right_area.scale_by(1, 0.4).move_to(
            topleft=self.player_buildings_area.bottomleft)
        return self


SC_INFO = ScreenInfo().from_sc_size(Vec2(1200, 750))


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
    area_getter: Callable[[], IRect]
    all_contracts: list[Contract]

    def begin(self):
        self.buttons = []

    @property
    def area(self):
        return self.area_getter()

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
            if not cls.can_buy_directly:
                continue
            costs = sorted(cls.cost, key=lambda cost: cost[1])
            cost_str = (f'{abbreviate(cls.name)}: {cls.productionRate} '
                        f'{cls.produces.name}/sec (COST: '
                        + ', '.join(f'{n} {ore_s}' for n, ore_s in costs)
                        + ')')
            tex = font.render(cost_str, True, 'white')
            btn_rect = pygame.draw.rect(dest, (50, 50, 50), IRect(5, y, tex.width + 10, tex.height + 10))
            dest.blit(tex, (5 + 5, y + 5))
            y += tex.height + 15
            btn_rect_outer = btn_rect.move(Vec2(SC_INFO.player_buy_area.topleft) - Vec2(0, 0))
            buttons.append((btn_rect_outer, m_id))
        return buttons

    def render_area(self, dest: pygame.Surface):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), 0.9))
        self.render_factories(clamped_subsurf(dest, SC_INFO.player_buildings_area))
        self.render_ores(clamped_subsurf(dest, SC_INFO.player_ores_area))
        self.buttons = self.render_buy_buttons(clamped_subsurf(dest, SC_INFO.player_buy_area))

    def _render_single_contract(self, c: Contract) -> pygame.Surface:
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            c.to_string(), True, 'white', wraplength=self.area.w // 2 - 20
        )
        tex = tex.subsurface(tex.get_bounding_rect())
        dest = pygame.Surface(tex.get_rect().size + Vec2(6, 6))
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), dest.get_rect())
        dest.blit(tex, tex.get_rect(center=dest.get_rect().center))
        return dest

    def render_contracts_area(self, dest: pygame.Surface):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), 0.9))
        x = y = 5
        h_max = 1
        for c in self.all_contracts:
            if c.party2 is self.factory:
                # Reverse it ('without loss of generality, self is c.party1')
                c = Contract(c.party2, c.party1, c.terms2, c.terms2, c.timeLimit)
            if c.party1 is not self.factory:
                continue
            tex = self._render_single_contract(c)  # TODO
            w, h = tex.size
            if x + w > dest.width:
                x = 5
                y += h_max + 5  # Next 'line'
                h_max = 1
            dest.blit(tex, (x, y))
            x += w + 5
            h_max = max(h_max, h)

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
    for p in players:
        p.begin()
        # p.render_area(clamped_subsurf(screen, p.area))
        p.render_contracts_area(clamped_subsurf(screen, p.area))


def demo_factory(name: str):
    factory1 = Factory(name, [CopperMineBasic()], [Copper(2), Iron(0)], 10)
    return factory1


def main():
    # pygame setup
    pygame.init()
    screen = pygame.display.set_mode(SC_INFO.sc_size, pygame.RESIZABLE)
    clock = pygame.time.Clock()
    running = True

    contracts = []
    p1 = Player(pygame.Color("Red"), demo_factory('Red'),
                lambda: SC_INFO.base_player_area, contracts)
    p2 = Player(pygame.Color("Yellow"), demo_factory('Yellow'),
                lambda: SC_INFO.base_player_area.move_to(left=SC_INFO.main_area.w / 2), contracts)
    p3 = Player(pygame.Color("Green"), demo_factory('Green'),
                lambda: SC_INFO.base_player_area.move_to(top=SC_INFO.main_area.h / 2), contracts)
    p4 = Player(pygame.Color("Blue"), demo_factory('Blue'),
                lambda: SC_INFO.base_player_area.move_to(topleft=Vec2(SC_INFO.main_area.size) / 2), contracts)
    players = [p1, p2, p3, p4]
    contracts.append(Contract(p1.factory, p2.factory, [(3, "Copper"), (1, "Iron")], [(2, "Copper"), (1, "Increase slot")], 130))

    i = 0
    while running:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.WINDOWRESIZED or event.type == pygame.WINDOWSIZECHANGED:
                new_size = Vec2(event.x, event.y)  # hope surf got resized??
                SC_INFO.from_sc_size(new_size)
            if event.type == pygame.MOUSEBUTTONUP:
                pos = Vec2(event.pos)
                for pl in players:
                    if pl.area.collidepoint(pos):
                        pl.onclick(pos - pl.area.topleft)
        i += 1

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("black")

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
