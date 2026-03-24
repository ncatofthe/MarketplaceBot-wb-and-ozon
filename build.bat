@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Сборка MarketplaceBot.exe
echo ========================================

:: Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    echo Установите Python 3.8+ с сайта python.org
    pause
    exit /b 1
)

:: Установка PyInstaller если не установлен
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
)

:: Очистка старой сборки
if exist "dist\MarketplaceBot.exe" (
    echo Удаление старой версии...
    del /q "dist\MarketplaceBot.exe"
)

:: Сборка с использованием spec файла
echo.
echo Сборка exe-файла...
python -m PyInstaller MarketplaceBot.spec --noconfirm

if exist "dist\MarketplaceBot.exe" (
    echo.
    echo ========================================
    echo Сборка завершена успешно!
    echo Файл: dist\MarketplaceBot.exe
    echo ========================================
) else (
    echo.
    echo ОШИБКА: Не удалось создать exe-файл!
    echo Проверьте сообщения об ошибках выше
)

echo.
pause

