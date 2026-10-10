@echo off
chcp 65001 > nul
title Removedor de Fundos com IA - Execução Rápida

cd /d "%~dp0"

IF EXIST ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" remover_fundo.py %*
) ELSE (
    echo [AVISO] Ambiente virtual (.venv) nao encontrado na pasta do projeto!
    echo Tentando executar com o Python global do sistema...
    python remover_fundo.py %*
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] Ocorreu uma interrupção ou erro durante a execução.
    echo Pressione qualquer tecla para sair...
    pause > nul
)
