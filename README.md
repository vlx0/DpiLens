# 🔍 DpiLens

Лупа DPI-скейла монитора под курсором + **реальное изменение** системного
масштаба (100/125/150/175/200%) из приложения.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Dependencies](https://img.shields.io/badge/Dependencies-zero-brightgreen)

---

## ✨ Что делает

- 🔍 **Показывает** per-monitor DPI для монитора под курсором (через `shcore.GetDpiForMonitor`)
- 🖥 **Multi-monitor** aware — определяет монитор по позиции курсора через `MonitorFromPoint`
- 🔄 **Авто-обновление** раз в секунду — двигай мышь, значения меняются
- 🎚 **Меняет масштаб** через .NET UI Automation (SendKeys + `ms-settings:display`)
- 🚫 **Без прав админа** — не вызывает SPI_SETLOGICALDPIOVERRIDE (сломан на Win 10 1709+)
- 🪶 **Без зависимостей** — только стандартная библиотека Python + PowerShell (встроен в Windows)

---

## 🚀 Запуск

```powershell
git clone https://github.com/<your-username>/DpiLens.git
cd DpiLens
python main.py
```

> Только Windows 10/11 (использует `shcore.dll` + .NET UIA через PowerShell).
> `requirements.txt` пустой.

---

## 🖱 Как это работает

### Чтение DPI
1. `user32.GetCursorPos` → позиция курсора
2. `user32.MonitorFromPoint` → HMONITOR под курсором
3. `shcore.GetDpiForMonitor(MDT_EFFECTIVE_DPI)` → DPI (0–65535)
4. Перевод в проценты: `int(dpi / 96 * 100)`

### Изменение DPI
1. PowerShell-скрипт `set_dpi.ps1`:
   - открывает `ms-settings:display` через `Start-Process`
   - ищет combobox `SystemSettings_Display_Scaling_ItemSizeOverride_ComboBox`
   - **раскрывает его**, печатает `100{Enter}` (через `SendKeys`) — type-ahead
     в Win 11 надёжнее, чем клик по items (которые в отдельном popup-окне)
2. Windows применяет масштаб; в большинстве случаев без перелогина

---

## 📁 Структура

```
DpiLens/
├── main.py              # GUI: показ DPI + кнопки 100/125/150/175/200%
├── set_dpi.ps1          # UIA-скрипт: меняет масштаб через SendKeys
├── requirements.txt     # Пустой (только stdlib)
├── LICENSE              # MIT
└── README.md
```

## 🪟 Сборка в .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name DpiLens main.py
```

---

## 🐛 Известные ограничения

- Только Windows 10/11 (использует `shcore.dll` + .NET UIA).
- Per-monitor DPI v2 в Windows 11 иногда требует sign-out — программа
  не делает это автоматически (на твоё усмотрение).
- При первом клике `Settings → Display` открывается на переднем плане —
  программа автоматически снимает `-topmost` через 0.5 сек после старта.
- На Win 8.0 fallback на GDI `GetDeviceCaps`, но современные системы
  используют shcore.

## 📝 Лицензия

MIT — делай что хочешь, только копирайт сохрани.
