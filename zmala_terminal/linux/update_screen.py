"""Independent localized HDMI progress; never controls TV, USB, media or calls."""
import io
import json
from pathlib import Path

# @llr LLR-TERM-UI-028
MESSAGES = {
 'en': ('Updating Zmala.\nPlease wait.', 'Checking the update.\nPlease wait.', 'Restoring Zmala.\nPlease wait.', 'Zmala needs help.\nPlease contact the person who set it up.'),
 'fr': ('Mise à jour de Zmala.\nVeuillez patienter.', 'Vérification de la mise à jour.\nVeuillez patienter.', 'Restauration de Zmala.\nVeuillez patienter.', 'Zmala a besoin d’aide.\nContactez la personne qui l’a installé.'),
 'de': ('Zmala wird aktualisiert.\nBitte warten.', 'Das Update wird geprüft.\nBitte warten.', 'Zmala wird wiederhergestellt.\nBitte warten.', 'Zmala benötigt Hilfe.\nBitte kontaktieren Sie die Person, die es eingerichtet hat.'),
 'es': ('Actualizando Zmala.\nEspere, por favor.', 'Comprobando la actualización.\nEspere, por favor.', 'Restaurando Zmala.\nEspere, por favor.', 'Zmala necesita ayuda.\nContacte con la persona que lo configuró.'),
 'pt': ('A atualizar o Zmala.\nAguarde, por favor.', 'A verificar a atualização.\nAguarde, por favor.', 'A restaurar o Zmala.\nAguarde, por favor.', 'O Zmala precisa de ajuda.\nContacte quem o configurou.'),
 'pl': ('Aktualizowanie Zmala.\nProszę czekać.', 'Sprawdzanie aktualizacji.\nProszę czekać.', 'Przywracanie Zmala.\nProszę czekać.', 'Zmala potrzebuje pomocy.\nSkontaktuj się z osobą, która go skonfigurowała.'),
 'el': ('Ενημέρωση του Zmala.\nΠαρακαλώ περιμένετε.', 'Έλεγχος ενημέρωσης.\nΠαρακαλώ περιμένετε.', 'Επαναφορά του Zmala.\nΠαρακαλώ περιμένετε.', 'Το Zmala χρειάζεται βοήθεια.\nΕπικοινωνήστε με το άτομο που το εγκατέστησε.'),
 'ru': ('Обновление Zmala.\nПожалуйста, подождите.', 'Проверка обновления.\nПожалуйста, подождите.', 'Восстановление Zmala.\nПожалуйста, подождите.', 'Zmala нужна помощь.\nОбратитесь к тому, кто его настроил.'),
 'ur': ('Zmala کو اپ ڈیٹ کیا جا رہا ہے۔\nبراہ کرم انتظار کریں۔', 'اپ ڈیٹ کی جانچ ہو رہی ہے۔\nبراہ کرم انتظار کریں۔', 'Zmala بحال کیا جا رہا ہے۔\nبراہ کرم انتظار کریں۔', 'Zmala کو مدد کی ضرورت ہے۔\nاسے ترتیب دینے والے شخص سے رابطہ کریں۔'),
 'ar': ('جارٍ تحديث Zmala.\nيُرجى الانتظار.', 'جارٍ التحقق من التحديث.\nيُرجى الانتظار.', 'جارٍ استعادة Zmala.\nيُرجى الانتظار.', 'يحتاج Zmala إلى مساعدة.\nيُرجى التواصل مع الشخص الذي أعدّه.'),
 'hi': ('Zmala अपडेट हो रहा है।\nकृपया प्रतीक्षा करें।', 'अपडेट की जाँच हो रही है।\nकृपया प्रतीक्षा करें।', 'Zmala बहाल हो रहा है।\nकृपया प्रतीक्षा करें।', 'Zmala को सहायता चाहिए।\nइसे सेट अप करने वाले व्यक्ति से संपर्क करें।'),
 'bn': ('Zmala আপডেট হচ্ছে।\nঅনুগ্রহ করে অপেক্ষা করুন।', 'আপডেট যাচাই হচ্ছে।\nঅনুগ্রহ করে অপেক্ষা করুন।', 'Zmala পুনরুদ্ধার হচ্ছে।\nঅনুগ্রহ করে অপেক্ষা করুন।', 'ZmalaCall-এর সহায়তা প্রয়োজন।\nযিনি এটি সেট আপ করেছেন তাঁর সঙ্গে যোগাযোগ করুন।'),
 'th': ('กำลังอัปเดต Zmala\nโปรดรอสักครู่', 'กำลังตรวจสอบการอัปเดต\nโปรดรอสักครู่', 'กำลังกู้คืน Zmala\nโปรดรอสักครู่', 'Zmala ต้องการความช่วยเหลือ\nโปรดติดต่อผู้ที่ตั้งค่าระบบให้คุณ'),
 'ko': ('Zmala 업데이트 중입니다.\n잠시 기다려 주세요.', '업데이트를 확인 중입니다.\n잠시 기다려 주세요.', 'Zmala 복원 중입니다.\n잠시 기다려 주세요.', 'ZmalaCall에 도움이 필요합니다.\n설정해 준 분에게 문의해 주세요.'),
 'ja': ('Zmala を更新しています。\nしばらくお待ちください。', '更新を確認しています。\nしばらくお待ちください。', 'Zmala を復元しています。\nしばらくお待ちください。', 'Zmala にサポートが必要です。\n設定した方にご連絡ください。'),
 'zh-Hans': ('正在更新 Zmala。\n请稍候。', '正在检查更新。\n请稍候。', '正在恢复 Zmala。\n请稍候。', 'Zmala 需要帮助。\n请联系为您设置设备的人。'),
}
STATES = {'updating': 0, 'checking': 1, 'rollback': 2, 'recovery_failed': 3}
DOWNLOAD_MESSAGES = {
    'en': 'Downloading the update.\nPlease wait.',
    'fr': 'Téléchargement de la mise à jour.\nVeuillez patienter.',
    'de': 'Das Update wird heruntergeladen.\nBitte warten.',
    'es': 'Descargando la actualización.\nEspere, por favor.',
    'pt': 'A descarregar a atualização.\nAguarde, por favor.',
    'pl': 'Pobieranie aktualizacji.\nProszę czekać.',
    'el': 'Λήψη της ενημέρωσης.\nΠαρακαλώ περιμένετε.',
    'ru': 'Загрузка обновления.\nПожалуйста, подождите.',
    'ur': 'اپ ڈیٹ ڈاؤن لوڈ ہو رہی ہے۔\nبراہ کرم انتظار کریں۔',
    'ar': 'جارٍ تنزيل التحديث.\nيُرجى الانتظار.',
    'hi': 'अपडेट डाउनलोड हो रहा है।\nकृपया प्रतीक्षा करें।',
    'bn': 'আপডেট ডাউনলোড হচ্ছে।\nঅনুগ্রহ করে অপেক্ষা করুন।',
    'th': 'กำลังดาวน์โหลดการอัปเดต\nโปรดรอสักครู่',
    'ko': '업데이트를 다운로드 중입니다.\n잠시 기다려 주세요.',
    'ja': '更新をダウンロードしています。\nしばらくお待ちください。',
    'zh-Hans': '正在下载更新。\n请稍候。',
}


