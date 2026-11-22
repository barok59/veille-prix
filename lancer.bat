@echo off
cd /d "%~dp0"
set HEADLESS=1
python veille\main.py %1 >> veille.log 2>&1
