import dataclasses
import functools
from pathlib import Path
from typing import Callable

import pygame
from pygame import Vector2 as Vec2, Color
from pygame import FRect, Rect as IRect

import factoryMechanics as backend
from factoryMechanics import Factory, CopperMineBasic, Copper, Building, Contract, \
    NullResource

ORE_TEXT_COLOR = 'white'
BUILDING_TEXT_COLOR = 'white'


class ScreenInfo:
    def from_sc_size(self, sc_size: Vec2):
        self.sc_size = sc_size
        self.sc_rect = IRect((0, 0), sc_size)
        self.turnCount_area = self.sc_rect.move_to(height=25, topleft=(0,0))
        self.rem_area = self.sc_rect.move_to(height=self.sc_rect.height-25, bottom=self.sc_rect.bottom)
        self.main_area = self.rem_area.scale_by(1, 0.9).move_to(topleft=self.turnCount_area.bottomleft)
        self.menu_area = self.rem_area.scale_by(1, 0.1).move_to(topleft=self.main_area.bottomleft)
        self.base_player_area = self.main_area.scale_by(0.5, 0.5).move_to(topleft=self.main_area.topleft)
        self.player_ores_area = self.base_player_area.scale_by(0.15, 1).move_to(
            topleft=self.base_player_area.topleft)
        self.player_right_area = self.base_player_area.scale_by(0.85, 1).move_to(
            topleft=self.player_ores_area.topright)
        self.player_buildings_area = self.player_right_area.scale_by(1, 0.6).move_to(
            topleft=self.player_right_area.topleft)
        self.player_buy_area = self.player_right_area.scale_by(1, 0.4).move_to(
            topleft=self.player_buildings_area.bottomleft)
        self.left_button_area = self.menu_area.scale_by(0.5, 1).move_to(
            topleft=self.menu_area.topleft)
        self.right_button_area = self.menu_area.scale_by(0.5, 1).move_to(
            topleft=self.left_button_area.topright)
        self.contract_list_area = self.base_player_area.scale_by(1, 0.85).move_to(
            topleft=(0, 0))
        self.contract_new_area = self.base_player_area.scale_by(1, 0.15).move_to(
            bottomleft=self.base_player_area.bottomleft)
        self.overlay_area = self.sc_rect.scale_by(0.9, 0.9)  # smae cetner?
        return self


SC_INFO = ScreenInfo().from_sc_size(Vec2(1200, 750))


def clamped_subsurf(s: pygame.Surface, r: IRect | FRect):
    r2 = r.clamp(s.get_rect())
    r2.move_to(top=max(r2.top, 0), left=max(r2.left, 0), size=r2.size)
    # print(s.get_rect())
    left = max(r2.left, 0)
    top = max(r2.top, 0)
    right = min(r2.right, s.width)
    bottom = min(r2.bottom, s.height)
    width = right - left
    height = bottom - top
    r2 = IRect(left, top, width, height)
    try:
        return s.subsurface(r2)
    except ValueError:
        print(s, r2)
        raise


@functools.cache
def _load_from_fontspec(*fontspec: str, size=20):
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


def load_from_fontspec(*fontspec: str, size=20, align: int = pygame.FONT_LEFT):
    f = _load_from_fontspec(*fontspec, size=size)
    f.align = align
    return f


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
class State:
    creating_contract: Factory | None = None


