"""Generate the printable credential-free server activation card."""
from pathlib import Path
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen.canvas import Canvas

from zmala_terminal.common.server_activation import ACTIVATION_QR


def generate(destination):
    width, height = A5
    pdf = Canvas(str(destination), pagesize=A5, invariant=True)
    pdf.setTitle('Zmala | Activate Server')
    pdf.setFillColor(HexColor('#234f47'))
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(32, height-52, 'Zmala')
    pdf.setFillColor(HexColor('#162e2b'))
    pdf.setFont('Helvetica-Bold', 32)
    pdf.drawString(32, height-110, 'Activate Server')
    pdf.setFont('Helvetica', 13)
    pdf.drawString(32, height-140, 'Use this card when the TV asks for the server QR code.')
    size = 254
    symbol = QrCodeWidget(ACTIVATION_QR, barWidth=size, barHeight=size, barLevel='M', barBorder=4)
    drawing = Drawing(size,size)
    drawing.add(symbol)
    renderPDF.draw(drawing,pdf,(width-size)/2, height-419)
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(32, 130, 'Hold the code up to the terminal camera.')
    pdf.setFont('Helvetica', 12)
    pdf.drawString(32, 103, 'This box will start its own server and connect to it.')
    pdf.drawString(32, 83, 'Follow the instructions on the TV to add contacts.')
    pdf.showPage()
    pdf.save()


if __name__ == '__main__':
    generate(Path(__file__).resolve().parents[2]/'docs/leaflet/activate-server.pdf')
