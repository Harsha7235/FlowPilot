@echo off
setlocal

set "CONDA_ROOT=C:\Users\harsh\Miniconda3"
set "FLOWPILOT_HOME=C:\Projects\FlowPilot"
set "FLOWPILOT_DIR=C:\Projects\FlowPilot\flowpilot-grc"

rem Clear Python environment overrides inherited from other environments.
set "PYTHONHOME="
set "PYTHONPATH="
set "VIRTUAL_ENV="
set "CONDA_PREFIX="
set "CONDA_DEFAULT_ENV="
set "CONDA_SHLVL="

rem Put Miniconda's executable and DLL directories first.
set "PATH=%CONDA_ROOT%;%CONDA_ROOT%\Scripts;%CONDA_ROOT%\Library\bin;%CONDA_ROOT%\Library\usr\bin;%CONDA_ROOT%\Library\mingw-w64\bin;%SystemRoot%\System32;%SystemRoot%"

rem Verify GNU Radio imports using the intended interpreter.
"%CONDA_ROOT%\python.exe" -c "from gnuradio import gr; print('GNU Radio version:', gr.version())"
if errorlevel 1 (
    echo.
    echo ERROR: GNU Radio cannot be imported from Miniconda.
    echo Check the Miniconda installation before launching GRC.
    pause
    exit /b 1
)

rem Launch GNU Radio Companion with FlowPilot paths configured.
"%CONDA_ROOT%\Library\bin\gnuradio-companion.exe" --qt

endlocal
