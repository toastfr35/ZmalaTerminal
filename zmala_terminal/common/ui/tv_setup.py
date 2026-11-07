"""Optional TV checks opened from Settings, with remote-only interaction."""
import tkinter as tk
import time

from zmala_terminal.common.localization import font_family
from zmala_terminal.common.platform_services import create_tv_check_transport as CheckTransport
from zmala_terminal.common.tv_check import TVCheck
from zmala_terminal.common.tv_check_messages import MESSAGES
from zmala_terminal.common.tv_profiles import DRIVERS, read_profile, write_profile, brand_artwork
from zmala_terminal.common.theme import BG, FG, MUTED, PANEL, ACCENT, BUTTON_GREEN, BUTTON_RED


class TVSetupView:
    def build_tv_setup(self):
        self.tv_check = None
        self.tv_setup_checked = False
        self.tv_check_config = None
        self.tv_check_page = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        self.tv_check_page.bind('<Configure>', lambda e: self.draw_tv_setup())
        self.tv_check_signature = None
        self.tv_check_images = []
        self.tv_check_restore = False
        self.tv_profile_page = None
        self.tv_profiles = tuple(DRIVERS)
        self.tv_profile_index = 0
        self.tv_profile_saved = read_profile(self.enrollment.path.parent / 'tv-profile.json')

    # @llr LLR-TERM-TV-019, LLR-TERM-TV-024
    def restore_tv_capabilities(self):
        """Validate saved TV identity in the background, without a setup screen."""
        if not getattr(self.tv_control, 'supports_setup', True):
            return
        profile = read_profile(self.enrollment.path.parent / 'tv-profile.json')
        self.tv_control.select_driver(profile)
        self.tv_control.power_enabled = self.tv_control.source_enabled = False
        path = self.enrollment.path.parent / 'tv-check.json'
        if not path.is_file():
            return
        self.tv_check = TVCheck(path, CheckTransport(self.tv_control), profile=profile)
        self.tv_check_restore = True
        self.tv_check.start()

    # @llr LLR-TERM-TV-019
    def begin_tv_setup(self, config):
        if self.setup_stage or not self.settings_open:
            return False
        if not getattr(self.tv_control, 'supports_setup', True):
            return False
        if self.tv_check:
            self.tv_check.close()
            self.tv_check = None
        self.tv_check_restore = False
        self.tv_control.pause_for_setup()
        if self.maintenance:
            self.maintenance.stop()
            self.maintenance = None
        self.language = config.get('language', 'en')
        self.font_family = font_family(self.language, self.available_fonts)
        self.tv_check_config = config
        self.setup_stage = 'tv'
        self.tv_profile_page = 'models'
        self.tv_profile_saved = read_profile(self.enrollment.path.parent / 'tv-profile.json')
        self.tv_profile_index = self.tv_profiles.index(self.tv_profile_saved)
        return True

    def accept_tv_profile(self, test):
        profile = self.tv_profiles[self.tv_profile_index]
        try:
            write_profile(self.enrollment.path.parent / 'tv-profile.json', profile)
        except OSError:
            self.tv_profile_page = 'profile_save_error'
            self.tv_profile_test = test
            return
        if profile != self.tv_profile_saved or test:
            self.tv_control.power_enabled = self.tv_control.source_enabled = False
            self.tv_control.select_driver(profile)
        self.tv_profile_saved = profile
        self.tv_profile_page = None
        if test:
            self.tv_check = TVCheck(self.enrollment.path.parent / 'tv-check.json',
                                    CheckTransport(self.tv_control), restart=True, profile=profile)
            self.tv_check.start()
        else:
            self.finish_tv_setup()

    def finish_tv_setup(self):
        self.tv_profile_page = None
        self.setup_stage = None
        self.last_button = time.monotonic()
        self.settings_open = True
        self.apply_config(self.pending_config or self.tv_check_config)
        self.tv_check_config = None
        self.maintenance = self.make_maintenance(self.configuration)
        self.settings_signature = None
        self.render()

    def tick_tv_setup(self):
        check = self.tv_check
        if not check:
            return
        if self.tv_check_restore:
            if check.poll():
                record = check.record if check.page == 'done' else {}
                self.tv_control.power_enabled = record.get('power', {}).get('status') == 'passed'
                self.tv_control.source_enabled = record.get('source', {}).get('status') == 'passed'
                check.close()
                self.tv_check = None
                self.tv_check_restore = False
            return
        if self.setup_stage != 'tv':
            return
        if getattr(self.tv_control, 'simulated', False):
            self.render()
        if check.poll():
            self.render()
        if check.page == 'done':
            record = check.record
            self.tv_control.power_enabled = record['power']['status'] == 'passed'
            self.tv_control.source_enabled = record['source']['status'] == 'passed'
            check.close()
            self.tv_check = None
            self.finish_tv_setup()

    def tv_setup_button(self, button):
        if self.setup_stage == 'tv' and self.tv_profile_page:
            if self.tv_profile_page == 'models':
                if button in ('left', 'right'):
                    self.tv_profile_index = (self.tv_profile_index + (1 if button == 'right' else -1)) % len(self.tv_profiles)
                elif button == 'green':
                    self.tv_profile_page = 'test_controls'
                elif button == 'red':
                    self.finish_tv_setup()
            elif self.tv_profile_page == 'test_controls' and button in ('green', 'red'):
                self.accept_tv_profile(button == 'green')
            elif self.tv_profile_page == 'profile_save_error':
                if button == 'green':
                    self.accept_tv_profile(self.tv_profile_test)
                elif button == 'red':
                    self.tv_profile_page = 'models'
            self.render()
            return True
        if self.setup_stage == 'tv' and self.tv_check:
            self.tv_check.button(button)
            self.render()
            return True
        return False

    def render_tv_setup(self):
        if self.setup_stage == 'tv' and (self.tv_check or self.tv_profile_page):
            self.video.place_forget()
            self.confirmation.place_forget()
            self.settings_canvas.place_forget()
            self.remote_help.place_forget()
            self.tv_check_page.place(x=0, y=0, relwidth=1, relheight=1)
            tk.Misc.lift(self.tv_check_page)
            self.draw_tv_setup()
            return True
        self.tv_check_page.place_forget()
        self.tv_check_signature = None
        return False

    def draw_tv_setup(self):
        check = self.tv_check
        if self.setup_stage != 'tv' or not (check or self.tv_profile_page):
            return
        w, h = self.root.winfo_width(), self.root.winfo_height()
        signature = (w, h, self.language, self.tv_profile_page, self.tv_profile_index,
                     (check.page, check.selection, check.error, str(check.record)) if check else None,
                     getattr(self.tv_control, 'simulation_scene', None))
        if signature == self.tv_check_signature:
            return
        self.tv_check_signature = signature
        c = self.tv_check_page
        c.delete('all')
        self.tv_check_images = [self.corner_logo]
        c.create_image(42, 40, image=self.corner_logo, tags='zmala-logo')
        messages = MESSAGES.get(self.language, MESSAGES['en'])
        def text(key):
            return messages[key]
        scale = min(w/1280, h/720)
        def label(value, y, size=26, color=FG, maximum=320, x=None, width=None, background=BG, bold=False, tags=()):
            picture = None
            while size >= 13:
                picture = self.text_renderer.photo(value, self.font_family, round(size*scale), background, color, int(width or w*.84), bold)
                if picture.height() <= maximum*scale:
                    break
                size -= 1
            self.tv_check_images.append(picture)
            c.create_image(w/2 if x is None else x, h*y, image=picture, anchor='center', tags=tags)
        label(text('title'), .09, 32, maximum=60)
        if self.tv_profile_page:
            self.draw_tv_profiles(w, h, label, text)
            return
        page = check.page
        scene = getattr(self.tv_control, 'simulation_scene', None)
        if getattr(self.tv_control, 'simulated', False):
            label(text('simulation'), .17, 16, MUTED, maximum=40)
            if check.busy and scene in ('standby', 'broadcast', 'terminal'):
                label(text('sim_'+scene), .45, 36, maximum=180)
                return
        if page in ('done', 'probe'):
            label(text('probe'), .45)
            return
        detail = text(page)
        if page == 'choose_tv':
            candidate = check.candidates[check.selection]
            detail += '\n\n' + candidate['name'] + '\n' + candidate['host']
        elif page == 'summary':
            detail += '\n\n' + '\n'.join(text(kind) + ' : ' + text(check.record[kind]['status']) for kind in ('power', 'source'))
        label(detail, .45, maximum=380)
        if check.error and page.endswith('_confirm'):
            label(text('error'), .76, 18, MUTED, maximum=60)
        if check.busy:
            return
        green, red = 'yes', 'no'
        if page == 'power_ready':
            green, red = 'start', 'skip'
        elif page == 'source_ready':
            green, red = 'start', 'skip'
        elif page in ('retry_power', 'retry_source', 'paired', 'unavailable'):
            green, red = 'retry', 'without'
        elif page in ('samsung_help', 'sony_help', 'no_tv'):
            green, red = 'continue', 'back'
        elif page == 'choose_tv':
            green, red = 'select', 'back'
        elif page in ('save_error', 'summary', 'source_timeout'):
            green, red = 'retry' if page == 'save_error' else 'continue', None
        for index, (key, color) in enumerate(((green, BUTTON_GREEN), (red, BUTTON_RED))):
            if key is None:
                continue
            bw, bh = int(w*.34), int(64*scale)
            x = w*(.31 if index == 0 else .69)
            bg = self.icon_renderer.rounded_button(bw, bh, color, BG)
            self.tv_check_images.append(bg)
            c.create_image(x, h*.9, image=bg)
            image = self.text_renderer.photo(text(key), self.font_family, round(23*scale), color, FG, bw-20, True)
            self.tv_check_images.append(image)
            c.create_image(x, h*.9, image=image)

    def draw_tv_profiles(self, w, h, label, text):
        c = self.tv_check_page
        profile = DRIVERS[self.tv_profiles[self.tv_profile_index]]
        if self.tv_profile_page == 'models':
            label(text('models'), .20, 24, maximum=70)
            gap, margin = 16, 34
            width = (w-2*margin-4*gap)/5
            for slot, offset in enumerate((-2, -1, 0, 1, 2)):
                info = DRIVERS[self.tv_profiles[(self.tv_profile_index+offset) % len(self.tv_profiles)]]
                selected = offset == 0
                x, y = margin+slot*(width+gap), h*(.29 if selected else .32)
                height = h*.40
                fill = '#303b50' if selected else PANEL
                if selected:
                    border = self.icon_renderer.rounded_button(int(width), int(height), ACCENT, BG)
                    self.tv_check_images.append(border)
                    c.create_image(x, y, image=border, anchor='nw', tags='tv-profile-card')
                panel = self.icon_renderer.rounded_button(int(width)-6, int(height)-6, fill, None if selected else BG)
                self.tv_check_images.append(panel)
                c.create_image(x+3, y+3, image=panel, anchor='nw', tags='tv-profile-card')
                icon_width = min(width-24, height*.42) if info.brand == 'Generic' else width-24
                picture = self.text_renderer.portrait(brand_artwork(info.brand), int(icon_width), fill)
                self.tv_check_images.append(picture)
                c.create_image(x+width/2, y+height*.32, image=picture, tags='tv-brand')
                label(text('other') if info.brand == 'Generic' else info.brand, (y+height*.63)/h,
                      23, maximum=65, x=x+width/2, width=width-18, background=fill, bold=True)
                label(info.model_family, (y+height*.84)/h, 18, MUTED, maximum=60,
                      x=x+width/2, width=width-18, background=fill)
            label(f'‹    {self.tv_profile_index+1} / {len(self.tv_profiles)}    ›', .78, 20, MUTED, maximum=40)
            green, red = 'select', 'cancel'
        else:
            if self.tv_profile_page == 'test_controls':
                picture = self.text_renderer.portrait(brand_artwork(profile.brand), int(w*.18), BG)
                self.tv_check_images.append(picture)
                c.create_image(w/2, h*.29, image=picture, tags='tv-brand')
                label(text('test_controls'), .56, 30, maximum=160)
                green, red = 'yes', 'no'
            else:
                label(text('profile_save_error'), .45, maximum=200)
                green, red = 'retry', 'cancel'
        for index, key in enumerate((green, red)):
            fill = BUTTON_GREEN if index == 0 else BUTTON_RED
            width, height = int(w*.34), int(h*.085)
            x = w*(.31 if index == 0 else .69)
            panel = self.icon_renderer.rounded_button(width, height, fill, BG)
            self.tv_check_images.append(panel)
            c.create_image(x, h*.9, image=panel)
            label(text(key), .9, 23, maximum=50, x=x, width=width-20, background=fill, bold=True)
