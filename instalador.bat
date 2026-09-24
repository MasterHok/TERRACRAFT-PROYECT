@echo off
setlocal enabledelayedexpansion
title INSTALADOR TERRACRAFT
color 0a

set "BASE=%~dp0"

echo ========================================
echo        INSTALADOR TERRACRAFT
echo ========================================
echo.
echo Este instalador prepara el entorno Python
echo y genera los lanzadores. Java, Purpur y
echo los plugins los gestiona el propio launcher.
echo.

:: ============================================================
:: 0/5 - COMPROBAR TERRACRAFT.py
:: ============================================================
if not exist "%BASE%TERRACRAFT.py" (
    echo ERROR: No se encuentra TERRACRAFT.py
    echo Coloca TERRACRAFT.py junto a este instalador.
    echo.
    pause
    exit /b 1
)

:: ============================================================
:: 1/5 - COMPROBAR PYTHON
:: ============================================================
echo [1/5] Comprobando Python...
echo.

where python3 >nul 2>&1
if not errorlevel 1 (set "PYTHON=python3" & goto PythonEncontrado)

where python >nul 2>&1
if not errorlevel 1 (set "PYTHON=python" & goto PythonEncontrado)

where py >nul 2>&1
if not errorlevel 1 (set "PYTHON=py -3" & goto PythonEncontrado)

echo Python no esta instalado.
echo.
echo Instalando Python 3.12...
echo.

winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo instalar Python automaticamente.
    echo Instala Python manualmente desde https://www.python.org/downloads/
    echo Marca la casilla "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)

echo.
echo Python instalado correctamente.
echo.
echo Cerrando el instalador para actualizar el PATH...
echo Vuelve a ejecutar INSTALAR.bat.
echo.
pause
exit /b 0

:PythonEncontrado
echo Python encontrado:
%PYTHON% --version
echo.
timeout /t 1 >nul

:: ============================================================
:: 2/5 - INSTALAR DEPENDENCIAS
:: ============================================================
echo [2/5] Instalando dependencias Python...
echo.

%PYTHON% -m pip install --upgrade pip
if errorlevel 1 (
    echo AVISO: No se pudo actualizar pip. Continuando...
)

%PYTHON% -m pip install pyside6 minecraft-launcher-lib pillow skinpy

if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias.
    echo Comprueba tu conexion a Internet e intentalo de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo Dependencias instaladas correctamente.
echo.
timeout /t 1 >nul

:: ============================================================
:: 3/5 - COMPROBAR ASSETS
:: ============================================================
echo [3/5] Comprobando carpeta assets...
echo.

if not exist "%BASE%assets\" (
    echo AVISO: No se encuentra la carpeta assets\
    echo Creando assets\ vacia...
    mkdir "%BASE%assets" 2>nul
)

if not exist "%BASE%assets\fondo.gif" (
    echo AVISO: Falta assets\fondo.gif ^(fondo animado^)
)
if not exist "%BASE%assets\music.mp3" (
    echo AVISO: Falta assets\music.mp3 ^(musica de fondo^)
)
if not exist "%BASE%assets\icon.png" (
    echo AVISO: Falta assets\icon.png ^(icono de la ventana^)
)

:: Generar icon.ico a partir de icon.png si no existe
if not exist "%BASE%assets\icon.ico" (
    if exist "%BASE%assets\icon.png" (
        echo Generando assets\icon.ico desde icon.png...
        %PYTHON% -c "from PIL import Image; img = Image.open('assets/icon.png'); img.save('assets/icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
        if errorlevel 1 (
            echo AVISO: No se pudo generar icon.ico automaticamente.
        ) else (
            echo OK - icon.ico generado.
        )
    )
)

echo.
echo Assets verificados.
echo.
timeout /t 1 >nul

:: ============================================================
:: 4/5 - GENERAR LANZADOR_PYTHON.bat
:: ============================================================
echo [4/5] Generando LANZADOR_PYTHON.bat...
echo.

if exist "%BASE%LANZADOR_PYTHON.bat" del "%BASE%LANZADOR_PYTHON.bat"

