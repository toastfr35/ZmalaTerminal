"""Export miniature UI examples using the real contact-card geometry.

Run through run_display.py. Uses five fictional contacts and drawn silhouettes;
no personal photographs, server, media devices or desktop capture are involved.
The two PNGs are intentional runtime assets, not temporary test output.
"""
from pathlib import Path
import time
from PIL import Image, ImageDraw, ImageTk
from zmala_terminal.common.main import Terminal
from zmala_terminal.common.carousel import CarouselLayout, carousel_contacts
from zmala_terminal.common.theme import BG, FG
from tests.terminal.LLT.test_terminal import config


class Preview(Terminal):
    def restore_enrollment(self, *args): self.setup_stage = None
    def bind_inputs(self): pass
    def start_services(self): pass
    def action(self, action): pass

    def contact_image(self, person, size, background):
        colours = ['#b8a6fa', '#78ddb5', '#93d2f5', '#f3c76a', '#ef909e']
        colour = colours[int(person['id'][-1])]
        def draw(line, ellipse, rectangle, arc, polygon, curve, text):
            ellipse((0,0,size,size), '#33415b')
            ellipse((size*.35,size*.18,size*.3,size*.3), '#edf1fb')
            ellipse((size*.2,size*.52,size*.6,size*.45), colour)
        return self.icon_renderer._photo(('example-person', person['id'], size), size, size, draw, background)


app = Preview(profile='portrait-choice-artwork')
try:
    app.root.geometry('1280x720'); app.root.update()
    base = config()
    base['contacts'] = [dict(base['contacts'][0], id=f'example{i}', name=name)
                        for i,name in enumerate(('Alex','Maya','Sam','Jo','Lou'))]
    app.model.configure(base); app.model.index = 2
    app.language = 'en'; app.server_seen = time.monotonic()
    app.carousel_motion = None
    output = Path(__file__).resolve().parents[3] / 'zmala_terminal/common/assets/settings'
    for count in (3,5):
        app.avatar.delete('all'); app.current_photos = []; app.current_text_images = []
        layout = CarouselLayout.fit(1280,550,5,count)
        for index,person in enumerate(carousel_contacts(app.model.contacts,2,count)):
            app.draw_card(person,index-count//2,640,385,1280,550,True,layout)
        rendered = Image.new('RGB',(1280,720),BG); draw = ImageDraw.Draw(rendered)
        pictures = {str(p):p for p in [*app.current_photos,*app.current_text_images]}
        for item in app.avatar.find_all():
            kind, coordinates = app.avatar.type(item), app.avatar.coords(item)
            if kind == 'image':
                pixels = ImageTk.getimage(pictures[app.avatar.itemcget(item,'image')])
                x,y,_,_ = app.avatar.bbox(item); rendered.paste(pixels,(x,y),pixels)
            elif kind in ('rectangle','oval'):
                getattr(draw, 'rectangle' if kind == 'rectangle' else 'ellipse')(
                    coordinates, fill=app.avatar.itemcget(item,'fill') or None,
                    outline=app.avatar.itemcget(item,'outline') or None,
                    width=round(float(app.avatar.itemcget(item,'width'))))
        heading = ImageTk.getimage(app.text_renderer.photo('Who would you like to call?', app.font_family, 32, BG, FG, 1080, True))
        rendered.paste(heading,(100,35),heading)
        logo = ImageTk.getimage(app.corner_logo); rendered.paste(logo,(22,20),logo)
        rendered.resize((640,360),Image.Resampling.LANCZOS).save(output/f'portraits-{count}.png')
finally:
    app.tv_control.close(); app.text_renderer.close(); app.root.destroy()