@dataclasses.dataclass
class Player:
    color: pygame.Color
    factory: Factory
    area_getter: Callable[[], IRect]
    all_contracts: list[Contract]
    state: State

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

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
        buttons: list[tuple[IRect, Callable[[], None]]] = []
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
            btn_rect_outer = btn_rect.move(Vec2(SC_INFO.player_buy_area.topleft) - SC_INFO.base_player_area.topleft)
            buttons.append((btn_rect_outer, lambda m_id=m_id: self.factory.createBuilding(m_id)))
        return buttons

    def render_area(self, dest: pygame.Surface, brightness):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), brightness))
        self.render_factories(clamped_subsurf(dest, SC_INFO.player_buildings_area))
        self.render_ores(clamped_subsurf(dest, SC_INFO.player_ores_area))
        self.buttons += self.render_buy_buttons(clamped_subsurf(dest, SC_INFO.player_buy_area))

    def _render_single_contract(self, c: Contract) -> pygame.Surface:
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            c.to_string(), True, 'white', wraplength=self.area.w // 2 - 20
        )
        tex = tex.subsurface(tex.get_bounding_rect())
        dest = pygame.Surface(tex.get_rect().size + Vec2(6, 6))
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), dest.get_rect())
        dest.blit(tex, tex.get_rect(center=dest.get_rect().center))
        return dest

    def render_contracts(self, dest: pygame.Surface):
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

    def render_new_contract_button(self, dest: pygame.Surface):
        crect = dest.get_rect().inflate(-10, -10)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), crect)
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            'Propose contract', True, 'white'
        )
        dest.blit(tex, tex.get_rect(center=dest.get_rect().center))
        self.buttons += [(crect.move(Vec2(SC_INFO.contract_new_area.topleft) - SC_INFO.base_player_area.topleft), self.on_new_clicked)]

    def on_new_clicked(self):
        self.state.creating_contract = self.factory

    def render_contracts_area(self, dest: pygame.Surface, brightness):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), brightness))
        self.render_contracts(clamped_subsurf(dest, SC_INFO.contract_list_area))
        self.render_new_contract_button(clamped_subsurf(dest, SC_INFO.contract_new_area))

    def onclick(self, pos: Vec2):
        print('Recv Player.onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, action = self.buttons[c_idx]
        action()


@dataclasses.dataclass
class Overlay:
    area_getter: Callable[[], IRect]
    state: State
    players: list[Player]
    current: Contract = None

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

    @property
    def area(self):
        return self.area_getter()

    @property
    def main_section_rel(self):
        return self.area.scale_by(1, 0.85).move_to(topleft=(0, 0))

    @property
    def bot_section_rel(self):
        return self.area.scale_by(1, 0.15).move_to(topleft=self.main_section_rel.bottomleft)

    @property
    def cancel_button_rel(self):
        return self.bot_section_rel.scale_by(0.5, 1).move_to(topleft=self.bot_section_rel.topleft)

    @property
    def send_button_rel(self):
        return self.bot_section_rel.scale_by(0.5, 1).move_to(topright=self.bot_section_rel.topright)

    @property
    def left_main_rel(self):
        return self.main_section_rel.scale_by(0.5, 1).move_to(topleft=self.main_section_rel.topleft)

    @property
    def right_main_rel(self):
        return self.main_section_rel.scale_by(0.5, 1).move_to(topright=self.main_section_rel.topright)

    @property
    def other_players(self):
        return [p.factory for p in self.players if p.factory is not self.state.creating_contract]

    def display(self, dest: pygame.Surface):
        self.begin()
        if self.state.creating_contract is None:
            return
        if self.current is None:
            self.current = Contract(
                self.state.creating_contract, self.other_players[0],
                [(0, t) for t in backend.TRADE_POSSIBILITIES],
                [(0, t) for t in backend.TRADE_POSSIBILITIES], -1)
        # CANCEL
        cbb = self.cancel_button_rel.inflate(-4, -4)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), cbb)
        tex = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER).render(
            'Cancel', True, 'white'
        )
        dest.blit(tex, tex.get_rect(center=self.cancel_button_rel.center))
        # SEND
        sbb = self.send_button_rel.inflate(-4, -4)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), sbb)
        tex = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER).render(
            'Send', True, 'white'
        )
        dest.blit(tex, tex.get_rect(center=self.send_button_rel.center))
        # Register buttons, ig
        self.buttons += [(cbb, self.action_cancel)]

        self.display_side(clamped_subsurf(dest, self.left_main_rel), self.current.terms1, 1)
        self.display_side(clamped_subsurf(dest, self.right_main_rel), self.current.terms2, 2)

    def display_side(self, dest: pygame.Surface, terms: list[tuple[int, str]], side: int):
        inner = dest.get_rect().inflate(-10, -10)  # le bordure
        y = 10  # 5 + pad 5
        pygame.draw.rect(dest, pygame.Color(20, 20, 20), inner)
        if side == 1:
            tex = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER).render(
                f'{self.current.party1.name}', True, 'white'
            )
            pygame.draw.rect(dest, pygame.Color(30, 30, 30), tex.get_rect(width=inner.width - 10, centerx=inner.centerx, top=y).inflate(2, 2))
            dest.blit(tex, tex.get_rect(centerx=inner.centerx, top=y))
            y += tex.height + 10  # 5 pad each
        else:
            pygame.draw.aalines(dest, pygame.Color(50, 50, 50), True,
                                [(15, y + 11), (23, y + 19), (23, y + 3)])
            pygame.draw.aalines(dest, pygame.Color(50, 50, 50), True,
                                [(dest.width - 16, y + 11), (dest.width - 24, y + 19), (dest.width - 24, y + 3)])
            tex = load_from_fontspec('Helvetica', 'sans-serif',
                                     align=pygame.FONT_CENTER).render(
                f'{self.current.party2.name}', True, 'white'
            )
            pygame.draw.rect(dest, pygame.Color(30, 30, 30),
                             tex.get_rect(width=inner.width - 60, centerx=inner.centerx,
                                          top=y).inflate(2, 2))
            dest.blit(tex, tex.get_rect(centerx=inner.centerx, top=y))
            y += tex.height + 10  # 5 pad each
        max_w = 10
        ys = []
        for n, t in terms:
            td = "Machine Slot" if t == "Increase slot" else t
            tex = load_from_fontspec('Helvetica', 'sans-serif').render(
                f'{td}:', True, 'white'
            )
            dest.blit(tex, txr := tex.get_rect(left=inner.left + 8, top=y))
            ys.append(y)
            y += tex.height + 5
            max_w = max(max_w, txr.right)
        for y, (n, t) in zip(ys, terms):
            tex = load_from_fontspec('Courier New', 'monospace').render(
                f'-', True, 'white'
            )
            txr = tex.get_rect(left=max_w + 20, top=y)
            pygame.draw.rect(dest, Color(50, 50, 50), txx := txr.inflate(txr.h - txr.w, 0), border_radius=8)
            dest.blit(tex, txr)
            self.buttons += [(self.texas(side, txx), lambda t=t: self.decrease(side, t))]

            x = txr.right
            tex = load_from_fontspec('Courier New', 'monospace').render(
                f'{n}', True, 'white'
            )
            dest.blit(tex, txr := tex.get_rect(left=x + 20, top=y))
            x = txr.right
            tex = load_from_fontspec('Courier New', 'monospace').render(
                f'+', True, 'white'
            )
            txr = tex.get_rect(left=x + 20, top=y)
            pygame.draw.rect(dest, Color(50, 50, 50), txx := txr.inflate(txr.h - txr.w, 0),
                             border_radius=8)
            dest.blit(tex, txr)
            self.buttons += [(self.texas(side, txx), lambda t=t: self.increase(side, t))]

    def texas(self, side: int, txx: IRect):
        if side == 1:
            return txx  # no texas required
        return txx.move(Vec2(self.right_main_rel.topleft) - Vec2(self.main_section_rel.topleft))

    def decrease(self, side: int, res: str):
        ls = self.current.terms1 if side == 1 else self.current.terms2
        for i, (n, t) in enumerate(ls):
            if t == res:
                ls[i] = max(n - 1, 0), t

    def increase(self, side: int, res: str):
        ls = self.current.terms1 if side == 1 else self.current.terms2
        for i, (n, t) in enumerate(ls):
            if t == res:
                ls[i] = n + 1, t

    def action_cancel(self):
        self.state.creating_contract = None
        self.current = None

    def onclick(self, pos: Vec2):
        print('Recv Overlay.onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, action = self.buttons[c_idx]
        action()


@dataclasses.dataclass
class BottomMenu:
    area_getter: Callable[[], IRect]
    screen_num: int = 0

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

    @property
    def area(self):
        return self.area_getter()

    def display(self, dest: pygame.Surface):
        font = load_from_fontspec('Helvetica', 'sans-serif')
        font.align = pygame.FONT_CENTER
        abt = font.render(
            'Factories', True, 'white', wraplength=dest.width // 2 - 7
        )
        abt_r = abt.get_rect(left=2, centery=dest.get_rect().centery)
        cbt = font.render(
            'Contracts', True, 'white', wraplength=dest.width // 2 - 7
        )
        cbt_r = cbt.get_rect(right=dest.get_rect().right - 2,
                             centery=dest.get_rect().centery)
        abt_rr = abt_r.inflate(2, 2).move_to(height=dest.height - 5, centery=dest.get_rect().centery)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), abt_rr)
        cbt_rr = cbt_r.inflate(2, 2).move_to(height=dest.height - 5, centery=dest.get_rect().centery)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), cbt_rr)

        dest.blit(abt, abt_r)
        dest.blit(cbt, cbt_r)

        self.buttons = [(abt_rr, self.set_left), (cbt_rr, self.set_right)]

    def set_left(self):
        self.screen_num = 0

    def set_right(self):
        self.screen_num = 1

    def onclick(self, pos: Vec2):
        print('Recv Menu.onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, action = self.buttons[c_idx]
        action()


def render_player_area(dest: pygame.Surface, data):  # TODO: get the data!
    dest.fill(data)


def render_players_screen(screen: pygame.Surface, players: list[Player], playerTurn):
    for p in players:
        p.begin()
        # p.render_area(clamped_subsurf(screen, p.area))
        if players[playerTurn] == p:
            brightness = 0.3
        else:
            brightness = 0.9
        p.render_area(clamped_subsurf(screen, p.area), brightness)


def demo_factory(name: str):
    factory1 = Factory(name, [CopperMineBasic()],
                       [Copper(12),
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != NullResource)], 10)
    return factory1