def message(language, phase):
    if phase == 'downloading':
        return DOWNLOAD_MESSAGES.get(language, DOWNLOAD_MESSAGES['en'])
    return MESSAGES.get(language, MESSAGES['en'])[STATES[phase]]


def render_message(text, language, width, height):
    # Kept independent of the application renderer: this process must survive
    # replacement of every application module while retaining Pango bidi shaping.
    import cairo
    import gi
    gi.require_version('Pango', '1.0')
    gi.require_version('PangoCairo', '1.0')
    from gi.repository import Pango, PangoCairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    context = cairo.Context(surface)
    context.set_source_rgb(0, 0, 0)
    context.paint()
    layout = PangoCairo.create_layout(context)
    layout.get_context().set_language(Pango.Language.from_string(language))
    layout.set_text(text, -1)
    text_width = int(width * .8)
    layout.set_width(text_width * Pango.SCALE)
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_alignment(Pango.Alignment.CENTER)
    for size in range(min(48, max(20, width//40)), 15, -1):
        font = Pango.FontDescription('Noto Sans')
        font.set_absolute_size(size * Pango.SCALE)
        layout.set_font_description(font)
        measured_width, measured_height = layout.get_pixel_size()
        if measured_height <= height * .42:
            break
    context.set_source_rgb(237/255, 241/255, 251/255)
    context.move_to((width - text_width)/2, (height-measured_height)/2)
    PangoCairo.show_layout(context, layout)
    stream = io.BytesIO()
    surface.write_to_png(stream)
    return stream.getvalue(), (measured_width, measured_height)


# @llr LLR-TERM-UI-028
def main(state_file='/run/zmalacall-updater/state.json'):
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    root.title("Zmala update")
    root.overrideredirect(True)
    root.configure(bg='#000000')
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f'{width}x{height}+0+0')
    canvas = tk.Canvas(root, bg='#000000', highlightthickness=0)
    canvas.pack(fill='both', expand=True)
    previous = None
    last_percent = None
    message_height = 0

    def refresh():
        nonlocal previous, last_percent, message_height
        try:
            path = Path(state_file)
            if path.stat().st_size > 8192:
                raise ValueError('Invalid state')
            value = json.loads(path.read_text(encoding='utf-8'))
            phase, language = value.get('phase'), value.get('language', 'en')
            percent = value.get('download_percent')
            if phase != 'updating' or type(percent) is not int or not 0 <= percent <= 100:
                percent = None
            if phase not in STATES:
                root.withdraw()
                previous = None
            else:
                display_phase = 'downloading' if percent is not None else phase
                if (display_phase, language) != previous:
                    data, (_, message_height) = render_message(message(language, display_phase), language, width, height)
                    root.image = tk.PhotoImage(master=root, data=data, format='PNG')
                    canvas.delete('all')
                    canvas.create_image(width//2, height//2, image=root.image)
                    previous = display_phase, language
                    last_percent = None
                if percent is not None and percent != last_percent:
                    left, right = width * .25, width * .75
                    top = max(height * .60, (height + message_height) / 2 + height * .035)
                    canvas.delete('download')
                    canvas.create_rectangle(left, top, right, top + 14, fill='#1b2330', width=0, tags='download')
                    if percent:
                        canvas.create_rectangle(left, top, left + (right - left) * percent / 100, top + 14,
                                                fill='#73dbbf', width=0, tags='download')
                    canvas.create_text(width / 2, top + 42, text=f'{percent}%', fill='#edf1fb',
                                       font=('Noto Sans', 20), tags='download')
                    last_percent = percent
                root.deiconify()
                root.lift()
        except (OSError, ValueError, TypeError, KeyError):
            # Retain an already displayed recovery message if the producer dies.
            pass
        root.after(500, refresh)
    refresh()
    root.mainloop()


if __name__ == '__main__':
    main()
