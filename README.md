# YVORA | Requisições

App Streamlit para requisição, aprovação, compras, acompanhamento e recebimento.

## 1. Estrutura esperada no Google Sheets
Use a planilha:
`19CH28p4VI4iFv9mRPnRPBMW1MHTqdW0-ZQhghC2_nrk`

Abas principais:
- itens
- fornecedores
- usuarios
- requisicoes
- parametros
- log_alteracoes

## 2. Como rodar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 3. Secrets do Streamlit
Crie `.streamlit/secrets.toml` com base no arquivo `secrets_example.toml`.

## 4. Compartilhar a planilha com a conta de serviço
No arquivo `secrets.toml`, copie o campo:
- `client_email`

Depois compartilhe a planilha do Google com esse e-mail como Editor.

## 5. Perfis aceitos
Na aba `usuarios`, coluna `perfil`, use:
- solicitante
- aprovador
- compras
- recebimento
- admin

Você pode combinar perfis no mesmo usuário:
`aprovador;compras`
`admin`
`solicitante;recebimento`

## 6. Deploy no Streamlit Cloud
1. Suba estes arquivos no GitHub
2. No Streamlit Cloud, crie um novo app apontando para `app.py`
3. Cole o conteúdo do `secrets_example.toml` no campo Secrets, trocando pelos dados reais
4. Faça deploy

## 7. Sugestão de primeiro usuário admin
Cadastre manualmente na aba `usuarios`:
- usuario: admin
- nome: Administrador
- senha: 123456
- perfil: admin
- setor: administrativo
- ativo: SIM

Depois entre no app e cadastre os demais.
