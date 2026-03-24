"""
Главное окно GUI приложения
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
from bots import OzonBot, WildberriesBot
from config import config
from utils import logger


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Бот для маркетплейсов v1.0")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Боты
        self.ozon_bot = None
        self.wb_bot = None
        
        # Настройка GUI
        self._setup_styles()
        self._create_widgets()
        
        # Подключение logger к GUI
        logger.set_gui_callback(self._log_message)
        
        # Загрузка конфигурации
        self._load_config()
    
    def _setup_styles(self):
        """Настройка стилей"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка цветов
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 11, 'bold'))
        style.configure('Normal.TLabel', font=('Arial', 10))
        
        style.configure('Success.TButton', foreground='green')
        style.configure('Danger.TButton', foreground='red')
    
    def _create_widgets(self):
        """Создание виджетов"""
        # Создание вкладок
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Вкладка "Настройки"
        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="Настройки")
        self._create_settings_tab()
        
        # Вкладка "Шаблоны ответов"
        self.templates_frame = ttk.Frame(notebook)
        notebook.add(self.templates_frame, text="Шаблоны ответов")
        self._create_templates_tab()
        
        # Вкладка "Логи"
        self.logs_frame = ttk.Frame(notebook)
        notebook.add(self.logs_frame, text="Логи")
        self._create_logs_tab()
        
        # Вкладка "Статус"
        self.status_frame = ttk.Frame(notebook)
        notebook.add(self.status_frame, text="Статус")
        self._create_status_tab()
    
    def _create_settings_tab(self):
        """Создание вкладки настроек"""
        # Ozon настройки
        ozon_group = ttk.LabelFrame(self.settings_frame, text="Настройки Ozon", padding=10)
        ozon_group.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(ozon_group, text="Включить бота Ozon:").grid(row=0, column=0, sticky='w', pady=5)
        self.ozon_enabled = tk.BooleanVar()
        ttk.Checkbutton(ozon_group, variable=self.ozon_enabled).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(ozon_group, text="API Key:").grid(row=1, column=0, sticky='w', pady=5)
        self.ozon_api_key = tk.StringVar()
        ttk.Entry(ozon_group, textvariable=self.ozon_api_key, width=50, show="*").grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(ozon_group, text="Company ID:").grid(row=2, column=0, sticky='w', pady=5)
        self.ozon_company_id = tk.StringVar()
        ttk.Entry(ozon_group, textvariable=self.ozon_company_id, width=50).grid(row=2, column=1, sticky='w', pady=5)
        
        # Wildberries настройки
        wb_group = ttk.LabelFrame(self.settings_frame, text="Настройки Wildberries", padding=10)
        wb_group.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(wb_group, text="Включить бота WB:").grid(row=0, column=0, sticky='w', pady=5)
        self.wb_enabled = tk.BooleanVar()
        ttk.Checkbutton(wb_group, variable=self.wb_enabled).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(wb_group, text="API Key:").grid(row=1, column=0, sticky='w', pady=5)
        self.wb_api_key = tk.StringVar()
        ttk.Entry(wb_group, textvariable=self.wb_api_key, width=50, show="*").grid(row=1, column=1, sticky='w', pady=5)
        
        # Общие настройки
        general_group = ttk.LabelFrame(self.settings_frame, text="Общие настройки", padding=10)
        general_group.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(general_group, text="Интервал проверки (минуты):").grid(row=0, column=0, sticky='w', pady=5)
        self.check_interval = tk.IntVar(value=60)
        ttk.Entry(general_group, textvariable=self.check_interval, width=10).grid(row=0, column=1, sticky='w', pady=5)
        
        ttk.Label(general_group, text="Мин. звезд для ответа:").grid(row=1, column=0, sticky='w', pady=5)
        self.min_stars = tk.IntVar(value=1)
        ttk.Spinbox(general_group, from_=1, to=5, textvariable=self.min_stars, width=8).grid(row=1, column=1, sticky='w', pady=5)
        
        ttk.Label(general_group, text="Макс. ответов за один цикл:").grid(row=2, column=0, sticky='w', pady=5)
        self.max_answers = tk.IntVar(value=-1)
        ttk.Entry(general_group, textvariable=self.max_answers, width=10).grid(row=2, column=1, sticky='w', pady=5)
        ttk.Label(general_group, text="(-1 = без ограничений)", font=('Arial', 8)).grid(row=2, column=2, sticky='w', pady=5)
        
        ttk.Label(general_group, text="Задержка между запросами (сек):").grid(row=3, column=0, sticky='w', pady=5)
        self.short_sleep = tk.DoubleVar(value=0.5)
        ttk.Entry(general_group, textvariable=self.short_sleep, width=10).grid(row=3, column=1, sticky='w', pady=5)
        
        # Кнопки
        buttons_frame = ttk.Frame(self.settings_frame)
        buttons_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Сохранить настройки", command=self._save_settings).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Запустить ботов", command=self._start_bots).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Остановить ботов", command=self._stop_bots).pack(side='left', padx=5)
    
    def _create_templates_tab(self):
        """Создание вкладки шаблонов ответов"""
        # Кнопки управления
        buttons_frame = ttk.Frame(self.templates_frame)
        buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Загрузить шаблоны", command=self._load_templates).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Сохранить шаблоны", command=self._save_templates).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Сбросить по умолчанию", command=self._reset_templates).pack(side='left', padx=5)
        
        # Текстовое поле для редактирования шаблонов
        ttk.Label(self.templates_frame, text="Редактирование шаблонов ответов (JSON):").pack(anchor='w', padx=10, pady=5)
        
        self.templates_text = scrolledtext.ScrolledText(self.templates_frame, width=90, height=30)
        self.templates_text.pack(fill='both', expand=True, padx=10, pady=5)
    
    def _create_logs_tab(self):
        """Создание вкладки логов"""
        # Кнопки управления
        buttons_frame = ttk.Frame(self.logs_frame)
        buttons_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Очистить логи", command=self._clear_logs).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Сохранить лог в файл", command=self._save_logs).pack(side='left', padx=5)
        
        # Текстовое поле для логов
        self.logs_text = scrolledtext.ScrolledText(self.logs_frame, width=90, height=30)
        self.logs_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Автопрокрутка
        self.logs_text.config(state='disabled')
    
    def _create_status_tab(self):
        """Создание вкладки статуса"""
        # Статус Ozon
        ozon_status_group = ttk.LabelFrame(self.status_frame, text="Статус Ozon", padding=10)
        ozon_status_group.pack(fill='x', padx=10, pady=5)
        
        self.ozon_status_label = ttk.Label(ozon_status_group, text="Остановлен", foreground='red')
        self.ozon_status_label.pack(anchor='w')
        
        # Статус WB
        wb_status_group = ttk.LabelFrame(self.status_frame, text="Статус Wildberries", padding=10)
        wb_status_group.pack(fill='x', padx=10, pady=5)
        
        self.wb_status_label = ttk.Label(wb_status_group, text="Остановлен", foreground='red')
        self.wb_status_label.pack(anchor='w')
        
        # Статистика
        stats_group = ttk.LabelFrame(self.status_frame, text="Статистика", padding=10)
        stats_group.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_group, text="Запустите бота для просмотра статистики")
        self.stats_label.pack(anchor='w')
        
        # Кнопка обновления статуса
        ttk.Button(self.status_frame, text="Обновить статус", command=self._update_status).pack(pady=10)
    
    def _load_config(self):
        """Загрузка конфигурации"""
        try:
            # Ozon
            ozon_config = config.get("ozon")
            if ozon_config:
                self.ozon_enabled.set(ozon_config.get("enabled", False))
                self.ozon_api_key.set(ozon_config.get("api_key", ""))
                self.ozon_company_id.set(ozon_config.get("company_id", ""))
            
            # Wildberries
            wb_config = config.get("wildberries")
            if wb_config:
                self.wb_enabled.set(wb_config.get("enabled", False))
                self.wb_api_key.set(wb_config.get("api_key", ""))
            
            # Общие
            general = config.get("general")
            if general:
                self.check_interval.set(general.get("check_interval", 60))
                self.min_stars.set(general.get("min_stars", 1))
                self.max_answers.set(general.get("max_answers_per_run", -1))
                self.short_sleep.set(general.get("short_sleep", 0.5))
            
            # Шаблоны
            templates = config.get_answer_templates()
            import json
            self.templates_text.delete('1.0', 'end')
            self.templates_text.insert('1.0', json.dumps(templates, ensure_ascii=False, indent=4))
            
            logger.info("Конфигурация загружена")
            
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
    
    def _save_settings(self):
        """Сохранение настроек"""
        try:
            # Ozon
            config.set("ozon", "enabled", self.ozon_enabled.get())
            config.set("ozon", "api_key", self.ozon_api_key.get())
            config.set("ozon", "company_id", self.ozon_company_id.get())
            
            # Wildberries
            config.set("wildberries", "enabled", self.wb_enabled.get())
            config.set("wildberries", "api_key", self.wb_api_key.get())
            
            # Общие
            config.set("general", "check_interval", self.check_interval.get())
            config.set("general", "min_stars", self.min_stars.get())
            config.set("general", "max_answers_per_run", self.max_answers.get())
            config.set("general", "short_sleep", self.short_sleep.get())
            
            config.save_config()
            messagebox.showinfo("Успех", "Настройки сохранены!")
            logger.info("Настройки сохранены")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {e}")
    
    def _load_templates(self):
        """Загрузка шаблонов из файла"""
        try:
            filename = filedialog.askopenfilename(
                title="Выберите файл шаблонов",
                filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
            )
            
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    import json
                    templates = json.load(f)
                
                self.templates_text.delete('1.0', 'end')
                self.templates_text.insert('1.0', json.dumps(templates, ensure_ascii=False, indent=4))
                logger.info(f"Шаблоны загружены из {filename}")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки шаблонов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить шаблоны: {e}")
    
    def _save_templates(self):
        """Сохранение шаблонов"""
        try:
            import json
            templates_text = self.templates_text.get('1.0', 'end')
            templates = json.loads(templates_text)
            
            # Сохранение в конфигурацию
            config.answers = templates
            config.save_answers()
            
            messagebox.showinfo("Успех", "Шаблоны сохранены!")
            logger.info("Шаблоны сохранены")
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка JSON: {e}")
            messagebox.showerror("Ошибка", f"Неверный формат JSON: {e}")
        except Exception as e:
            logger.error(f"Ошибка сохранения шаблонов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить шаблоны: {e}")
    
    def _reset_templates(self):
        """Сброс шаблонов по умолчанию"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сбросить шаблоны?"):
            try:
                from config import DEFAULT_ANSWERS
                import json
                self.templates_text.delete('1.0', 'end')
                self.templates_text.insert('1.0', json.dumps(DEFAULT_ANSWERS, ensure_ascii=False, indent=4))
                logger.info("Шаблоны сброшены по умолчанию")
            except Exception as e:
                logger.error(f"Ошибка сброса шаблонов: {e}")
    
    def _start_bots(self):
        """Запуск ботов"""
        try:
            # Сохраняем настройки перед запуском
            self._save_settings()
            
            # Запуск Ozon бота
            if self.ozon_enabled.get():
                logger.info("Запуск бота Ozon...")
                self.ozon_bot = OzonBot()
                self.ozon_bot.start()
            
            # Запуск WB бота
            if self.wb_enabled.get():
                logger.info("Запуск бота Wildberries...")
                self.wb_bot = WildberriesBot()
                self.wb_bot.start()
            
            if not self.ozon_enabled.get() and not self.wb_enabled.get():
                messagebox.showwarning("Внимание", "Выберите хотя бы одного бота для запуска")
                return
            
            messagebox.showinfo("Успех", "Боты запущены!")
            self._update_status()
            
        except Exception as e:
            logger.error(f"Ошибка запуска ботов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить ботов: {e}")
    
    def _stop_bots(self):
        """Остановка ботов"""
        try:
            if self.ozon_bot:
                self.ozon_bot.stop()
                logger.info("Бот Ozon остановлен")
            
            if self.wb_bot:
                self.wb_bot.stop()
                logger.info("Бот Wildberries остановлен")
            
            messagebox.showinfo("Успех", "Боты остановлены!")
            self._update_status()
            
        except Exception as e:
            logger.error(f"Ошибка остановки ботов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось остановить ботов: {e}")
    
    def _update_status(self):
        """Обновление статуса"""
        # Ozon
        if self.ozon_bot and self.ozon_bot.is_running:
            self.ozon_status_label.config(text="Запущен и работает", foreground="green")
        else:
            self.ozon_status_label.config(text="Остановлен", foreground="red")
        
        # WB
        if self.wb_bot and self.wb_bot.is_running:
            self.wb_status_label.config(text="Запущен и работает", foreground="green")
        else:
            self.wb_status_label.config(text="Остановлен", foreground="red")
    
    def _log_message(self, message):
        """Добавление сообщения в лог"""
        def _update():
            self.logs_text.config(state='normal')
            self.logs_text.insert('end', message + '\n')
            self.logs_text.see('end')
            self.logs_text.config(state='disabled')
        
        try:
            self.root.after(0, _update)
        except:
            pass
    
    def _clear_logs(self):
        """Очистка логов"""
        self.logs_text.config(state='normal')
        self.logs_text.delete('1.0', 'end')
        self.logs_text.config(state='disabled')
        logger.info("Логи очищены")
    
    def _save_logs(self):
        """Сохранение логов в файл"""
        try:
            filename = filedialog.asksaveasfilename(
                title="Сохранить лог",
                defaultextension=".log",
                filetypes=[("LOG файлы", "*.log"), ("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
            )
            
            if filename:
                logs = self.logs_text.get('1.0', 'end')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs)
                logger.info(f"Логи сохранены в {filename}")
                messagebox.showinfo("Успех", f"Логи сохранены в {filename}")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения логов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить логи: {e}")


def run_gui():
    """Запуск GUI приложения"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()

