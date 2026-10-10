# 🖼️ Removedor de Fundos de Imagem com Inteligência Artificial

Aplicativo em Python de alta performance para remoção automática de fundos de imagens em lote, utilizando modelos de Inteligência Artificial com suporte a preservação total de transparência (canal alfa em formato `.png`).

---

## 📋 Sumário
1. [Visão Geral](#-visão-geral)
2. [Estrutura de Arquivos](#-estrutura-de-arquivos)
3. [Segurança e Criptografia](#-segurança-e-criptografia)
4. [Instalação e Ambiente Virtual](#-instalação-e-ambiente-virtual)
5. [Como Usar (Execução Rápida via `.bat`)](#-como-usar-execução-rápida-via-bat)
6. [Modelos de IA (Local vs. Google)](#-modelos-de-ia-local-vs-google)
7. [Resolução de Dúvidas e Problemas](#-resolução-de-dúvidas-e-problemas)

---

## 🌟 Visão Geral

O aplicativo lê as imagens da pasta `Imagens` (ou arquivos arrastados diretamente), processa os recortes utilizando redes neurais convolucionais e visão computacional (U²-Net) ou o modelo Google Gemini, e salva as imagens resultantes com fundo transparente na pasta `ImagensSemFundo` em formato `.png`.

### Principais Características:
- **Execução Ultra-rápida via `.bat`**: Com 2 cliques no Windows, basta pressionar **ENTER** para iniciar o processamento de todas as imagens.
- **Suporte a Drag & Drop**: É possível arrastar arquivos de imagem ou pastas inteiras diretamente para cima do arquivo `executar.bat`.
- **Transparência nativa**: Saída em formato PNG 32-bit (RGBA) com recorte suave nos contornos.
- **Formatos suportados**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`.
- **Dois motores de IA**:
  1. **IA Local (Rembg / U²-Net)**: 100% offline, gratuita, sem limites e sem necessidade de login.
  2. **IA Google Gemini**: Suporte a modelos generativos do Google com credenciais protegidas por criptografia.

---

## 📁 Estrutura de Arquivos

```text
RemovedorDeFundos/
│
├── Imagens/                  <-- Coloque suas fotos originais aqui (.jpg, .png, etc.)
│   └── .gitkeep              <-- Mantém a pasta no Git sem expor suas fotos
├── ImagensSemFundo/          <-- As imagens recortadas são salvas aqui (.png transparente)
│   └── .gitkeep              <-- Mantém a pasta no Git sem expor suas fotos
│
├── remover_fundo.py          <-- Código principal de processamento em lote
├── seguranca.py              <-- Módulo de segurança, criptografia AES e Windows DPAPI
├── executar.bat              <-- Atalho rápido de 2 cliques (com suporte a Drag & Drop)
├── requirements.txt          <-- Lista de dependências exatas do projeto
├── .gitignore                <-- Regras estritas de segurança (chaves, fotos e ambientes)
├── .env.example              <-- Modelo seguro de variáveis de ambiente
├── INSTRUCOES.md             <-- Guia detalhado de segurança e execução
└── README.md                 <-- Visão geral do projeto
```

---

## 🔒 Segurança e Criptografia

O projeto implementa uma camada rigorosa de segurança da informação:

### 1. Criptografia em Repouso de Chaves de API
- Chaves confidenciais (ex: `GEMINI_API_KEY`) nunca são salvas em texto puro.
- São cifradas com algoritmo simétrico autenticado **AES-128-CBC + HMAC-SHA256 (Fernet)**.
- No Windows, a chave mestre é protegida pelo **Windows DPAPI** (`CryptProtectData`), que vincula a chave criptográfica à conta do usuário logado e ao hardware do sistema. Nenhum outro usuário ou máquina consegue decifrar o arquivo.

### 2. Ocultação de Entrada no Terminal
- Ao cadastrar uma chave no terminal, o cursor utiliza `getpass` (entrada oculta). Caracteres não aparecem na tela, prevenindo espionagem visual (*shoulder surfing*).

### 3. Mascaramento e Sanitização de Logs
- Chaves em memória são mascaradas (ex: `AIzaSy...4xQ9`) antes de qualquer exibição.
- Mensagens de erro da API ou da biblioteca são sanitizadas automaticamente por regex antes de irem para o console, impedindo vazamento de tokens em exceções.

### 4. Proteção contra *Path Traversal* e *Decompression Bomb*
- Nomes de arquivos gerados passam por sanitização estrita, impedindo injeção de diretórios (`../`) ou caracteres maliciosos.
- Limite de segurança de descompressão do Pillow ativo para mitigar ataques de negação de serviço (*zip bombs* / imagens gigantes forjadas).

### 5. Regras do `.gitignore`
O arquivo `.gitignore` bloqueia:
- Arquivos de credenciais criptografadas: `.credenciais.enc`, `.secrets.key`, `master.key*`.
- Chaves e certificados: `*.key`, `*.enc`, `*.secret`, `*.pem`, `*.crt`.
- Variáveis de ambiente: `.env`, `.env.*`.
- Fotos pessoais do usuário: `Imagens/*` e `ImagensSemFundo/*` (garantindo que fotos particulares nunca sejam commitadas acidentalmente).
- Ambientes virtuais e caches pesados: `.venv/`, `__pycache__/`, `*.onnx`.

---

## 📦 Instalação e Ambiente Virtual

### 1. Criar o Ambiente Virtual (se ainda não existir)
```powershell
python -m venv .venv
```

### 2. Instalar as Dependências
Com o ambiente ativado:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 🚀 Como Usar (Execução Rápida via `.bat`)

### Método 1: Dois cliques rápidos no Windows (Mais Fácil)
1. Dê um duplo clique no arquivo **`executar.bat`**.
2. Pressione **ENTER**: o processamento com a **IA Local** inicia imediatamente!
3. Ao finalizar, o programa perguntará se deseja abrir a pasta `ImagensSemFundo/` no Windows Explorer.

### Método 2: Arrastar e Soltar (Drag & Drop)
- Arraste uma foto ou uma pasta cheia de fotos diretamente para cima do ícone **`executar.bat`**. O processamento dos arquivos arrastados começará imediatamente!

### Método 3: Linha de Comando (Modo Direto)
```powershell
# Execução direta sem perguntas:
.venv\Scripts\python.exe remover_fundo.py --rapido

# Processar arquivo específico:
.venv\Scripts\python.exe remover_fundo.py "caminho\foto.jpg"

# Gerenciar chaves salvas criptografadas:
.venv\Scripts\python.exe remover_fundo.py --gerenciar-chave
```

---

## 🤖 Modelos de IA (Local vs. Google)

### 1. IA Local (Rembg / U²-Net) - *Padrão Recomendado*
- **100% Offline**: As fotos nunca saem do seu computador.
- **Gratuita e sem limites**: Sem necessidade de cadastro, quotas ou logins.
- O modelo `u2net.onnx` fica armazenado em cache local e executa com aceleração ONNX Runtime.

### 2. IA Google (Google Gemini)
- Utiliza a API do Google AI Studio (`gemini-2.0-flash`) para segmentação e detecção de sujeito.
- Para usar:
  1. Acesse: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
  2. Gere sua chave gratuita.
  3. No menu do aplicativo (opção `[2]` ou `[3]`), cole a chave (a digitação será oculta por segurança).
  4. O aplicativo perguntará se deseja salvá-la criptografada. Aceitando, as próximas execuções via `.bat` utilizarão a chave automaticamente sem perguntas.

---

## 🛠️ Resolução de Dúvidas e Problemas

### 1. "Nenhuma imagem encontrada na pasta"
- Coloque suas fotos na pasta `Imagens/` localizada no mesmo diretório do arquivo `.bat`.
- Formatos aceitos: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`.

### 2. "A imagem de saída está com fundo preto ou branco"
- O arquivo é salvo com canal alfa de 32 bits (RGBA). Alguns visualizadores básicos do Windows exibem preto onde há transparência. Ao abrir no navegador, Canva, Photoshop ou PowerPoint, a transparência estará 100% perfeita.

### 3. "Como apagar minha chave de API salva?"
- Execute `executar.bat`, escolha a opção **`[3] Gerenciar Chave Google`** e selecione a opção de exclusão, ou execute:
  ```powershell
  .venv\Scripts\python.exe remover_fundo.py --gerenciar-chave
  ```
