"""Five-card settings carousel and focused, remote-only setting pages."""
from datetime import date
import json
from pathlib import Path
import re
import tkinter as tk
import unicodedata
from zmala_terminal.common.local_settings import FIELDS, SettingsDraft
from zmala_terminal.common.settings_artwork import artwork_path
from zmala_terminal.common.localization import LANGUAGES, font_family
from zmala_terminal.common.system_settings import appliance_release
from zmala_terminal.common.theme import BG, FG, MUTED, PANEL, ACCENT, BUTTON_GREEN, BUTTON_RED, RED
from zmala_terminal.common.ui.system_settings import SystemSettingsView

MESSAGES = json.loads((Path(__file__).resolve().parents[1] / 'shared/settings-messages.json').read_text(encoding='utf-8'))
KEYS = ('settings', 'language', 'auto_answer', 'auto_framing', 'ringtone_volume',
        'carousel_portraits', 'never', 'open', 'accept', 'exit', 'current', 'tv_idle_seconds', 'ringtone', 'action_sound_volume',
        'tv_setup', 'tv_unavailable', 'reset', 'updates', 'information', 'maintenance',
        'terminal_details', 'device_id', 'os_version', 'software_version', 'ip_address',
        'account', 'account_id', 'account_name', 'no_portrait', 'unavailable',
        'shutdown', 'reboot', 'confirm_shutdown', 'confirm_reboot', 'back',
        'power_requested', 'power_failed', 'power_unavailable', 'simulated',
        'usb_power', 'usb_always_on', 'usb_camera', 'usb_camera_and_dock', 'usb_power_unavailable')

UPDATE_MESSAGES = {
    'en': {'checking': 'Checking for updates…', 'current': 'Your software is up to date.',
           'available': 'Version {version} is available.\nApply the update now?',
           'available_release': 'Terminal release {version} is available.\nApply the update now?',
           'release_label': 'Terminal release {version}',
           'submitting': 'Requesting the update…', 'unavailable': 'Update service unavailable.',
           'error': 'Could not complete the update request.', 'apply': 'Apply update', 'back': 'Back'},
    'fr': {'checking': 'Recherche de mises à jour…', 'current': 'Le logiciel est à jour.',
           'available': 'La version {version} est disponible.\nAppliquer la mise à jour maintenant ?',
           'available_release': 'La version {version} du terminal est disponible.\nAppliquer la mise à jour maintenant ?',
           'release_label': 'Version {version} du terminal',
           'submitting': 'Demande de mise à jour…', 'unavailable': 'Service de mise à jour indisponible.',
           'error': 'Impossible de traiter la demande de mise à jour.', 'apply': 'Appliquer', 'back': 'Retour'},
}

UPDATE_BLOCKERS = {
    'en': {'call': 'A call or call action is active.', 'setup': 'Setup is active.',
           'settings': 'A settings operation is active.', 'input': 'Release the remote buttons.',
           'worker': 'A background operation is finishing.', 'usb': 'Camera power is changing.',
           'tv': 'The television is still being controlled.', 'idle': 'Waiting for inactivity.',
           'terminal': 'The terminal did not acknowledge the request.'},
    'fr': {'call': 'Un appel ou une action d’appel est en cours.', 'setup': 'La configuration est en cours.',
           'settings': 'Un réglage est en cours.', 'input': 'Relâchez les boutons de la télécommande.',
           'worker': 'Une opération en arrière-plan se termine.', 'usb': 'L’alimentation de la caméra change.',
           'tv': 'La commande du téléviseur est en cours.', 'idle': 'En attente d’inactivité.',
           'terminal': 'Le terminal n’a pas confirmé la demande.'},
}
UPDATE_MESSAGES['en'].update(waiting='The update is still waiting to start.', retry='Retry')
UPDATE_MESSAGES['fr'].update(waiting='La mise à jour attend toujours de démarrer.', retry='Réessayer')


