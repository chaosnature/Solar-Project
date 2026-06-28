@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0patch_and_compile.ps1" %*
