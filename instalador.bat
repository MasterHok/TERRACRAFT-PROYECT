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
:: AVISO DE DESCARGAS
:: ============================================================
cls
echo ============================================================
echo           AVISO - INSTALADOR TERRACRAFT
echo ============================================================
echo.
echo Este instalador preparara el entorno para el launcher.
echo.
echo Se descargara desde Internet:
echo.
echo   [1] Python 3.12 (si no lo tienes instalado)
echo         Origen:  winget / python.org
echo.
echo   [2] Dependencias Python (via pip):
echo         - PySide6                (^~ 100 MB)  Interfaz grafica Qt6
echo         - minecraft-launcher-lib (^~   1 MB)  Descarga de Minecraft
echo         - Pillow                 (^~   3 MB)  Procesamiento de imagenes
echo         - skinpy                 (^~   1 MB)  Render 3D de skins
echo         - PyInstaller            (^~  10 MB)  Solo si compilas el .exe
echo         Origen:  pypi.org
echo.
echo NO se descarga:
echo   - Minecraft
echo   - Java
echo   - Servidores Purpur o Vanilla
echo   - Plugins (Geyser, Floodgate, etc.)
echo.
echo Todo eso lo gestiona el launcher despues de instalarlo.
echo.
echo ------------------------------------------------------------
echo.
set /p CONFIRMAR="Aceptas estas descargas? (S/N): "

if /i not "%CONFIRMAR%"=="S" (
    echo.
    echo Operacion cancelada por el usuario.
    echo No se ha descargado ni modificado nada.
    echo.
    pause
    exit /b 0
)

echo.
echo OK - Continuando con la instalacion...
echo.
timeout /t 1 >nul

:: ============================================================
:: AVISO DE ARQUITECTURA (ARM)
:: ============================================================
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" (
    echo AVISO: Este launcher esta pensado para Windows x64.
    echo En ARM puede que Java x64 no funcione correctamente.
    echo.
)

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
echo Se instalara Python 3.12 (~25 MB) desde winget.
echo.
set /p CONFIRMAR_PY="Continuar con la instalacion de Python? (S/N): "
if /i not "%CONFIRMAR_PY%"=="S" (
    echo.
    echo Operacion cancelada por el usuario.
    echo.
    pause
    exit /b 0
)

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

echo Instalando dependencias basicas...
%PYTHON% -m pip install pyside6 minecraft-launcher-lib pillow

if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias basicas.
    echo Comprueba tu conexion a Internet e intentalo de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando skinpy (opcional, para render 3D de skins)...
%PYTHON% -m pip install skinpy

if errorlevel 1 (
    echo.
    echo AVISO: No se pudo instalar skinpy.
    echo La previsualizacion 3D de skins no funcionara,
    echo pero el launcher seguira siendo usable.
    echo.
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
    mkdir "%BASE%assets"
    if errorlevel 1 (
        echo ERROR: No se pudo crear la carpeta assets.
        echo Comprueba los permisos de la carpeta.
        echo.
        pause
        exit /b 1
    )
)

:: --- Assets del launcher principal ---
if not exist "%BASE%assets\fondo.gif" (
    echo AVISO: Falta assets\fondo.gif ^(fondo animado del launcher^)
)
if not exist "%BASE%assets\music.mp3" (
    echo AVISO: Falta assets\music.mp3 ^(musica de fondo^)
)
if not exist "%BASE%assets\icon.ico" (
    if not exist "%BASE%assets\icon.png" (
        echo AVISO: Falta assets\icon.ico y assets\icon.png ^(icono de la ventana^)
    )
)

:: --- Assets del dialogo de bienvenida ---
if not exist "%BASE%assets\fondo_info.gif" (
    if not exist "%BASE%assets\fondo_info.png" (
        echo AVISO: Falta assets\fondo_info.gif ^(fondo del dialogo de bienvenida^)
    )
)
if not exist "%BASE%assets\click_yes.wav" (
    echo AVISO: Falta assets\click_yes.wav ^(sonido boton Si^)
)
if not exist "%BASE%assets\click_no.wav" (
    echo AVISO: Falta assets\click_no.wav ^(sonido boton No^)
)
if not exist "%BASE%assets\dialog_intro.wav" (
    echo AVISO: Falta assets\dialog_intro.wav ^(narracion del dialogo^)
)

:: --- Assets de la interfaz ---
if not exist "%BASE%assets\banner.png" (
    echo AVISO: Falta assets\banner.png ^(banner superior^)
)
if not exist "%BASE%assets\web.png" (
    echo AVISO: Falta assets\web.png ^(icono web^)
)
if not exist "%BASE%assets\github.png" (
    echo AVISO: Falta assets\github.png ^(icono GitHub^)
)
if not exist "%BASE%assets\discord.png" (
    echo AVISO: Falta assets\discord.png ^(icono Discord^)
)
if not exist "%BASE%assets\author.png" (
    echo AVISO: Falta assets\author.png ^(foto del creador^)
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
    ) else (
        echo AVISO: No hay icon.png, no se puede generar icon.ico.
        echo La compilacion del .exe se hara sin icono personalizado.
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
echo %PYTHON% TERRACRAFT.py>> "%BASE%LANZADOR_PYTHON.bat"
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
echo setlocal enabledelayedexpansion>> "%BASE%CREAR_UN_EXE.bat"
echo title COMPILAR TERRACRAFT>> "%BASE%CREAR_UN_EXE.bat"
echo cd /d "%%%%~dp0">> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo   COMPILANDO TERRACRAFT>> "%BASE%CREAR_UN_EXE.bat"
echo echo ========================================>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Instalando PyInstaller...>> "%BASE%CREAR_UN_EXE.bat"
echo %PYTHON% -m pip install pyinstaller>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo if errorlevel 1 ^(>> "%BASE%CREAR_UN_EXE.bat"
echo     echo ERROR: No se pudo instalar PyInstaller.>> "%BASE%CREAR_UN_EXE.bat"
echo     pause>> "%BASE%CREAR_UN_EXE.bat"
echo     exit /b 1>> "%BASE%CREAR_UN_EXE.bat"
echo ^)>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Detectando icono...>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo set "ICON_OPT=">> "%BASE%CREAR_UN_EXE.bat"
echo if exist assets\icon.ico set "ICON_OPT=--icon assets\icon.ico">> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo echo Compilando con PyInstaller...>> "%BASE%CREAR_UN_EXE.bat"
echo echo.>> "%BASE%CREAR_UN_EXE.bat"
echo.>> "%BASE%CREAR_UN_EXE.bat"
echo %PYTHON% -m PyInstaller --onefile --windowed --clean %%ICON_OPT%% --add-data "assets;assets" --distpath "TERRALAUNCHER" --name TERRACRAFT TERRACRAFT.py>> "%BASE%CREAR_UN_EXE.bat"
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
echo endlocal>> "%BASE%CREAR_UN_EXE.bat"

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
echo   - La API Key de MineSkin es OPCIONAL. Si quieres
echo     subir skins desde el juego con SkinsRestorer,
echo     consigue una gratis en https://mineskin.org/apikey
echo     y pegala en la pestana "Skins de Purpur".
echo.
pause
endlocal
exit /b 0