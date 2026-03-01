import dataclasses
import functools
from pathlib import Path
from typing import Callable
import random

import pygame
from pygame import Vector2 as Vec2, Color
from pygame import FRect, Rect as IRect

import factoryMechanics as backend
from factoryMechanics import Factory, CopperMineBasic, CopperMineAdvanced, IronMine, Copper, Iron, Titanium, Tantalum, Building, Contract, \
    NullResource

ORE_TEXT_COLOR = 'white'
BUILDING_TEXT_COLOR = 'white'


class ScreenInfo:
    def from_sc_size(self, sc_size: Vec2):
        self.sc_size = sc_size
        self.sc_rect = IRect((0, 0), sc_size)
        self.top_area = self.sc_rect.move_to(height=50, topleft=(0,0))
        self.turnCount_area = self.top_area.scale_by(0.5, 1).move_to(topleft=self.top_area.topleft)
        self.next_turn_area = self.top_area.scale_by(0.5, 1).move_to(topright=self.top_area.topright)
        self.rem_area = self.sc_rect.move_to(height=self.sc_rect.height-self.turnCount_area.height, bottom=self.sc_rect.bottom)
        self.main_area = self.rem_area.scale_by(1, 0.9).move_to(topleft=self.turnCount_area.bottomleft)
        self.menu_area = self.rem_area.scale_by(1, 0.1).move_to(topleft=self.main_area.bottomleft)
        self.base_player_area = self.main_area.scale_by(0.5, 0.5).move_to(topleft=self.main_area.topleft)
        self.base_player_area_rel = self.base_player_area.move_to(topleft=(0, 0))
        self.player_ores_area = self.base_player_area.scale_by(0.18, 1).move_to(
            topleft=(0, 0))
        self.player_right_area = self.base_player_area.scale_by(0.82, 1).move_to(
            topleft=self.player_ores_area.topright)
        self.player_buildings_area = self.player_right_area.scale_by(1, 0.4).move_to(
            topleft=self.player_right_area.topleft)
        self.player_buy_area = self.player_right_area.scale_by(1, 0.6).move_to(
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
def _load_from_fontspec(*fontspec: str, size=20, bold=False):
    for f in fontspec:
        if '/' in f or '\\' in f and Path(f).is_file():  # Filename
            p = Path(f)
        else:
            p = pygame.font.match_font(f, bold=bold)
        if p:
            fnt = pygame.font.Font(p, size)
            # May segfault, so segfault early:
            _ = fnt.name
            return fnt


def load_from_fontspec(*fontspec: str, size=20, align: int = pygame.FONT_LEFT,
                       strikethrough: bool = False, bold: bool = False):
    f = _load_from_fontspec(*fontspec, size=size, bold=bold)
    f.align = align
    f.strikethrough = strikethrough
    return f


def render_building(b: Building):
    dest = pygame.Surface((40, 40))
    pygame.draw.rect(dest, b.ore.colour, IRect(0, 0, 40, 40))
    font = load_from_fontspec('Helvetica', 'sans-serif')
    tex = font.render(b.get_abbreviation(), True, BUILDING_TEXT_COLOR)
    tex_area = tex.get_rect(center=dest.get_rect().center)
    dest.blit(tex, tex_area)
    return dest


def render_emptySlot():
    dest = pygame.Surface((40, 40))
    pygame.draw.rect(dest, 'black', IRect(0, 0, 40, 40))
    return dest


@dataclasses.dataclass
class State:
    creating_contract: Factory | None = None
    req_next_turn: bool = False


@dataclasses.dataclass
class Player:
    color: pygame.Color
    factory: Factory
    area_getter: Callable[[], IRect]
    all_contracts: list[Contract]
    state: State
    incoming_contracts: list[Contract] = dataclasses.field(default_factory=list)

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

    @property
    def area(self):
        return self.area_getter()

    def render_factories(self, dest: pygame.Surface):
        x = 5
        y = 5
        h_max = 1
        for i in range(self.factory.capacity):
            if i < len(self.factory.buildings): 
                tex = render_building(self.factory.buildings[i])
            else:
                tex = render_emptySlot()
            w, h = tex.size
            if x + w > dest.width:
                x = 5
                y += h_max + 5  # Next 'line'
                h_max = 1
            dest.blit(tex, (x, y))
            x += w + 5
            h_max = max(h_max, h)

    def render_ores(self, dest: pygame.Surface):
        ores = sorted(self.factory.ores, key=lambda i: [*backend.RESOURCE_CLASSES].index(i.type))
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
            cost_str = (f'{cls.get_abbreviation()}: {cls.productionRate} '
                        f'{cls.produces.name}/sec (COST: '
                        + ', '.join(f'{n} {ore_s}' for n, ore_s in costs)
                        + ')')
            text_color = 'white' if self.factory.can_buy(m_id) else (120, 120, 120)
            rect_color = ((50,) if self.factory.can_buy(m_id) else (68,)) * 3
            tex = font.render(cost_str, True, text_color)
            btn_rect = pygame.draw.rect(dest, rect_color, IRect(5, y, tex.width + 10, tex.height + 10))
            dest.blit(tex, (5 + 5, y + 5))
            y += tex.height + 15
            btn_rect_outer = btn_rect.move(Vec2(SC_INFO.player_buy_area.topleft))
            buttons.append((btn_rect_outer, lambda m_id=m_id: self.factory.createBuilding(m_id)))
        return buttons

    def maybe_show_blocked(self, dest: pygame.Surface):
        if not self.factory.blockedFromPlaying:
            return
        self.buttons = []
        tex = load_from_fontspec('Helvetica', 'sans-serif',
                                 bold=True, align=pygame.FONT_CENTER,
                                 size=100).render(
            f'BLOCKED\nFOR {self.factory.blockedFromPlaying} TURNS',
            True, (200,) * 3 + (200,),
            wraplength=dest.width - 8
        )
        tex_shadow = load_from_fontspec('Helvetica', 'sans-serif',
                                 bold=True, align=pygame.FONT_CENTER,
                                 size=100).render(
            f'BLOCKED\nFOR {self.factory.blockedFromPlaying} TURNS',
            True, 'black',
            wraplength=dest.width - 8
        )
        tex_shadow_c = pygame.Surface(Vec2(tex_shadow.size) + (10, 10), pygame.SRCALPHA)
        tex_shadow_c.blit(tex_shadow, tex_shadow.get_rect(center=tex_shadow_c.get_rect().center))
        # tex_shadow_c2 = pygame.Surface(tex_shadow_c.size, pygame.SRCALPHA)
        tex_shadow_c2 = pygame.transform.box_blur(tex_shadow_c, 5)
        dest.blit(tex_shadow_c2, tex_shadow_c2.get_rect(center=dest.get_rect().center))
        dest.blit(tex, tex.get_rect(center=dest.get_rect().center))

    def render_area(self, dest: pygame.Surface, brightness):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), brightness))
        self.render_factories(clamped_subsurf(dest, SC_INFO.player_buildings_area))
        self.render_ores(clamped_subsurf(dest, SC_INFO.player_ores_area))
        self.buttons += self.render_buy_buttons(clamped_subsurf(dest, SC_INFO.player_buy_area))
        self.maybe_show_blocked(dest)

    def _render_single_contract(self, c: Contract) -> pygame.Surface:
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            c.to_string(), True, 'white', wraplength=self.area.w // 2 - 20
        )
        tex = tex.subsurface(tex.get_bounding_rect())
        dest = pygame.Surface(tex.get_rect().size + Vec2(6, 6))
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), dest.get_rect())
        dest.blit(tex, tex.get_rect(center=dest.get_rect().center))
        return dest

    def render_contracts(self, dest: pygame.Surface, time):
        x = y = 5
        h_max = 1
        for c in self.all_contracts:
            print(time)
            print(c.timeLimit)
            print('---')
            if c.timeLimit <= time:
                continue
            if c.party2 is self.factory:
                # Reverse it ('without loss of generality, self is c.party1')
                c = c.op()
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

    def render_contracts_area(self, dest: pygame.Surface, brightness, time):
        dest.fill(self.color.lerp(pygame.Color(0, 0, 0), brightness))
        self.render_contracts(clamped_subsurf(dest, SC_INFO.contract_list_area), time)
        self.render_new_contract_button(clamped_subsurf(dest, SC_INFO.contract_new_area))
        self.maybe_show_blocked(dest)

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
    current: Contract | None = None
    t: int = 0

    CANCEL_TEXT = 'Cancel'
    SEND_TEXT = 'Send'

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

    @property
    def area(self):
        return self.area_getter()

    @property
    def main_section_rel(self):
        return self.area.scale_by(1, 0.75).move_to(topleft=(0, 0))

    @property
    def deadline_container_rel(self):
        return self.area.scale_by(1, 0.1).move_to(topleft=self.main_section_rel.bottomleft)

    @property
    def deadline_intro_rel(self):
        return self.deadline_container_rel.scale_by(0.5, 1).move_to(topleft=self.deadline_container_rel.topleft)

    @property
    def deadline_main_rel(self):
        return self.deadline_container_rel.scale_by(0.5, 1).move_to(topleft=self.deadline_intro_rel.topright)

    @property
    def bot_section_rel(self):
        return self.area.scale_by(1, 0.15).move_to(topleft=self.deadline_container_rel.bottomleft)

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
        return [p.factory for p in self.players if p.factory is not self.current_player]

    @property
    def current_player(self):
        return self.state.creating_contract

    @property
    def disabled(self):
        return self.current.is_null()

    def display(self, dest: pygame.Surface):
        self.begin()
        if self.current_player is None:
            return
        if self.current is None:
            self.current = Contract(
                self.current_player, self.other_players[0],
                [(0, t) for t in backend.TRADE_POSSIBILITIES],
                [(0, t) for t in backend.TRADE_POSSIBILITIES], self.t + 30)  # TODO DEFAULT
        # CANCEL
        cbb = self.cancel_button_rel.inflate(-4, -4)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50), cbb)
        tex = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER).render(
            self.CANCEL_TEXT, True, 'white'
        )
        dest.blit(tex, tex.get_rect(center=self.cancel_button_rel.center))
        # SEND
        sbb = self.send_button_rel.inflate(-4, -4)
        pygame.draw.rect(dest, pygame.Color(50, 50, 50) if not self.disabled else pygame.Color(68, 68, 68), sbb)
        tex = load_from_fontspec(
            'Helvetica', 'sans-serif', align=pygame.FONT_CENTER, strikethrough=self.disabled
        ).render(
            self.SEND_TEXT, True, pygame.Color(120, 120, 120) if self.disabled else 'white'
        )
        dest.blit(tex, tex.get_rect(center=self.send_button_rel.center))
        # Register buttons, ig
        self.buttons += [(cbb, self.action_cancel)]
        self.buttons += [(sbb, self.action_submit)]

        self.display_deadline(dest)

        self.display_side(clamped_subsurf(dest, self.left_main_rel), self.current.terms1, 1)
        self.display_side(clamped_subsurf(dest, self.right_main_rel), self.current.terms2, 2)

    def display_deadline(self, dest: pygame.Surface):
        dlc = self.deadline_container_rel.inflate(-4, -4)
        pygame.draw.rect(dest, pygame.Color(20, 20, 20), dlc)
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            'Contract deadline (turn number):', True, 'white'
        )
        dest.blit(tex, tex.get_rect(center=self.deadline_intro_rel.center))
        tex = load_from_fontspec('Courier New', 'monospace').render(
            f'{self.current.timeLimit:^3}', True, 'white'
        )
        dest.blit(tex, txr := tex.get_rect(center=self.deadline_main_rel.center))
        # side=1 to force no texas adjustment
        xl = self._display_button(dest, 1, '<deadline>', tex.height, txr.left, txr.top, -1, is_left=True)
        xl = self._display_button(dest, 1, '<deadline>', tex.height, xl, txr.top, -10, is_left=True)

        xr = self._display_button(dest, 1, '<deadline>', tex.height, txr.right, txr.top, 1)
        xr = self._display_button(dest, 1, '<deadline>', tex.height, xr, txr.top, 10)
        # dest.blit(tex, txr := tex.get_rect(left=x + 20, top=y))
        # x = txr.right

    def display_side(self, dest: pygame.Surface, terms: list[tuple[int, str]], side: int):
        inner = dest.get_rect().inflate(-5, -5)  # le bordure
        y = 10  # 5 + pad 5
        pygame.draw.rect(dest, pygame.Color(20, 20, 20), inner)
        if side == 1:
            tex = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER).render(
                f'You give', True, 'white'
            )
            pygame.draw.rect(dest, pygame.Color(30, 30, 30), tex.get_rect(width=inner.width - 10, centerx=inner.centerx, top=y).inflate(2, 2))
            dest.blit(tex, tex.get_rect(centerx=inner.centerx, top=y))
            y += tex.height + 10  # 5 pad each
        else:
            self._render_player_lr_arrows(dest, y)
            tex = load_from_fontspec('Helvetica', 'sans-serif',
                                     align=pygame.FONT_CENTER).render(
                f'{self.current.party2.name} gives', True, 'white'
            )
            pygame.draw.rect(dest, pygame.Color(30, 30, 30),
                             tex.get_rect(width=inner.width - 60, centerx=inner.centerx,
                                          top=y).inflate(2, 2))
            dest.blit(tex, tex.get_rect(centerx=inner.centerx, top=y))
            y += tex.height + 10  # 5 pad each

        max_w = 10
        ys = []
        heights = []
        for n, t in terms:
            td = "Machine Slot" if t == "Increase slot" else t
            tex = load_from_fontspec('Helvetica', 'sans-serif').render(
                f'{td}:', True, 'white'
            )
            dest.blit(tex, txr := tex.get_rect(left=inner.left + 8, top=y))
            ys.append(y)
            heights.append(tex.height)
            y += tex.height + 5
            max_w = max(max_w, txr.right)
        for h, y, (n, t) in zip(heights, ys, terms):
            x = max_w

            x = self._display_button(dest, side, t, h, x, y, -10, offset=25)
            x = self._display_button(dest, side, t, h, x, y, -1)

            tex = load_from_fontspec('Courier New', 'monospace').render(
                f'{n:>2}', True, 'white'
            )
            dest.blit(tex, txr := tex.get_rect(left=x + 20, top=y))
            x = txr.right

            x = self._display_button(dest, side, t, h, x, y, 1, offset=15)
            x = self._display_button(dest, side, t, h, x, y, 10)

    def _render_player_lr_arrows(self, dest: pygame.Surface, y: int):
        lpt = [(15, y + 11), (23, y + 19), (23, y + 3)]
        lbb = pygame.draw.aalines(dest, pygame.Color(50, 50, 50), True, lpt)
        pygame.draw.polygon(dest, pygame.Color(150, 150, 150), lpt)
        rpt = [(dest.width - 16, y + 11), (dest.width - 24, y + 19),
               (dest.width - 24, y + 3)]
        pygame.draw.polygon(dest, pygame.Color(150, 150, 150), rpt)
        rbb = pygame.draw.aalines(dest, pygame.Color(50, 50, 50), True, rpt)
        self.buttons += [(self.texas(2, lbb), self.pleft), (self.texas(2, rbb), self.pright)]

    def _display_button(self, dest: pygame.Surface, side: int, resource: str,
                        h: int, x: int, y: int, n: int, offset: int = 20,
                        is_left: bool = False) -> int:
        tex = load_from_fontspec('Courier New', 'monospace', size=15).render(
            f'{f"{n:+}" if abs(n) != 1 else f"{n:+}"[0]}', True, 'white'
        )
        txx = IRect().move_to(height=h, width=max(h, tex.width + 10), left=x + offset, top=y)
        if is_left:
            txx.right = x - offset  # overwrite .left
        txr = txx.move_to(size=tex.size, center=txx.center)
        pygame.draw.rect(dest, Color(50, 50, 50), txx, border_radius=8)
        dest.blit(tex, txr)
        self.buttons += [
            (self.texas(side, txx), lambda: self.adjust_quantity(side, resource, n))]
        if is_left:
            x = txr.left
        else:
            x = txr.right
        return x

    def pleft(self):
        self.current.party2 = self.other_players[
            (self.other_players.index(self.current.party2) + 1) % len(self.other_players)]

    def pright(self):
        self.current.party2 = self.other_players[
            (self.other_players.index(self.current.party2) + 1) % len(self.other_players)]

    def texas(self, side: int, txx: IRect):
        if side == 1:
            return txx  # no texas required
        return txx.move(Vec2(self.right_main_rel.topleft) - Vec2(self.main_section_rel.topleft))

    def adjust_quantity(self, side: int, res: str, amount: int) -> None:
        ls = self.current.terms1 if side == 1 else self.current.terms2
        if res == '<deadline>':
            self.current.timeLimit = max(self.current.timeLimit + amount, self.t+4)
            return
        for i, (n, t) in enumerate(ls):
            if t == res:
                ls[i] = (max(n + amount, 0), t)

    def postprocess_contract(self):
        self.current.terms1 = [(n, t) for n, t in self.current.terms1 if n > 0]
        self.current.terms2 = [(n, t) for n, t in self.current.terms2 if n > 0]

    def action_cancel(self):
        self.state.creating_contract = None
        self.current = None

    def action_submit(self):
        if self.disabled:
            print('Cannot accept null contract')
            return
        self.state.creating_contract = None
        self.postprocess_contract()
        player = next(p for p in self.players if p.factory is self.current.party2)
        player.incoming_contracts.append(self.current)
        self.current = None

    def onclick(self, pos: Vec2):
        print('Recv Overlay.onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, action = self.buttons[c_idx]
        action()


# What is this accursed inheritance borne out of sheer laziness?!
class FinalContractAgreement(Overlay):
    current_player_object: Player | None = None
    CANCEL_TEXT = 'Reject contract'
    SEND_TEXT = 'Accept contract'

    @property
    def current_player(self):
        return self.current_player_object.factory if self.current_player_object else None

    def _display_button(self, dest: pygame.Surface, side: int, resource: str,
                        h: int, x: int, y: int, n: int, offset: int = 20,
                        is_left: bool = False) -> int:
        return x  # Nah, no editing it.

    def _render_player_lr_arrows(self, dest: pygame.Surface, y: int):
        pass  # Nah, no changing target player for you

    def action_cancel(self):
        del self.current_player_object.incoming_contracts[0]
        self.current = None
        self.current_player_object = None

    def action_submit(self):
        self.current_player_object.all_contracts.append(self.current)
        del self.current_player_object.incoming_contracts[0]
        self.current = None
        self.current_player_object = None
        print('Submitted')


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


def render_players_screen(screen: pygame.Surface, players: list[Player], playerTurn):
    for p in players:
        p.begin()
        # p.render_area(clamped_subsurf(screen, p.area))
        if players[playerTurn] == p:
            if p.factory.blockedFromPlaying > 0:
                brightness = 0.6
            else:
                brightness = 0.3
        else:
            brightness = 0.9
        p.render_area(clamped_subsurf(screen, p.area), brightness)


def demo_factory(name: str):
    factoryA = Factory(name, [IronMine()],
                       [Copper(10), Iron(30), 
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != Iron and oc != NullResource)], 10)
    factoryB = Factory(name, [CopperMineBasic()],
                       [Copper(95),
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != NullResource)], 10)
    factoryC = Factory(name, [CopperMineAdvanced()],
                       [Copper(5), Iron(15),
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != Iron and oc != NullResource)], 10)
    factoryD = Factory(name, [IronMine()],
                       [Copper(0), 
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != NullResource)], 12)
    factoryE = Factory(name, [CopperMineBasic()],
                       [Copper(33), Iron(10),
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != NullResource)], 11)
    factoryL = Factory(name, [],
                       [Copper(0),
                        *(oc(0) for oc in backend.RESOURCE_CLASSES.values()
                          if oc != Copper and oc != NullResource)], 10)
    Luck = random.randint(1, 100)
    if Luck < 20:
        factoryN = factoryA
    elif Luck < 39:
        factoryN = factoryB
    elif Luck < 58:
        factoryN = factoryC
    elif Luck < 77:
        factoryN = factoryD
    elif Luck < 96:
        factoryN = factoryE
    else:
        factoryN = factoryL
    return factoryN


