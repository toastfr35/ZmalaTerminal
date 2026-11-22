"""Remote-operated combined server configuration page."""
import tkinter as tk
from functools import partial
from zmala_terminal.common.server_page import server_label
from zmala_terminal.common.theme import ACCENT, BUTTON_GREEN, BUTTON_RED, FG, MUTED, PANEL


def draw_server_configuration(view, width, height):
    page = view.settings_draft.server_page
    details = page.details
    text = partial(server_label, view.language)
    view.settings_label(text('Server Configuration'), width/2, 108, width-80, 32,
                        bold=True, anchor='center', max_height=56)
    x, y, gap = 38, 151, 18
    left = int((width-2*x-gap)*.49)
    right = x+left+gap
    remaining = width-x-right
    panel_height = height-y-120
    for start, size in ((x,left), (right,remaining)):
        view.settings_panel(start,y,size,panel_height,PANEL)

    state = details.get('state')
    reached = page.when('reached')
    checked = page.when('call')
    public = {'unconfigured':'Remote access not configured', 'expired':'No connection confirmed',
              'waiting':'Waiting for your phone…'}.get(state, text('Reached')+' · '+reached if reached else 'Not yet verified')
    running = page.stage in ('connected','disconnected')
    rows = (
        ('Server status', 'Running' if running else {'starting':'Starting…','stopped':'Couldn’t start'}.get(page.stage,'Checking…')),
        ('This terminal', {'connected':'Connected to local server','disconnected':'Connection failed'}.get(page.stage,'Waiting for local server')),
        ('Access from outside your network', public),
        ('Remote calling', text('Confirmed')+' · '+checked if checked else 'Two-way audio and video not yet tested'))
    row_height = (panel_height-32)/len(rows)
    for index,(label,value) in enumerate(rows):
        top = y+17+row_height*index
        view.settings_label(text(label),x+22,top,left-44,16,MUTED,PANEL,max_height=row_height*.39)
        view.settings_label(text(value),x+22,top+row_height*.39,left-44,21,FG,PANEL,True,max_height=row_height*.53)
    center = right+remaining/2
    heading = 'Test with a phone' if state == 'waiting' else 'Open server administration'
    if page.confirm_call:
        heading = 'Confirm a remote call'
    view.settings_label(text(heading),center,y+28,remaining-32,22,FG,PANEL,True,anchor='center',max_height=51)
    if page.confirm_call:
        instruction = ('Make a call from the Zmala app using mobile data. Confirm only after both people '
                       'could see and hear each other.')
    elif state == 'waiting':
        instruction = 'Turn off Wi-Fi on your phone. Scan this code using mobile data.'
    elif details.get('admin'):
        instruction = ('Scan on the same network to set the administrator password and add contacts.'
                       if details.get('first_setup') else 'Scan on the same network to manage accounts and contacts.')
    else:
        instruction = 'The local administration address will appear when the server has a network connection.'
    qr = details.get('qr')
    if qr and not page.confirm_call:
        picture = tk.PhotoImage(data=qr, format='png')
        if panel_height < 370:
            picture = picture.subsample(2)
        view.settings_images.append(picture)
        view.settings_canvas.create_image(center,y+panel_height*.45,image=picture)
    if state != 'waiting' and not page.confirm_call:
        view.settings_label(details.get('admin',''),center,y+panel_height*.76,remaining-34,19,ACCENT,PANEL,
                            True,anchor='center',max_height=42)
    view.settings_label(instruction,center,y+panel_height*(.5 if page.confirm_call else .895),
                        remaining-44,17,FG,PANEL,anchor='center',max_height=panel_height*(.55 if page.confirm_call else .19))
    actions = page.actions
    hints = [('‹ ›  '+view.text('select').capitalize(), PANEL)] if len(actions)>1 else []
    if actions:
        hints.append(('✓  '+text(actions[page.index]), BUTTON_GREEN))
    if view.setup_stage != 'activation':
        hints.append(('×  '+(text('Contacts') if page.first else view.settings_text('back')), BUTTON_RED))
    if hints:
        view.settings_hints(width,height,hints)
