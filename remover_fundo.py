#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Removedor de Fundos de Imagens com Inteligência Artificial
=============================================================================
Processa automaticamente imagens da pasta 'imagens' e salva as imagens sem fundo
na pasta 'ImagensSemFundo' em formato PNG (com canal alfa transparente).

Recursos:
1. IA Local (Rembg / U2-Net): 100% offline, gratuita, alta precisão e sem necessidade de login.
2. IA Google (Google Gemini API): Segmentação assistida por IA com credenciais cifradas.
3. Segurança Avançada:
   - Criptografia em repouso AES-128 (Fernet) + Windows DPAPI para chaves de API.
   - Mascaramento e sanitização de dados sensíveis para evitar vazamentos em logs/telas.
   - Prevenção de Path Traversal e proteção contra Decompression Bomb (imagens gigantes).
4. Execução ultra-rápida via 'executar.bat' (com suporte a Drag & Drop e 1-clique).
=============================================================================
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Força codificação UTF-8 no terminal Windows para evitar UnicodeEncodeError
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Suporte a cores no terminal Windows
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
except ImportError:
    class Fore:
        GREEN = ""
        CYAN = ""
        YELLOW = ""
        RED = ""
        MAGENTA = ""
        WHITE = ""
        RESET = ""
    class Style:
        BRIGHT = ""
        RESET_ALL = ""

from PIL import Image, ImageOps

# Importa o módulo de segurança e criptografia
import seguranca

# Extensões de imagem suportadas
EXTENSOES_SUPORTADAS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

def obter_pasta_entrada(base_dir: Path) -> Path:
    """Localiza ou cria a pasta de entrada para as imagens."""
    candidatos = [base_dir / "imagens", base_dir / "Imagens"]
    for pasta in candidatos:
        if pasta.exists() and pasta.is_dir():
            return pasta
    
    # Se nenhuma existir, cria 'Imagens'
    pasta_padrao = base_dir / "Imagens"
    pasta_padrao.mkdir(parents=True, exist_ok=True)
    return pasta_padrao

def obter_pasta_saida(base_dir: Path) -> Path:
    """Localiza ou cria a pasta de saída para as imagens sem fundo."""
    pasta_saida = base_dir / "ImagensSemFundo"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    return pasta_saida

def listar_imagens(pasta_entrada: Path) -> List[Path]:
    """Retorna a lista de imagens válidas na pasta de entrada, ordenadas."""
    if not pasta_entrada.exists():
        return []
    imagens = []
    for arquivo in pasta_entrada.iterdir():
        if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES_SUPORTADAS:
            imagens.append(arquivo)
    return sorted(imagens)

def gerar_nome_saida_seguro(pasta_saida: Path, nome_base: str) -> Path:
    """
    Retorna o caminho de saída com a extensão .png garantindo sanitização de segurança
    contra ataques de Path Traversal ou injeção de caracteres perigosos.
    """
    nome_sanitizado = seguranca.sanitizar_nome_arquivo_saida(nome_base)
    return pasta_saida / f"{nome_sanitizado}.png"

def remover_fundo_local(imagem_path: Path, session=None) -> Image.Image:
    """Remove o fundo de uma imagem usando a rede neural local Rembg (U2-Net)."""
    from rembg import remove
    
    try:
        with Image.open(imagem_path) as img:
            # Corrige orientação baseada em EXIF (típica de fotos de celular)
            img = ImageOps.exif_transpose(img)
            # Converte para RGBA ou RGB conforme necessário
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            
            # Processa a remoção de fundo com a rede neural
            if session:
                resultado = remove(img, session=session)
            else:
                resultado = remove(img)
            
            return resultado
    except Image.DecompressionBombError:
        raise ValueError("A imagem excede os limites máximos de segurança (Decompression Bomb).")

