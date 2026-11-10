@echo off
setlocal
set "ROOT_DIR=%~dp0..\.."
set "PYTHONPATH=%ROOT_DIR%;%ROOT_DIR%\july_distribution;%PYTHONPATH%"
python -m july_distribution.client.cli %*
endlocal
