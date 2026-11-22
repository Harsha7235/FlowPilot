"""
FlowPilot Main Window
=====================

Integrated research and GNU Radio workbench.

Features:
    1. Research paper PDF import
    2. PDF page navigation
    3. Paper overview and keyword search
    4. Research section analysis
    5. Rule-based research chat
    6. Explicit Python tool calling
    7. Research-to-GNU-Radio design suggestions
    8. GNU Radio Companion detection and launching

Design constraints:
    - No language model
    - No Ollama
    - No machine learning
    - No cloud APIs
    - No arbitrary Python execution from chat messages
"""

import re
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QFileDialog,
    QSplitter,
    QListWidget,
    QMessageBox,
    QLineEdit,
    QStatusBar,
    QTabWidget,
    QFrame,
)

from app.paper.pdf_reader import PDFReader
from app.core.tool_registry import ToolRegistry
from app.grc.grc_manager import GRCManager
from app.paper.paper_assistant import PaperAssistant

try:
    from app.paper.section_extractor import SectionExtractor
except ImportError:
    SectionExtractor = None

try:
    from app.grc.research_bridge import ResearchBridge
except ImportError:
    ResearchBridge = None


class PDFWorker(QThread):
    """Read a PDF without freezing the GUI."""

    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            result = PDFReader().read(self.file_path)
            self.completed.emit(result)

        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "FlowPilot | Research + GNU Radio Workbench"
        )

        self.resize(1450, 900)

        self.project_root = Path(
            __file__
        ).resolve().parents[2]

        self.paper_data = None
        self.sections = []
        self.worker = None

        self.paper_assistant = PaperAssistant()
        self.research_bridge = (
            ResearchBridge()
            if ResearchBridge is not None
            else None
        )

        self.grc_manager = GRCManager(
            self.project_root
        )

        self.tools = ToolRegistry()

        self.build_menu()
        self.register_tools()
        self.build_interface()

        self.setStatusBar(QStatusBar())

        self.statusBar().showMessage(
            "Ready | Local Python tools | No AI APIs"
        )

        self.show_welcome_message()

    # ==================================================
    # MENU
    # ==================================================

    def build_menu(self):

        file_menu = self.menuBar().addMenu("File")

        import_action = QAction(
            "Import Research Paper",
            self
        )

        import_action.setShortcut("Ctrl+O")
        import_action.triggered.connect(self.open_pdf)

        file_menu.addAction(import_action)

        exit_action = QAction(
            "Exit",
            self
        )

        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

        file_menu.addAction(exit_action)

        tools_menu = self.menuBar().addMenu("Tools")

        paper_action = QAction(
            "Paper Overview",
            self
        )

        paper_action.triggered.connect(
            self.show_overview
        )

        tools_menu.addAction(paper_action)

        sections_action = QAction(
            "Analyze Paper Sections",
            self
        )

        sections_action.triggered.connect(
            self.analyze_sections
        )

        tools_menu.addAction(sections_action)

        grc_action = QAction(
            "Open GNU Radio Companion",
            self
        )

        grc_action.triggered.connect(
            self.launch_grc
        )

        tools_menu.addAction(grc_action)

    # ==================================================
    # PYTHON TOOL REGISTRATION
    # ==================================================

    def register_tools(self):

        self.tools.register(
            "paper_overview",
            "Display metadata and opening text from the loaded paper",
            self.tool_paper_overview
        )

        self.tools.register(
            "paper_search",
            "Search the loaded paper; accepts query='...'",
            self.tool_paper_search
        )

        self.tools.register(
            "paper_sections",
            "List the sections detected in the loaded paper",
            self.tool_paper_sections
        )

        self.tools.register(
            "grc_status",
            "Check GNU Radio Companion availability",
            self.tool_grc_status
        )

        self.tools.register(
            "grc_list",
            "List saved .grc files in the FlowPilot workspace",
            self.tool_grc_list
        )

        self.tools.register(
            "grc_launch",
            "Launch GNU Radio Companion if installed",
            self.tool_grc_launch
        )

        if self.research_bridge is not None:

            self.tools.register(
                "research_methods",
                "Detect supported signal-processing methods in the paper",
                self.tool_research_methods
            )

            self.tools.register(
                "research_parameters",
                "Extract candidate numerical parameters from the paper",
                self.tool_research_parameters
            )

            self.tools.register(
                "research_design",
                "Propose candidate GNU Radio blocks; accepts method='ofdm'",
                self.tool_research_design
            )

    # ==================================================
    # TOOL HANDLERS
    # ==================================================

    def tool_paper_overview(self):

        return self.paper_assistant.overview()

    def tool_paper_search(self, query=""):

        if not query:
            return (
                "Provide a search query.\n"
                "Example: /paper search OFDM"
            )

        return self.paper_assistant.answer(
            query
        )

    def tool_paper_sections(self):

        if not self.sections:

            return (
                "No sections detected yet. "
                "Import a paper and run Analyze Sections."
            )

        output = []

        for section in self.sections:

            output.append(
                f"{section.title} "
                f"(pages {section.start_page}-"
                f"{section.end_page})"
            )

        return "\n".join(output)

    def tool_grc_status(self):

        info = self.grc_manager.check_installation()

        return (
            info["message"]
            + "\n\nFlowgraph directory:\n"
            + info["flowgraph_directory"]
        )

    def tool_grc_list(self):

        files = self.grc_manager.list_flowgraphs()

        if not files:
            return (
                "No .grc files found in:\n"
                f"{self.grc_manager.flowgraph_dir}"
            )

        return "\n".join(
            str(path)
            for path in files
        )

    def tool_grc_launch(self):

        return self.grc_manager.launch()

    def tool_research_methods(self):

        if not self.paper_data:
            return "Import a research paper first."

        self.research_bridge.set_paper(
            self.paper_data
        )

        methods = (
            self.research_bridge.detect_methods()
        )

        if not methods:

            return (
                "No supported method keywords were detected.\n"
                "Currently supported: OFDM, QAM, PSK, FFT, FM."
            )

        return (
            "Methods detected in extracted paper text:\n\n"
            + "\n".join(
                f"- {method.upper()}"
                for method in methods
            )
            + "\n\nKeyword detection is not proof that the paper "
              "implements each method experimentally."
        )

    def tool_research_parameters(self):

        if not self.paper_data:
            return "Import a research paper first."

        self.research_bridge.set_paper(
            self.paper_data
        )

        parameters = (
            self.research_bridge.extract_parameters()
        )

        if not parameters:

            return (
                "No supported numerical parameter patterns were detected. "
                "Check the paper text and PDF extraction quality."
            )

        lines = [
            "CANDIDATE PARAMETERS FROM PAPER TEXT",
            "Verify each value against its original page before use.",
            ""
        ]

        for item in parameters:

            lines.append(
                f"{item['parameter']}: "
                f"{item['value']} {item.get('unit', '')}"
            )

            lines.append(
                f"Context: {item.get('context', '')}"
            )

            lines.append("")

        return "\n".join(lines)

    def tool_research_design(self, method=""):

        if not self.paper_data:
            return "Import a research paper first."

        if self.research_bridge is None:
            return (
                "ResearchBridge is unavailable.\n"
                "Check app/grc/research_bridge.py."
            )

        if not method:
            return (
                "Specify a supported method.\n"
                "Example: /research design ofdm"
            )

        design = (
            self.research_bridge.propose_design(
                method
            )
        )

        return self.research_bridge.format_design(
            design
        )

    # ==================================================
    # GUI
    # ==================================================

    def build_interface(self):

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)

        root.setContentsMargins(
            12, 12, 12, 12
        )

        root.setSpacing(10)

        # ------------------------------
        # Header
        # ------------------------------

        header = QHBoxLayout()

        title_box = QVBoxLayout()

        title = QLabel("FLOWPILOT")

        title.setFont(
            QFont(
                "Arial",
                24,
                QFont.Weight.Bold
            )
        )

        subtitle = QLabel(
            "Research papers | Python tools | "
            "Signal processing | GNU Radio"
        )

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.open_button = QPushButton(
            "Import PDF"
        )

        self.overview_button = QPushButton(
            "Paper Overview"
        )

        self.sections_button = QPushButton(
            "Analyze Sections"
        )

        self.gnu_radio_button = QPushButton(
            "Open GNU Radio"
        )

        header.addWidget(self.open_button)
        header.addWidget(self.overview_button)
        header.addWidget(self.sections_button)
        header.addWidget(self.gnu_radio_button)

        root.addLayout(header)

        # ------------------------------
        # Main split
        # ------------------------------

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        root.addWidget(
            splitter,
            1
        )

        # ------------------------------
        # Left workspace
        # ------------------------------

        left_panel = QFrame()

        left_layout = QVBoxLayout(
            left_panel
        )

        self.paper_title = QLabel(
            "No paper loaded"
        )

        self.paper_title.setWordWrap(True)

        self.paper_info = QLabel(
            "Import a research paper to begin."
        )

        self.paper_info.setWordWrap(True)

        left_layout.addWidget(
            self.paper_title
        )

        left_layout.addWidget(
            self.paper_info
        )

        left_layout.addWidget(
            QLabel("Paper Pages")
        )

        self.page_list = QListWidget()

        left_layout.addWidget(
            self.page_list,
            2
        )

        left_layout.addWidget(
            QLabel("Detected Sections")
        )

        self.section_list = QListWidget()

        left_layout.addWidget(
            self.section_list,
            2
        )

        splitter.addWidget(
            left_panel
        )

        # ------------------------------
        # Right tabs
        # ------------------------------

        self.tabs = QTabWidget()

        splitter.addWidget(
            self.tabs
        )

        splitter.setSizes(
            [310, 1090]
        )

        # Paper tab

        paper_panel = QWidget()

        paper_layout = QVBoxLayout(
            paper_panel
        )

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "Search methods, equations, parameters, or results..."
        )

        self.output = QTextEdit()

        self.output.setReadOnly(True)

        paper_layout.addWidget(
            self.search_box
        )

        paper_layout.addWidget(
            self.output,
            1
        )

        self.tabs.addTab(
            paper_panel,
            "Research Paper"
        )

        # Chat tab

        chat_panel = QWidget()

        chat_layout = QVBoxLayout(
            chat_panel
        )

        self.chat_output = QTextEdit()

        self.chat_output.setReadOnly(True)

        self.chat_input = QLineEdit()

        self.chat_input.setPlaceholderText(
            "Ask about the paper or enter /help..."
        )

        self.send_button = QPushButton(
            "Send"
        )

        chat_row = QHBoxLayout()

        chat_row.addWidget(
            self.chat_input,
            1
        )

        chat_row.addWidget(
            self.send_button
        )

        chat_layout.addWidget(
            self.chat_output,
            1
        )

        chat_layout.addLayout(
            chat_row
        )

        self.tabs.addTab(
            chat_panel,
            "Chat + Python Tools"
        )

        # GNU Radio tab

        grc_panel = QWidget()

        grc_layout = QVBoxLayout(
            grc_panel
        )

        self.grc_output = QTextEdit()

        self.grc_output.setReadOnly(True)

        grc_layout.addWidget(
            QLabel(
                "GNU Radio Companion and flowgraph workspace"
            )
        )

        grc_layout.addWidget(
            self.grc_output,
            1
        )

        grc_row = QHBoxLayout()

        self.grc_check_button = QPushButton(
            "Check Installation"
        )

        self.grc_list_button = QPushButton(
            "List Flowgraphs"
        )

        self.grc_launch_button = QPushButton(
            "Launch GRC"
        )

        grc_row.addWidget(
            self.grc_check_button
        )

        grc_row.addWidget(
            self.grc_list_button
        )

        grc_row.addWidget(
            self.grc_launch_button
        )

        grc_layout.addLayout(
            grc_row
        )

        self.tabs.addTab(
            grc_panel,
            "GNU Radio"
        )

        # ------------------------------
        # Connections
        # ------------------------------

        self.open_button.clicked.connect(
            self.open_pdf
        )

        self.overview_button.clicked.connect(
            self.show_overview
        )

        self.sections_button.clicked.connect(
            self.analyze_sections
        )

        self.gnu_radio_button.clicked.connect(
            self.open_grc_tab
        )

        self.search_box.returnPressed.connect(
            self.search_paper
        )

        self.page_list.currentRowChanged.connect(
            self.show_page
        )

        self.section_list.currentRowChanged.connect(
            self.show_section
        )

        self.send_button.clicked.connect(
            self.send_chat
        )

        self.chat_input.returnPressed.connect(
            self.send_chat
        )

        self.grc_check_button.clicked.connect(
            self.check_grc
        )

        self.grc_list_button.clicked.connect(
            self.list_grc
        )

        self.grc_launch_button.clicked.connect(
            self.launch_grc
        )

        # ------------------------------
        # Theme
        # ------------------------------

        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #10151d;
                color: #e6edf5;
                font-size: 13px;
            }

            QPushButton {
                background: #26384b;
                border: 1px solid #3c536b;
                border-radius: 7px;
                padding: 9px 12px;
            }

            QPushButton:hover {
                background: #34516b;
            }

            QLineEdit, QTextEdit, QListWidget {
                background: #0c1118;
                border: 1px solid #293747;
                border-radius: 7px;
                padding: 8px;
                selection-background-color: #2d6288;
            }

            QTabBar::tab {
                background: #18222f;
                padding: 10px 15px;
                border: 1px solid #293747;
            }

            QTabBar::tab:selected {
                background: #26384b;
            }
        """)

    # ==================================================
    # CHAT
    # ==================================================

    def show_welcome_message(self):

        self.chat_output.append(
            "<b>FlowPilot</b><br>"
            "Welcome. I can search your loaded paper, "
            "display extracted evidence, inspect candidate "
            "signal-processing methods, and connect to GNU Radio.<br><br>"
            "Commands:<br>"
            "/help<br>"
            "/tools<br>"
            "/paper overview<br>"
            "/paper search OFDM<br>"
            "/paper sections<br>"
            "/research methods<br>"
            "/research parameters<br>"
            "/research design ofdm<br>"
            "/grc status<br>"
            "/grc list<br>"
            "/grc launch<br><br>"
        )

    def append_chat(
        self,
        speaker: str,
        message: str
    ):

        safe = (
            str(message)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

        self.chat_output.append(
            f"<b>{speaker}</b><br>{safe}<br><br>"
        )

    def send_chat(self):

        message = self.chat_input.text().strip()

        if not message:
            return

        self.chat_input.clear()

        self.append_chat(
            "You",
            message
        )

        try:

            response = self.route_chat_message(
                message
            )

        except Exception:

            response = (
                "The operation failed:\n\n"
                + traceback.format_exc()
            )

        self.append_chat(
            "FlowPilot",
            response
        )

    def route_chat_message(
        self,
        message: str
    ) -> str:

        command = message.strip()

        lower = command.lower()

        if lower in (
            "/help",
            "help",
            "what can you do"
        ):

            return (
                "FlowPilot capabilities:\n\n"
                "Paper:\n"
                "/paper overview\n"
                "/paper search <terms>\n"
                "/paper sections\n\n"
                "Research-to-GNU-Radio:\n"
                "/research methods\n"
                "/research parameters\n"
                "/research design ofdm\n\n"
                "GNU Radio:\n"
                "/grc status\n"
                "/grc list\n"
                "/grc launch\n\n"
                "Python tools:\n"
                "/tools\n\n"
                "Ordinary text searches the loaded paper."
            )

        if lower == "/tools":

            return "\n".join(
                self.tools.descriptions()
            )

        if lower == "/paper overview":

            self.tabs.setCurrentIndex(0)

            return self.tools.call(
                "paper_overview"
            )

        if lower.startswith(
            "/paper search "
        ):

            query = command[
                len("/paper search "):
            ].strip()

            return self.tools.call(
                "paper_search",
                query=query
            )

        if lower == "/paper sections":

            return self.tools.call(
                "paper_sections"
            )

        if lower == "/research methods":

            if not self.research_bridge:
                return "ResearchBridge is unavailable."

            return self.tools.call(
                "research_methods"
            )

        if lower == "/research parameters":

            if not self.research_bridge:
                return "ResearchBridge is unavailable."

            return self.tools.call(
                "research_parameters"
            )

        if lower.startswith(
            "/research design "
        ):

            method = command[
                len("/research design "):
            ].strip()

            if not self.research_bridge:
                return "ResearchBridge is unavailable."

            self.tabs.setCurrentIndex(2)

            result = self.tools.call(
                "research_design",
                method=method
            )

            self.grc_output.setPlainText(
                result
            )

            return result

        if lower == "/grc status":

            result = self.tools.call(
                "grc_status"
            )

            self.grc_output.setPlainText(
                result
            )

            self.tabs.setCurrentIndex(2)

            return result

        if lower == "/grc list":

            result = self.tools.call(
                "grc_list"
            )

            self.grc_output.setPlainText(
                result
            )

            self.tabs.setCurrentIndex(2)

            return result

        if lower == "/grc launch":

            return self.tools.call(
                "grc_launch"
            )

        if lower.startswith("/tool "):

            return self.execute_explicit_tool(
                command
            )

        if lower.startswith("/"):

            return (
                "Unknown command. Type /help "
                "to see the available commands."
            )

        # Normal chat message: search the research paper.
        return self.paper_assistant.answer(
            command
        )

    def execute_explicit_tool(
        self,
        command: str
    ) -> str:

        parts = command.split()

        if len(parts) < 2:

            return (
                "Usage: /tool TOOL_NAME key=value"
            )

        name = parts[1]

        kwargs = {}

        for part in parts[2:]:

            if "=" not in part:
                continue

            key, value = part.split(
                "=",
                1
            )

            kwargs[key] = value.strip(
                "\"'"
            )

        result = self.tools.call_safely(
            name,
            **kwargs
        )

        if result["success"]:

            return str(
                result["result"]
            )

        return (
            "Tool failed:\n"
            + str(result["error"])
        )

    # ==================================================
    # PDF IMPORT
    # ==================================================

    def open_pdf(self):

        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Select Research Paper",
                str(Path.home()),
                "PDF Documents (*.pdf)"
            )
        )

        if not file_path:
            return

        if (
            self.worker is not None
            and self.worker.isRunning()
        ):

            QMessageBox.information(
                self,
                "Please wait",
                "The current PDF is still being processed."
            )

            return

        self.open_button.setEnabled(
            False
        )

        self.statusBar().showMessage(
            "Extracting PDF text..."
        )

        self.worker = PDFWorker(
            file_path
        )

        self.worker.completed.connect(
            self.on_pdf_loaded
        )

        self.worker.failed.connect(
            self.on_pdf_failed
        )

        self.worker.finished.connect(
            self.on_worker_finished
        )

        self.worker.start()

    def on_worker_finished(self):

        self.open_button.setEnabled(
            True
        )

    def on_pdf_loaded(
        self,
        data: dict
    ):

        self.paper_data = data
        self.sections = []

        self.paper_assistant.set_paper(
            data,
            []
        )

        if self.research_bridge:

            self.research_bridge.set_paper(
                data
            )

        self.paper_title.setText(
            data.get(
                "title",
                data.get(
                    "file_name",
                    "Unknown paper"
                )
            )
        )

        self.paper_info.setText(
            f"Author: {data.get('author', 'Unknown')} | "
            f"Pages: {data.get('page_count', 0)} | "
            f"Words: {data.get('word_count', 0)}"
        )

        self.page_list.clear()

        for page in data.get(
            "pages",
            []
        ):

            label = (
                f"Page {page.get('page_number', '?')}"
            )

            if not page.get(
                "has_text",
                bool(page.get("text"))
            ):

                label += " — no extractable text"

            self.page_list.addItem(
                label
            )

        if data.get("pages"):

            self.page_list.setCurrentRow(
                0
            )

        self.show_overview()

        self.statusBar().showMessage(
            f"Loaded paper: {data.get('file_name', 'PDF')}"
        )

        self.append_chat(
            "FlowPilot",
            f"Paper loaded successfully. "
            f"{data.get('page_count', 0)} pages and "
            f"{data.get('word_count', 0)} extracted words."
        )

        if data.get("empty_pages"):

            QMessageBox.warning(
                self,
                "PDF extraction warning",
                "Some pages have no extractable text:\n"
                + ", ".join(
                    map(
                        str,
                        data["empty_pages"]
                    )
                )
                + "\n\nScanned pages may require OCR."
            )

    def on_pdf_failed(
        self,
        message: str
    ):

        QMessageBox.critical(
            self,
            "PDF Import Failed",
            message
        )

        self.statusBar().showMessage(
            "PDF import failed"
        )

    # ==================================================
    # PAPER DISPLAY AND SEARCH
    # ==================================================

    def show_page(
        self,
        row: int
    ):

        if not self.paper_data or row < 0:
            return

        pages = self.paper_data.get(
            "pages",
            []
        )

        if row >= len(pages):
            return

        page = pages[row]

        text = page.get(
            "text",
            ""
        )

        if not text:

            text = (
                "No selectable text was extracted from this page.\n\n"
                "It may contain scanned text, images, or complex "
                "document content."
            )

        self.output.setPlainText(
            f"PAGE {page.get('page_number', row + 1)}\n"
            f"{'=' * 50}\n\n"
            f"{text}"
        )

        self.tabs.setCurrentIndex(0)

    def show_overview(self):

        if not self.paper_data:

            self.output.setPlainText(
                "Import a research paper first."
            )

            return

        self.output.setPlainText(
            self.paper_assistant.overview()
        )

        self.tabs.setCurrentIndex(0)

    def search_paper(self):

        query = self.search_box.text().strip()

        if not query:

            QMessageBox.information(
                self,
                "Search",
                "Enter a word or phrase to search for."
            )

            return

        result = self.paper_assistant.answer(
            query
        )

        self.output.setPlainText(
            result
        )

        self.tabs.setCurrentIndex(0)

    # ==================================================
    # SECTION ANALYSIS
    # ==================================================

    def analyze_sections(self):

        if not self.paper_data:

            QMessageBox.information(
                self,
                "No Paper",
                "Import a research paper first."
            )

            return

        if SectionExtractor is None:

            QMessageBox.warning(
                self,
                "Section extractor unavailable",
                "Could not import app.paper.section_extractor.SectionExtractor."
            )

            return

        try:

            extractor = SectionExtractor()

            self.sections = extractor.extract(
                self.paper_data
            )

            self.paper_assistant.set_paper(
                self.paper_data,
                self.sections
            )

            self.section_list.clear()

            for section in self.sections:

                self.section_list.addItem(
                    f"{section.title} "
                    f"(pages {section.start_page}-"
                    f"{section.end_page})"
                )

            if self.research_bridge:

                self.research_bridge.set_paper(
                    self.paper_data
                )

            self.append_chat(
                "FlowPilot",
                f"Section analysis complete. "
                f"Detected {len(self.sections)} sections."
            )

            self.statusBar().showMessage(
                f"Detected {len(self.sections)} sections"
            )

        except Exception:

            QMessageBox.critical(
                self,
                "Section analysis failed",
                traceback.format_exc()
            )

    def show_section(
        self,
        row: int
    ):

        if not 0 <= row < len(
            self.sections
        ):

            return

        section = self.sections[row]

        self.output.setPlainText(
            f"{section.title}\n"
            f"Pages {section.start_page}-{section.end_page}\n\n"
            f"{section.text}"
        )

        self.tabs.setCurrentIndex(0)

    # ==================================================
    # GNU RADIO
    # ==================================================

    def open_grc_tab(self):

        self.tabs.setCurrentIndex(2)

        self.check_grc()

    def check_grc(self):

        try:

            result = self.tools.call(
                "grc_status"
            )

        except Exception:

            result = traceback.format_exc()

        self.grc_output.setPlainText(
            result
        )

        self.statusBar().showMessage(
            "GNU Radio installation checked"
        )

    def list_grc(self):

        try:

            result = self.tools.call(
                "grc_list"
            )

        except Exception:

            result = traceback.format_exc()

        self.grc_output.setPlainText(
            result
        )

    def launch_grc(self):

        try:

            result = self.tools.call(
                "grc_launch"
            )

            self.grc_output.setPlainText(
                result
            )

            self.tabs.setCurrentIndex(2)

            self.statusBar().showMessage(
                "GNU Radio Companion launch requested"
            )

        except Exception as exc:

            QMessageBox.warning(
                self,
                "GNU Radio Companion",
                str(exc)
            )

    # ==================================================
    # CLEAN SHUTDOWN
    # ==================================================

    def closeEvent(self, event):

        if (
            self.worker is not None
            and self.worker.isRunning()
        ):

            self.worker.wait(3000)

        event.accept()