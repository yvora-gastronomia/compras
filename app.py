import os
import json
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None


APP_TITLE = "YVORA | Requisições"
BRAND_BG = "#EFE7DD"
BRAND_BLUE = "#0E2A47"
BRAND_CARD = "rgba(255,255,255,0.55)"
BRAND_BORDER = "rgba(14,42,71,0.14)"
DEFAULT_SPREADSHEET_ID = "19CH28p4VI4iFv9mRPnRPBMW1MHTqdW0-ZQhghC2_nrk"

REQUIRED_SHEETS = [
    "itens",
    "fornecedores",
    "usuarios",
    "requisicoes",
    "parametros",
    "log_alteracoes",
]

ITEM_COLS = [
    "cod_item", "produto", "categoria", "unidade", "fornecedor_principal",
    "contato_fornecedor", "preco_referencia", "estoque_minimo", "ativo", "observacao"
]

USER_COLS = ["usuario", "nome", "senha", "perfil", "setor", "ativo"]

REQ_COLS = [
    "id_requisicao", "data_solicitacao", "hora_solicitacao", "solicitante", "nome_solicitante", "setor",
    "cod_item", "produto", "categoria", "unidade", "fornecedor_sugerido",
    "quantidade_solicitada", "prioridade", "data_necessaria", "justificativa",
    "status", "aprovador", "data_aprovacao", "observacao_aprovacao", "quantidade_aprovada",
    "comprador", "fornecedor_final", "data_compra", "previsao_entrega", "observacao_compras",
    "recebedor", "data_recebimento", "quantidade_recebida", "observacao_recebimento",
    "ultima_atualizacao"
]

LOG_COLS = ["data", "hora", "usuario", "id_requisicao", "acao", "status_anterior", "status_novo", "observacao"]

STATUS_FLOW = [
    "PENDENTE_APROVACAO",
    "REPROVADO",
    "APROVADO",
    "COMPRADO",
    "RECEBIDO",
    "CANCELADO",
]


def now_br() -> datetime:
    return datetime.now()


