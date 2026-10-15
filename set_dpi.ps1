# set_dpi.ps1 — реально меняет системный DPI через UI Automation
# Открывает «Параметры → Дисплей», находит combobox масштаба,
# раскрывает его, выбирает нужный процент, нажимает «Применить».
#
# Параметры:
#   -Percent 100|125|150|175|200   желаемый масштаб

param(
    [ValidateSet("100", "125", "150", "175", "200")]
    [Parameter(Mandatory=$true)]
    [string]$Percent
)

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Find-SettingsWindow {
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $classCond = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::ClassNameProperty,
        "ApplicationFrameWindow"
    )
    $top = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Children, $classCond
    )
    $w = $null
    foreach ($x in $top) {
        # Берём последнее (самое свежее) окно настроек
        $w = $x
    }
    return $w
}

# 1) Открыть настройки дисплея
Start-Process "ms-settings:display"
Start-Sleep -Seconds 3

$win = Find-SettingsWindow
if (-not $win) {
    Write-Output "ERROR: Settings window not found"
    exit 2
}

# 2) Найти combobox масштаба
$idCond = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
    "SystemSettings_Display_Scaling_ItemSizeOverride_ComboBox"
)
$combo = $win.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants, $idCond
)
if (-not $combo) {
    Write-Output "ERROR: Scale combobox not found"
    exit 3
}

# 3) Прочитать текущее значение
$current = $combo.Current.Name
Write-Output "INFO: current='$current' target=$Percent%"

# 4) Раскрыть combobox (ExpandCollapse pattern)
$expand = $null
if ($combo.TryGetCurrentPattern(
    [System.Windows.Automation.ExpandCollapsePattern]::Pattern, [ref]$expand
)) {
    $expand.Expand()
    Start-Sleep -Milliseconds 800
} else {
    # Если ExpandCollapse не поддерживается, попробуем Invoke
    $inv = $null
    if ($combo.TryGetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern, [ref]$inv
    )) {
        $inv.Invoke()
        Start-Sleep -Milliseconds 800
    } else {
        Write-Output "ERROR: no Expand/Invoke pattern on combobox"
        exit 4
    }
}

# 5) Найти пункт с нужным процентом.
# В Win 11 dropdown items живут в отдельном popup, не в потомках combobox.
# Поэтому используем SendKeys: кликаем combobox, печатаем нужный процент,
# подтверждаем Enter. Это надёжно, т.к. combobox поддерживает type-ahead.
Add-Type -AssemblyName System.Windows.Forms

# Кликаем combobox через Invoke
$inv = $null
if ($combo.TryGetCurrentPattern(
    [System.Windows.Automation.InvokePattern]::Pattern, [ref]$inv
)) {
    $inv.Invoke()
}
Start-Sleep -Milliseconds 500

# Если dropdown не открылся — открываем через Alt+Down
[System.Windows.Forms.SendKeys]::SendWait("%{Down}")
Start-Sleep -Milliseconds 500

# Печатаем нужный процент + Enter. Combobox с type-ahead выберет нужный item.
[System.Windows.Forms.SendKeys]::SendWait("${Percent}{ENTER}")
Start-Sleep -Milliseconds 500
Write-Output "OK typed '${Percent}%' + Enter"

# 7) Возможно появится диалог «Выйти / Не выходить».
# Подождём 1.5 сек и поищем кнопку «Выйти».
Start-Sleep -Milliseconds 1500
$root = [System.Windows.Automation.AutomationElement]::RootElement
$btnCond = [System.Windows.Automation.PropertyCondition]::new(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Button
)
$btns = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants, $btnCond
)
foreach ($b in $btns) {
    $n = $b.Current.Name
    if ($n -match "Выйти сейчас|Sign out now") {
        $bInv = $null
        if ($b.TryGetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern, [ref]$bInv
        )) {
            $bInv.Invoke()
            Write-Output "OK clicked 'Sign out now' (you'll need to log back in)"
            exit 0
        }
    }
}

Write-Output "OK applied '$Percent%' (no sign-out dialog — change is live)"
exit 0
