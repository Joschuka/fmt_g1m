@echo off 
Pushd "%~dp0"
PVRTexToolCLI -i "%~1" -o "%~1.dds" -d "%~1.png" -f r8g8b8a8