def render_turnCount(dest: pygame.Surface, turn):
    font = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER)
    text = f'Turn {turn}'
    rendered = font.render(text, antialias=True, color='white', wraplength=dest.width - 5)
    dest.blit(rendered, (3,2))


def main():
    # pygame setup
    pygame.init()
    screen_real = pygame.display.set_mode(SC_INFO.sc_size, pygame.RESIZABLE | pygame.SRCALPHA)
    screen = pygame.Surface(screen_real.size, pygame.SRCALPHA)
    clock = pygame.time.Clock()
    running = True

    state = State()
    contracts = []
    p1 = Player(pygame.Color("Red"), demo_factory('Red'),
                lambda: SC_INFO.base_player_area, contracts, state)
    p2 = Player(pygame.Color("Yellow"), demo_factory('Yellow'),
                lambda: SC_INFO.base_player_area.move(SC_INFO.main_area.w / 2, 0), contracts, state)
    p3 = Player(pygame.Color("Green"), demo_factory('Green'),
                lambda: SC_INFO.base_player_area.move(0, SC_INFO.main_area.h / 2), contracts, state)
    p4 = Player(pygame.Color("Blue"), demo_factory('Blue'),
                lambda: SC_INFO.base_player_area.move(Vec2(SC_INFO.main_area.size) / 2), contracts, state)
    players = [p1, p2, p3, p4]
    contracts.append(Contract(p1.factory, p2.factory, [(3, "Copper"), (1, "Iron")], [(2, "Copper"), (1, "Increase slot")], 130))
    bm = BottomMenu(lambda: SC_INFO.menu_area)
    ol = Overlay(lambda: SC_INFO.overlay_area, state, players)

    i = 0
    t = 0
    while running:
        playerTurn = t%4
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.WINDOWRESIZED or event.type == pygame.WINDOWSIZECHANGED:
                new_size = Vec2(event.x, event.y)  # hope surf got resized??
                SC_INFO.from_sc_size(new_size)
                screen = pygame.Surface(screen_real.size, pygame.SRCALPHA)
            if event.type == pygame.MOUSEBUTTONUP:
                pos = Vec2(event.pos)
                if state.creating_contract is not None:
                    print('Click -> Overlay')
                    ol.onclick(pos - ol.area.topleft)
                else:
                    print('Click -> Regular')
                    pl = players[playerTurn]
                    if pl.area.collidepoint(pos):
                        pl.onclick(pos - pl.area.topleft)
                    if bm.area.collidepoint(pos):
                        bm.onclick(pos - bm.area.topleft)

        i += 1

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("black")

        # if state.creating_contract:
        #     print('CC')
        #     state.creating_contract = False

        render_turnCount(clamped_subsurf(screen, SC_INFO.turnCount_area), t)
        # RENDER YOUR GAME HERE
        if (i + 1) % 300 == 0:
            for p in players:
                p.factory.mineLoop(collecting=True)
            t += 1
        bm.display(clamped_subsurf(screen, bm.area))
        if bm.screen_num == 0:
            render_players_screen(screen, players, playerTurn)
        else:
            assert bm.screen_num == 1
            for p in players:
                p.begin()
                if p == players[playerTurn]:
                    brightness = 0.3
                else:
                    brightness = 0.9
                p.render_contracts_area(clamped_subsurf(screen, p.area), brightness)
            # IMPORTANT: LAST
            if state.creating_contract:
                s = pygame.Surface(screen.size, pygame.SRCALPHA)
                pygame.draw.rect(s, pygame.Color(0, 0, 0, 129), s.get_rect())
                screen.blit(s)
                # pygame.draw.rect(screen, pygame.Color(0, 0, 0, 10), screen.get_rect())
            ol.display(clamped_subsurf(screen, ol.area))

        screen_real.blit(screen)
        pygame.display.flip()
        clock.tick(60)  # limits FPS to 60

    pygame.quit()


if __name__ == '__main__':
    main()
