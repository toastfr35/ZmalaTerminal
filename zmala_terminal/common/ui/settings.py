"""Five-card settings carousel and focused, remote-only setting pages."""
import json
from pathlib import Path
import tkinter as tk
import unicodedata
from zmala_terminal.common.local_settings import FIELDS, SettingsDraft
from zmala_terminal.common.localization import LANGUAGES, font_family
from zmala_terminal.common.theme import BG, FG, MUTED, PANEL, ACCENT, BUTTON_GREEN, BUTTON_RED, RED

MESSAGES = json.loads((Path(__file__).resolve().parents[1] / 'shared/settings-messages.json').read_text(encoding='utf-8'))
KEYS = ('settings', 'language', 'auto_answer', 'auto_framing', 'ringtone_volume',
        'carousel_portraits', 'never', 'open', 'accept', 'exit', 'current', 'tv_idle_seconds', 'ringtone', 'action_sound_volume',
        'tv_setup', 'tv_unavailable')


class SettingsView:
    def settings_text(self, key):
        if key == 'reset':
            return self.text('reset')
        return MESSAGES.get(self.language, MESSAGES['en'])[KEYS.index(key)]

    def build_settings(self):
        self.settings_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.settings_canvas.bind('<Configure>', lambda event: self.draw_settings())
        self.settings_images = []
        self.settings_signature = None

    def settings_value(self, key, value):
        if key in ('reset', 'tv_setup'):
            return ''
        if key == 'language':
            return LANGUAGES[value]['native']
        if key in ('auto_answer', 'tv_idle_seconds'):
            return self.settings_text('never') if not value else f'{value//60} min' if value % 60 == 0 else f'{value} s'
        if key == 'auto_framing':
            return self.text('yes' if value else 'no')
        # @llr LLR-TERM-AUDIO-009
        if key == 'ringtone':
            choices = self.model.config.get('ringtones', [{'id': 'nokia', 'name': 'Nokia'}])
            return next((item['name'] for item in choices if item['id'] == value), 'Nokia')
        return f'{value} %' if key in ('ringtone_volume', 'action_sound_volume') else str(value)

    def render_settings(self):
        sequence = getattr(self, 'settings_hold', None)
        active = getattr(self, 'settings_open', False) or bool(sequence and sequence.capturing)
        if active:
            self.settings_canvas.place(x=0, y=0, relwidth=1, relheight=1)
            tk.Misc.lift(self.settings_canvas)
            self.draw_settings()
        else:
            self.settings_canvas.place_forget()
            self.settings_signature = None
        return active

    # @llr LLR-TERM-UI-024
    def settings_label(self, text, x, y, width, size=22, color=FG, background=BG,
                       bold=False, anchor='nw', language=None, max_height=None, tags=()):
        if not text:
            return
        family = font_family(language or self.language, self.available_fonts)
        while True:
            picture = self.text_renderer.photo(text, family, size, background, color, int(width), bold)
            if not max_height or picture.height() <= max_height or size <= 11:
                break
            size -= 1
        # A long translated hint can still wrap at the minimum font size.
        # Keep trailing combining marks with their base while eliding, instead
        # of shrinking to unreadable glyphs or overlapping adjacent controls.
        shortened = text
        while max_height and picture.height() > max_height and len(shortened) > 1:
            while shortened and unicodedata.category(shortened[-1]).startswith('M'):
                shortened = shortened[:-1]
            shortened = shortened[:-1].rstrip()
            picture = self.text_renderer.photo(shortened+'…', family, size, background, color, int(width), bold)
        self.settings_images.append(picture)
        self.settings_canvas.create_image(x, y, image=picture, anchor=anchor, tags=tags)

    def settings_panel(self, x, y, width, height, fill, outline=None, tags=()):
        if outline:
            image = self.icon_renderer.rounded_button(int(width), int(height), outline, BG)
            self.settings_images.append(image)
            self.settings_canvas.create_image(x, y, image=image, anchor='nw', tags=tags)
            x, y, width, height = x+3, y+3, width-6, height-6
        image = self.icon_renderer.rounded_button(int(width), int(height), fill, outline or BG)
        self.settings_images.append(image)
        self.settings_canvas.create_image(x, y, image=image, anchor='nw', tags=tags)

    def settings_icon(self, key, x, y, size, color=FG):
        """Distinct outlined symbols, independent of emoji/font availability."""
        c = self.settings_canvas
        def points(values):
            return [origin+size*value for index,value in enumerate(values) for origin in [x if index%2==0 else y]]
        def line(*values):
            c.create_line(*points(values), fill=color, width=3, capstyle='round', joinstyle='round', tags='settings-icon')
        def oval(*values):
            c.create_oval(*points(values), outline=color, width=3, tags='settings-icon')
        def rect(*values):
            c.create_rectangle(*points(values), outline=color, width=3, tags='settings-icon')
        if key == 'language':
            oval(-.42,-.42,.42,.42); oval(-.19,-.42,.19,.42)
            line(-.4,0,.4,0); line(-.34,-.23,.34,-.23); line(-.34,.23,.34,.23)
        elif key == 'auto_answer':
            oval(-.42,-.42,.42,.42); line(0,-.27,0,0,.23,.13)
            line(-.08,-.53,.08,-.53)
        elif key == 'auto_framing':
            for horizontal,vertical in ((-1,-1),(-1,1),(1,-1),(1,1)):
                line(horizontal*.23,vertical*.43,horizontal*.43,vertical*.43,horizontal*.43,vertical*.23)
            oval(-.13,-.23,.13,.03)
            line(-.23,.3,-.23,.2,0,.1,.23,.2,.23,.3)
        elif key in ('ringtone_volume','action_sound_volume'):
            line(-.4,-.13,-.2,-.13,0,-.32,0,.32,-.2,.13,-.4,.13,-.4,-.13)
            for fraction in (.24,.43):
                c.create_arc(*points((-.1-fraction,-fraction,-.1+fraction,fraction)),
                             start=-55,extent=110,style='arc',outline=color,width=3,tags='settings-icon')
            if key == 'action_sound_volume':
                oval(.25,.28,.48,.51)
        elif key == 'ringtone':
            line(-.32,.2,-.24,.08,-.24,-.18,-.13,-.33,.13,-.33,.24,-.18,.24,.08,.32,.2,-.32,.2)
            oval(-.08,.3,.08,.46); line(0,-.44,0,-.34)
        elif key == 'carousel_portraits':
            for offset in (-.33,0,.33):
                oval(offset-.1,-.25,offset+.1,-.05)
                line(offset-.13,.3,offset-.13,.08,offset+.13,.08,offset+.13,.3)
        elif key in ('tv_idle_seconds','tv_setup'):
            rect(-.43,-.3,.43,.23); line(0,.23,0,.4); line(-.21,.4,.21,.4)
            if key == 'tv_setup':
                line(-.18,-.03,-.04,.1,.22,-.16)
            else:
                oval(-.16,-.22,.16,.1); line(0,-.16,0,-.06,.1,-.01)
        elif key == 'reset':
            c.create_arc(*points((-.4,-.4,.4,.4)),start=40,extent=290,style='arc',outline=color,width=3,tags='settings-icon')
            line(.06,-.35,.33,-.35,.33,-.08)

    def settings_hints(self, width, height):
        draft = self.settings_draft
        if draft.busy:
            return
        back = self.text('cancel') if draft.editing else self.settings_text('exit')
        labels = [('‹ › ' + self.text('select'), PANEL),
                  ('✓ ' + self.settings_text('accept' if draft.editing else 'open'), BUTTON_GREEN),
                  ('× ' + back, BUTTON_RED)]
        margin, gap = 40, 16
        part = (width-2*margin-2*gap)/3
        for index, (label, fill) in enumerate(labels):
            x, y = margin+index*(part+gap), height-86
            self.settings_panel(x, y, part, 48, fill, tags='settings-hint')
            self.settings_label(label, x+part/2, y+24, part-18, 20, FG, fill,
                                True, anchor='center', max_height=40)

    # @llr LLR-TERM-CONFIG-019, LLR-TERM-CONFIG-020
    def draw_settings(self):
        if not (self.settings_open or self.settings_hold.capturing):
            return
        c, config = self.settings_canvas, self.model.config
        width, height = max(900, c.winfo_width()), max(620, c.winfo_height())
        draft = self.settings_draft
        signature = (width, height, self.language, self.settings_open, int(self.settings_hold.progress*100),
                     draft.row, draft.editing, draft.index,
                     draft.busy, draft.error, draft.confirm_exit, getattr(self, 'ringtone_preview_state', ''),
                     tuple(SettingsDraft.value(config, key) for key in FIELDS),
                     tuple((item['id'], item.get('name', '')) for item in config.get('ringtones', [])))
        if signature == self.settings_signature:
            return
        self.settings_signature = signature
        c.delete('all')
        self.settings_images = []
        self.settings_label('ID : ' + config.get('device_id', ''), width/2, height-17,
                            width-64, 11, MUTED, anchor='center', tags='settings-serial')
        if not self.settings_open:
            self.settings_label(self.settings_text('settings'), width/2, height*.35, width-80,
                                36, bold=True, anchor='center')
            x, y, bar_width = width*.2, height*.55, width*.6
            self.settings_panel(x, y, bar_width, 32, PANEL)
            c.create_rectangle(x+5, y+5, x+5+(bar_width-10)*self.settings_hold.progress,
                               y+27, fill=BUTTON_RED, outline='', tags='settings-progress')
            return
        if draft.confirm_exit:
            self.draw_settings_exit(width, height)
            return
        self.settings_label(self.settings_text('settings'), width/2, 48, width-80, 28,
                            MUTED, anchor='center', max_height=60)
        if draft.editing:
            self.draw_setting_editor(width, height)
        else:
            # All settings share one carousel, with five visible cards.
            gap, margin = 14, 28
            card_width = (width-2*margin-4*gap)/5
            for slot, offset in enumerate((-2,-1,0,1,2)):
                key = FIELDS[(draft.row+offset) % len(FIELDS)]
                selected = offset == 0
                x, y = margin+slot*(card_width+gap), 126 if selected else 148
                card_height = height-185-y
                fill = '#303b50' if selected else PANEL
                self.settings_panel(x, y, card_width, card_height, fill, ACCENT if selected else None,
                                    tags=('settings-card', 'settings-card-'+key))
                self.settings_icon(key, x+card_width/2, y+card_height*.25, min(76,card_width*.55),
                                   RED if key == 'reset' else ACCENT if selected else MUTED)
                self.settings_label(self.settings_text(key), x+card_width/2, y+card_height*.57,
                                    card_width-18, 22, RED if key == 'reset' else FG, fill, True,
                                    anchor='center', max_height=card_height*.27, tags=('settings-card-label',key))
                self.settings_label(self.settings_value(key, SettingsDraft.value(config,key)),
                                    x+card_width/2, y+card_height*.83, card_width-18, 23,
                                    FG if selected else MUTED, fill, anchor='center',
                                    max_height=card_height*.23, tags=('settings-value',key))
            self.settings_label(f'‹    {draft.row+1} / {len(FIELDS)}    ›', width/2, height-150,
                                width-80, 22, MUTED, anchor='center')
        if draft.busy or draft.error:
            message = (self.settings_text('tv_unavailable') if draft.key == 'tv_setup' and draft.error
                       else self.text('wait' if draft.busy else 'help'))
            self.settings_label(message, width/2, height-115, width-100, 18,
                                MUTED if draft.busy else RED, anchor='center', max_height=42)
        self.settings_hints(width, height)

    def draw_setting_editor(self, width, height):
        draft, config = self.settings_draft, self.model.config
        key, value = draft.key, draft.options[draft.index]
        self.settings_label(self.settings_text(key), width/2, 132, width-100, 32,
                            bold=True, anchor='center', max_height=88)
        x, y, available, panel_height = 96, 202, width-192, height-416
        self.settings_panel(x, y, available, panel_height, PANEL, ACCENT, tags='settings-editor')
        self.settings_label('‹', x+35, y+panel_height/2, 48, 40, ACCENT, PANEL, anchor='center')
        self.settings_label('›', x+available-35, y+panel_height/2, 48, 40, ACCENT, PANEL, anchor='center')
        self.settings_label(self.settings_value(key, value), width/2, y+panel_height/2,
                            available-150, 42, FG, PANEL, True, anchor='center',
                            language=value if key == 'language' else None, max_height=panel_height-30,
                            tags='settings-draft-value')
        if key in ('ringtone_volume', 'action_sound_volume'):
            left, right, top = width*.25, width*.75, height-197
            self.settings_canvas.create_rectangle(left, top, right, top+12, fill=PANEL, outline='')
            if value:
                self.settings_canvas.create_rectangle(left, top, left+(right-left)*value/100,
                                                       top+12, fill=ACCENT, outline='')
        current = self.settings_value(key, SettingsDraft.value(config, key))
        self.settings_label(self.settings_text('current')+' : '+current, width/2, height-155,
                            width-128, 20, MUTED, anchor='center', max_height=42)
        if key == 'ringtone' and not draft.busy and not draft.error:
            preview = getattr(self, 'ringtone_preview_state', '')
            caption = self.text('help') if preview == 'error' else self.text('wait') if preview == 'waiting' else '0 %' if preview == 'muted' else '♫' if preview == 'playing' else ''
            self.settings_label(caption, width/2, height-115, width-100, 18,
                                RED if preview == 'error' else MUTED, anchor='center', max_height=36, tags='ringtone-preview')

    # @llr LLR-TERM-CONFIG-019
    def draw_settings_exit(self, width, height):
        self.settings_label(self.settings_text('settings'), width/2, height*.23, width-80,
                            34, bold=True, anchor='center', max_height=height*.15)
        self.settings_label(self.settings_text('exit')+' ?', width/2, height*.43, width-80,
                            36, bold=True, anchor='center', max_height=height*.2,
                            tags='settings-exit-question')
        gap = 24
        part = min(320, (width-80-gap)/2)
        y = height*.65
        for index, (answer, fill) in enumerate((('yes', BUTTON_GREEN), ('no', BUTTON_RED))):
            x = width/2-gap/2-part if index == 0 else width/2+gap/2
            tag = 'settings-exit-'+answer
            self.settings_panel(x, y, part, 70, fill, tags=tag)
            self.settings_label(('✓ ' if index == 0 else '× ')+self.text(answer),
                                x+part/2, y+35, part-24, 26, FG, fill, True,
                                anchor='center', max_height=60, tags=tag)
