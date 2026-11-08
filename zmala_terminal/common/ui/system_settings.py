"""Information and maintenance pages rendered on the Settings canvas."""
from zmala_terminal.common.local_settings import MAINTENANCE_ACTIONS
from zmala_terminal.common.theme import ACCENT, BG, BUTTON_GREEN, BUTTON_RED, FG, MUTED, PANEL, RED


class SystemSettingsView:
    # @llr LLR-TERM-CONFIG-020
    def draw_information(self, width, height):
        draft, config = self.settings_draft, self.model.config
        self.settings_label(self.settings_text('information'), width/2, 116, width-100, 32,
                            bold=True, anchor='center', max_height=65)
        left, top, gap = 42, 165, 20
        panel_width = (width-2*left-gap)/2
        panel_height = height-top-115
        right = left+panel_width+gap
        for x, title in ((left, 'terminal_details'), (right, 'account')):
            self.settings_panel(x, top, panel_width, panel_height, PANEL, tags='information-panel')
            self.settings_label(self.settings_text(title), x+22, top+20, panel_width-44, 25, FG, PANEL,
                                True, max_height=42)
        unavailable = self.settings_text('unavailable')
        os_version, address = draft.information or (self.text('wait'), self.text('wait'))
        values = (('device_id', config.get('device_id')), ('os_version', os_version),
                  ('software_version', self.settings_version), ('ip_address', address))
        row_height = (panel_height-82)/4
        for index, (key, value) in enumerate(values):
            self.information_value(key, value or unavailable, left+22, top+66+index*row_height,
                                   panel_width-44, row_height)
        photo_size = min(180, int(panel_height*.40), int(panel_width*.46))
        photo = self.contact_image({'photo': config.get('account_photo')}, photo_size, PANEL)
        portrait_y = top+65+photo_size/2
        if photo:
            self.settings_images.append(photo)
            self.settings_canvas.create_image(right+panel_width/2, portrait_y, image=photo,
                                              tags='information-portrait')
        else:
            self.settings_icon('account', right+panel_width/2, portrait_y-9, photo_size-24)
            self.settings_label(self.settings_text('no_portrait'), right+panel_width/2,
                                portrait_y+photo_size/2-7, panel_width-40, 14, MUTED, PANEL,
                                anchor='center', max_height=28, tags='information-no-portrait')
        self.information_value('account_name', config.get('display_name') or unavailable,
                               right+22, top+74+photo_size, panel_width-44, row_height)
        self.information_value('account_id', config.get('sip', {}).get('username') or unavailable,
                               right+22, top+74+photo_size+row_height, panel_width-44, row_height)
        self.settings_hints(width, height, [('× ' + self.settings_text('back'), BUTTON_RED)])

    def information_value(self, key, value, x, y, width, row_height):
        self.settings_label(self.settings_text(key), x, y, width, 15, MUTED, PANEL,
                            max_height=30, tags=('information-label', 'information-label-'+key))
        self.settings_label(value, x, y+29, width, 21, FG, PANEL, True,
                            max_height=row_height-30, tags=('information-value', 'information-'+key))

    # @llr LLR-TERM-CONFIG-019, LLR-TERM-SETUP-032
    def draw_maintenance(self, width, height):
        draft = self.settings_draft
        action = MAINTENANCE_ACTIONS[draft.maintenance_index]
        self.settings_label(self.settings_text('maintenance'), width/2, 116, width-100, 32,
                            bold=True, anchor='center', max_height=65)
        back = ('× ' + self.settings_text('back'), BUTTON_RED)
        if draft.maintenance_status or draft.busy:
            message = self.settings_text(draft.maintenance_status) if draft.maintenance_status else self.text('wait')
            self.settings_icon(action, width/2, height*.38, 96, BG)
            self.settings_label(message, width/2, height*.61, width-140, 28, anchor='center',
                                max_height=height*.22, tags='maintenance-result')
            self.settings_hints(width, height, [back])
        elif draft.maintenance_confirm:
            self.settings_icon(action, width/2, height*.38, 96, BG)
            question = self.text('factory_reset') if action == 'reset' else self.settings_text('confirm_'+action)
            confirm = self.text('reset') if action == 'reset' else self.settings_text(action)
            self.settings_label(question, width/2, height*.61, width-140,
                                32, bold=True, anchor='center', max_height=height*.22,
                                tags='maintenance-confirmation')
            self.settings_hints(width, height, [('✓ ' + confirm, BUTTON_GREEN),
                                                ('× ' + self.text('cancel').capitalize(), BUTTON_RED)])
        else:
            gap, margin, y = 20, 54, 174
            card_width = (width-2*margin-2*gap)/3
            card_height = height-y-125
            for index, key in enumerate(MAINTENANCE_ACTIONS):
                x = margin+index*(card_width+gap)
                selected = index == draft.maintenance_index
                fill = '#303b50' if selected else PANEL
                self.settings_panel(x, y, card_width, card_height, fill, ACCENT if selected else None,
                                    tags=('maintenance-card', 'maintenance-'+key))
                self.settings_icon(key, x+card_width/2, y+card_height*.34, 105, fill)
                self.settings_label(self.settings_text(key), x+card_width/2, y+card_height*.71,
                                    card_width-25, 25, RED if key == 'reset' else FG, fill, True,
                                    anchor='center', max_height=card_height*.35)
            self.settings_hints(width, height, [('‹ › ' + self.text('select').capitalize(), PANEL),
                                                ('✓ ' + self.settings_text('open'), BUTTON_GREEN), back])