def terminal_version(root):
    for name in ('update-release.json', 'build_tools/linux/release-info.json', 'VERSION.json'):
        try:
            version = json.loads((root / name).read_text(encoding='utf-8'))['version']
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(version, str) and re.fullmatch(r'\d+\.\d+\.\d+', version):
            return version
    return None


def release_label(version):
    stamp, _, revision = version.partition('.0.')
    if len(stamp) != 8 or not revision.isdecimal():
        return version
    try:
        day = date.fromisoformat(stamp).isoformat()
    except ValueError:
        return version
    return day if revision == '1' else f'{day} ({revision})'


class SettingsView(SystemSettingsView):
    def settings_text(self, key):
        return MESSAGES.get(self.language, MESSAGES['en'])[KEYS.index(key)]

    def build_settings(self):
        self.settings_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.settings_canvas.bind('<Configure>', lambda event: self.draw_settings())
        self.settings_images = []
        self.settings_signature = None
        self.settings_version = terminal_version(Path(__file__).resolve().parents[3])
        self.settings_release = appliance_release()

    def settings_value(self, key, value):
        if key == 'tv_setup':
            from zmala_terminal.common.tv_profiles import DRIVERS
            profile = DRIVERS[getattr(self, 'tv_profile_saved', 'samsung')]
            return profile.model_family if profile.brand == 'Generic' else profile.brand
        if key in ('updates', 'information', 'maintenance'):
            return ''
        if key == 'usb_power':
            return self.settings_text('usb_'+value)
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
        image = self.icon_renderer.rounded_button(int(width), int(height), fill, None if outline else BG)
        self.settings_images.append(image)
        self.settings_canvas.create_image(x, y, image=image, anchor='nw', tags=tags)

    def settings_icon(self, key, x, y, size, background=PANEL, value=None):
        language = value if key == 'language' else 'en'
        picture = self.text_renderer.portrait(artwork_path(key, language), int(size), background)
        self.settings_images.append(picture)
        tags = ('settings-icon', 'settings-flag-'+language) if key == 'language' else ('settings-icon',)
        self.settings_canvas.create_image(x, y, image=picture, tags=tags)

    def settings_hints(self, width, height, labels=None):
        draft = self.settings_draft
        if draft.busy:
            return
        if labels is None:
            back = self.text('cancel').capitalize() if draft.editing else self.settings_text('exit')
            labels = [('‹ › ' + self.text('select').capitalize(), PANEL),
                      ('✓ ' + self.settings_text('accept' if draft.editing else 'open'), BUTTON_GREEN),
                      ('× ' + back, BUTTON_RED)]
        margin, gap = 40, 16
        part = (width-2*margin-(len(labels)-1)*gap)/len(labels)
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
        device_id = config.get('device_id', '')
        system_signature = (draft.page, draft.information, draft.maintenance_index, draft.maintenance_confirm,
                            draft.maintenance_status, config.get('display_name'), config.get('account_photo'),
                            config.get('sip', {}).get('username'))
        update_signature = (draft.updates.state, draft.updates.version) if draft.updates else None
        signature = (width, height, self.language, self.settings_open, int(self.settings_hold.progress*100),
                     device_id, draft.row, draft.editing, draft.index,
                     draft.busy, draft.error, draft.confirm_exit, update_signature, system_signature,
                     getattr(self, 'ringtone_preview_state', ''),
                     tuple(SettingsDraft.value(config, key) for key in FIELDS),
                     tuple((item['id'], item.get('name', '')) for item in config.get('ringtones', [])))
        if signature == self.settings_signature:
            return
        self.settings_signature = signature
        c.delete('all')
        self.settings_images = []
        c.create_image(42, 40, image=self.corner_logo, tags='zmala-logo')
        footer = f'ID : {device_id}'
        if self.settings_release:
            messages = UPDATE_MESSAGES.get(self.language, UPDATE_MESSAGES['en'])
            footer += '  ·  ' + messages['release_label'].format(version=release_label(self.settings_release))
        elif self.settings_version:
            footer += f'  ·  v{self.settings_version}'
        self.settings_label(footer, width/2, height-17,
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
        self.settings_label(self.settings_text('settings'), width/2, 48, width-180, 28,
                            MUTED, anchor='center', max_height=60, tags='settings-title')
        if draft.updates:
            self.draw_update_menu(width, height, draft.updates)
            return
        if draft.page == 'information':
            self.draw_information(width, height)
            return
        if draft.page == 'maintenance':
            self.draw_maintenance(width, height)
            return
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
                self.settings_icon(key, x+card_width/2, y+card_height*.25, min(112,card_width*.76),
                                   fill, SettingsDraft.value(config, key))
                self.settings_label(self.settings_text(key), x+card_width/2, y+card_height*.57,
                                    card_width-18, min(22, int(card_width*.12)), FG, fill, True,
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

    def draw_update_menu(self, width, height, menu):
        messages = UPDATE_MESSAGES.get(self.language, UPDATE_MESSAGES['en'])
        self.settings_label(self.settings_text('updates'), width/2, 132, width-100, 32,
                            bold=True, anchor='center', max_height=88)
        self.settings_icon('updates', width/2, height*.34, 96, BG)
        message, version = menu.state, menu.version
        if message == 'available' and self.settings_release:
            message, version = 'available_release', release_label(version)
        caption = messages[message].format(version=version)
        if message in ('error', 'waiting') and getattr(menu, 'blockers', None):
            reasons = UPDATE_BLOCKERS.get(self.language, UPDATE_BLOCKERS['en'])
            caption += '\n' + reasons.get(menu.blockers[0], reasons['terminal'])
        self.settings_label(caption, width/2, height*.56,
                            width-150, 28, anchor='center', max_height=height*.24)
        actions = [(messages['back'], BUTTON_RED)]
        if menu.state == 'available':
            actions.insert(0, (messages['apply'], BUTTON_GREEN))
        elif menu.state == 'error':
            actions.insert(0, (messages['retry'], BUTTON_GREEN))
        card_width = min(320, width*.34)
        for index, (label, color) in enumerate(actions):
            center = width/2 + (index-(len(actions)-1)/2)*(card_width+24)
            self.settings_panel(center-card_width/2, height-86, card_width, 48, color)
            self.settings_label(label, center, height-62, card_width-20, 20, FG, color,
                                True, anchor='center', max_height=40)

    def draw_setting_editor(self, width, height):
        draft, config = self.settings_draft, self.model.config
        key = draft.key
        self.settings_label(self.settings_text(key), width/2, 132, width-100, 32,
                            bold=True, anchor='center', max_height=88)
        if key in ('auto_answer', 'tv_idle_seconds', 'ringtone_volume', 'action_sound_volume'):
            self.draw_numeric_setting(width, height)
        elif key != 'ringtone' and len(draft.options) == 2:
            self.draw_setting_choices(width, height, two_boxes=True)
        else:
            self.draw_setting_choices(width, height)
        current = self.settings_value(key, SettingsDraft.value(config, key))
        self.settings_label(self.settings_text('current')+' : '+current, width/2, height-155,
                            width-128, 20, MUTED, anchor='center', max_height=42)
        if (key == 'usb_power' and not getattr(self, 'simulate_usb_power', False)
                and not getattr(getattr(self, 'usb_power', None), 'enabled', False)):
            self.settings_label(self.settings_text('usb_power_unavailable'), width/2, height-113,
                                width-100, 16, MUTED, anchor='center', max_height=34)
        if key == 'ringtone' and not draft.busy and not draft.error:
            preview = getattr(self, 'ringtone_preview_state', '')
            caption = self.text('help') if preview == 'error' else self.text('wait') if preview == 'waiting' else '0 %' if preview == 'muted' else '♫' if preview == 'playing' else ''
            self.settings_label(caption, width/2, height-115, width-100, 18,
                                RED if preview == 'error' else MUTED, anchor='center', max_height=36, tags='ringtone-preview')

    def draw_setting_choices(self, width, height, two_boxes=False):
        draft = self.settings_draft
        key = draft.key
        count = 2 if two_boxes else min(5, len(draft.options))
        indices = list(range(count)) if two_boxes or count < 5 else [(draft.index+offset) % len(draft.options) for offset in (-2,-1,0,1,2)]
        gap, available = (24, min(1080, width-144)) if two_boxes else (14, width-112)
        card_width = (available-gap*(count-1))/count if two_boxes or key == 'usb_power' else (available-4*gap)/5
        available = count*card_width+(count-1)*gap
        left = (width-available)/2
        for slot, index in enumerate(indices):
            value = draft.options[index]
            selected = index == draft.index
            x = left+slot*(card_width+gap)
            y = 202 if selected or two_boxes else 220
            card_height = height-214-y
            fill = '#303b50' if selected else PANEL
            tags = ('settings-editor', 'settings-choice', 'settings-choice-'+str(index))
            self.settings_panel(x, y, card_width, card_height, fill,
                                ACCENT if selected else None, tags=tags)
            if key in ('auto_framing', 'carousel_portraits'):
                name = f'framing-{int(value)}' if key == 'auto_framing' else f'portraits-{value}'
                size = min(card_width-32, card_height*.58*16/9)
                picture = self.text_renderer.portrait(artwork_path(name), int(size), fill)
                self.settings_images.append(picture)
                self.settings_canvas.create_image(x+card_width/2, y+card_height*.36,
                                                  image=picture, tags=('settings-choice-preview', name))
            else:
                self.settings_icon(key, x+card_width/2, y+card_height*.29,
                                   min(112, card_width*.72, card_height*.45), fill, value)
            self.settings_label(self.settings_value(key, value), x+card_width/2, y+card_height*(.81 if two_boxes else .71),
                                card_width-24, 30 if two_boxes else min(26, int(card_width*.14)), FG if selected else MUTED, fill,
                                selected, anchor='center', max_height=card_height*.38,
                                language=value if key == 'language' else None,
                                tags='settings-draft-value' if selected else 'settings-choice-value')
        if not two_boxes:
            self.settings_label(f'{draft.index+1} / {len(draft.options)}', width/2, height-190,
                                width-128, 14, MUTED, anchor='center', max_height=38)
        for x, arrow in ((36, '‹'), (width-36, '›')):
            self.settings_label(arrow, x, (height-12)/2, 40, 36, ACCENT,
                                anchor='center', max_height=70)

    def draw_numeric_setting(self, width, height):
        draft = self.settings_draft
        key, value = draft.key, draft.options[draft.index]
        x, y, available, panel_height = 96, 202, width-192, height-416
        self.settings_panel(x, y, available, panel_height, PANEL, ACCENT, tags='settings-editor')
        self.settings_label(self.settings_value(key, value), width/2, y+panel_height*.28,
                            available-80, 42, FG, PANEL, True, anchor='center',
                            max_height=panel_height*.36, tags='settings-draft-value')
        left, right, top = x+60, x+available-60, y+panel_height*.63
        c = self.settings_canvas
        c.create_line(left, top, right, top, fill='#43516b', width=12,
                      capstyle='round', tags='settings-bar')
        # Delays are discrete choices with uneven intervals; ticks show supported
        # stops, including Never. Positions represent stops, not elapsed time.
        selected_x = left+(right-left)*draft.index/(len(draft.options)-1)
        if draft.index:
            c.create_line(left, top, selected_x, top, fill=ACCENT, width=12,
                          capstyle='round', tags='settings-bar-fill')
        for index in range(len(draft.options)):
            tick = left+(right-left)*index/(len(draft.options)-1)
            c.create_oval(tick-2, top-2, tick+2, top+2, fill=FG, outline='', tags='settings-bar-tick')
        c.create_oval(selected_x-11, top-11, selected_x+11, top+11,
                      fill=FG, outline=ACCENT, width=3, tags='settings-bar-thumb')
        for index, position in ((0,left), (-1,right)):
            self.settings_label(self.settings_value(key, draft.options[index]), position,
                                y+panel_height*.85, 112, 17, MUTED, PANEL,
                                anchor='center', max_height=38, tags='settings-bar-endpoint')

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