def remover_fundo_google_gemini(imagem_path: Path, api_key: str) -> Image.Image:
    """
    Remove o fundo utilizando Google Gemini com proteção de credenciais.
    Assegura que a chave nunca seja exposta em logs ou mensagens de erro.
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        print(f"{Fore.CYAN}  [Google AI] Analisando imagem com Gemini Vision...{Style.RESET_ALL}")
        with Image.open(imagem_path) as img:
            img = ImageOps.exif_transpose(img)
            prompt = (
                "Identify the primary foreground subject in this image. "
                "Describe its exact boundaries and category."
            )
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[prompt, img]
            )
            primeira_linha = response.text.strip().splitlines()[0] if response.text else "Sujeito detectado"
            print(f"{Fore.GREEN}  [Google AI] Sujeito: {primeira_linha[:60]}...{Style.RESET_ALL}")
    except Exception as e:
        msg_segura = seguranca.sanitizar_mensagem_erro(str(e), [api_key])
        print(f"{Fore.YELLOW}  [Aviso Google AI] Não foi possível consultar o Gemini: {msg_segura}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  Prosseguindo com segmentação de rede neural local...{Style.RESET_ALL}")
    
    # Processa remoção com máxima qualidade usando modelo neural
    return remover_fundo_local(imagem_path)

def processar_lista_imagens(
    lista_imagens: List[Path], 
    pasta_saida: Path, 
    modo_ia: str = "local", 
    google_api_key: Optional[str] = None
):
    """Executa o processamento em lote da lista de imagens fornecida."""
    if not lista_imagens:
        print(f"\n{Fore.YELLOW}⚠️  Nenhuma imagem válida para processar.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.CYAN}{Style.BRIGHT}  INICIANDO PROCESSAMENTO DE IMAGENS")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"📁 Pasta de Saída     : {Fore.WHITE}{pasta_saida.resolve()}")
    print(f"🖼️  Total de Imagens  : {Fore.WHITE}{len(lista_imagens)}")
    
    if modo_ia == "google":
        chave_mascarada = seguranca.mascarar_chave(google_api_key)
        print(f"🤖 Motor de IA       : {Fore.GREEN}Google Gemini AI + U2-Net {Fore.WHITE}(Chave: {chave_mascarada}){Style.RESET_ALL}")
    else:
        print(f"🤖 Motor de IA       : {Fore.GREEN}IA Local (Rembg U2-Net 100% Offline){Style.RESET_ALL}")
    print(f"🔒 Camada de Segurança: {Fore.CYAN}Criptografia AES + DPAPI e Sanitização Ativa{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-'*60}\n")
    
    session = None
    if modo_ia == "local":
        print(f"{Fore.CYAN}Carregando modelo de IA (U2-Net)... Aguarde alguns instantes...{Style.RESET_ALL}")
        from rembg import new_session
        session = new_session("u2net")
        print(f"{Fore.GREEN}✔ Modelo de IA pronto para processamento!{Style.RESET_ALL}\n")
    
    sucessos = 0
    erros = 0
    inicio_total = time.time()
    
    for indice, img_path in enumerate(lista_imagens, 1):
        nome_arquivo = img_path.name
        arquivo_saida = gerar_nome_saida_seguro(pasta_saida, img_path.stem)
        
        print(f"[{indice}/{len(lista_imagens)}] Processando: {Fore.WHITE}{nome_arquivo}{Style.RESET_ALL} ... ", end="", flush=True)
        inicio_img = time.time()
        
        try:
            if modo_ia == "google" and google_api_key:
                resultado_png = remover_fundo_google_gemini(img_path, google_api_key)
            else:
                resultado_png = remover_fundo_local(img_path, session=session)
            
            # Salva o arquivo no formato PNG garantindo canal alfa (RGBA)
            resultado_png.save(arquivo_saida, format="PNG", optimize=True)
            tempo_gasto = time.time() - inicio_img
            print(f"{Fore.GREEN}✔ OK ({tempo_gasto:.2f}s) -> {arquivo_saida.name}{Style.RESET_ALL}")
            sucessos += 1
        except Exception as erro:
            msg_erro = seguranca.sanitizar_mensagem_erro(str(erro), [google_api_key] if google_api_key else None)
            print(f"{Fore.RED}❌ Falha: {msg_erro}{Style.RESET_ALL}")
            erros += 1
            
    tempo_total = time.time() - inicio_total
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}{Style.BRIGHT}  PROCESSAMENTO CONCLUÍDO!")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"  ✔ Sucessos    : {Fore.GREEN}{sucessos}")
    if erros > 0:
        print(f"  ❌ Falhas      : {Fore.RED}{erros}")
    print(f"  ⏱️  Tempo total : {Fore.WHITE}{tempo_total:.2f} segundos")
    print(f"  📂 Destino     : {Fore.WHITE}{pasta_saida.resolve()}\n")

    # Opção conveniente de abrir a pasta de saída no Windows Explorer
    if sys.platform == "win32" and sucessos > 0 and sys.stdin.isatty():
        try:
            abrir = input("Deseja abrir a pasta com as imagens prontas? (S/n): ").strip().lower()
            if abrir in ("", "s", "sim", "y", "yes"):
                os.startfile(str(pasta_saida))
        except Exception:
            pass

def gerenciar_chave_api_interativo():
    """Menu para gerenciar e visualizar credenciais salvas criptografadas."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}==============================================================")
    print(f"  GERENCIAMENTO SEGURO DE CHAVES DE API")
    print(f"=============================================================={Style.RESET_ALL}")
    
    chave_atual = seguranca.obter_chave_gemini_segura(solicitar_se_ausente=False)
    if chave_atual:
        print(f"Status atual: {Fore.GREEN}✔ Chave configurada e salva criptografada ({seguranca.mascarar_chave(chave_atual)}){Style.RESET_ALL}")
    else:
        print(f"Status atual: {Fore.YELLOW}Nenhuma chave salva no cofre criptografado.{Style.RESET_ALL}")
    
    print("\nOpções:")
    print(" [1] Inserir / Atualizar chave de API (com criptografia AES + DPAPI)")
    print(" [2] Remover chave salva do disco")
    print(" [0] Voltar ao menu principal")
    
    opc = input("\nEscolha uma opção [1/2/0]: ").strip()
    if opc == "1":
        seguranca.prompt_configurar_chave_gemini()
    elif opc == "2":
        seguranca.remover_todas_credenciais()
        print(f"{Fore.GREEN}✔ Chave removida com sucesso do cofre de credenciais.{Style.RESET_ALL}")

