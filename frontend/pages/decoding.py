import pathlib
import asyncio
from typing import Tuple, List
from nicegui import ui, events, Client
from backend.config.config import URLS, CONFIG, SIZE_FACTOR
from backend.decoder.pdf import PDF
from frontend.pages.ui_custom import ui_dialog, UIGrid
from frontend.pages.page_abc import Page


class Decoding(Page):

    def __init__(self) -> None:
        super().__init__(url = URLS.DECODING)
        self.ui_grid: UIGrid = None  # noqa
        self.len_words: int = 0
        self.sentences: List[str] = []
        self.s_hash: int = 0
        self.d_hash: int = 0
        self.c_hash: int = 0
        self.content: bytes = b''
        self.max_file_size: int = CONFIG.Upload.max_file_size
        self.auto_upload: bool = CONFIG.Upload.auto_upload
        self.max_files: int = CONFIG.Upload.max_files

    def _open_upload(self) -> None:
        self._update_words()
        self.del_app_routes(url = URLS.DOWNLOAD)
        self.update_url_history()
        ui.open(f'{URLS.UPLOAD}')

    def _open_dictionaries(self) -> None:
        self._update_words()
        self.del_app_routes(url = URLS.DOWNLOAD)
        self.update_url_history()
        ui.open(f'{URLS.DICTIONARIES}')

    def _open_settings(self) -> None:
        self._update_words()
        self.del_app_routes(url = URLS.DOWNLOAD)
        self.update_url_history()
        ui.open(f'{URLS.SETTINGS}')

    @staticmethod
    def _open_pdf_view(pdf_view_path: str) -> None:
        ui.open(f'{pdf_view_path}', new_tab = True)

    def _load_table(self) -> None:
        self._set_item_size()
        self._table.refresh()
        self.ui_grid.load_table(self.decoder.source_words, self.decoder.target_words)

    def _preload_table(self) -> None:
        self._set_item_size()
        self._table.refresh()
        self.ui_grid.load_table(self.decoder.source_words, [''] * self.len_words)

    def _update_words(self) -> None:
        source_words, target_words = self.ui_grid.get_values()
        self.decoder.source_words = source_words
        self.decoder.target_words = target_words

    def _save_words(self):
        self._update_words()
        self._set_item_size()
        self._table.refresh()
        self._load_table()

    def _set_item_size(self) -> None:
        chars = self.utils.lonlen(self.decoder.source_words + self.decoder.target_words)
        chars = 20 if chars > 20 else chars
        self.ui_grid.item_size = chars * SIZE_FACTOR

    def _split_text(self) -> None:
        _hash = hash(self.decoder.source_text)
        if self.s_hash != _hash:
            self.s_hash = _hash
            self.decoder.split_text()
            self.len_words = len(self.decoder.source_words)

    async def _decode_words(self) -> None:
        _hash = hash(f'{self.decoder.source_text}{self.decoder.source_language}{self.decoder.target_language}')
        if self.decoder.source_text and self.d_hash != _hash:
            self.d_hash = _hash
            # FIXME: strange JavaScript TimeoutError with notification (over ~380 words)
            #   but applications seems to run anyway
            notification = ui.notification(
                message = f'{self.ui_language.DECODING.Messages.decoding} {self.len_words}',
                position = 'top',
                type = 'ongoing',
                multi_line = True,
                timeout = None,
                spinner = True,
                close_button = False,
            )
            await asyncio.to_thread(self.decoder.decode_words)
            self.sentences = await asyncio.to_thread(self.decoder.decode_sentences)
            self._apply_dict()
            notification.dismiss()
            return
        self._load_table()

    def _apply_dict(self):
        self.decoder.apply_dict()
        self._load_table()

    def _export(self):
        self._update_words()
        filename = self.decoder.title if self.decoder.title else 'decoded'
        content = self.decoder.export()
        route = self.upd_app_route(
            url = URLS.DOWNLOAD,
            content = content,
            file_type = 'json',
            filename = filename,
        )
        ui.download(route)

    def _create_dpf(self) -> Tuple[str, str]:
        _hash = hash(f'{self.decoder.title}{self.decoder.source_words}{self.decoder.target_words}')
        if self.c_hash != _hash:
            self.c_hash = _hash
            pdf = PDF(**self.pdf_params)
            self.content = pdf.convert2pdf(
                title = self.decoder.title,
                source_words = self.decoder.source_words,
                target_words = self.decoder.target_words
            )
        filename = self.decoder.title if self.decoder.title else 'decoded'
        route_view = self.upd_app_route(
            url = URLS.DOWNLOAD,
            content = self.content,
            file_type = 'pdf',
            filename = filename,
            disposition = 'inline'
        )
        route_down = self.upd_app_route(
            url = URLS.DOWNLOAD,
            content = self.content,
            file_type = 'pdf',
            filename = filename
        )
        return route_view, route_down

    def _dialog(self) -> ui_dialog:
        return ui_dialog(label_list = self.ui_language.DECODING.Dialogs)

    def _dialog_sentences(self) -> ui_dialog:
        return ui_dialog(label_list = self.sentences)

    def _pdf_dialog(self) -> None:
        self._save_words()
        route_view, route_down = self._create_dpf()
        with ui.dialog() as dialog:
            with ui.card().classes('items-center'):
                ui.button(icon = 'close', on_click = dialog.close) \
                    .classes('absolute-top-right') \
                    .props('dense round size=12px')
                ui.space()
                ui.label(self.ui_language.DECODING.Dialogs_pdf[0])
                ui.label(self.ui_language.DECODING.Dialogs_pdf[1])
                ui.button(text = 'VIEW PDF', on_click = lambda: self._open_pdf_view(route_view))
                ui.label(self.ui_language.DECODING.Dialogs_pdf[2])
                ui.button(text = 'DOWNLOAD', on_click = lambda: ui.download(route_down))
                dialog.open()

    def _on_upload_reject(self) -> None:
        ui.notify(f'{self.ui_language.DECODING.Messages.reject} {self.max_file_size / 10 ** 3} KB',
                  type = 'warning', position = 'top')

    def _upload_handler(self, event: events.UploadEventArguments) -> None:
        try:
            data = event.content.read().decode('utf-8')
        except Exception:
            ui.notify(self.ui_language.DECODING.Messages.invalid,
                      type = 'warning', position = 'top')
            return
        self.decoder.title = pathlib.Path(event.name).stem
        status = self.decoder.import_(data = data)
        if status:
            self._load_table()
        else:
            ui.notify(self.ui_language.DECODING.Messages.invalid,
                      type = 'warning', position = 'top')
        event.sender.reset()  # noqa upload reset

    def _import(self) -> None:
        with ui.dialog() as dialog:
            with ui.card().classes('items-center'):
                ui.button(icon = 'close', on_click = dialog.close) \
                    .classes('absolute-top-right') \
                    .props('dense round size=12px')
                ui.label(text = self.ui_language.DECODING.Dialogs_import[0])
                ui.upload(
                    label = self.ui_language.DECODING.Dialogs_import[1],
                    on_upload = self._upload_handler,
                    on_rejected = self._on_upload_reject,
                    max_file_size = self.max_file_size,
                    auto_upload = self.auto_upload,
                    max_files = self.max_files) \
                    .props('accept=.json flat dense')
            dialog.open()

    def _header(self) -> None:
        with ui.header():
            ui.button(text = 'GO BACK TO UPLOAD', on_click = self._open_upload)
            ui.label('DECODING').classes('absolute-center')
            ui.space()
            ui.button(text = 'DICTIONARIES', on_click = self._open_dictionaries)
            ui.button(icon = 'settings', on_click = self._open_settings)

    async def _center(self) -> None:
        self._split_text()
        with ui.column().classes('w-full items-center'):
            with ui.card().style('min-width:1000px; min-height:562px'):
                self._table()  # noqa
        self._preload_table()
        await self._decode_words()
        with ui.row().classes('absolute-top-right').style('gap:0.0rem'):
            with ui.column().style('gap:0.0rem'):
                ui.space().style('height:5px')
                with ui.button(icon = 'help', on_click = self._dialog().open).props('dense'):
                    if self.show_tips: ui.tooltip(self.ui_language.DECODING.Tips.help).style('width:70px')
            ui.space().style('width:5px')

    @ui.refreshable
    def _table(self) -> None:
        self.ui_grid = UIGrid()

    def _footer(self) -> None:
        with ui.footer():
            with ui.button(icon = 'find_replace', on_click = None).props('dense'):
                if self.show_tips: ui.tooltip('Replace')
                with ui.menu():
                    with ui.menu_item(auto_close = False):
                        ui.input(label = 'find')
                    with ui.menu_item(auto_close = False):
                        ui.input(label = 'replace')
            ui.space()
            with ui.button(text = 'IMPORT', on_click = self._import):
                if self.show_tips: ui.tooltip('Import words')
            ui.space()
            ui.button(text = 'APPLY DICT', on_click = self._apply_dict)
            ui.space()
            with ui.button(icon = 'save', on_click = self._save_words):
                if self.show_tips: ui.tooltip(self.ui_language.DECODING.Tips.save)
            ui.space()
            ui.button(text = 'CREATE PDF', on_click = self._pdf_dialog)
            ui.space()
            with ui.button(text = 'Export', on_click = self._export):
                if self.show_tips: ui.tooltip('Export words')
            ui.space().style()
            with ui.button(icon = 'article', on_click = self._dialog_sentences().open).props('dense'):
                if self.show_tips: ui.tooltip('Sentence view')

    async def page(self, client: Client) -> None:
        self.__init_ui__(client = client)
        await self._center()
        self._header()
        self._footer()
