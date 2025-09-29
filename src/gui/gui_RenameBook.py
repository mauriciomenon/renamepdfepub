from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from PyQt6.QtCore import QByteArray, QObject, QThread, Qt, QUrl, pyqtSignal, QSettings
from PyQt6.QtGui import QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QGridLayout,
    QLineEdit,
    QProgressBar,
    QSpinBox,
    QWidget,
)

try:
    import renamepdfepub.metadata_extractor as extractor
except ModuleNotFoundError:  # pragma: no cover - fallback para execucao direta
    if __package__:
        raise
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
        import renamepdfepub.metadata_extractor as extractor  # type: ignore[no-redef]
    else:
        raise


FIELD_ORDER: Sequence[str] = ("Title", "Author", "Year", "Publisher", "ISBN")
FIELD_SET: Set[str] = set(FIELD_ORDER)
DEFAULT_SELECTED_FIELDS = {"Title", "Author", "Year", "ISBN"}
FIELD_LABELS = {
    "Title": "Titulo",
    "Author": "Autor",
    "Year": "Ano",
    "Publisher": "Editora",
    "ISBN": "ISBN",
}
INVALID_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|]+")
DEFAULT_MAX_LENGTH = 90
MIN_FILENAME_LENGTH = 10


def normalize_metadata(raw: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    normalized: Dict[str, Optional[str]] = {field: None for field in FIELD_ORDER}

    title = raw.get("title") or raw.get("Title")
    subtitle = raw.get("subtitle") or raw.get("Subtitle")
    if title and subtitle:
        normalized["Title"] = f"{title}: {subtitle}"
    else:
        normalized["Title"] = title or subtitle

    normalized["Author"] = raw.get("authors") or raw.get("Author")
    normalized["Publisher"] = raw.get("publisher") or raw.get("Publisher")
    normalized["Year"] = raw.get("year") or raw.get("Year")

    isbn = (
        raw.get("isbn13")
        or raw.get("ISBN13")
        or raw.get("isbn10")
        or raw.get("ISBN")
    )
    if isbn:
        normalized["ISBN"] = isbn

    return normalized


def _validate_year(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        year = int(str(value)[:4])
    except ValueError:
        return None
    from datetime import datetime
    current = datetime.now().year
    if 1900 <= year <= current:
        return str(year)
    return None


def _clean_noise(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    t = str(text).strip()
    # Remove ocorrencias conhecidas de ruido
    noise_tokens = [
        "Fading Channels",
    ]
    for token in noise_tokens:
        t = t.replace(token, " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _fallback_from_filename(path: Path) -> Dict[str, Optional[str]]:
    """Heuristicas simples para extrair metadados do nome do arquivo."""
    name = path.stem
    result: Dict[str, Optional[str]] = {field: None for field in FIELD_ORDER}
    # Ano entre parenteses
    m = re.search(r"\((\d{4})\)", name)
    if m:
        result["Year"] = _validate_year(m.group(1))
        name = re.sub(r"\(\d{4}\)", "", name).strip()
    # Autor antes de " - "
    if " - " in name:
        author, title = name.split(" - ", 1)
        if author and not author[0].isdigit():
            result["Author"] = author.strip()
            name = title.strip()
    # Resto e titulo
    if name:
        result["Title"] = name.strip(" -")
    return result


def read_metadata(path: Path) -> Dict[str, Optional[str]]:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            raw = extractor.extract_from_pdf(str(path))
        elif ext == ".epub":
            raw = extractor.extract_from_epub(str(path))
        else:
            raw = {}
    except Exception as exc:  # pragma: no cover - GUI feedback only
        raise RuntimeError(str(exc))
    data = normalize_metadata(raw)
    # Limpeza de ruido e validacao
    data["Title"] = _clean_noise(data.get("Title"))
    data["Author"] = _clean_noise(data.get("Author"))
    data["Publisher"] = _clean_noise(data.get("Publisher"))
    data["Year"] = _validate_year(data.get("Year"))

    # Fallback por nome de arquivo quando campos essenciais estao ausentes
    if not data.get("Title") or not data.get("Author") or not data.get("Year"):
        fb = _fallback_from_filename(path)
        for k in ("Title", "Author", "Year"):
            if not data.get(k) and fb.get(k):
                data[k] = fb[k]
    return data


def sanitize_component(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = INVALID_FILENAME_CHARS.sub("_", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace("..", ".")
    while "__" in value:
        value = value.replace("__", "_")
    value = value.strip(" .-_")
    return value


def reduce_length(value: str, max_length: int = DEFAULT_MAX_LENGTH) -> str:
    max_length = max(MIN_FILENAME_LENGTH, max_length)
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def generate_new_name(
    source: Path,
    metadata: Dict[str, Optional[str]],
    field_order: Sequence[str],
    selected_fields: Sequence[str],
    max_length: int = DEFAULT_MAX_LENGTH,
) -> str:
    selected = set(selected_fields)
    components: List[str] = []
    for field in field_order:
        if field not in selected:
            continue
        value = metadata.get(field)
        if not value:
            continue
        sanitized = sanitize_component(value)
        if sanitized:
            components.append(sanitized)

    if not components:
        components.append(sanitize_component(source.stem) or "arquivo")

    joined = " - ".join(components)
    return reduce_length(joined, max_length)


def ensure_unique_path(directory: Path, base: str, suffix: str) -> Path:
    candidate = directory / f"{base}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = directory / f"{base} ({counter}){suffix}"
        counter += 1
    return candidate


def build_dependency_message() -> str:
    missing = []
    if getattr(extractor, "PdfReader", None) is None and getattr(extractor, "pdfplumber", None) is None:
        missing.append("pypdf/PyPDF2 ou pdfplumber")
    if getattr(extractor, "epub", None) is None:
        missing.append("ebooklib")
    if not missing:
        return "Dependencias opcionais carregadas."
    return (
        "Dependencias ausentes: "
        + ", ".join(missing)
        + ". Algumas funcionalidades podem ficar indisponiveis."
    )


class RenameWorker(QObject):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)

    def __init__(
        self,
        files: Sequence[str],
        copy_mode: bool,
        field_order: Sequence[str],
        selected_fields: Sequence[str],
        max_length: int = DEFAULT_MAX_LENGTH,
    ) -> None:
        super().__init__()
        self.files = list(files)
        self.copy_mode = copy_mode
        self.field_order = field_order
        self.selected_fields = selected_fields
        self.max_length = max_length
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:  # pragma: no cover - executed via thread
        results: List[str] = []
        total = len(self.files)
        cancelled = False
        for index, file_path in enumerate(self.files, start=1):
            if self._cancelled or QThread.currentThread().isInterruptionRequested():
                cancelled = True
                break
            source = Path(file_path)
            try:
                metadata = read_metadata(source)
                new_base = generate_new_name(
                    source,
                    metadata,
                    self.field_order,
                    self.selected_fields,
                    self.max_length,
                )
                target = ensure_unique_path(source.parent, new_base, source.suffix)
                if self.copy_mode:
                    shutil.copy2(source, target)
                    action = "Copiado"
                else:
                    source.rename(target)
                    action = "Renomeado"
                results.append(f"{action}: {source.name} -> {target.name}")
            except Exception as exc:
                results.append(f"Falhou: {source.name} ({exc})")
            self.progress.emit(index, total, source.name)
        if cancelled:
            results.append("Processo cancelado pelo usuario.")
        self.finished.emit(results)


class PreviewWorker(QObject):
    finished = pyqtSignal(int, dict, object)

    def __init__(self, token: int, file_path: Path) -> None:
        super().__init__()
        self.token = token
        self.file_path = file_path
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:  # pragma: no cover - executed via thread
        if self._cancelled:
            self.finished.emit(self.token, {}, "__cancelled__")
            return
        try:
            metadata = read_metadata(self.file_path)
        except RuntimeError as exc:
            self.finished.emit(self.token, {}, str(exc))
            return
        if self._cancelled:
            self.finished.emit(self.token, {}, "__cancelled__")
            return
        self.finished.emit(self.token, metadata, None)


class FileRenamer(QWidget):
    def __init__(self, initial_directory: Optional[str] = None) -> None:
        super().__init__()

        self.settings = QSettings("renamepdfepub", "GuiRenamer")
        self.last_directory = initial_directory or self._load_last_directory()
        stored_fields = self._load_selected_fields()
        copy_mode = self._load_copy_mode()
        max_length = self._load_max_length()

        self.setWindowTitle("Ebook Renamer: PDF/EPUB")
        self.setGeometry(100, 100, 560, 360)
        self.setAcceptDrops(True)

        geometry = self.settings.value("window_geometry")
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)
        elif isinstance(geometry, (bytes, bytearray)):
            self.restoreGeometry(QByteArray(geometry))

        self.selected_files: List[str] = []
        self.current_metadata: Dict[str, Optional[str]] = {field: None for field in FIELD_ORDER}
        self._metadata_ready = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[RenameWorker] = None
        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[PreviewWorker] = None
        self._preview_token = 0
        self._cancel_requested = False
        self._dependency_message = build_dependency_message()
        self._selected_fields_cached: Tuple[str, ...] = tuple()

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)

        self.instructions = QLabel("Selecione ou arraste arquivos PDF/EPUB para gerar um novo nome.")
        self.instructions.setWordWrap(True)
        grid.addWidget(self.instructions, 0, 0, 1, 3)

        self.open_button = QPushButton("Selecionar Arquivo(s)")
        self.open_button.clicked.connect(self.open_file_dialog)
        grid.addWidget(self.open_button, 1, 0)

        self.copy_check = QCheckBox("Copia (mantem o original)")
        self.copy_check.setChecked(copy_mode)
        self.copy_check.stateChanged.connect(self.on_copy_mode_changed)
        grid.addWidget(self.copy_check, 1, 1)

        # Utilitarios de relatorio
        self.scan_recursive_check = QCheckBox("Recursivo")
        grid.addWidget(self.scan_recursive_check, 1, 2)

        self.scan_button = QPushButton("Gerar relatorio da pasta")
        self.scan_button.clicked.connect(self.on_generate_folder_report)
        grid.addWidget(self.scan_button, 1, 3)

        self.drop_area = QLabel("Arraste e solte arquivos aqui.")
        self.drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_area.setMinimumHeight(55)
        self.drop_area.setStyleSheet("border: 2px dashed gray; color: #404040; padding: 8px;")
        grid.addWidget(self.drop_area, 2, 0, 1, 4)

        self.field_checkboxes: Dict[str, QCheckBox] = {}
        self.info_boxes: Dict[str, QLineEdit] = {}

        start_row = 3
        for offset, field in enumerate(FIELD_ORDER):
            checkbox = QCheckBox(FIELD_LABELS[field])
            checkbox.setChecked(field in stored_fields)
            checkbox.stateChanged.connect(self.on_field_checkbox_change)
            grid.addWidget(checkbox, start_row + offset, 0)
            self.field_checkboxes[field] = checkbox

            info_box = QLineEdit()
            info_box.setReadOnly(True)
            grid.addWidget(info_box, start_row + offset, 1, 1, 3)
            self.info_boxes[field] = info_box

        self._update_selected_fields_cache()

        preview_row = start_row + len(FIELD_ORDER)
        self.preview_label = QLabel("Previa do novo nome:")
        grid.addWidget(self.preview_label, preview_row, 0)

        self.preview_line = QLineEdit()
        self.preview_line.setReadOnly(True)
        grid.addWidget(self.preview_line, preview_row, 1, 1, 3)

        length_row = preview_row + 1
        self.length_label = QLabel("Limite de caracteres:")
        grid.addWidget(self.length_label, length_row, 0)

        self.max_length_spin = QSpinBox()
        self.max_length_spin.setMinimum(30)
        self.max_length_spin.setMaximum(255)
        self.max_length_spin.setValue(max_length)
        self.max_length_spin.valueChanged.connect(self.on_max_length_changed)
        grid.addWidget(self.max_length_spin, length_row, 1, 1, 3)

        status_row = length_row + 1
        self.status_label = QLabel(self._dependency_message)
        self.status_label.setWordWrap(True)
        grid.addWidget(self.status_label, status_row, 0, 1, 4)

        progress_row = status_row + 1
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.progress_bar, progress_row, 0, 1, 4)

        log_row = progress_row + 1
        self.log_label = QLabel("Historico do processamento:")
        grid.addWidget(self.log_label, log_row, 0)

        self.results_log = QPlainTextEdit()
        self.results_log.setReadOnly(True)
        self.results_log.setMinimumHeight(90)
        self.results_log.setPlaceholderText("Os resultados serao exibidos aqui apos a execucao.")
        grid.addWidget(self.results_log, log_row, 1, 1, 2)

        button_row = log_row + 1
        button_layout = QHBoxLayout()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.request_cancel)
        button_layout.addWidget(self.cancel_btn)

        self.open_folder_btn = QPushButton("Abrir pasta")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self.open_selected_folder)
        button_layout.addWidget(self.open_folder_btn)

        self.copy_log_btn = QPushButton("Copiar resultado")
        self.copy_log_btn.setEnabled(False)
        self.copy_log_btn.clicked.connect(self.copy_results_to_clipboard)
        button_layout.addWidget(self.copy_log_btn)

        button_layout.addStretch()

        self.confirm_btn = QPushButton("Renomear")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.execute_renaming)
        button_layout.addWidget(self.confirm_btn)

        grid.addLayout(button_layout, button_row, 0, 1, 3)

        self.setLayout(grid)
        self.update_copy_button_state()
        self.update_folder_button_state()

    # --- Drag and drop ---------------------------------------------------------------
    def dragEnterEvent(self, event):  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):  # type: ignore[override]
        self.drop_area.setText("Arraste e solte arquivos aqui.")

    def dropEvent(self, event):  # type: ignore[override]
        if self._thread is not None:
            QMessageBox.warning(self, "Processo em andamento", "Aguarde o termino da operacao atual.")
            return
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.handle_new_selection(paths)

    # --- Interaction -----------------------------------------------------------------
    def open_file_dialog(self) -> None:
        if self._thread is not None:
            QMessageBox.warning(self, "Processo em andamento", "Aguarde o termino da operacao atual.")
            return
        start_dir = self.last_directory if Path(self.last_directory).exists() else str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecione um ou mais arquivos",
            start_dir,
            "PDF (*.pdf);;EPUB (*.epub)",
        )
        if files:
            self.handle_new_selection(files)

    def handle_new_selection(self, files: List[str]) -> None:
        self.selected_files = files
        if not files:
            self.reset_state()
            return

        first_path = Path(files[0])
        self.last_directory = str(first_path.parent)
        pretty_list = ", ".join(Path(f).name for f in files[:3])
        if len(files) > 3:
            pretty_list += f" (+{len(files) - 3})"
        self.instructions.setText(f"Selecionado(s): {pretty_list}")
        self.drop_area.setText("Arquivos carregados.")
        self.confirm_btn.setEnabled(True)
        self.update_folder_button_state()

        self.current_metadata = {field: None for field in FIELD_ORDER}
        self._metadata_ready = False
        self.preview_line.clear()
        self._set_info_boxes_text("Carregando...")

        self.save_preferences()
        self.start_preview_loader(first_path)
        self.update_preview()

    def selected_fields(self) -> List[str]:
        return list(self._selected_fields_cached)

    def on_copy_mode_changed(self, _state: int) -> None:
        self.save_preferences()

    def on_field_checkbox_change(self, _state: int) -> None:
        self._update_selected_fields_cache()
        self.save_preferences()
        self.update_preview()

    def on_max_length_changed(self, _value: int) -> None:
        self.save_preferences()
        self.update_preview()

    # --- Metadata preview ------------------------------------------------------------
    def update_preview(self) -> None:
        if not self.selected_files:
            self.preview_line.clear()
            return

        first_path = Path(self.selected_files[0])
        new_name = generate_new_name(
            first_path,
            self.current_metadata,
            FIELD_ORDER,
            self.selected_fields(),
            self.max_length_spin.value(),
        )
        self.preview_line.setText(f"{new_name}{first_path.suffix}")

    # --- Renaming --------------------------------------------------------------------
    def execute_renaming(self) -> None:
        if not self.selected_files or self._thread is not None:
            return

        selected_fields = self.selected_fields()
        if not selected_fields:
            choice = QMessageBox.question(
                self,
                "Nenhum campo selecionado",
                "Nenhum campo esta marcado para compor o novo nome. Deseja continuar usando o nome atual do arquivo?",
            )
            if choice != QMessageBox.StandardButton.Yes:
                return

        files_snapshot = list(self.selected_files)

        self.save_preferences()
        self.results_log.clear()
        self.update_copy_button_state()
        self._cancel_requested = False
        self.toggle_interaction(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(files_snapshot))
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.status_label.setText("Iniciando renomeacao...")

        self._thread = QThread(self)
        self._worker = RenameWorker(
            files_snapshot,
            self.copy_check.isChecked(),
            FIELD_ORDER,
            selected_fields,
            max_length=self.max_length_spin.value(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_worker_progress)
        self._worker.finished.connect(self.on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self.cleanup_thread)
        self._thread.start()

    def on_worker_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total} - {filename}")
        self.status_label.setText(f"Processando ({current}/{total}): {filename}")

    def on_worker_finished(self, results: List[str]) -> None:
        summary = "\n".join(results) if results else "Nenhum arquivo processado."
        self.results_log.setPlainText(summary)
        self.update_copy_button_state()
        was_cancelled = bool(results and results[-1] == "Processo cancelado pelo usuario.")
        title = "Operacao cancelada" if was_cancelled else "Processo concluido"
        QMessageBox.information(self, title, summary)
        status_message = (
            "Operacao cancelada pelo usuario. Veja o historico abaixo."
            if was_cancelled
            else "Processo concluido. Veja o historico abaixo."
        )
        self.reset_state(status_message, clear_results=False)

    def cleanup_thread(self) -> None:
        if self._thread:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self.toggle_interaction(True)

    def reset_state(self, status_message: Optional[str] = None, clear_results: bool = True) -> None:
        self._preview_token += 1
        self._stop_preview_thread(wait=False)
        self._metadata_ready = False
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.status_label.setText(status_message or self._dependency_message)
        self.confirm_btn.setEnabled(False)
        self.selected_files = []
        self.preview_line.clear()
        self.drop_area.setText("Arraste e solte arquivos aqui.")
        self.instructions.setText("Selecione ou arraste arquivos PDF/EPUB para gerar um novo nome.")
        for box in self.info_boxes.values():
            box.clear()
            box.setPlaceholderText("Nao disponivel")
        if clear_results:
            self.results_log.clear()
        self.update_folder_button_state()
        self.update_copy_button_state()
        self.cancel_btn.setEnabled(False)
        self._cancel_requested = False
        self.save_preferences()

    def toggle_interaction(self, enabled: bool) -> None:
        self.open_button.setEnabled(enabled)
        self.copy_check.setEnabled(enabled)
        self.max_length_spin.setEnabled(enabled)
        for checkbox in self.field_checkboxes.values():
            checkbox.setEnabled(enabled)
        if not enabled:
            self.confirm_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
        else:
            self.confirm_btn.setEnabled(bool(self.selected_files))
            self.cancel_btn.setEnabled(False)
        self.update_folder_button_state()

    def save_preferences(self) -> None:
        self.settings.setValue("selected_fields", ",".join(self._selected_fields_cached))
        self.settings.setValue("copy_mode", self.copy_check.isChecked())
        self.settings.setValue("max_length", self.max_length_spin.value())
        if getattr(self, "last_directory", None):
            self.settings.setValue("last_directory", self.last_directory)

    def update_folder_button_state(self) -> None:
        if hasattr(self, "open_folder_btn"):
            can_open = bool(self.selected_files) and self.open_button.isEnabled()
            self.open_folder_btn.setEnabled(can_open)

    def update_copy_button_state(self) -> None:
        if hasattr(self, "copy_log_btn"):
            has_text = bool(self.results_log.toPlainText().strip())
            self.copy_log_btn.setEnabled(has_text)

    def open_selected_folder(self) -> None:
        if not self.selected_files:
            return
        folder = Path(self.selected_files[0]).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def copy_results_to_clipboard(self) -> None:
        text = self.results_log.toPlainText().strip()
        if not text:
            self.status_label.setText("Nenhum resultado para copiar ainda.")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText("Historico copiado para a area de transferencia.")

    def _update_selected_fields_cache(self) -> None:
        self._selected_fields_cached = tuple(
            field for field in FIELD_ORDER if self.field_checkboxes[field].isChecked()
        )

    def _set_info_boxes_text(self, text: str) -> None:
        for box in self.info_boxes.values():
            box.setText(text)

    def _apply_metadata_to_fields(self, metadata: Dict[str, Optional[str]]) -> None:
        for field, box in self.info_boxes.items():
            value = metadata.get(field)
            box.setText(value if value else "Nao disponivel")

    def start_preview_loader(self, file_path: Path) -> None:
        self._stop_preview_thread(wait=False)
        self._preview_token += 1
        self._preview_worker = PreviewWorker(self._preview_token, file_path)
        self._preview_thread = QThread()
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.finished.connect(self.on_preview_finished)
        self._preview_worker.finished.connect(self._preview_thread.quit)
        self._preview_worker.finished.connect(self._preview_worker.deleteLater)
        self._preview_thread.finished.connect(self._on_preview_thread_finished)
        self.status_label.setText("Carregando metadados...")
        self._preview_thread.start()

    def _stop_preview_thread(self, wait: bool) -> None:
        if self._preview_worker:
            self._preview_worker.cancel()
        if self._preview_thread:
            self._preview_thread.quit()
            if wait:
                self._preview_thread.wait()
                if not self._preview_thread.isRunning():
                    self._preview_thread.deleteLater()
                    self._preview_thread = None
                    self._preview_worker = None

    def _on_preview_thread_finished(self) -> None:
        if self._preview_thread:
            self._preview_thread.deleteLater()
        self._preview_thread = None
        self._preview_worker = None

    def on_preview_finished(self, token: int, metadata: Dict[str, Optional[str]], error: object) -> None:
        if token != self._preview_token:
            return
        self._metadata_ready = False
        if error and error != "__cancelled__":
            message = str(error)
            self.current_metadata = {field: None for field in FIELD_ORDER}
            self._set_info_boxes_text("Nao disponivel")
            first_file = Path(self.selected_files[0]) if self.selected_files else None
            self.status_label.setText(f"Falha ao extrair metadados: {message}")
            if first_file is not None:
                QMessageBox.warning(
                    self,
                    "Erro ao extrair metadados",
                    f"Nao foi possivel ler os metadados de {first_file.name}: {message}",
                )
            self.update_preview()
            return
        if error == "__cancelled__":
            return
        self.current_metadata = metadata
        self._metadata_ready = True
        self._apply_metadata_to_fields(metadata)
        self.status_label.setText(self._dependency_message)
        self.update_preview()

    def request_cancel(self) -> None:
        if not self._thread or not self._worker:
            return
        self._cancel_requested = True
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Cancelando operacao...")
        self._worker.cancel()
        self._thread.requestInterruption()

    def _load_selected_fields(self) -> Set[str]:
        value = self.settings.value("selected_fields")
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            if items:
                return set(items).intersection(FIELD_SET)
        elif isinstance(value, (list, tuple)):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return set(items).intersection(FIELD_SET)
        return set(DEFAULT_SELECTED_FIELDS)

    def _load_copy_mode(self) -> bool:
        value = self.settings.value("copy_mode")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return False

    def _load_max_length(self) -> int:
        value = self.settings.value("max_length")
        try:
            number = int(value)
        except (TypeError, ValueError):
            return DEFAULT_MAX_LENGTH
        return max(30, min(255, number))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread and self._thread.isRunning():
            choice = QMessageBox.question(
                self,
                "Processo em andamento",
                "Uma renomeacao esta em progresso. Deseja cancelar e fechar a aplicacao?",
            )
            if choice != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.request_cancel()
            if self._thread.isRunning() and not self._thread.wait(5000):
                QMessageBox.warning(
                    self,
                    "Encerramento em andamento",
                    "A operacao ainda esta finalizando. Tente novamente em alguns instantes.",
                )
                event.ignore()
                return

        self._stop_preview_thread(wait=True)
        self.save_preferences()
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.sync()
        super().closeEvent(event)

    def _load_last_directory(self) -> str:
        value = self.settings.value("last_directory")
        if isinstance(value, str) and value:
            return value
        return str(Path.home())

    def on_generate_folder_report(self) -> None:
        """Executa varredura de metadados na pasta escolhida e gera JSON/HTML em reports/."""
        from PyQt6.QtWidgets import QFileDialog
        import subprocess
        import sys as _sys

        start_dir = self.last_directory or str(Path.home())
        directory = QFileDialog.getExistingDirectory(self, "Selecione a pasta para relatorio", start_dir)
        if not directory:
            return

        recursive = self.scan_recursive_check.isChecked()
        extractor = Path(__file__).resolve().parent / "renomeia_livro_renew_v2.py"
        if not extractor.exists():
            QMessageBox.warning(self, "Ferramenta ausente", "renomeia_livro_renew_v2.py nao encontrada.")
            return
        args = [_sys.executable, str(extractor), directory]
        if recursive:
            args.append("-r")
        self.status_label.setText("Gerando relatorio da pasta...")
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=600)
        except Exception as exc:
            QMessageBox.critical(self, "Erro na varredura", str(exc))
            self.status_label.setText(self._dependency_message)
            return
        if result.returncode == 0:
            QMessageBox.information(self, "Concluido", "Relatorio gerado em reports/. Abra no navegador ou use o Dashboard.")
        else:
            QMessageBox.warning(self, "Falha", result.stderr or result.stdout or "Falha desconhecida.")
        self.status_label.setText(self._dependency_message)


if __name__ == "__main__":
    app = QApplication([])
    window = FileRenamer()
    window.show()
    app.exec()