echo @echo off>> "%BASE%LANZADOR_PYTHON.bat"
echo title TERRACRAFT>> "%BASE%LANZADOR_PYTHON.bat"
echo cd /d "%%%%~dp0">> "%BASE%LANZADOR_PYTHON.bat"
echo python3 TERRACRAFT.py>> "%BASE%LANZADOR_PYTHON.bat"
echo pause>> "%BASE%LANZADOR_PYTHON.bat"

if not exist "%BASE%LANZADOR_PYTHON.bat" (
    echo ERROR: No se pudo crear LANZADOR_PYTHON.bat
    pause
    exit /b 1
)

echo OK - LANZADOR_PYTHON.bat creado.
echo.

:: ============================================================
:: 5/5 - GENERAR CREAR_UN_EXE.bat
:: ============================================================
echo [5/5] Generando CREAR_UN_EXE.bat...
echo.

if exist "%BASE%CREAR_UN_EXE.bat" del "%BASE%CREAR_UN_EXE.bat"

echo @echo off>> "%BASE%CREAR_UN_EXE.bat"
echo title COMPILAR TERRACRAFT>> "%BASE%CREAR_UN_EXE.bat"
echo cd /d "%%%%~dp0">> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo   COMPILANDO TERRACRAFT>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Instalando PyInstaller...>> "%BASE%CREAR_UN_EXE.bat"
echo python -m pip install pyinstaller>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo if errorlevel 1 ^(>> "%BASE%CREAR_UN_EXE.bat"
echo     echo ERROR: No se pudo instalar PyInstaller.>> "%BASE%CREAR_UN_EXE.bat"
echo     pause>> "%BASE%CREAR_UN_EXE.bat"
echo     exit /b 1>> "%BASE%CREAR_UN_EXE.bat"
echo ^)>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Compilando con PyInstaller...>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo python3 -m PyInstaller --onefile --windowed --clean --icon assets\icon.ico --add-data "assets;assets" --distpath "TERRALAUNCHER" --name TERRACRAFT TERRACRAFT.py>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo if errorlevel 1 ^(>> "%BASE%CREAR_UN_EXE.bat"
echo     echo ERROR: La compilacion fallo.>> "%BASE%CREAR_UN_EXE.bat"
echo     pause>> "%BASE%CREAR_UN_EXE.bat"
echo     exit /b 1>> "%BASE%CREAR_UN_EXE.bat"
echo ^)>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo   COMPILACION COMPLETADA>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Ejecutable generado en:>> "%BASE%CREAR_UN_EXE.bat"
echo echo   TERRALAUNCHER\TERRACRAFT.exe>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo IMPORTANTE: El .exe debe ir junto a:>> "%BASE%CREAR_UN_EXE.bat"
echo echo   - assets\    ^(fondo, musica, icono^)>> "%BASE%CREAR_UN_EXE.bat"
echo echo   - la carpeta del launcher ^(para config\, minecraft\, server\, java\^)>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo pause>> "%BASE%CREAR_UN_EXE.bat"

if not exist "%BASE%CREAR_UN_EXE.bat" (
    echo ERROR: No se pudo crear CREAR_UN_EXE.bat
    pause
    exit /b 1
)

echo OK - CREAR_UN_EXE.bat creado.
echo.

:: ============================================================
:: FINAL
:: ============================================================
echo ========================================
echo       INSTALACION COMPLETADA
echo ========================================
echo.
echo Archivos generados:
echo.
echo   LANZADOR_PYTHON.bat   ^(arranca el launcher en modo desarrollo^)
echo   CREAR_UN_EXE.bat      ^(compila el .exe con PyInstaller^)
echo.
echo Para ejecutar el launcher:
echo   LANZADOR_PYTHON.bat
echo.
echo Para compilar el .exe:
echo   CREAR_UN_EXE.bat
echo.
echo Recordatorio:
echo   - Java se descarga automaticamente desde el launcher
echo     cuando instales un servidor.
echo   - Purpur y Geyser/Floodgate tambien se descargan
echo     desde el launcher en la pestana "Servidor".
echo.
pause
endlocal
exit /b 0