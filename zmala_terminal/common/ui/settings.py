"""Three-category carousel and focused, remote-only setting pages."""
import json
from pathlib import Path
import tkinter as tk
import unicodedata
from zmala_terminal.common.local_settings import FIELDS, CATEGORIES, CATEGORY_FIELDS, SettingsDraft
from zmala_terminal.common.localization import LANGUAGES, font_family
from zmala_terminal.common.theme import BG, FG, MUTED, PANEL, ACCENT, BUTTON_GREEN, BUTTON_RED, RED

MESSAGES = json.loads((Path(__file__).resolve().parents[1] / 'shared/settings-messages.json').read_text(encoding='utf-8'))
KEYS = ('settings', 'language', 'auto_answer', 'auto_framing', 'ringtone_volume',
        'carousel_portraits', 'never', 'open', 'accept', 'exit', 'current', 'tv_idle_seconds', 'ringtone', 'action_sound_volume',
        'calls', 'sound', 'tv_setup', 'back', 'tv_unavailable')


class SettingsView:
    def settings_text(self, key):
        if key == 'terminal':
            return self.text('terminal')
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

    def settings_icon(self, category, x, y, size, color=FG):
        """Simple outlined symbols stay legible on a TV, without emoji fonts."""
        c = self.settings_canvas
        def line(*points):
            c.create_line(*points, fill=color, width=4, capstyle='round', joinstyle='round', tags='settings-icon')
        if category == 'calls':
            c.create_rectangle(x-size*.35, y-size*.25, x+size*.15, y+size*.25,
                               outline=color, width=4, tags='settings-icon')
            line(x+size*.15, y-size*.12, x+size*.38, y-size*.28,
                 x+size*.38, y+size*.28, x+size*.15, y+size*.12)
        elif category == 'sound':
            line(x-size*.35, y-size*.12, x-size*.15, y-size*.12, x+size*.04, y-size*.3,
                 x+size*.04, y+size*.3, x-size*.15, y+size*.12, x-size*.35, y+size*.12,
                 x-size*.35, y-size*.12)
            for fraction in (.23, .39):
                c.create_arc(x-size*fraction, y-size*fraction, x+size*fraction, y+size*fraction,
                             start=-55, extent=110, style='arc', outline=color, width=4, tags='settings-icon')
        else:
            c.create_rectangle(x-size*.4, y-size*.28, x+size*.4, y+size*.22,
                               outline=color, width=4, tags='settings-icon')
            line(x, y+size*.22, x, y+size*.36)
            line(x-size*.19, y+size*.36, x+size*.19, y+size*.36)

    def settings_hints(self, width, height):
        draft = self.settings_draft
        if draft.busy:
            return
        back = self.text('cancel') if draft.editing else self.settings_text('back' if draft.category_open else 'exit')
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
                     draft.category, draft.category_open, draft.row, draft.editing, draft.index,
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
        title = self.settings_text('settings')
        if draft.category_open:
            title += '  /  ' + self.settings_text(draft.category_key)
        self.settings_label(title, width/2, 48, width-80, 28, MUTED, anchor='center', max_height=60)
        if draft.editing:
            self.draw_setting_editor(width, height)
        elif draft.category_open:
            fields = CATEGORY_FIELDS[draft.category_key]
            gap, top = 10, 106
            row_height = min(86, (height-244-gap*(len(fields)-1))/len(fields))
            for index, key in enumerate(fields):
                x, y, available = 64, top+index*(row_height+gap), width-128
                selected = key == draft.key
                fill = '#303b50' if selected else PANEL
                self.settings_panel(x, y, available, row_height, fill,
                                    ACCENT if selected else None, tags=('settings-row', 'settings-row-'+key))
                self.settings_label(('›  ' if selected else '')+self.settings_text(key),
                                    x+18, y+row_height/2, available*.58-18, 24,
                                    RED if key == 'reset' else FG, fill, True, anchor='w', max_height=row_height-12)
                self.settings_label(self.settings_value(key, SettingsDraft.value(config, key)),
                                    x+available*.61, y+row_height/2, available*.39-18, 23,
                                    MUTED, fill, anchor='w', max_height=row_height-12, tags=('settings-value', key))
        else:
            # The selected category is always centred, like the contact carousel.
            gap, margin = 22, 48
            card_width = (width-2*margin-2*gap)/3
            card_height = min(300, height-270)
            for slot, offset in enumerate((-1, 0, 1)):
                category = CATEGORIES[(draft.category+offset) % len(CATEGORIES)]
                selected = offset == 0
                x, y = margin+slot*(card_width+gap), 140 if selected else 160
                fill = '#303b50' if selected else PANEL
                self.settings_panel(x, y, card_width, card_height, fill, ACCENT if selected else None,
                                    tags=('settings-category', 'settings-category-'+category))
                self.settings_icon(category, x+card_width/2, y+card_height*.34, 94, ACCENT if selected else MUTED)
                self.settings_label(self.settings_text(category), x+card_width/2, y+card_height*.70,
                                    card_width-28, 28, FG, fill, True, anchor='center', max_height=90)
            self.settings_label(f'‹    {draft.category+1} / 3    ›', width/2, height-155,
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
