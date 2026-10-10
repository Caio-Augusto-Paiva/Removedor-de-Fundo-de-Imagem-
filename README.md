# ✂️ Removedor de Fundos de Imagens com Inteligência Artificial

Aplicativo de alta performance em Python para remoção automática de fundos de imagens em lote, com recorte preciso e fundo transparente em `.png`.

---

## ⚡ Início Rápido (Execução Rápida via `.bat`)

1. Coloque suas fotos na pasta **`Imagens/`** (ou arraste as fotos diretamente para cima do arquivo `executar.bat`).
2. Dê um duplo clique no arquivo **`executar.bat`**.
3. Pressione **ENTER** para iniciar com a **IA Local** (100% offline, gratuita e ultra-rápida) ou escolha o Google Gemini.
4. Suas fotos com fundo transparente estarão prontas na pasta **`ImagensSemFundo/`**!

---

## 🔒 Segurança e Proteção de Dados

- **Criptografia em Repouso**: Chaves confidenciais (como a API Key do Google Gemini) são criptografadas com **AES-128 (Fernet)** e protegidas pelo **Windows DPAPI** (atrelado ao seu usuário no Windows). Elas nunca são salvas em texto puro.
- **Entrada Oculta**: Ao cadastrar uma chave, os caracteres ficam ocultos no terminal contra observadores (*shoulder surfing*).
- **Sanitização Ativa**: Chaves e credenciais são mascaradas (`AIzaSy...XXXX`) e nunca são expostas em logs, telas ou mensagens de erro.
- **Proteção via `.gitignore`**: Arquivos de chaves (`.secrets.key`, `.credenciais.enc`, `*.key`, `*.enc`), variáveis `.env`, modelos neurais e fotos pessoais de entrada/saída são estritamente bloqueados para evitar vazamentos acidentais para repositórios públicos.
- **Defesa Contra Ataques**: Sanitização de nomes de arquivo contra *Path Traversal* e proteção contra bombas de descompressão (*Decompression Bomb*).

Para instruções detalhadas de configuração, consulte o arquivo [INSTRUCOES.md](file:///c:/Users/capra/OneDrive/Desktop/RemovedorDeFundos/INSTRUCOES.md).