@dataclasses.dataclass
class Topbar:
    area_getter: Callable[[], IRect]
    state: State

    def begin(self):
        self.buttons: list[tuple[IRect, Callable[[], None]]] = []

    @property
    def area(self):
        return self.area_getter()

    def render(self, dest: pygame.Surface, turn: int):
        self.begin()
        self.render_turn_count(clamped_subsurf(dest, SC_INFO.turnCount_area), turn)
        self.render_next_turn(clamped_subsurf(dest, SC_INFO.next_turn_area))

    def render_turn_count(self, dest: pygame.Surface, turn: int):
        font = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER)
        text = f'Turn {turn}'
        rendered = font.render(text, antialias=True, color='white', wraplength=dest.width - 5)
        dest.blit(rendered, rendered.get_rect().move_to(center=dest.get_rect().center))

    def render_next_turn(self, dest: pygame.Surface):
        cr = pygame.draw.rect(dest, Color(50, 50, 50), dest.get_rect().inflate(-8, -8))
        tex = load_from_fontspec('Helvetica', 'sans-serif').render(
            'Next Turn', True, 'white'
        )
        dest.blit(tex, tex.get_rect().move_to(center=dest.get_rect().center))
        self.buttons += [(cr.move(Vec2(SC_INFO.next_turn_area.topleft) - SC_INFO.top_area.topleft),
                          self.next_turn_action)]

    def next_turn_action(self):
        self.state.req_next_turn = True

    def onclick(self, pos: Vec2):
        print('Recv Topbar.onclick')
        c_idx = IRect(pos, (1, 1)).collidelist([r for r, _name in self.buttons])
        if c_idx == -1:
            print(pos, [r for r, _name in self.buttons])
            return
        _, action = self.buttons[c_idx]
        action()

