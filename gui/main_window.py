"""
Главное окно GUI приложения
"""
import copy
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from bots import BotManager
from config import config
from utils import answer_generator, logger


class MainWindow:
    """Главное окно приложения."""

    ACCOUNT_MARKETPLACES = ("ozon", "wildberries")

    def __init__(self, root):
        self.root = root
        self.root.title("Бот для маркетплейсов v1.0")
        self.root.geometry("900x760")
        self.root.resizable(True, True)

        self.bot_manager = BotManager(config_manager=config)
        self.accounts = []
        self.selected_account_index = None
        self.entry_context_menu = None
        self._entry_context_widget = None

        self._setup_styles()
        self._create_widgets()

        logger.set_gui_callback(self._log_message)
        self._load_config()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        """Настройка стилей."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Title.TLabel", font=("Arial", 14, "bold"))
        style.configure("Header.TLabel", font=("Arial", 11, "bold"))
        style.configure("Normal.TLabel", font=("Arial", 10))

        style.configure("Success.TButton", foreground="green")
        style.configure("Danger.TButton", foreground="red")

    def _create_widgets(self):
        """Создание виджетов."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="Настройки")
        self._create_settings_tab()

        self.templates_frame = ttk.Frame(notebook)
        notebook.add(self.templates_frame, text="Шаблоны ответов")
        self._create_templates_tab()

        self.logs_frame = ttk.Frame(notebook)
        notebook.add(self.logs_frame, text="Логи")
        self._create_logs_tab()

        self.status_frame = ttk.Frame(notebook)
        notebook.add(self.status_frame, text="Статус")
        self._create_status_tab()

    def _create_settings_tab(self):
        """Создание вкладки настроек."""
        accounts_group = ttk.LabelFrame(self.settings_frame, text="Аккаунты", padding=10)
        accounts_group.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(
            accounts_group,
            text=(
                "Добавьте кабинеты Ozon и Wildberries. Для изменения списка аккаунтов "
                "остановите всех ботов, затем нажмите «Сохранить изменения»."
            ),
            font=("Arial", 8),
            foreground="gray25",
        ).pack(anchor="w", pady=(0, 8))

        accounts_buttons = ttk.Frame(accounts_group)
        accounts_buttons.pack(fill="x", pady=(0, 8))

        self.add_account_button = ttk.Button(accounts_buttons, text="Добавить", command=self._add_account)
        self.add_account_button.pack(side="left", padx=(0, 5))

        self.save_account_button = ttk.Button(
            accounts_buttons,
            text="Сохранить изменения",
            command=self._save_settings,
        )
        self.save_account_button.pack(side="left", padx=5)

        self.delete_account_button = ttk.Button(accounts_buttons, text="Удалить", command=self._delete_account)
        self.delete_account_button.pack(side="left", padx=5)

        self.account_lock_label = ttk.Label(accounts_buttons, text="", foreground="orange")
        self.account_lock_label.pack(side="right")

        accounts_content = ttk.Frame(accounts_group)
        accounts_content.pack(fill="both", expand=True)
        accounts_content.columnconfigure(0, weight=1)
        accounts_content.columnconfigure(1, weight=1)
        accounts_content.rowconfigure(0, weight=1)

        list_frame = ttk.Frame(accounts_content)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.accounts_tree = ttk.Treeview(
            list_frame,
            columns=("name", "marketplace", "enabled"),
            show="headings",
            height=8,
            selectmode="browse",
        )
        self.accounts_tree.heading("name", text="Название")
        self.accounts_tree.heading("marketplace", text="Маркетплейс")
        self.accounts_tree.heading("enabled", text="Включен")
        self.accounts_tree.column("name", width=220, anchor="w")
        self.accounts_tree.column("marketplace", width=120, anchor="w")
        self.accounts_tree.column("enabled", width=90, anchor="center")
        self.accounts_tree.grid(row=0, column=0, sticky="nsew")
        self.accounts_tree.bind("<<TreeviewSelect>>", self._on_account_selected)

        tree_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.accounts_tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.accounts_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.accounts_empty_label = ttk.Label(
            list_frame,
            text="Аккаунты еще не добавлены. Нажмите «Добавить», чтобы создать первый кабинет.",
            foreground="gray25",
            wraplength=320,
            justify="left",
        )
        self.accounts_empty_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        form_frame = ttk.LabelFrame(accounts_content, text="Редактирование аккаунта", padding=10)
        form_frame.grid(row=0, column=1, sticky="nsew")
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Название:").grid(row=0, column=0, sticky="w", pady=5)
        self.account_name_var = tk.StringVar()
        self.account_name_entry = ttk.Entry(form_frame, textvariable=self.account_name_var, width=40)
        self.account_name_entry.grid(row=0, column=1, sticky="we", pady=5)

        ttk.Label(form_frame, text="Маркетплейс:").grid(row=1, column=0, sticky="w", pady=5)
        self.account_marketplace_var = tk.StringVar(value="ozon")
        self.account_marketplace_combo = ttk.Combobox(
            form_frame,
            textvariable=self.account_marketplace_var,
            values=self.ACCOUNT_MARKETPLACES,
            state="readonly",
            width=18,
        )
        self.account_marketplace_combo.grid(row=1, column=1, sticky="w", pady=5)
        self.account_marketplace_combo.bind("<<ComboboxSelected>>", self._on_marketplace_changed)

        ttk.Label(form_frame, text="Включен:").grid(row=2, column=0, sticky="w", pady=5)
        self.account_enabled_var = tk.BooleanVar(value=False)
        self.account_enabled_checkbutton = ttk.Checkbutton(form_frame, variable=self.account_enabled_var)
        self.account_enabled_checkbutton.grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(form_frame, text="API Key:").grid(row=3, column=0, sticky="w", pady=5)
        self.account_api_key_var = tk.StringVar()
        self.account_api_key_visible = tk.BooleanVar(value=False)
        self.account_api_key_entry = self._create_entry_field(
            form_frame,
            row=3,
            textvariable=self.account_api_key_var,
            show="*",
            visibility_var=self.account_api_key_visible,
        )
        self._create_entry_hint(
            form_frame,
            row=4,
            text="Вставьте API Key. Работают Ctrl+V, Shift+Insert и правый клик мыши.",
        )

        self.account_company_id_label = ttk.Label(form_frame, text="Company ID:")
        self.account_company_id_label.grid(row=5, column=0, sticky="w", pady=5)
        self.account_company_id_var = tk.StringVar()
        self.account_company_id_entry = self._create_entry_field(
            form_frame,
            row=5,
            textvariable=self.account_company_id_var,
        )
        self.account_company_id_hint_label = ttk.Label(
            form_frame,
            text="Для Ozon это поле обязательно. Для Wildberries оно не используется.",
            font=("Arial", 8),
            foreground="gray25",
        )
        self.account_company_id_hint_label.grid(row=6, column=1, sticky="w", pady=(0, 5))

        general_group = ttk.LabelFrame(self.settings_frame, text="Общие настройки", padding=10)
        general_group.pack(fill="x", padx=10, pady=5)

        ttk.Label(general_group, text="Интервал проверки (минуты):").grid(row=0, column=0, sticky="w", pady=5)
        self.check_interval = tk.IntVar(value=60)
        ttk.Entry(general_group, textvariable=self.check_interval, width=10).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(general_group, text="Мин. звезд для ответа:").grid(row=1, column=0, sticky="w", pady=5)
        self.min_stars = tk.IntVar(value=1)
        ttk.Spinbox(general_group, from_=1, to=5, textvariable=self.min_stars, width=8).grid(
            row=1,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Label(general_group, text="Макс. ответов за один цикл:").grid(row=2, column=0, sticky="w", pady=5)
        self.max_answers = tk.IntVar(value=-1)
        ttk.Entry(general_group, textvariable=self.max_answers, width=10).grid(row=2, column=1, sticky="w", pady=5)
        ttk.Label(general_group, text="(-1 = без ограничений)", font=("Arial", 8)).grid(
            row=2,
            column=2,
            sticky="w",
            pady=5,
        )

        ttk.Label(general_group, text="Задержка между запросами (сек):").grid(row=3, column=0, sticky="w", pady=5)
        self.short_sleep = tk.DoubleVar(value=0.5)
        ttk.Entry(general_group, textvariable=self.short_sleep, width=10).grid(row=3, column=1, sticky="w", pady=5)

        buttons_frame = ttk.Frame(self.settings_frame)
        buttons_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            buttons_frame,
            text="Запустить включенные аккаунты",
            command=self._start_bots,
        ).pack(side="left", padx=5)
        ttk.Button(
            buttons_frame,
            text="Остановить всех ботов",
            command=self._stop_bots,
        ).pack(side="left", padx=5)

    def _create_entry_field(self, parent, row, textvariable, show=None, visibility_var=None):
        """Создание поля ввода с привычным для desktop UX."""
        field_frame = ttk.Frame(parent)
        field_frame.grid(row=row, column=1, sticky="we", pady=5)
        field_frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(field_frame, textvariable=textvariable, width=50, show=show)
        entry.grid(row=0, column=0, sticky="we")
        self._bind_entry_ux(entry)

        if visibility_var is not None:
            ttk.Checkbutton(
                field_frame,
                text="Показать",
                variable=visibility_var,
                command=lambda entry=entry, var=visibility_var: self._toggle_secret_visibility(entry, var),
            ).grid(row=0, column=1, padx=(8, 0))

        return entry

    @staticmethod
    def _create_entry_hint(parent, row, text):
        """Короткая подсказка под полем ввода."""
        ttk.Label(parent, text=text, font=("Arial", 8), foreground="gray25").grid(
            row=row,
            column=1,
            sticky="w",
            pady=(0, 5),
        )

    def _bind_entry_ux(self, entry):
        """Горячие клавиши и правый клик для стандартных полей ввода."""
        shortcuts = {
            "<Control-x>": "cut",
            "<Control-X>": "cut",
            "<Control-c>": "copy",
            "<Control-C>": "copy",
            "<Control-v>": "paste",
            "<Control-V>": "paste",
            "<Shift-Insert>": "paste",
            "<Control-a>": "select_all",
            "<Control-A>": "select_all",
        }

        for sequence, action in shortcuts.items():
            entry.bind(sequence, lambda event, action=action: self._handle_entry_shortcut(event, action))

        entry.bind("<Button-3>", self._show_entry_context_menu)
        return entry

    def _ensure_entry_context_menu(self):
        """Ленивая инициализация контекстного меню для Entry."""
        if self.entry_context_menu is not None:
            return self.entry_context_menu

        self.entry_context_menu = tk.Menu(self.root, tearoff=0)
        self.entry_context_menu.add_command(label="Вырезать", command=lambda: self._perform_context_menu_action("cut"))
        self.entry_context_menu.add_command(label="Копировать", command=lambda: self._perform_context_menu_action("copy"))
        self.entry_context_menu.add_command(label="Вставить", command=lambda: self._perform_context_menu_action("paste"))
        self.entry_context_menu.add_separator()
        self.entry_context_menu.add_command(
            label="Выделить всё",
            command=lambda: self._perform_context_menu_action("select_all"),
        )
        return self.entry_context_menu

    def _show_entry_context_menu(self, event):
        """Открытие контекстного меню по правому клику."""
        self._entry_context_widget = getattr(event, "widget", None)
        if self._entry_context_widget and hasattr(self._entry_context_widget, "focus_set"):
            self._entry_context_widget.focus_set()

        menu = self._ensure_entry_context_menu()
        menu.tk_popup(event.x_root, event.y_root)
        if hasattr(menu, "grab_release"):
            menu.grab_release()
        return "break"

    def _handle_entry_shortcut(self, event, action):
        """Обработка keyboard shortcuts для Entry."""
        self._perform_entry_action(getattr(event, "widget", None), action)
        return "break"

    def _perform_context_menu_action(self, action):
        """Действие контекстного меню для текущего активного поля."""
        self._perform_entry_action(self._entry_context_widget, action)

    @staticmethod
    def _perform_entry_action(widget, action):
        """Безопасное действие над полем ввода."""
        if widget is None:
            return

        try:
            if action == "select_all":
                if hasattr(widget, "focus_set"):
                    widget.focus_set()
                if hasattr(widget, "selection_range"):
                    widget.selection_range(0, "end")
                if hasattr(widget, "icursor"):
                    widget.icursor("end")
                return

            event_name = {
                "cut": "<<Cut>>",
                "copy": "<<Copy>>",
                "paste": "<<Paste>>",
            }.get(action)
            if event_name and hasattr(widget, "event_generate"):
                widget.event_generate(event_name)
        except tk.TclError:
            pass

    @staticmethod
    def _toggle_secret_visibility(entry, visibility_var):
        """Показать или скрыть содержимое secret-поля."""
        entry.configure(show="" if visibility_var.get() else "*")

    def _create_templates_tab(self):
        """Создание вкладки шаблонов ответов."""
        buttons_frame = ttk.Frame(self.templates_frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(buttons_frame, text="Загрузить шаблоны", command=self._load_templates).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Сохранить шаблоны", command=self._save_templates).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Сбросить по умолчанию", command=self._reset_templates).pack(side="left", padx=5)

        ttk.Label(self.templates_frame, text="Редактирование шаблонов ответов (JSON):").pack(
            anchor="w",
            padx=10,
            pady=5,
        )

        self.templates_text = scrolledtext.ScrolledText(self.templates_frame, width=90, height=30)
        self.templates_text.pack(fill="both", expand=True, padx=10, pady=5)

    def _create_logs_tab(self):
        """Создание вкладки логов."""
        buttons_frame = ttk.Frame(self.logs_frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(buttons_frame, text="Очистить логи", command=self._clear_logs).pack(side="left", padx=5)
        ttk.Button(buttons_frame, text="Сохранить лог в файл", command=self._save_logs).pack(side="left", padx=5)

        self.logs_text = scrolledtext.ScrolledText(self.logs_frame, width=90, height=30)
        self.logs_text.pack(fill="both", expand=True, padx=10, pady=5)
        self.logs_text.config(state="disabled")

    def _create_status_tab(self):
        """Создание вкладки статуса."""
        status_group = ttk.LabelFrame(self.status_frame, text="Статусы аккаунтов", padding=10)
        status_group.pack(fill="both", expand=True, padx=10, pady=5)

        self.status_text = scrolledtext.ScrolledText(status_group, width=90, height=30, wrap="word")
        self.status_text.pack(fill="both", expand=True)
        self.status_text.config(state="disabled")

        ttk.Button(self.status_frame, text="Обновить статус", command=self._update_status).pack(pady=10)

    @staticmethod
    def _marketplace_display_name(marketplace):
        """Человекочитаемое имя маркетплейса."""
        return "Ozon" if marketplace == "ozon" else "Wildberries"

    def _default_account_name(self, marketplace, exclude_index=None):
        """Имя нового аккаунта по умолчанию."""
        existing_accounts = [
            account
            for index, account in enumerate(self.accounts)
            if index != exclude_index and account.get("marketplace") == marketplace
        ]
        base_name = self._marketplace_display_name(marketplace)
        return base_name if not existing_accounts else f"{base_name} {len(existing_accounts) + 1}"

    def _next_account_id(self, marketplace, exclude_index=None):
        """Следующий свободный account_id."""
        used_ids = {
            str(account.get("id"))
            for index, account in enumerate(self.accounts)
            if index != exclude_index and account.get("id")
        }
        index = 1
        while True:
            candidate = f"{marketplace}-{index}"
            if candidate not in used_ids:
                return candidate
            index += 1

    def _load_config(self):
        """Загрузка конфигурации."""
        try:
            self.accounts = config.get_accounts()

            general = config.get("general")
            if general:
                self.check_interval.set(general.get("check_interval", 60))
                self.min_stars.set(general.get("min_stars", 1))
                self.max_answers.set(general.get("max_answers_per_run", -1))
                self.short_sleep.set(general.get("short_sleep", 0.5))

            templates = config.get_answer_templates()
            import json

            self.templates_text.delete("1.0", "end")
            self.templates_text.insert("1.0", json.dumps(templates, ensure_ascii=False, indent=4))

            self._refresh_accounts_tree()
            if self.accounts:
                self._select_account(0)
            else:
                self._clear_account_form()
                self.selected_account_index = None
                self._update_account_form_state()

            self._update_status()
            logger.info("Конфигурация загружена")
        except Exception as error:
            logger.error(f"Ошибка загрузки конфигурации: {error}")

    def _save_settings(self, show_message=True):
        """Сохранение аккаунтов и общих настроек."""
        if self._account_changes_locked(show_message=show_message):
            return False

        try:
            account_id_to_restore = None
            if self.selected_account_index is not None and 0 <= self.selected_account_index < len(self.accounts):
                updated_account = self._build_account_from_form(self.selected_account_index)
                if updated_account is None:
                    return False
                self.accounts[self.selected_account_index] = updated_account
                account_id_to_restore = updated_account.get("id")
            elif self.accounts:
                account_id_to_restore = self.accounts[0].get("id")

            config.set_accounts(copy.deepcopy(self.accounts))
            config.set("general", "check_interval", self.check_interval.get())
            config.set("general", "min_stars", self.min_stars.get())
            config.set("general", "max_answers_per_run", self.max_answers.get())
            config.set("general", "short_sleep", self.short_sleep.get())
            config.save_config()

            self.accounts = config.get_accounts()
            self._refresh_accounts_tree(account_id_to_restore)
            if self.accounts:
                if account_id_to_restore is not None:
                    self._select_account_by_id(account_id_to_restore)
                elif self.selected_account_index is not None:
                    self._select_account(min(self.selected_account_index, len(self.accounts) - 1))
                else:
                    self._select_account(0)
            else:
                self.selected_account_index = None
                self._clear_account_form()
                self._update_account_form_state()

            self._update_status()
            if show_message:
                messagebox.showinfo("Успех", "Изменения сохранены.")
            logger.info("Настройки сохранены")
            return True
        except Exception as error:
            logger.error(f"Ошибка сохранения настроек: {error}")
            if show_message:
                messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {error}")
            return False

    def _load_templates(self):
        """Загрузка шаблонов из файла."""
        try:
            filename = filedialog.askopenfilename(
                title="Выберите файл шаблонов",
                filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
            )

            if filename:
                with open(filename, "r", encoding="utf-8") as file:
                    import json

                    templates = json.load(file)

                self.templates_text.delete("1.0", "end")
                self.templates_text.insert("1.0", json.dumps(templates, ensure_ascii=False, indent=4))
                logger.info(f"Шаблоны загружены из {filename}")
        except Exception as error:
            logger.error(f"Ошибка загрузки шаблонов: {error}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить шаблоны: {error}")

    def _save_templates(self):
        """Сохранение шаблонов."""
        try:
            import json

            templates_text = self.templates_text.get("1.0", "end")
            templates = json.loads(templates_text)

            config.set_answers(templates)
            config.save_answers()
            answer_generator.update_templates(templates)

            messagebox.showinfo("Успех", "Шаблоны сохранены!")
            logger.info("Шаблоны сохранены")
        except json.JSONDecodeError as error:
            logger.error(f"Ошибка JSON: {error}")
            messagebox.showerror("Ошибка", f"Неверный формат JSON: {error}")
        except Exception as error:
            logger.error(f"Ошибка сохранения шаблонов: {error}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить шаблоны: {error}")

    def _reset_templates(self):
        """Сброс шаблонов по умолчанию."""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сбросить шаблоны?"):
            try:
                from config import DEFAULT_ANSWERS
                import json

                self.templates_text.delete("1.0", "end")
                self.templates_text.insert("1.0", json.dumps(DEFAULT_ANSWERS, ensure_ascii=False, indent=4))
                logger.info("Шаблоны сброшены по умолчанию")
            except Exception as error:
                logger.error(f"Ошибка сброса шаблонов: {error}")

    def _build_new_account(self, marketplace="ozon"):
        """Создание нового локального аккаунта по умолчанию."""
        return {
            "id": self._next_account_id(marketplace),
            "name": self._default_account_name(marketplace),
            "marketplace": marketplace,
            "enabled": False,
            "api_key": "",
            "company_id": "" if marketplace == "ozon" else "",
        }

    def _add_account(self):
        """Добавление нового аккаунта в локальный список."""
        if self._account_changes_locked(show_message=True):
            return

        account = self._build_new_account()
        self.accounts.append(account)
        self._refresh_accounts_tree(account.get("id"))
        self._select_account_by_id(account.get("id"))
        logger.info(f"Добавлен новый аккаунт {account.get('name')}")

    def _delete_account(self):
        """Удаление выбранного аккаунта из локального списка."""
        if self._account_changes_locked(show_message=True):
            return

        if self.selected_account_index is None or not (0 <= self.selected_account_index < len(self.accounts)):
            messagebox.showwarning("Внимание", "Выберите аккаунт, который нужно удалить.")
            return

        account = self.accounts.pop(self.selected_account_index)
        self.bot_manager.bots.pop(account.get("id"), None)

        if self.accounts:
            new_index = min(self.selected_account_index, len(self.accounts) - 1)
            self._refresh_accounts_tree(self.accounts[new_index].get("id"))
            self._select_account(new_index)
        else:
            self._refresh_accounts_tree()
            self.selected_account_index = None
            self._clear_account_form()
            self._update_account_form_state()

        logger.info(f"Аккаунт {account.get('name')} удален из локального списка")

    def _refresh_accounts_tree(self, selected_account_id=None):
        """Перерисовка списка аккаунтов."""
        for item_id in self.accounts_tree.get_children():
            self.accounts_tree.delete(item_id)

        for account in self.accounts:
            self.accounts_tree.insert(
                "",
                "end",
                iid=str(account.get("id")),
                values=(
                    account.get("name") or "Без названия",
                    self._marketplace_display_name(account.get("marketplace")),
                    "Да" if account.get("enabled") else "Нет",
                ),
            )

        empty_text = ""
        if not self.accounts:
            empty_text = "Аккаунты еще не добавлены. Нажмите «Добавить», чтобы создать первый кабинет."
        self.accounts_empty_label.config(text=empty_text)

        if selected_account_id is not None:
            self._set_tree_selection(selected_account_id)

    def _set_tree_selection(self, account_id):
        """Установка выделения в Treeview по account_id."""
        account_id = str(account_id)
        children = set(self.accounts_tree.get_children())
        if account_id not in children:
            return
        self.accounts_tree.selection_set(account_id)
        if hasattr(self.accounts_tree, "focus"):
            self.accounts_tree.focus(account_id)

    def _select_account(self, index):
        """Выбор аккаунта по индексу."""
        if index is None or not (0 <= index < len(self.accounts)):
            self.selected_account_index = None
            self._clear_account_form()
            self._update_account_form_state()
            return

        self.selected_account_index = index
        account = self.accounts[index]
        self._set_tree_selection(account.get("id"))
        self._populate_account_form(account)
        self._update_account_form_state()

    def _select_account_by_id(self, account_id):
        """Выбор аккаунта по account_id."""
        for index, account in enumerate(self.accounts):
            if str(account.get("id")) == str(account_id):
                self._select_account(index)
                return

    def _on_account_selected(self, _event=None):
        """Обработчик выбора строки в списке аккаунтов."""
        selection = self.accounts_tree.selection()
        if not selection:
            self.selected_account_index = None
            self._clear_account_form()
            self._update_account_form_state()
            return

        selected_id = str(selection[0])
        for index, account in enumerate(self.accounts):
            if str(account.get("id")) == selected_id:
                self.selected_account_index = index
                self._populate_account_form(account)
                self._update_account_form_state()
                return

    def _populate_account_form(self, account):
        """Заполнение формы выбранным аккаунтом."""
        self.account_name_var.set(account.get("name", ""))
        self.account_marketplace_var.set(account.get("marketplace", "ozon"))
        self.account_enabled_var.set(bool(account.get("enabled", False)))
        self.account_api_key_var.set(account.get("api_key", ""))
        self.account_company_id_var.set(account.get("company_id", ""))
        self.account_api_key_visible.set(False)
        self._toggle_secret_visibility(self.account_api_key_entry, self.account_api_key_visible)
        self._update_company_id_state()

    def _clear_account_form(self):
        """Очистка формы аккаунта."""
        self.account_name_var.set("")
        self.account_marketplace_var.set("ozon")
        self.account_enabled_var.set(False)
        self.account_api_key_var.set("")
        self.account_company_id_var.set("")
        self.account_api_key_visible.set(False)
        self._toggle_secret_visibility(self.account_api_key_entry, self.account_api_key_visible)
        self._update_company_id_state()

    def _on_marketplace_changed(self, _event=None):
        """Обновление поля Company ID при смене маркетплейса."""
        self._update_company_id_state()

    @staticmethod
    def _set_widget_state(widget, state):
        """Унифицированная установка state для ttk/tk widgets."""
        if widget is None:
            return
        try:
            widget.configure(state=state)
            return
        except (tk.TclError, AttributeError):
            pass

        try:
            if state == "disabled":
                widget.state(["disabled"])
            else:
                widget.state(["!disabled"])
        except (tk.TclError, AttributeError):
            pass

    def _update_company_id_state(self):
        """Company ID нужен только для Ozon."""
        marketplace = self.account_marketplace_var.get()
        locked = self._has_active_bots()
        state = "normal" if marketplace == "ozon" and not locked else "disabled"
        self._set_widget_state(self.account_company_id_entry, state)

        try:
            self.account_company_id_label.config(foreground="black" if marketplace == "ozon" else "gray50")
        except tk.TclError:
            pass

        hint_text = "Для Ozon это поле обязательно. Для Wildberries оно не используется."
        if locked:
            hint_text = "Сначала остановите всех ботов, затем изменяйте структуру аккаунтов."
        self.account_company_id_hint_label.config(text=hint_text)

    def _update_account_form_state(self):
        """Блокировка опасных изменений аккаунтов во время работы ботов."""
        locked = self._has_active_bots()
        lock_message = ""
        if locked:
            lock_message = "Сначала остановите всех ботов, затем меняйте аккаунты."
        self.account_lock_label.config(text=lock_message)

        self._set_widget_state(self.add_account_button, "disabled" if locked else "normal")
        self._set_widget_state(self.save_account_button, "disabled" if locked else "normal")
        delete_state = "disabled" if locked or self.selected_account_index is None else "normal"
        self._set_widget_state(self.delete_account_button, delete_state)
        self._set_widget_state(self.account_marketplace_combo, "disabled" if locked else "readonly")
        self._set_widget_state(self.account_api_key_entry, "disabled" if locked else "normal")
        self._update_company_id_state()

    def _build_account_from_form(self, index):
        """Сборка account-конфига из формы."""
        current_account = self.accounts[index]
        marketplace = str(self.account_marketplace_var.get() or "").strip().lower()
        if marketplace not in self.ACCOUNT_MARKETPLACES:
            messagebox.showwarning("Внимание", "Выберите корректный маркетплейс для аккаунта.")
            return None

        name = str(self.account_name_var.get() or "").strip()
        if not name:
            name = self._default_account_name(marketplace, exclude_index=index)

        api_key = str(self.account_api_key_var.get() or "").strip()
        company_id = str(self.account_company_id_var.get() or "").strip() if marketplace == "ozon" else ""
        enabled = bool(self.account_enabled_var.get())

        # Для отключенного черновика разрешаем пустой Company ID, чтобы пользователь мог сохранить заготовку.
        requires_company_id = marketplace == "ozon" and (enabled or api_key or company_id)
        if requires_company_id and not company_id:
            messagebox.showwarning("Внимание", "Для аккаунта Ozon нужно указать Company ID.")
            return None

        return {
            "id": current_account.get("id") or self._next_account_id(marketplace, exclude_index=index),
            "name": name,
            "marketplace": marketplace,
            "enabled": enabled,
            "api_key": api_key,
            "company_id": company_id,
        }

    def _has_active_bots(self):
        """Есть ли сейчас running/stopping боты."""
        try:
            statuses = self.bot_manager.get_statuses() or {}
        except Exception:
            return False

        for status in statuses.values():
            if not isinstance(status, dict):
                continue
            if status.get("running") or status.get("stopping"):
                return True
        return False

    def _account_changes_locked(self, show_message=False):
        """Нужно ли блокировать структурные изменения аккаунтов."""
        locked = self._has_active_bots()
        if locked and show_message:
            messagebox.showwarning(
                "Внимание",
                "Пока боты работают или еще останавливаются, изменение списка аккаунтов заблокировано. "
                "Сначала остановите всех ботов.",
            )
        self._update_account_form_state()
        return locked

    @staticmethod
    def _empty_bot_status():
        """Базовый пустой статус для GUI."""
        return {
            "running": False,
            "stopping": False,
            "found_reviews": 0,
            "processed_reviews": 0,
            "answered_reviews": 0,
            "skipped_reviews": 0,
            "error_count": 0,
            "last_error": None,
            "last_run_started_at": None,
            "last_run_finished_at": None,
            "last_success_at": None,
            "account_id": None,
            "account_name": None,
            "marketplace": None,
            "account_enabled": False,
        }

    def _build_idle_status(self, account):
        """Статус аккаунта, который еще не запускался."""
        status = self._empty_bot_status()
        status.update(
            {
                "account_id": account.get("id"),
                "account_name": account.get("name"),
                "marketplace": account.get("marketplace"),
                "account_enabled": bool(account.get("enabled", False)),
            }
        )
        return status

    def _normalize_status(self, status, fallback_account=None):
        """Безопасная нормализация runtime-статуса для GUI."""
        normalized = self._empty_bot_status()
        if fallback_account:
            normalized.update(self._build_idle_status(fallback_account))
        if isinstance(status, dict):
            normalized.update(status)
        return normalized

    @staticmethod
    def _format_status_value(value, empty_text="еще не было"):
        """Форматирование отсутствующих значений для GUI."""
        return value if value else empty_text

    def _format_bot_stats(self, status):
        """Человекочитаемое представление статистики бота."""
        if status["running"]:
            lifecycle = "Останавливается" if status["stopping"] else "Запущен"
        elif status["last_run_started_at"]:
            lifecycle = "Остановлен"
        else:
            lifecycle = "Еще не запускался"

        enabled_text = "включен" if status.get("account_enabled") else "выключен"
        marketplace_name = self._marketplace_display_name(status.get("marketplace"))
        account_name = status.get("account_name") or "Без названия"

        return "\n".join(
            [
                f"{account_name} ({marketplace_name}, {enabled_text})",
                f"Состояние: {lifecycle}",
                f"Найдено отзывов: {status['found_reviews']}",
                f"Обработано: {status['processed_reviews']}",
                f"Отправлено ответов: {status['answered_reviews']}",
                f"Пропущено: {status['skipped_reviews']}",
                f"Ошибок: {status['error_count']}",
                f"Последняя ошибка: {self._format_status_value(status['last_error'], 'нет')}",
                f"Последний запуск: {self._format_status_value(status['last_run_started_at'])}",
                f"Последнее завершение: {self._format_status_value(status['last_run_finished_at'])}",
                f"Последний успешный цикл: {self._format_status_value(status['last_success_at'])}",
            ]
        )

    def _get_display_statuses(self):
        """Статусы в порядке, удобном для отображения в GUI."""
        raw_statuses = self.bot_manager.get_statuses() or {}
        statuses = []
        seen_ids = set()

        for account in self.accounts:
            account_id = account.get("id")
            statuses.append(self._normalize_status(raw_statuses.get(account_id), fallback_account=account))
            seen_ids.add(account_id)

        for account_id, status in raw_statuses.items():
            if account_id in seen_ids:
                continue
            statuses.append(self._normalize_status(status))

        return statuses

    def _set_status_text(self, text):
        """Безопасное обновление read-only виджета статуса."""
        try:
            self.status_text.config(state="normal")
        except (tk.TclError, AttributeError):
            pass

        if hasattr(self.status_text, "delete"):
            self.status_text.delete("1.0", "end")
        if hasattr(self.status_text, "insert"):
            self.status_text.insert("1.0", text)
        elif hasattr(self.status_text, "config"):
            self.status_text.config(text=text)

        try:
            self.status_text.config(state="disabled")
        except (tk.TclError, AttributeError):
            pass

    def _update_status(self):
        """Обновление вкладки статуса."""
        try:
            statuses = self._get_display_statuses()
        except Exception as error:
            logger.error(f"Ошибка чтения статусов ботов: {error}")
            statuses = []

        if not statuses:
            text = (
                "Аккаунты еще не добавлены.\n"
                "Откройте вкладку «Настройки», создайте хотя бы один аккаунт и сохраните изменения."
            )
        else:
            text = "\n\n".join(self._format_bot_stats(status) for status in statuses)

        self._set_status_text(text)
        self._update_account_form_state()

    def _start_bots(self):
        """Запуск всех включенных аккаунтов через BotManager."""
        try:
            if not self._has_active_bots():
                if not self._save_settings(show_message=False):
                    return

            enabled_accounts = [account for account in config.get_accounts() if account.get("enabled")]
            if not enabled_accounts:
                messagebox.showwarning("Внимание", "Нет включенных аккаунтов для запуска.")
                return

            results = self.bot_manager.start_all_enabled()
            statuses = self.bot_manager.get_statuses()

            started = []
            already_running = []
            still_stopping = []

            for account in enabled_accounts:
                account_id = account.get("id")
                status = self._normalize_status(statuses.get(account_id), fallback_account=account)
                account_name = account.get("name") or self._marketplace_display_name(account.get("marketplace"))
                if results.get(account_id):
                    started.append(account_name)
                elif status.get("stopping"):
                    still_stopping.append(account_name)
                elif status.get("running"):
                    already_running.append(account_name)

            if started:
                parts = [f"Запущено: {', '.join(started)}."]
                if already_running:
                    parts.append(f"Уже работали: {', '.join(already_running)}.")
                if still_stopping:
                    parts.append(f"Еще останавливаются: {', '.join(still_stopping)}.")
                messagebox.showinfo("Успех", " ".join(parts))
            elif still_stopping:
                messagebox.showwarning(
                    "Внимание",
                    f"Повторный запуск заблокирован: еще не завершилась остановка {', '.join(still_stopping)}.",
                )
            elif already_running:
                messagebox.showinfo("Информация", f"Аккаунты уже запущены: {', '.join(already_running)}.")
            else:
                messagebox.showwarning("Внимание", "Не удалось запустить выбранные аккаунты.")

            self._update_status()
        except Exception as error:
            logger.error(f"Ошибка запуска ботов: {error}")
            messagebox.showerror("Ошибка", f"Не удалось запустить ботов: {error}")

    def _stop_bots(self, show_message=True):
        """Остановка всех созданных runtime-ботов."""
        try:
            results = self.bot_manager.stop_all()
            statuses = self.bot_manager.get_statuses()

            stopped = []
            stopping = []

            for account_id, result in results.items():
                status = self._normalize_status(statuses.get(account_id))
                account_name = status.get("account_name") or account_id
                if result and not status.get("stopping"):
                    stopped.append(account_name)
                else:
                    stopping.append(account_name)

            if show_message:
                if stopping:
                    stopped_text = f" Успешно остановлены: {', '.join(stopped)}." if stopped else ""
                    messagebox.showwarning(
                        "Внимание",
                        f"Остановка еще не завершена для: {', '.join(stopping)}.{stopped_text}",
                    )
                elif stopped:
                    messagebox.showinfo("Успех", f"Остановлены аккаунты: {', '.join(stopped)}.")
                else:
                    messagebox.showinfo("Информация", "Активных runtime-ботов нет.")

            self._update_status()
        except Exception as error:
            logger.error(f"Ошибка остановки ботов: {error}")
            if show_message:
                messagebox.showerror("Ошибка", f"Не удалось остановить ботов: {error}")

    def _log_message(self, message):
        """Добавление сообщения в лог."""
        def _update():
            self.logs_text.config(state="normal")
            self.logs_text.insert("end", message + "\n")
            self.logs_text.see("end")
            self.logs_text.config(state="disabled")

        try:
            self.root.after(0, _update)
        except Exception:
            pass

    def _on_close(self):
        """Остановка фоновых потоков при закрытии окна."""
        self._stop_bots(show_message=False)
        self.root.destroy()

    def _clear_logs(self):
        """Очистка логов."""
        self.logs_text.config(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.config(state="disabled")
        logger.info("Логи очищены")

    def _save_logs(self):
        """Сохранение логов в файл."""
        try:
            filename = filedialog.asksaveasfilename(
                title="Сохранить лог",
                defaultextension=".log",
                filetypes=[("LOG файлы", "*.log"), ("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            )

            if filename:
                logs = self.logs_text.get("1.0", "end")
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(logs)
                logger.info(f"Логи сохранены в {filename}")
                messagebox.showinfo("Успех", f"Логи сохранены в {filename}")
        except Exception as error:
            logger.error(f"Ошибка сохранения логов: {error}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить логи: {error}")


def run_gui():
    """Запуск GUI приложения."""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
