"""
report_generator.py

Handles PDF generation for PSC Calibration reports using ReportLab.
"""

from datetime import datetime
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


class CalibrationReport:
    """
    Manages the creation and formatting of PSC Calibration PDF reports.
    """
    def __init__(self, filename: str, psc_designation: str,
                 serial_number: str):
        self.filename = filename
        self.c = canvas.Canvas(filename, pagesize=LETTER)
        self.width, self.height = LETTER

        # Margins & Layout
        self.x_margin = 0.75 * inch
        self.y_margin = 0.5 * inch  # Tighter top margin
        self.y = self.height - self.y_margin
        self.line_height = 11       # Tighter line spacing

        # Setup Font
        self.c.setFont("Courier", 9)

        # Metadata
        self.designation = psc_designation
        self.sn = serial_number
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _check_page_break(self, lines_needed=1):
        """Checks if we need a new page before writing."""
        # Check against margin + footer space (approx 1.5 inches from bottom)
        limit = self.y_margin + (1.5 * inch)
        if self.y < (limit + (lines_needed * self.line_height)):
            self.c.showPage()
            self.c.setFont("Courier", 9)
            self.y = self.height - self.y_margin

    def write_line(self, text: str):
        """Writes a simple line of text and advances the cursor."""
        # Strip newlines to prevent square glyphs
        clean_text = text.replace('\n', '')
        self._check_page_break()
        self.c.drawString(self.x_margin, self.y, clean_text)
        self.y -= self.line_height

    def write_header(self):
        """Writes the standard calibration header."""
        self.write_line("Report of Calibration")
        self.write_line(f"PSC {self.designation} S/N {self.sn}")
        self.write_line(self.timestamp)
        self.write_line("")
        self.write_line("Calibration Current standard: BNL PSC ATE S/N 001")
        self.write_line("Calibration Volt standard:    "
                        "HP 3458A-002 S/N 2823A 23647")
        self.write_line("Calibration Res. standard:    "
                        "Fluke 742A-1 S/N 1063008")
        self.write_line("End Header")
        self.write_line("")
        self.write_line("")

    def draw_footer(self, current_page, total_pages):
        """Draws the footer at a fixed location at the bottom of the page."""
        footer_y = 0.75 * inch  # Fixed position from bottom
        
        # Save current font state
        self.c.setFont("Courier", 9)
        
        # 1. Signature Line (ONLY on the last page)
        if current_page == total_pages:
            self.c.drawString(self.x_margin, footer_y, 
                "Test data reviewed by ______________________________"
                            "   Date_____________")
        
        # 2. Page Number (On every page)
        page_str = f"Page {current_page} of {total_pages}"
        self.c.drawString(self.x_margin, footer_y - 12, page_str)

    def next_page(self):
        """Finalizes the current page and prepares the next one."""
        self.c.showPage()
        self.c.setFont("Courier", 9)
        self.y = self.height - self.y_margin

    def save(self):
        """Saves the PDF to disk."""
        self.c.save()
        print(f"Report saved to: {self.filename}")