# def render_turnCount(dest: pygame.Surface, turn):
#     font = load_from_fontspec('Helvetica', 'sans-serif', align=pygame.FONT_CENTER)
#     text = f'Turn {turn}'
#     rendered = font.render(text, antialias=True, color='white', wraplength=dest.width - 5)
#     dest.blit(rendered, rendered.get_rect().move_to(center=dest.get_rect().center))


class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.music_event = pygame.event.custom_type()
        pygame.mixer.music.set_endevent(self.music_event)
        self.rotation = ["CaveV1.wav", "CaveFast.wav"]
        self.current = 0

    def start(self):
        pygame.mixer.music.load(self.rotation[self.current])
        pygame.mixer.music.play()
        pygame.mixer.music.set_volume(0.5)

    def play_next(self):
        self.current = (self.current + 1) % len(self.rotation)
        self.start()

    def update(self, e):
        if e.type == self.music_event:
            # end event
            self.play_next()


def main():
    # pygame setup
    pygame.init()
    pygame.mixer.init()
    screen_real = pygame.display.set_mode(SC_INFO.sc_size, pygame.RESIZABLE | pygame.SRCALPHA)
    screen = pygame.Surface(screen_real.size, pygame.SRCALPHA)
    clock = pygame.time.Clock()
    running = True

    music_player = MusicPlayer()
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
    tb = Topbar(lambda: SC_INFO.top_area, state)
    ol = Overlay(lambda: SC_INFO.overlay_area, state, players)
    olf = FinalContractAgreement(lambda: SC_INFO.overlay_area, state, players)

    i = 0
    t = 0

    music_player.start()
    while running:
        playerTurn = t%4
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.WINDOWRESIZED or event.type == pygame.WINDOWSIZECHANGED:
                new_size = Vec2(event.x, event.y)  # hope surf got resized??
                SC_INFO.from_sc_size(new_size)
                screen = pygame.Surface(screen_real.size, pygame.SRCALPHA)
            if event.type == music_player.music_event:
                music_player.update(event)
            if event.type == pygame.MOUSEBUTTONUP:
                pos = Vec2(event.pos)
                if players[playerTurn].incoming_contracts:
                    print('Click -> OverlayFinal')
                    olf.onclick(pos - olf.area.topleft)
                elif state.creating_contract is not None:
                    print('Click -> Overlay')
                    ol.onclick(pos - ol.area.topleft)
                else:
                    print('Click -> Regular')
                    pl = players[playerTurn]
                    if pl.factory.blockedFromPlaying <= 0:
                        ## Can't buy buildings if failed contract recently
                        if pl.area.collidepoint(pos):
                            pl.onclick(pos - pl.area.topleft)
                    else:
                        print('[blocked]')
                    if bm.area.collidepoint(pos):
                        bm.onclick(pos - bm.area.topleft)
                    if tb.area.collidepoint(pos):
                        tb.onclick(pos - tb.area.topleft)

        i += 1

        # fill the screen with a color to wipe away anything from last frame
        screen.fill("black")

        # if state.creating_contract:
        #     print('CC')
        #     state.creating_contract = False

        # render_turnCount(clamped_subsurf(screen, SC_INFO.turnCount_area), t)
        # RENDER YOUR GAME HERE
        if state.req_next_turn:
            state.req_next_turn = False
            t += 1
            # Only mine once everyone has had a turn
            if t%4 == 0:
                for p in players:
                    if p.factory.blockedFromPlaying > 0:
                        p.factory.blockedFromPlaying -= 1
                        continue
                    p.factory.mineLoop(collecting=True)

            ## Check if any contracts need to be executed
            for contract in contracts:
                if t == contract.timeLimit:
                    contract.checkFulfilled()

            ol.t = t
            olf.t = t
        bm.display(clamped_subsurf(screen, bm.area))
        tb.render(clamped_subsurf(screen, tb.area), t)
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
                p.render_contracts_area(clamped_subsurf(screen, p.area), brightness, t)
            # IMPORTANT: LAST
            if state.creating_contract:
                s = pygame.Surface(screen.size, pygame.SRCALPHA)
                pygame.draw.rect(s, pygame.Color(0, 0, 0, 129), s.get_rect())
                screen.blit(s)
                # pygame.draw.rect(screen, pygame.Color(0, 0, 0, 10), screen.get_rect())
            ol.display(clamped_subsurf(screen, ol.area))
        p = players[playerTurn]
        # print(f'{p.incoming_contracts=}')
        if p.incoming_contracts:
            s = pygame.Surface(screen.size, pygame.SRCALPHA)
            pygame.draw.rect(s, pygame.Color(0, 0, 0, 129), s.get_rect())
            screen.blit(s)
            c = p.incoming_contracts[0]
            olf.current = c.op()
            olf.current_player_object = p
            olf.display(clamped_subsurf(screen, olf.area))


        screen_real.blit(screen)
        pygame.display.flip()
        clock.tick(60)  # limits FPS to 60

    pygame.quit()


if __name__ == '__main__':
    main()
