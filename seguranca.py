#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Módulo de Segurança e Criptografia de Credenciais
=============================================================================
Responsável por:
1. Criptografia em repouso de credenciais confidenciais (ex: Google Gemini API Key)
   usando AES-128-CBC + HMAC-SHA256 (Fernet) com chave mestre protegida pelo
   Windows DPAPI (Data Protection API) quando em ambiente Windows.
2. Mascaramento e sanitização de dados confidenciais em logs e telas.
3. Prevenção de Path Traversal na manipulação de nomes de arquivos.
4. Entrada segura de credenciais com ocultação no terminal (anti-shoulder surfing).
=============================================================================
"""

import os
import sys
import json
import re
import getpass
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from cryptography.fernet import Fernet, InvalidToken

# Diretório base
BASE_DIR = Path(__file__).resolve().parent

# Arquivos de segurança (estritamente ignorados pelo .gitignore)
ARQUIVO_CHAVE_MESTRE_DPAPI = BASE_DIR / ".master.key.enc"
ARQUIVO_CHAVE_MESTRE_PLAIN = BASE_DIR / ".secrets.key"
ARQUIVO_CREDENCIAIS_ENC = BASE_DIR / ".credenciais.enc"

# Cache em memória durante a execução para evitar re-descriptografias redundantes
_CHAVE_MESTRE_CACHE: Optional[bytes] = None


# ---------------------------------------------------------------------------
# Proteção Windows DPAPI (Data Protection API)
# ---------------------------------------------------------------------------
def _dpapi_disponivel() -> bool:
    """Verifica se o Windows DPAPI está disponível no sistema operacional."""
    return sys.platform == "win32"


def _proteger_com_dpapi(dados: bytes) -> bytes:
    """Cifra dados usando Windows DPAPI (atrelado ao usuário/máquina logado)."""
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    blob_in = DATA_BLOB(
        len(dados),
        ctypes.cast(ctypes.create_string_buffer(dados), ctypes.POINTER(ctypes.c_byte))
    )
    blob_out = DATA_BLOB()

    descricao = "RemovedorDeFundos_MasterKey"
    sucesso = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        descricao,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out)
    )
    if not sucesso:
        raise RuntimeError("Falha ao proteger chave com Windows DPAPI.")

    resultado = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return resultado


def _desproteger_com_dpapi(dados_cifrados: bytes) -> bytes:
    """Decifra dados protegidos com Windows DPAPI."""
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    blob_in = DATA_BLOB(
        len(dados_cifrados),
        ctypes.cast(ctypes.create_string_buffer(dados_cifrados), ctypes.POINTER(ctypes.c_byte))
    )
    blob_out = DATA_BLOB()

    sucesso = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out)
    )
    if not sucesso:
        raise RuntimeError("Falha ao descriptografar chave com Windows DPAPI.")

    resultado = ctypes.string_at(blob_out.pbData, blob_out.cbData)
    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
    return resultado


# ---------------------------------------------------------------------------
# Gestão da Chave Mestre de Criptografia (Fernet)
# ---------------------------------------------------------------------------
def obter_ou_criar_chave_mestre() -> bytes:
    """
    Retorna a chave simétrica Fernet.
    Se ainda não existir, gera uma chave criptográfica forte de 256 bits,
    protege-a com DPAPI no Windows e armazena em disco com proteção.
    """
    global _CHAVE_MESTRE_CACHE
    if _CHAVE_MESTRE_CACHE:
        return _CHAVE_MESTRE_CACHE

    # 1. Tenta carregar chave protegida com DPAPI (Windows)
    if _dpapi_disponivel() and ARQUIVO_CHAVE_MESTRE_DPAPI.exists():
        try:
            conteudo_cifrado = ARQUIVO_CHAVE_MESTRE_DPAPI.read_bytes()
            _CHAVE_MESTRE_CACHE = _desproteger_com_dpapi(conteudo_cifrado)
            return _CHAVE_MESTRE_CACHE
        except Exception:
            pass

    # 2. Tenta carregar chave direta (fallback multiplataforma)
    if ARQUIVO_CHAVE_MESTRE_PLAIN.exists():
        try:
            chave = ARQUIVO_CHAVE_MESTRE_PLAIN.read_bytes().strip()
            # Valida formato da chave Fernet
            Fernet(chave)
            _CHAVE_MESTRE_CACHE = chave
            return _CHAVE_MESTRE_CACHE
        except Exception:
            pass

    # 3. Chave não existe: gera uma nova chave forte
    nova_chave = Fernet.generate_key()

    if _dpapi_disponivel():
        try:
            chave_dpapi = _proteger_com_dpapi(nova_chave)
            ARQUIVO_CHAVE_MESTRE_DPAPI.write_bytes(chave_dpapi)
            # Oculta arquivo no Windows se possível
            _ocultar_arquivo_windows(ARQUIVO_CHAVE_MESTRE_DPAPI)
        except Exception:
            # Fallback caso DPAPI falhe
            ARQUIVO_CHAVE_MESTRE_PLAIN.write_bytes(nova_chave)
            _restringir_permissoes_arquivo(ARQUIVO_CHAVE_MESTRE_PLAIN)
    else:
        ARQUIVO_CHAVE_MESTRE_PLAIN.write_bytes(nova_chave)
        _restringir_permissoes_arquivo(ARQUIVO_CHAVE_MESTRE_PLAIN)

    _CHAVE_MESTRE_CACHE = nova_chave
    return _CHAVE_MESTRE_CACHE


def _ocultar_arquivo_windows(caminho: Path):
    """Aplica atributo oculto no Windows."""
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(caminho), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass


def _restringir_permissoes_arquivo(caminho: Path):
    """Em sistemas Unix-like, restringe permissão para 0600 (apenas proprietário)."""
    try:
        if hasattr(os, "chmod") and sys.platform != "win32":
            os.chmod(caminho, 0o600)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Criptografia e Descriptografia de Dados
# ---------------------------------------------------------------------------
def criptografar_texto(texto: str) -> bytes:
    """Cifra uma string em UTF-8 com AES-128-CBC + HMAC-SHA256 (Fernet)."""
    chave = obter_ou_criar_chave_mestre()
    fernet = Fernet(chave)
    return fernet.encrypt(texto.encode("utf-8"))


def descriptografar_texto(dados_cifrados: bytes) -> str:
    """Decifra dados cifrados e retorna a string original."""
    chave = obter_ou_criar_chave_mestre()
    fernet = Fernet(chave)
    return fernet.decrypt(dados_cifrados).decode("utf-8")


# ---------------------------------------------------------------------------
# Armazenamento e Recuperação de Credenciais
# ---------------------------------------------------------------------------
def salvar_credencial(nome_chave: str, valor: str) -> bool:
    """
    Armazena com segurança uma credencial cifrada em disco.
    Ex: salvar_credencial("GEMINI_API_KEY", "AIzaSy...")
    """
    try:
        dados: Dict[str, Any] = {}
        if ARQUIVO_CREDENCIAIS_ENC.exists():
            try:
                conteudo_cifrado = ARQUIVO_CREDENCIAIS_ENC.read_bytes()
                dados_json = descriptografar_texto(conteudo_cifrado)
                dados = json.loads(dados_json)
            except Exception:
                dados = {}

        dados[nome_chave] = valor
        conteudo_serializado = json.dumps(dados, ensure_ascii=False)
        cifrado = criptografar_texto(conteudo_serializado)
        ARQUIVO_CREDENCIAIS_ENC.write_bytes(cifrado)
        _ocultar_arquivo_windows(ARQUIVO_CREDENCIAIS_ENC)
        _restringir_permissoes_arquivo(ARQUIVO_CREDENCIAIS_ENC)
        return True
    except Exception as e:
        print(f"[Aviso Segurança] Não foi possível salvar credencial criptografada: {e}")
        return False


def obter_credencial(nome_chave: str) -> Optional[str]:
    """Recupera e decifra uma credencial armazenada em disco."""
    if not ARQUIVO_CREDENCIAIS_ENC.exists():
        return None
    try:
        conteudo_cifrado = ARQUIVO_CREDENCIAIS_ENC.read_bytes()
        dados_json = descriptografar_texto(conteudo_cifrado)
        dados = json.loads(dados_json)
        return dados.get(nome_chave)
    except (InvalidToken, Exception):
        return None


def remover_todas_credenciais() -> bool:
    """Remove com segurança os arquivos de credenciais e chaves criptografadas."""
    global _CHAVE_MESTRE_CACHE
    _CHAVE_MESTRE_CACHE = None

    removidos = False
    for arquivo in [ARQUIVO_CREDENCIAIS_ENC, ARQUIVO_CHAVE_MESTRE_DPAPI, ARQUIVO_CHAVE_MESTRE_PLAIN]:
        if arquivo.exists():
            try:
                arquivo.unlink()
                removidos = True
            except Exception:
                pass
    return removidos


# ---------------------------------------------------------------------------
# Gestão Específica da Google Gemini API Key
# ---------------------------------------------------------------------------
def obter_chave_gemini_segura(solicitar_se_ausente: bool = False) -> Optional[str]:
    """
    Busca a Chave de API Google Gemini na seguinte ordem de prioridade de segurança:
    1. Variável de ambiente (GEMINI_API_KEY ou GOOGLE_API_KEY)
    2. Cofre criptografado local (.credenciais.enc)
    3. Se solicitar_se_ausente for True: Solicita com máscara de entrada e oferece
       salvamento criptografado automático para execuções rápidas do .bat.
    """
    # 1. Variável de ambiente
    chave_env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if chave_env and chave_env.strip():
        return chave_env.strip()

    # 2. Cofre cifrado
    chave_cifrada = obter_credencial("GEMINI_API_KEY")
    if chave_cifrada and chave_cifrada.strip():
        return chave_cifrada.strip()

    # 3. Solicitação interativa segura
    if solicitar_se_ausente:
        return prompt_configurar_chave_gemini()

    return None


def prompt_configurar_chave_gemini() -> Optional[str]:
    """
    Solicita ao usuário a chave de API no terminal com digitação oculta
    para evitar exposição visual (shoulder surfing) e oferece criptografia em repouso.
    """
    print("\n" + "=" * 60)
    print("🔒 CONFIGURAÇÃO SEGURA DA CHAVE DE API GOOGLE GEMINI")
    print("=" * 60)
    print("Obtenha sua chave gratuita em: https://aistudio.google.com/app/apikey\n")
    print("Dica: Ao colar sua chave, os caracteres ficarão OCULTOS por segurança.")
    
    try:
        chave = getpass.getpass("Cole sua Chave de API Google (ou pressione Enter para cancelar): ").strip()
    except Exception:
        chave = input("Cole sua Chave de API Google (ou pressione Enter para cancelar): ").strip()

    if not chave:
        print("Operação cancelada. Nenhuma chave informada.")
        return None

    # Validação básica de formato
    if len(chave) < 15:
        print("[Erro] Chave informada parece ser inválida ou muito curta.")
        return None

    mascarada = mascarar_chave(chave)
    print(f"\n✔ Chave recebida com sucesso: {mascarada}")
    
    salvar = input("Deseja salvar esta chave CRIPTOGRAFADA para execuções rápidas do .bat? (S/n): ").strip().lower()
    if salvar in ("", "s", "sim", "y", "yes"):
        sucesso = salvar_credencial("GEMINI_API_KEY", chave)
        if sucesso:
            print("🔒 Chave criptografada com AES-128 e protegida com segurança no disco!")
        else:
            print("[Aviso] A chave será usada apenas na sessão atual.")

    return chave


# ---------------------------------------------------------------------------
# Mascaramento, Sanitização e Prevenção de Path Traversal
# ---------------------------------------------------------------------------
def mascarar_chave(chave: Optional[str]) -> str:
    """Retorna a chave mascarada para exibição segura (ex: AIzaSy...4xQ9)."""
    if not chave:
        return "[NÃO CONFIGURADA]"
    chave = chave.strip()
    if len(chave) <= 10:
        return "*" * len(chave)
    return f"{chave[:6]}...{chave[-4:]}"


def sanitizar_mensagem_erro(mensagem: str, chaves_sensiveis: Optional[list] = None) -> str:
    """
    Remove quaisquer chaves ou tokens de mensagens de erro ou logs
    antes de imprimir no terminal, impedindo vazamentos acidentais.
    """
    if not mensagem:
        return ""
    
    resultado = str(mensagem)
    
    # Sanitiza padrões conhecidos da Google (AIzaSy...)
    padrao_google = re.compile(r"AIza[0-9A-Za-z-_]{35}")
    resultado = padrao_google.sub("[CHAVE_GOOGLE_REMOVIDA_POR_SEGURANCA]", resultado)

    if chaves_sensiveis:
        for segredo in chaves_sensiveis:
            if segredo and len(segredo) >= 8 and segredo in resultado:
                resultado = resultado.replace(segredo, "[DADO_CONFIDENCIAL_REMOVIDO]")
                
    return resultado


def sanitizar_nome_arquivo_saida(nome_base: str) -> str:
    """
    Protege contra ataques de Path Traversal e injeção de caracteres perigosos
    em nomes de arquivos ao salvar as imagens recortadas.
    """
    # Remove qualquer referência a diretórios pai e separadores de caminho
    nome_limpo = Path(nome_base).name
    # Substitui caracteres não alfanuméricos ou traços/sublinhados
    nome_limpo = re.sub(r'[^a-zA-Z0-9_\-\.\s]', '_', nome_limpo).strip()
    # Impede arquivos vazios ou iniciados por ponto relativo
    if not nome_limpo or nome_limpo.startswith("."):
        nome_limpo = "imagem_processada"
    return nome_limpo