def fmt_dt(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y %H:%M")


def fmt_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def inject_css():
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            background: {BRAND_BG} !important;
        }}
        .stApp {{
            background: {BRAND_BG};
        }}
        section[data-testid="stSidebar"] {{
            background: rgba(255,255,255,0.45);
            border-right: 1px solid {BRAND_BORDER};
        }}
        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 5rem;
            max-width: 880px;
        }}
        h1, h2, h3 {{
            color: {BRAND_BLUE} !important;
            font-family: Georgia, "Times New Roman", serif !important;
        }}
        .yv-sub {{
            color: rgba(14,42,71,0.75);
            font-size: 14px;
            margin-top: -8px;
            margin-bottom: 14px;
        }}
        .yv-card {{
            background: {BRAND_CARD};
            border: 1px solid {BRAND_BORDER};
            border-radius: 18px;
            padding: 14px 14px;
            margin-bottom: 12px;
            box-shadow: 0 1px 0 rgba(14,42,71,0.03);
        }}
        .yv-card-title {{
            color: {BRAND_BLUE};
            font-weight: 800;
            font-size: 16px;
            margin-bottom: 6px;
        }}
        .yv-grid-2 {{
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .yv-meta {{
            color: rgba(14,42,71,0.74);
            font-size: 12px;
            line-height: 1.25rem;
        }}
        .yv-big {{
            font-size: 24px;
            font-weight: 900;
            color: {BRAND_BLUE};
        }}
        .yv-chip {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            border: 1px solid {BRAND_BORDER};
            margin-right: 6px;
            margin-bottom: 6px;
            background: rgba(255,255,255,0.55);
            color: {BRAND_BLUE};
        }}
        .yv-status {{
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 900;
        }}
        .status-pendente_aprovacao {{
            background: rgba(198,169,106,0.22);
            color: #7c5b12;
        }}
        .status-aprovado {{
            background: rgba(14,42,71,0.12);
            color: {BRAND_BLUE};
        }}
        .status-comprado {{
            background: rgba(233,128,23,0.16);
            color: #9b5d00;
        }}
        .status-recebido {{
            background: rgba(47,93,75,0.16);
            color: #2F5D4B;
        }}
        .status-reprovado {{
            background: rgba(140,28,28,0.12);
            color: #8C1C1C;
        }}
        .status-cancelado {{
            background: rgba(120,120,120,0.16);
            color: #555;
        }}
        .kpi {{
            background: rgba(255,255,255,0.45);
            border: 1px solid {BRAND_BORDER};
            border-radius: 18px;
            padding: 12px 14px;
            min-height: 84px;
        }}
        .kpi-label {{
            color: rgba(14,42,71,0.7);
            font-size: 12px;
        }}
        .kpi-value {{
            color: {BRAND_BLUE};
            font-size: 24px;
            font-weight: 900;
            margin-top: 6px;
        }}
        .stButton > button {{
            border-radius: 16px !important;
            min-height: 2.6rem !important;
            font-weight: 700 !important;
        }}
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            border-radius: 14px !important;
        }}
        div[data-baseweb="select"] > div,
        .stDateInput > div > div {{
            border-radius: 14px !important;
        }}
        @media (max-width: 720px) {{
            .main .block-container {{
                padding-left: 0.9rem;
                padding-right: 0.9rem;
                max-width: 100%;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def maybe_show_logo():
    for fn in ["logo.png", "yvora_logo.png", "logo.jpg", "yvora_logo.jpg"]:
        if os.path.exists(fn):
            st.image(fn, width=170)
            return


def show_header():
    left, right = st.columns([1, 3])
    with left:
        maybe_show_logo()
    with right:
        st.markdown(f"<h1>{APP_TITLE}</h1>", unsafe_allow_html=True)
        st.markdown(
            "<div class='yv-sub'>Solicitação, aprovação, compras, acompanhamento e recebimento em uma interface leve para celular.</div>",
            unsafe_allow_html=True,
        )


def safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x).strip()


def normalize_text(x: str) -> str:
    return safe_str(x).strip().upper()


def parse_profiles(profile_text: str) -> List[str]:
    raw = safe_str(profile_text)
    if not raw:
        return []
    parts = []
    for p in raw.replace("|", ";").replace(",", ";").split(";"):
        p = safe_str(p).lower()
        if p:
            parts.append(p)
    return list(dict.fromkeys(parts))


def has_profile(user: Dict, profile: str) -> bool:
    if not user:
        return False
    return profile.lower() in user.get("profiles", [])


def can_any(user: Dict, profiles: List[str]) -> bool:
    return any(has_profile(user, p) for p in profiles)


def status_badge(status: str) -> str:
    s = safe_str(status)
    klass = s.lower()
    return f"<span class='yv-status status-{klass}'>{s.replace('_', ' ')}</span>"


def kpi_box(label: str, value: str):
    st.markdown(
        f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_gsheet():
    if gspread is None or Credentials is None:
        raise RuntimeError("Dependências do Google Sheets não instaladas. Rode pip install -r requirements.txt")
    secrets = st.secrets
    if "gcp_service_account" not in secrets:
        raise RuntimeError("Configure gcp_service_account em .streamlit/secrets.toml")
    creds_info = dict(secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet_id = secrets.get("google_sheets", {}).get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
    return client.open_by_key(spreadsheet_id)


def ensure_worksheets(sh):
    current = {ws.title for ws in sh.worksheets()}
    for title in REQUIRED_SHEETS:
        if title not in current:
            ws = sh.add_worksheet(title=title, rows=1000, cols=30)
            if title == "itens":
                ws.append_row(ITEM_COLS)
            elif title == "usuarios":
                ws.append_row(USER_COLS)
            elif title == "requisicoes":
                ws.append_row(REQ_COLS)
            elif title == "log_alteracoes":
                ws.append_row(LOG_COLS)
            elif title == "fornecedores":
                ws.append_row(["fornecedor", "categoria_principal", "contato", "telefone", "email", "prazo_medio_dias", "ativo", "observacao"])
            elif title == "parametros":
                ws.append_row(["tipo", "valor"])


def ws_to_df(sh, title: str) -> pd.DataFrame:
    ws = sh.worksheet(title)
    records = ws.get_all_records(default_blank="")
    df = pd.DataFrame(records)
    if df.empty:
        if title == "itens":
            return pd.DataFrame(columns=ITEM_COLS)
        if title == "usuarios":
            return pd.DataFrame(columns=USER_COLS)
        if title == "requisicoes":
            return pd.DataFrame(columns=REQ_COLS)
        if title == "log_alteracoes":
            return pd.DataFrame(columns=LOG_COLS)
    return df


def append_row(sh, title: str, row: List):
    sh.worksheet(title).append_row(row, value_input_option="USER_ENTERED")


def update_cell_by_row_number(sh, title: str, row_number: int, headers: List[str], data: Dict[str, str]):
    ws = sh.worksheet(title)
    current = ws.row_values(row_number)
    if len(current) < len(headers):
        current += [""] * (len(headers) - len(current))
    for idx, header in enumerate(headers, start=1):
        if header in data:
            current[idx - 1] = data[header]
    ws.update(f"A{row_number}:{chr(64+min(len(headers),26))}{row_number}", [current[:len(headers)]], value_input_option="USER_ENTERED")
    if len(headers) > 26:
        ws.update(f"AA{row_number}:AD{row_number}", [current[26:30]], value_input_option="USER_ENTERED")


def get_next_req_id(req_df: pd.DataFrame) -> str:
    if req_df.empty or "id_requisicao" not in req_df.columns:
        return "RC000001"
    nums = []
    for v in req_df["id_requisicao"].astype(str).tolist():
        v = v.strip().upper()
        if v.startswith("RC"):
            try:
                nums.append(int(v.replace("RC", "")))
            except Exception:
                pass
    nxt = max(nums) + 1 if nums else 1
    return f"RC{nxt:06d}"


def find_row_number_by_id(sh, title: str, id_col_name: str, target_id: str) -> Optional[int]:
    ws = sh.worksheet(title)
    values = ws.get_all_values()
    if not values:
        return None
    headers = values[0]
    if id_col_name not in headers:
        return None
    idx = headers.index(id_col_name)
    for i, row in enumerate(values[1:], start=2):
        if idx < len(row) and safe_str(row[idx]) == safe_str(target_id):
            return i
    return None


def write_log(sh, usuario: str, req_id: str, acao: str, anterior: str, novo: str, obs: str):
    now = now_br()
    append_row(
        sh,
        "log_alteracoes",
        [
            fmt_date(now),
            now.strftime("%H:%M:%S"),
            usuario,
            req_id,
            acao,
            anterior,
            novo,
            obs,
        ],
    )


def load_data():
    sh = get_gsheet()
    ensure_worksheets(sh)
    itens = ws_to_df(sh, "itens")
    usuarios = ws_to_df(sh, "usuarios")
    requisicoes = ws_to_df(sh, "requisicoes")
    fornecedores = ws_to_df(sh, "fornecedores")
    parametros = ws_to_df(sh, "parametros")
    return sh, itens, usuarios, requisicoes, fornecedores, parametros


def coerce_requisicoes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=REQ_COLS)
    for c in REQ_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df.fillna("")
    return df


def coerce_itens(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=ITEM_COLS)
    for c in ITEM_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df.fillna("")
    df = df[df["ativo"].astype(str).str.upper().ne("NAO")]
    return df


def load_users_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=USER_COLS)
    for c in USER_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df.fillna("")
    return df[df["ativo"].astype(str).str.upper().ne("NAO")]


def authenticate(users_df: pd.DataFrame, usuario: str, senha: str) -> Optional[Dict]:
    if users_df.empty:
        return None
    match = users_df[
        (users_df["usuario"].astype(str).str.strip() == usuario.strip()) &
        (users_df["senha"].astype(str).str.strip() == senha.strip())
    ]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    row["profiles"] = parse_profiles(row.get("perfil", ""))
    return row


def mobile_menu_label(name: str) -> str:
    mapping = {
        "Início": "🏠 Início",
        "Nova requisição": "📝 Solicitar",
        "Minhas requisições": "📦 Minhas",
        "Aprovações": "✅ Aprovar",
        "Compras": "🛒 Compras",
        "Recebimento": "📥 Receber",
        "Painel": "📊 Painel",
        "Admin": "⚙️ Admin",
    }
    return mapping.get(name, name)


def render_home(req_df: pd.DataFrame, user: Dict):
    st.subheader("Visão geral")
    df = req_df.copy()
    if not can_any(user, ["admin", "aprovador", "compras", "recebimento"]):
        df = df[df["solicitante"].astype(str) == user["usuario"]]
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_box("Pendentes", str((df["status"] == "PENDENTE_APROVACAO").sum()))
    with c2:
        kpi_box("Comprados", str((df["status"] == "COMPRADO").sum()))
    with c3:
        kpi_box("Recebidos", str((df["status"] == "RECEBIDO").sum()))

    st.markdown("<div class='yv-card'>", unsafe_allow_html=True)
    st.markdown("<div class='yv-card-title'>Últimas requisições</div>", unsafe_allow_html=True)
    if df.empty:
        st.info("Ainda não há requisições.")
    else:
        prev = df.tail(8).iloc[::-1]
        for _, r in prev.iterrows():
            st.markdown(
                f"""
                <div class='yv-card' style='margin:8px 0 0 0;padding:12px;'>
                    <div style='display:flex;justify-content:space-between;gap:10px;align-items:center;'>
                        <div>
                            <div class='yv-card-title'>{safe_str(r["produto"])}</div>
                            <div class='yv-meta'>ID {safe_str(r["id_requisicao"])} | {safe_str(r["quantidade_solicitada"])} {safe_str(r["unidade"])} | {safe_str(r["fornecedor_sugerido"])}</div>
                        </div>
                        <div>{status_badge(safe_str(r["status"]))}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)


def render_new_request(sh, itens_df: pd.DataFrame, req_df: pd.DataFrame, user: Dict):
    st.subheader("Nova requisição")
    if itens_df.empty:
        st.warning("A aba de itens está vazia.")
        return

    search = st.text_input("Buscar item", placeholder="Digite nome, código ou categoria")
    tmp = itens_df.copy()
    if search:
        mask = (
            tmp["produto"].astype(str).str.contains(search, case=False, na=False) |
            tmp["cod_item"].astype(str).str.contains(search, case=False, na=False) |
            tmp["categoria"].astype(str).str.contains(search, case=False, na=False)
        )
        tmp = tmp[mask]

    options = tmp.apply(lambda x: f'{safe_str(x["produto"])} | cód. {safe_str(x["cod_item"])} | {safe_str(x["categoria"])}', axis=1).tolist()
    if not options:
        st.info("Nenhum item encontrado.")
        return

    selected = st.selectbox("Item", options)
    row = tmp.iloc[options.index(selected)]

    st.markdown(
        f"""
        <div class='yv-card'>
            <div class='yv-card-title'>{safe_str(row["produto"])}</div>
            <div class='yv-meta'>Código: {safe_str(row["cod_item"])}<br>Categoria: {safe_str(row["categoria"])}<br>Fornecedor sugerido: {safe_str(row["fornecedor_principal"])}<br>Custo ref.: {safe_str(row["preco_referencia"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    qtd = st.number_input("Quantidade solicitada", min_value=0.01, value=1.0, step=1.0)
    prioridade = st.selectbox("Prioridade", ["NORMAL", "URGENTE", "CRITICA"])
    data_necessaria = st.date_input("Necessário para quando")
    justificativa = st.text_area("Justificativa", placeholder="Explique a necessidade, principalmente em urgências")

    if st.button("Enviar requisição", type="primary", use_container_width=True):
        if prioridade in ["URGENTE", "CRITICA"] and not justificativa.strip():
            st.error("Justificativa obrigatória para prioridade urgente ou crítica.")
            return

        now = now_br()
        req_id = get_next_req_id(req_df)
        append_row(
            sh,
            "requisicoes",
            [
                req_id,
                fmt_date(now),
                now.strftime("%H:%M:%S"),
                user["usuario"],
                user.get("nome", user["usuario"]),
                user.get("setor", ""),
                safe_str(row["cod_item"]),
                safe_str(row["produto"]),
                safe_str(row["categoria"]),
                safe_str(row["unidade"]),
                safe_str(row["fornecedor_principal"]),
                qtd,
                prioridade,
                data_necessaria.strftime("%d/%m/%Y"),
                justificativa,
                "PENDENTE_APROVACAO",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                fmt_dt(now),
            ],
        )
        write_log(sh, user["usuario"], req_id, "nova_requisicao", "", "PENDENTE_APROVACAO", justificativa)
        st.success(f"Requisição {req_id} criada com sucesso.")
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()


def request_card(r: pd.Series):
    entrega = safe_str(r.get("previsao_entrega", ""))
    receb = safe_str(r.get("data_recebimento", ""))
    st.markdown(
        f"""
        <div class='yv-card'>
            <div style='display:flex;justify-content:space-between;gap:10px;align-items:flex-start;'>
                <div style='min-width:0;'>
                    <div class='yv-card-title'>{safe_str(r["produto"])}</div>
                    <div class='yv-meta'>
                        ID {safe_str(r["id_requisicao"])}<br>
                        Solicitante: {safe_str(r["nome_solicitante"])}<br>
                        Quantidade: {safe_str(r["quantidade_solicitada"])} {safe_str(r["unidade"])}<br>
                        Fornecedor: {safe_str(r["fornecedor_final"]) or safe_str(r["fornecedor_sugerido"])}<br>
                        Previsão: {entrega or "-"}<br>
                        Recebimento: {receb or "-"}
                    </div>
                </div>
                <div>{status_badge(safe_str(r["status"]))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_my_requests(req_df: pd.DataFrame, user: Dict):
    st.subheader("Minhas requisições")
    df = req_df[req_df["solicitante"].astype(str) == user["usuario"]].copy()
    status_filter = st.multiselect("Status", STATUS_FLOW, default=[])
    if status_filter:
        df = df[df["status"].isin(status_filter)]
    busca = st.text_input("Buscar por item ou ID")
    if busca:
        df = df[
            df["produto"].astype(str).str.contains(busca, case=False, na=False) |
            df["id_requisicao"].astype(str).str.contains(busca, case=False, na=False)
        ]
    if df.empty:
        st.info("Nenhuma requisição encontrada.")
        return
    for _, r in df.iloc[::-1].iterrows():
        request_card(r)


def render_approvals(sh, req_df: pd.DataFrame, user: Dict):
    if not can_any(user, ["aprovador", "admin"]):
        st.info("Seu perfil não possui acesso a aprovações.")
        return
    st.subheader("Aprovações")
    df = req_df[req_df["status"] == "PENDENTE_APROVACAO"].copy()
    if df.empty:
        st.success("Não há itens pendentes de aprovação.")
        return
    setor = st.selectbox("Filtrar por setor", ["Todos"] + sorted([x for x in df["setor"].astype(str).unique().tolist() if x]))
    if setor != "Todos":
        df = df[df["setor"].astype(str) == setor]

    for _, r in df.iloc[::-1].iterrows():
        request_card(r)
        with st.expander(f"Ações | {safe_str(r['id_requisicao'])}", expanded=False):
            qty_aprov = st.number_input(
                "Quantidade aprovada",
                min_value=0.0,
                value=float(r["quantidade_solicitada"]) if safe_str(r["quantidade_solicitada"]) else 0.0,
                key=f"aprv_qtd_{r['id_requisicao']}",
            )
            obs = st.text_area("Observação da aprovação", key=f"aprv_obs_{r['id_requisicao']}")
            c1, c2 = st.columns(2)
            if c1.button("Aprovar", key=f"btn_ok_{r['id_requisicao']}", use_container_width=True):
                row_n = find_row_number_by_id(sh, "requisicoes", "id_requisicao", safe_str(r["id_requisicao"]))
                if not row_n:
                    st.error("Requisição não encontrada na planilha.")
                    return
                now = now_br()
                update_cell_by_row_number(
                    sh, "requisicoes", row_n, REQ_COLS,
                    {
                        "status": "APROVADO",
                        "aprovador": user["usuario"],
                        "data_aprovacao": fmt_dt(now),
                        "observacao_aprovacao": obs,
                        "quantidade_aprovada": qty_aprov,
                        "ultima_atualizacao": fmt_dt(now),
                    },
                )
                write_log(sh, user["usuario"], safe_str(r["id_requisicao"]), "aprovar", "PENDENTE_APROVACAO", "APROVADO", obs)
                st.success("Requisição aprovada.")
                st.cache_resource.clear()
                st.rerun()

            if c2.button("Reprovar", key=f"btn_no_{r['id_requisicao']}", use_container_width=True):
                if not obs.strip():
                    st.error("Informe a observação para reprovar.")
                    return
                row_n = find_row_number_by_id(sh, "requisicoes", "id_requisicao", safe_str(r["id_requisicao"]))
                now = now_br()
                update_cell_by_row_number(
                    sh, "requisicoes", row_n, REQ_COLS,
                    {
                        "status": "REPROVADO",
                        "aprovador": user["usuario"],
                        "data_aprovacao": fmt_dt(now),
                        "observacao_aprovacao": obs,
                        "ultima_atualizacao": fmt_dt(now),
                    },
                )
                write_log(sh, user["usuario"], safe_str(r["id_requisicao"]), "reprovar", "PENDENTE_APROVACAO", "REPROVADO", obs)
                st.warning("Requisição reprovada.")
                st.cache_resource.clear()
                st.rerun()


def render_buying(sh, req_df: pd.DataFrame, user: Dict):
    if not can_any(user, ["compras", "admin"]):
        st.info("Seu perfil não possui acesso a compras.")
        return
    st.subheader("Compras")
    df = req_df[req_df["status"] == "APROVADO"].copy()
    if df.empty:
        st.success("Não há requisições aprovadas aguardando compra.")
        return
    fornecedor = st.selectbox("Fornecedor", ["Todos"] + sorted([x for x in df["fornecedor_sugerido"].astype(str).unique().tolist() if x]))
    if fornecedor != "Todos":
        df = df[df["fornecedor_sugerido"].astype(str) == fornecedor]

    for _, r in df.iloc[::-1].iterrows():
        request_card(r)
        with st.expander(f"Atualizar compra | {safe_str(r['id_requisicao'])}", expanded=False):
            fornecedor_final = st.text_input("Fornecedor final", value=safe_str(r["fornecedor_sugerido"]), key=f"comp_forn_{r['id_requisicao']}")
            data_compra = st.date_input("Data da compra", key=f"comp_data_{r['id_requisicao']}")
            prev_entrega = st.date_input("Previsão de entrega", key=f"comp_prev_{r['id_requisicao']}")
            obs = st.text_area("Observação compras", key=f"comp_obs_{r['id_requisicao']}")
            if st.button("Marcar como comprado", key=f"comp_btn_{r['id_requisicao']}", type="primary", use_container_width=True):
                row_n = find_row_number_by_id(sh, "requisicoes", "id_requisicao", safe_str(r["id_requisicao"]))
                now = now_br()
                update_cell_by_row_number(
                    sh, "requisicoes", row_n, REQ_COLS,
                    {
                        "status": "COMPRADO",
                        "comprador": user["usuario"],
                        "fornecedor_final": fornecedor_final,
                        "data_compra": data_compra.strftime("%d/%m/%Y"),
                        "previsao_entrega": prev_entrega.strftime("%d/%m/%Y"),
                        "observacao_compras": obs,
                        "ultima_atualizacao": fmt_dt(now),
                    },
                )
                write_log(sh, user["usuario"], safe_str(r["id_requisicao"]), "comprar", "APROVADO", "COMPRADO", obs)
                st.success("Compra registrada.")
                st.cache_resource.clear()
                st.rerun()


def render_receiving(sh, req_df: pd.DataFrame, user: Dict):
    if not can_any(user, ["recebimento", "admin"]):
        st.info("Seu perfil não possui acesso a recebimento.")
        return
    st.subheader("Recebimento")
    df = req_df[req_df["status"] == "COMPRADO"].copy()
    if df.empty:
        st.success("Não há itens aguardando recebimento.")
        return

    only_today = st.checkbox("Mostrar apenas entregas previstas para hoje")
    if only_today:
        today = now_br().strftime("%d/%m/%Y")
        df = df[df["previsao_entrega"].astype(str) == today]

    for _, r in df.iloc[::-1].iterrows():
        request_card(r)
        with st.expander(f"Confirmar recebimento | {safe_str(r['id_requisicao'])}", expanded=False):
            qtd_default = safe_str(r["quantidade_aprovada"]) or safe_str(r["quantidade_solicitada"]) or "0"
            try:
                qtd_default = float(str(qtd_default).replace(",", "."))
            except Exception:
                qtd_default = 0.0
            qtd = st.number_input("Quantidade recebida", min_value=0.0, value=qtd_default, key=f"rec_qtd_{r['id_requisicao']}")
            obs = st.text_area("Observação do recebimento", key=f"rec_obs_{r['id_requisicao']}")
            if st.button("Confirmar recebimento", key=f"rec_btn_{r['id_requisicao']}", type="primary", use_container_width=True):
                row_n = find_row_number_by_id(sh, "requisicoes", "id_requisicao", safe_str(r["id_requisicao"]))
                now = now_br()
                update_cell_by_row_number(
                    sh, "requisicoes", row_n, REQ_COLS,
                    {
                        "status": "RECEBIDO",
                        "recebedor": user["usuario"],
                        "data_recebimento": fmt_dt(now),
                        "quantidade_recebida": qtd,
                        "observacao_recebimento": obs,
                        "ultima_atualizacao": fmt_dt(now),
                    },
                )
                write_log(sh, user["usuario"], safe_str(r["id_requisicao"]), "receber", "COMPRADO", "RECEBIDO", obs)
                st.success("Recebimento confirmado.")
                st.cache_resource.clear()
                st.rerun()


def render_panel(req_df: pd.DataFrame, user: Dict):
    st.subheader("Acompanhamento")
    df = req_df.copy()
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_box("Pendente aprovação", str((df["status"] == "PENDENTE_APROVACAO").sum()))
    with c2:
        kpi_box("Aprovado", str((df["status"] == "APROVADO").sum()))
    with c3:
        kpi_box("Aguardando recebimento", str((df["status"] == "COMPRADO").sum()))

    busca = st.text_input("Buscar pedido por item, fornecedor ou ID")
    status = st.multiselect("Filtrar status", STATUS_FLOW)
    if busca:
        df = df[
            df["produto"].astype(str).str.contains(busca, case=False, na=False) |
            df["fornecedor_sugerido"].astype(str).str.contains(busca, case=False, na=False) |
            df["fornecedor_final"].astype(str).str.contains(busca, case=False, na=False) |
            df["id_requisicao"].astype(str).str.contains(busca, case=False, na=False)
        ]
    if status:
        df = df[df["status"].isin(status)]
    if df.empty:
        st.info("Nenhum resultado encontrado.")
        return
    for _, r in df.iloc[::-1].iterrows():
        request_card(r)


def render_admin(sh, itens_df: pd.DataFrame, users_df: pd.DataFrame, req_df: pd.DataFrame, user: Dict):
    if not has_profile(user, "admin"):
        st.info("Acesso exclusivo do administrador.")
        return
    st.subheader("Admin")
    tabs = st.tabs(["Usuários", "Itens", "Exportação"])

    with tabs[0]:
        st.caption("Cadastre usuários na aba usuarios do Google Sheets ou use o bloco abaixo.")
        with st.form("novo_usuario"):
            c1, c2 = st.columns(2)
            usuario = c1.text_input("Usuário")
            nome = c2.text_input("Nome")
            c3, c4 = st.columns(2)
            senha = c3.text_input("Senha")
            perfil = c4.text_input("Perfis", value="solicitante")
            c5, c6 = st.columns(2)
            setor = c5.text_input("Setor")
            ativo = c6.selectbox("Ativo", ["SIM", "NAO"])
            ok = st.form_submit_button("Adicionar usuário")
        if ok:
            if not usuario.strip() or not senha.strip():
                st.error("Usuário e senha são obrigatórios.")
            elif (users_df["usuario"].astype(str).str.strip() == usuario.strip()).any():
                st.error("Usuário já existe.")
            else:
                append_row(sh, "usuarios", [usuario.strip(), nome.strip(), senha.strip(), perfil.strip(), setor.strip(), ativo])
                st.success("Usuário criado.")
                st.cache_resource.clear()
                st.rerun()
        st.dataframe(users_df, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.caption("Os itens já vêm da sua planilha. Use a aba itens para manutenção completa.")
        st.dataframe(itens_df.head(300), use_container_width=True, hide_index=True)

    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "Baixar requisições em CSV",
                data=req_df.to_csv(index=False).encode("utf-8"),
                file_name="requisicoes_yvora.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with c2:
            st.download_button(
                "Baixar itens em CSV",
                data=itens_df.to_csv(index=False).encode("utf-8"),
                file_name="itens_yvora.csv",
                mime="text/csv",
                use_container_width=True,
            )


def login_screen(users_df: pd.DataFrame):
    st.subheader("Entrar")
    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Acessar", use_container_width=True, type="primary")
    if ok:
        user = authenticate(users_df, usuario, senha)
        if not user:
            st.error("Usuário ou senha inválidos.")
        else:
            st.session_state["yv_user"] = user
            st.rerun()


def logout_button():
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.pop("yv_user", None)
        st.rerun()


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="centered")
    inject_css()
    show_header()

    try:
        sh, itens_df, users_df, req_df, fornecedores_df, parametros_df = load_data()
    except Exception as e:
        st.error(f"Falha ao conectar no Google Sheets: {e}")
        st.info("Confira o arquivo README e o secrets_example.toml para configurar o acesso.")
        return

    itens_df = coerce_itens(itens_df)
    users_df = load_users_df(users_df)
    req_df = coerce_requisicoes(req_df)

    st.sidebar.markdown("### Navegação")
    user = st.session_state.get("yv_user")
    if not user:
        login_screen(users_df)
        st.stop()

    st.sidebar.success(f'{user.get("nome", user["usuario"])}')
    st.sidebar.caption(" | ".join(user.get("profiles", [])) or "sem perfil")
    logout_button()

    menu = ["Início", "Nova requisição", "Minhas requisições", "Painel"]
    if can_any(user, ["aprovador", "admin"]):
        menu.append("Aprovações")
    if can_any(user, ["compras", "admin"]):
        menu.append("Compras")
    if can_any(user, ["recebimento", "admin"]):
        menu.append("Recebimento")
    if has_profile(user, "admin"):
        menu.append("Admin")

    menu_label_map = {mobile_menu_label(x): x for x in menu}
    selected_label = st.sidebar.radio("Ir para", list(menu_label_map.keys()))
    selected = menu_label_map[selected_label]

    if selected == "Início":
        render_home(req_df, user)
    elif selected == "Nova requisição":
        render_new_request(sh, itens_df, req_df, user)
    elif selected == "Minhas requisições":
        render_my_requests(req_df, user)
    elif selected == "Aprovações":
        render_approvals(sh, req_df, user)
    elif selected == "Compras":
        render_buying(sh, req_df, user)
    elif selected == "Recebimento":
        render_receiving(sh, req_df, user)
    elif selected == "Painel":
        render_panel(req_df, user)
    elif selected == "Admin":
        render_admin(sh, itens_df, users_df, req_df, user)


if __name__ == "__main__":
    main()
