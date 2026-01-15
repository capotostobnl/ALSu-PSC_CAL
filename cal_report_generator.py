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

    This class provides a high-level interface for ReportLab to generate
    standardized calibration documents. It handles page layout, automated
    pagination (page breaks), monospace column alignment for test data,
    and inclusion of BNL laboratory standards metadata.

    Attributes:
        filename (str): Output path for the generated PDF.
        c (canvas.Canvas): The ReportLab canvas object used for drawing.
        width (float): The width of a standard LETTER page in points.
        height (float): The height of a standard LETTER page in points.
        x_margin (float): Horizontal margin from the left edge (0.75").
        y_margin (float): Vertical margin from the top/bottom edges (0.75").
        y (float): Current vertical cursor position on the page.
        line_height (int): Vertical spacing between lines of text (12 pts).
        designation (str): PSC model or designation (e.g., 'PSC-2HFS').
        sn (str): The serial number of the unit under test.
        timestamp (str): The execution time of the report generation.
    """
    def __init__(self, filename: str, psc_designation: str,
                 serial_number: str):
        self.filename = filename
        self.c = canvas.Canvas(filename, pagesize=LETTER)
        self.width, self.height = LETTER

        # Margins & Layout
        self.x_margin = 0.75 * inch
        self.y_margin = 0.75 * inch
        self.y = self.height - self.y_margin
        self.line_height = 12

        # Setup Font
        self.c.setFont("Courier", 9)  # Monospace ensures columns align nicely

        # Metadata
        self.designation = psc_designation
        self.sn = serial_number
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _check_page_break(self, lines_needed=1):
        """Checks if we need a new page before writing."""
        if self.y < (self.y_margin + (lines_needed * self.line_height)):
            self.c.showPage()
            self.c.setFont("Courier", 9)
            self.y = self.height - self.y_margin

    def write_line(self, text: str):
        """Writes a simple line of text and advances the cursor."""
        self._check_page_break()
        self.c.drawString(self.x_margin, self.y, text)
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

    def add_testpoint_row(self, data: list, print_header: bool = False):
        """
        Writes a formatted row of test data to the PDF.

        Args:
            data: List of floats [dmm, dac, adc1, adc2, adc3, err]
            print_header: If True, prints the column names first.
        """
        # Format string matching your original spacing
        # Fixed width monospaced columns
        header_fmt = "{:>14}{:>14}{:>14}{:>14}{:>14}{:>14}"
        data_fmt = "{:>14.6f}{:>14.6f}{:>14.6f}{:>14.6f}{:>14.6f}{:>14.6f}"

        if print_header:
            self._check_page_break(lines_needed=2)
            header_str = header_fmt.format("Itest", "dacSP", "dcct1", "dcct2",
                                           "dacRB", "err")
            self.write_line(header_str)

        row_str = data_fmt.format(*data)
        self.write_line(row_str)

    def write_footer_and_save(self):
        """Writes the signature lines and saves the PDF."""
        self._check_page_break(lines_needed=5)
        self.write_line("")
        self.write_line("")
        self.write_line("Test data reviewed by ______________________________"
                        "   Date_____________")

        # Save file
        self.c.save()
        print(f"Report saved to: {self.filename}")