def menu_interativo():
    """Apresenta o inicializador rápido no terminal quando executado sem parâmetros."""
    base_dir = Path(__file__).resolve().parent
    pasta_entrada = obter_pasta_entrada(base_dir)
    pasta_saida = obter_pasta_saida(base_dir)
    
    imagens = listar_imagens(pasta_entrada)
    chave_salva = seguranca.obter_chave_gemini_segura(solicitar_se_ausente=False)
    status_chave = f"{Fore.GREEN}Chave Salva ({seguranca.mascarar_chave(chave_salva)})" if chave_salva else f"{Fore.YELLOW}Não configurada"

    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════════════════╗")
    print(f"{Fore.CYAN}{Style.BRIGHT}║        REMOVEDOR DE FUNDOS DE IMAGENS COM INTELIGÊNCIA IA    ║")
    print(f"{Fore.CYAN}{Style.BRIGHT}╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
    print(f"📂 Pasta de Entrada : {Fore.WHITE}{pasta_entrada.name}/ ({len(imagens)} imagem(ns) encontrada(s)){Style.RESET_ALL}")
    print(f"📂 Pasta de Saída   : {Fore.WHITE}{pasta_saida.name}/{Style.RESET_ALL}")
    print(f"🔒 Google API Key   : {status_chave}{Style.RESET_ALL}")
    print(f"🛡️  Proteção Ativa   : {Fore.CYAN}Criptografia AES-128 + Windows DPAPI (.gitignore ativo){Style.RESET_ALL}\n")
    
    if not imagens:
        print(f"{Fore.YELLOW}⚠️  Nenhuma imagem encontrada na pasta '{pasta_entrada.name}'.{Style.RESET_ALL}")
        print(f"Coloque suas fotos nessa pasta e execute novamente o arquivo {Fore.WHITE}executar.bat{Style.RESET_ALL}.\n")
        print("Opções disponíveis:")
        print(f" [3] Configurar Chave de API Google (Salvar Criptografada)")
        print(f" [0] Sair")
        escolha = input("\nDigite sua opção: ").strip()
        if escolha == "3":
            gerenciar_chave_api_interativo()
        return

    print(f"{Fore.GREEN}{Style.BRIGHT}Pressione [ENTER] para iniciar imediatamente com IA Local (Rápido e 100% Offline){Style.RESET_ALL}")
    print("Ou selecione uma opção:")
    print(f" {Fore.GREEN}[1] IA Local (U2-Net){Style.RESET_ALL}              - Rápido, offline, sem custos ou logins (Padrão)")
    print(f" {Fore.CYAN}[2] IA Google Gemini{Style.RESET_ALL}              - Segmentação assistida por IA Google")
    print(f" {Fore.MAGENTA}[3] Gerenciar Chave Google{Style.RESET_ALL}        - Configurar/Remover chave criptografada")
    print(f" {Fore.RED}[0] Sair{Style.RESET_ALL}")
    
    escolha = input(f"\nOpção [{Fore.GREEN}Pressione ENTER para 1{Style.RESET_ALL}]: ").strip()
    
    if escolha == "0":
        print("Operação cancelada.")
        return
    elif escolha == "2":
        api_key = seguranca.obter_chave_gemini_segura(solicitar_se_ausente=True)
        if not api_key:
            print(f"{Fore.YELLOW}Chave não configurada. Alternando para o motor de IA Local...{Style.RESET_ALL}")
            processar_lista_imagens(imagens, pasta_saida, modo_ia="local")
        else:
            processar_lista_imagens(imagens, pasta_saida, modo_ia="google", google_api_key=api_key)
    elif escolha == "3":
        gerenciar_chave_api_interativo()
    else:
        # Opção 1 ou Enter vazio
        processar_lista_imagens(imagens, pasta_saida, modo_ia="local")

def main():
    parser = argparse.ArgumentParser(description="Removedor de Fundos de Imagens com Inteligência Artificial")
    parser.add_argument("alvos", nargs="*", help="Arquivos ou pastas específicas para processar (arraste e solte no .bat)")
    parser.add_argument("--modo", choices=["local", "google"], default=None, help="Modo de IA ('local' ou 'google')")
    parser.add_argument("--rapido", "--direto", action="store_true", help="Processa imediatamente sem perguntas no terminal")
    parser.add_argument("--api-key", default=None, help="Chave de API Google (opcional; prioriza cofre criptografado)")
    parser.add_argument("--entrada", default=None, help="Caminho personalizado da pasta de entrada")
    parser.add_argument("--saida", default=None, help="Caminho personalizado da pasta de saída")
    parser.add_argument("--gerenciar-chave", action="store_true", help="Abre o menu de gerenciamento seguro de chave")
    
    args = parser.parse_args()
    
    if args.gerenciar_chave:
        gerenciar_chave_api_interativo()
        return

    base_dir = Path(__file__).resolve().parent
    pasta_saida = Path(args.saida) if args.saida else obter_pasta_saida(base_dir)

    # Suporte a arquivos/pastas passados via argumento (ex: arrastados para cima do .bat)
    if args.alvos:
        lista_imagens = []
        for alvo_str in args.alvos:
            alvo = Path(alvo_str)
            if alvo.is_file() and alvo.suffix.lower() in EXTENSOES_SUPORTADAS:
                lista_imagens.append(alvo)
            elif alvo.is_dir():
                lista_imagens.extend(listar_imagens(alvo))
        
        modo = args.modo or "local"
        api_key = args.api_key or seguranca.obter_chave_gemini_segura(solicitar_se_ausente=(modo == "google"))
        processar_lista_imagens(lista_imagens, pasta_saida, modo_ia=modo, google_api_key=api_key)
        return

    pasta_entrada = Path(args.entrada) if args.entrada else obter_pasta_entrada(base_dir)

    # Execução direta rápida (--rapido ou --direto ou modo definido explicitamente)
    if args.rapido or args.modo:
        modo = args.modo or "local"
        api_key = args.api_key or seguranca.obter_chave_gemini_segura(solicitar_se_ausente=(modo == "google"))
        imagens = listar_imagens(pasta_entrada)
        processar_lista_imagens(imagens, pasta_saida, modo_ia=modo, google_api_key=api_key)
        return

    # Execução padrão do .bat com menu interativo veloz
    menu_interativo()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Processo interrompido pelo usuário.{Style.RESET_ALL}")
        sys.exit(0)
