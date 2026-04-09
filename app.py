import os
import math
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager

try:
    import gspread
    from gspread.exceptions import APIError
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None
    APIError = Exception


APP_TITLE = "YVORA | Requisições"
BRAND_BG = "#EFE7DD"
BRAND_BLUE = "#0E2A47"
BRAND_BORDER = "rgba(14,42,71,0.14)"
DEFAULT_SPREADSHEET_ID = "19CH28p4VI4iFv9mRPnRPBMW1MHTqdW0-ZQhghC2_nrk"

COOKIE_PASSWORD = "yvora_requisicoes_cookie_2026"
COOKIE_NAME_USER = "yv_user_login"
COOKIE_NAME_EXP = "yv_user_exp"

REQUIRED_SHEETS = [
    "itens",
    "fornecedores",
    "usuarios",
    "requisicoes",
    "parametros",
    "log_alteracoes",
]

ITEM_COLS = [
    "cod_item",
    "produto",
    "categoria",
    "unidade",
    "fornecedor_principal",
    "contato_fornecedor",
    "preco_referencia",
    "estoque_minimo",
    "ativo",
    "observacao",
]

FORN_COLS = [
    "fornecedor",
    "categoria_principal",
    "contato",
    "telefone",
    "email",
    "prazo_medio_dias",
    "ativo",
    "observacao",
]

USER_COLS = ["usuario", "nome", "senha", "perfil", "setor", "ativo"]

REQ_COLS = [
    "id_requisicao",
    "data_solicitacao",
    "hora_solicitacao",
    "solicitante",
    "nome_solicitante",
    "setor",
    "cod_item",
    "produto",
    "categoria",
    "unidade",
    "fornecedor_sugerido",
    "quantidade_solicitada",
    "prioridade",
    "data_necessaria",
    "justificativa",
    "status",
    "aprovador",
    "data_aprovacao",
    "observacao_aprovacao",
    "quantidade_aprovada",
    "comprador",
    "fornecedor_final",
    "data_compra",
    "previsao_entrega",
    "observacao_compras",
    "recebedor",
    "data_recebimento",
    "quantidade_recebida",
    "observacao_recebimento",
    "nf_recebimento",
    "ultima_atualizacao",
]

LOG_COLS = [
    "data",
    "hora",
    "usuario",
    "id_requisicao",
    "acao",
    "status_anterior",
    "status_novo",
    "observacao",
]

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


def combine_date_time(date_obj, time_obj) -> str:
    return f"{date_obj.strftime('%d/%m/%Y')} {time_obj.strftime('%H:%M')}"


def parse_date_br(text: str) -> Optional[datetime]:
    value = str(text).strip()
    if not value:
        return None

    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            pass
    return None


def only_date_str(text: str) -> str:
    dt = parse_date_br(text)
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def safe_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x).strip()


def safe_float(x, default: float = 0.0) -> float:
    try:
        s = safe_str(x).replace(".", "").replace(",", ".")
        if s == "":
            return default
        return float(s)
    except Exception:
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return default


def show_flash() -> None:
    flash = st.session_state.pop("flash_message", None)
    flash_type = st.session_state.pop("flash_type", "success")
    if flash:
        if flash_type == "success":
            st.success(flash)
        elif flash_type == "warning":
            st.warning(flash)
        else:
            st.error(flash)


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            background: {BRAND_BG} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
        }}
        .stApp {{
            background: {BRAND_BG};
        }}
        .main .block-container {{
            padding-top: 0.7rem;
            padding-bottom: 5rem;
            max-width: 980px;
        }}
        section[data-testid="stSidebar"] {{
            background: rgba(255,255,255,0.52);
            border-right: 1px solid {BRAND_BORDER};
        }}
        h1, h2, h3 {{
            color: {BRAND_BLUE} !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }}
        .yv-card {{
            background: rgba(255,255,255,0.60);
            border: 1px solid {BRAND_BORDER};
            border-radius: 20px;
            padding: 14px;
            margin-bottom: 12px;
        }}
        .yv-card.overdue {{
            border-color: rgba(140,28,28,0.24);
            background: rgba(255,246,246,0.95);
        }}
        .yv-card.today {{
            border-color: rgba(198,169,106,0.32);
            background: rgba(255,251,240,0.95);
        }}
        .yv-toolbar {{
            background: rgba(255,255,255,0.55);
            border: 1px solid {BRAND_BORDER};
            border-radius: 18px;
            padding: 10px 12px;
            margin-bottom: 12px;
        }}
        .yv-card-title {{
            color: {BRAND_BLUE};
            font-weight: 800;
            font-size: 16px;
            margin-bottom: 5px;
        }}
        .yv-meta {{
            color: rgba(14,42,71,0.76);
            font-size: 12px;
            line-height: 1.25rem;
        }}
        .yv-mini {{
            color: rgba(14,42,71,0.62);
            font-size: 11px;
        }}
        .yv-status, .pill {{
            display: inline-block;
            padding: 6px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 900;
            margin-right: 6px;
            margin-top: 4px;
        }}
        .status-pendente_aprovacao {{
            background: rgba(198,169,106,0.22);
            color: #7c5b12;
        }}
        .status-aprovado {{
            background: rgba(14,42,71,0.10);
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
        .pill {{
            border: 1px solid {BRAND_BORDER};
            background: rgba(255,255,255,0.65);
            color: {BRAND_BLUE};
        }}
        .pill-critical {{
            color: #8C1C1C;
            border-color: rgba(140,28,28,0.24);
            background: rgba(255,244,244,0.95);
        }}
        .pill-urgente {{
            color: #9b5d00;
            border-color: rgba(198,169,106,0.32);
            background: rgba(255,250,238,0.95);
        }}
        .kpi {{
            background: rgba(255,255,255,0.50);
            border: 1px solid {BRAND_BORDER};
            border-radius: 18px;
            padding: 12px 14px;
            min-height: 86px;
        }}
        .kpi-label {{
            color: rgba(14,42,71,0.70);
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
            min-height: 2.8rem !important;
            font-weight: 800 !important;
            font-size: 14px !important;
        }}
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{
            border-radius: 14px !important;
        }}
        div[data-baseweb="select"] > div,
        .stDateInput > div > div,
        .stTimeInput > div > div {{
            border-radius: 14px !important;
        }}
        .unit-box {{
            background: rgba(255,255,255,0.55);
            border: 1px dashed {BRAND_BORDER};
            border-radius: 14px;
            padding: 12px;
            color: {BRAND_BLUE};
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .login-wrap {{
            max-width: 430px;
            margin: 0 auto;
        }}
        @media (max-width: 720px) {{
            .main .block-container {{
                padding-left: 0.85rem;
                padding-right: 0.85rem;
                max-width: 100%;
            }}
            .stButton > button {{
                min-height: 3rem !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def maybe_show_logo() -> None:
    for fn in ["yvora_logo.png", "logo.png", "logo.jpg", "yvora_logo.jpg"]:
        if os.path.exists(fn):
            st.image(fn, width=180)
            return


def show_header() -> None:
    left, right = st.columns([1, 3])
    with left:
        maybe_show_logo()
    with right:
        st.markdown(f"<h1>{APP_TITLE}</h1>", unsafe_allow_html=True)


def parse_profiles(profile_text: str) -> List[str]:
    raw = safe_str(profile_text)
    if not raw:
        return []
    parts: List[str] = []
    for p in raw.replace("|", ";").replace(",", ";").split(";"):
        p = safe_str(p).lower()
        if p:
            parts.append(p)
    return list(dict.fromkeys(parts))


def has_profile(user: Dict, profile: str) -> bool:
    return profile.lower() in user.get("profiles", [])


def can_any(user: Dict, profiles: List[str]) -> bool:
    return any(has_profile(user, p) for p in profiles)


def can_manage_items(user: Dict) -> bool:
    return can_any(user, ["admin", "cadastro_itens"])


def can_manage_suppliers(user: Dict) -> bool:
    return can_any(user, ["admin", "cadastro_fornecedores"])


def status_badge(status: str) -> str:
    s = safe_str(status)
    return f"<span class='yv-status status-{s.lower()}'>{s.replace('_', ' ')}</span>"


def priority_badge(priority: str) -> str:
    p = safe_str(priority).upper()
    klass = "pill"
    if p == "CRITICA":
        klass += " pill-critical"
    elif p == "URGENTE":
        klass += " pill-urgente"
    return f"<span class='{klass}'>{p}</span>"


def kpi_box(label: str, value: str) -> None:
    st.markdown(
        f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )


def save_login_cookie(cookies, user: Dict) -> None:
    exp = datetime.now() + timedelta(hours=48)
    cookies[COOKIE_NAME_USER] = user.get("usuario", "")
    cookies[COOKIE_NAME_EXP] = exp.isoformat()
    cookies.save()


def clear_login_cookie(cookies) -> None:
    if COOKIE_NAME_USER in cookies:
        del cookies[COOKIE_NAME_USER]
    if COOKIE_NAME_EXP in cookies:
        del cookies[COOKIE_NAME_EXP]
    cookies.save()


def try_restore_login_from_cookie(cookies, users_df: pd.DataFrame) -> Optional[Dict]:
    usuario = cookies.get(COOKIE_NAME_USER)
    exp_str = cookies.get(COOKIE_NAME_EXP)

    if not usuario or not exp_str:
        return None

    try:
        exp = datetime.fromisoformat(exp_str)
    except Exception:
        return None

    if datetime.now() > exp:
        clear_login_cookie(cookies)
        return None

    match = users_df[
        users_df["usuario"].astype(str).str.strip() == str(usuario).strip()
    ]
    if match.empty:
        clear_login_cookie(cookies)
        return None

    row = match.iloc[0].to_dict()
    row["profiles"] = parse_profiles(row.get("perfil", ""))
    return row


def api_retry(func, retries: int = 3, wait_seconds: float = 1.0):
    last_error = None
    for attempt in range(retries):
        try:
            return func()
        except APIError as e:
            last_error = e
            if attempt == retries - 1:
                raise
            time.sleep(wait_seconds * (attempt + 1))
        except Exception as e:
            last_error = e
            if attempt == retries - 1:
                raise
            time.sleep(wait_seconds * (attempt + 1))
    raise last_error


@st.cache_resource(show_spinner=False)
def get_gsheet():
    if gspread is None or Credentials is None:
        raise RuntimeError("Dependências do Google Sheets não instaladas.")
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Configure gcp_service_account em .streamlit/secrets.toml")

    creds_info = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet_id = st.secrets.get("google_sheets", {}).get(
        "spreadsheet_id", DEFAULT_SPREADSHEET_ID
    )
    return client.open_by_key(spreadsheet_id)


def ensure_worksheets(sh) -> None:
    current = {ws.title for ws in api_retry(lambda: sh.worksheets())}
    for title in REQUIRED_SHEETS:
        if title not in current:
            ws = api_retry(lambda: sh.add_worksheet(title=title, rows=1000, cols=40))
            if title == "itens":
                api_retry(lambda: ws.append_row(ITEM_COLS))
            elif title == "usuarios":
                api_retry(lambda: ws.append_row(USER_COLS))
            elif title == "requisicoes":
                api_retry(lambda: ws.append_row(REQ_COLS))
            elif title == "log_alteracoes":
                api_retry(lambda: ws.append_row(LOG_COLS))
            elif title == "fornecedores":
                api_retry(lambda: ws.append_row(FORN_COLS))
            elif title == "parametros":
                api_retry(lambda: ws.append_row(["tipo", "valor"]))


def worksheet_to_df(sh, title: str, include_row_number: bool = False) -> pd.DataFrame:
    ws = sh.worksheet(title)
    values = api_retry(lambda: ws.get_all_values())
    if not values:
        return pd.DataFrame(columns=(["_sheet_row_number"] if include_row_number else []))

    headers = values[0]
    rows = values[1:]

    if not rows:
        df = pd.DataFrame(columns=headers)
    else:
        normalized_rows = []
        for row in rows:
            if len(row) < len(headers):
                row = row + [""] * (len(headers) - len(row))
            elif len(row) > len(headers):
                row = row[: len(headers)]
            normalized_rows.append(row)
        df = pd.DataFrame(normalized_rows, columns=headers)

    if include_row_number:
        df["_sheet_row_number"] = range(2, len(df) + 2)

    return df.fillna("")


def coerce(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols].fillna("")


@st.cache_data(ttl=90, show_spinner=False)
def load_data_cached():
    sh = get_gsheet()
    ensure_worksheets(sh)

    itens = coerce(worksheet_to_df(sh, "itens"), ITEM_COLS)
    itens = itens[itens["ativo"].astype(str).str.upper().ne("NAO")]

    usuarios = coerce(worksheet_to_df(sh, "usuarios"), USER_COLS)
    usuarios = usuarios[usuarios["ativo"].astype(str).str.upper().ne("NAO")]

    req = coerce(
        worksheet_to_df(sh, "requisicoes", include_row_number=True),
        REQ_COLS + ["_sheet_row_number"],
    )

    forn = coerce(worksheet_to_df(sh, "fornecedores"), FORN_COLS)
    forn = forn[forn["ativo"].astype(str).str.upper().ne("NAO")]

    params = worksheet_to_df(sh, "parametros")
    return itens, usuarios, req, forn, params


def clear_caches() -> None:
    load_data_cached.clear()


def append_row(sh, title: str, row: List) -> None:
    ws = sh.worksheet(title)
    api_retry(lambda: ws.append_row(row, value_input_option="USER_ENTERED"))


def append_rows(sh, title: str, rows: List[List]) -> None:
    if not rows:
        return
    ws = sh.worksheet(title)

    def _run():
        if hasattr(ws, "append_rows"):
            return ws.append_rows(rows, value_input_option="USER_ENTERED")
        for row in rows:
            ws.append_row(row, value_input_option="USER_ENTERED")
        return None

    api_retry(_run)


def update_row_by_number(
    sh,
    title: str,
    row_number: int,
    headers: List[str],
    data: Dict[str, str],
    current_row: Optional[Dict[str, str]] = None,
) -> None:
    ws = sh.worksheet(title)
    merged = {}
    if current_row:
        merged.update({h: safe_str(current_row.get(h, "")) for h in headers})
    for header in headers:
        if header in data:
            merged[header] = data[header]
        elif header not in merged:
            merged[header] = ""

    values = [merged.get(h, "") for h in headers]
    api_retry(
        lambda: ws.update(
            values=[values],
            range_name=f"A{row_number}",
            value_input_option="USER_ENTERED",
        )
    )


def batch_update_rows(
    sh,
    title: str,
    headers: List[str],
    updates: List[Tuple[int, Dict[str, str], Optional[Dict[str, str]]]],
) -> None:
    if not updates:
        return

    ws = sh.worksheet(title)
    batch_payload = []

    for row_number, data, current_row in updates:
        merged = {}
        if current_row:
            merged.update({h: safe_str(current_row.get(h, "")) for h in headers})
        for header in headers:
            if header in data:
                merged[header] = data[header]
            elif header not in merged:
                merged[header] = ""

        values = [merged.get(h, "") for h in headers]
        last_col = chr(ord("A") + len(headers) - 1)
        batch_payload.append(
            {
                "range": f"A{row_number}:{last_col}{row_number}",
                "values": [values],
            }
        )

    def _run():
        if hasattr(ws, "batch_update"):
            return ws.batch_update(batch_payload, value_input_option="USER_ENTERED")
        for item in batch_payload:
            ws.update(
                range_name=item["range"],
                values=item["values"],
                value_input_option="USER_ENTERED",
            )
        return None

    api_retry(_run)


def get_next_req_id(req_df: pd.DataFrame) -> str:
    nums: List[int] = []
    if "id_requisicao" in req_df.columns:
        for v in req_df["id_requisicao"].astype(str).tolist():
            v = v.strip().upper()
            if v.startswith("RC"):
                try:
                    nums.append(int(v.replace("RC", "")))
                except Exception:
                    pass
    nxt = max(nums) + 1 if nums else 1
    return f"RC{nxt:06d}"


def get_next_item_code(itens_df: pd.DataFrame) -> str:
    nums: List[int] = []
    if "cod_item" in itens_df.columns:
        for v in itens_df["cod_item"].astype(str).tolist():
            raw = "".join(ch for ch in v if ch.isdigit())
            if raw:
                try:
                    nums.append(int(raw))
                except Exception:
                    pass
    nxt = max(nums) + 1 if nums else 1
    return f"IT{nxt:05d}"


def find_row_number_by_id(
    req_df: pd.DataFrame,
    target_id: str,
) -> Optional[int]:
    if req_df.empty:
        return None
    match = req_df[req_df["id_requisicao"].astype(str).str.strip() == safe_str(target_id)]
    if match.empty:
        return None
    try:
        return int(match.iloc[0]["_sheet_row_number"])
    except Exception:
        return None


def write_log(
    sh,
    usuario: str,
    req_id: str,
    acao: str,
    anterior: str,
    novo: str,
    obs: str,
) -> None:
    now = now_br()
    append_row(
        sh,
        "log_alteracoes",
        [fmt_date(now), now.strftime("%H:%M:%S"), usuario, req_id, acao, anterior, novo, obs],
    )


def write_logs_batch(
    sh,
    logs: List[Tuple[str, str, str, str, str, str]],
) -> None:
    if not logs:
        return
    now = now_br()
    rows = []
    for usuario, req_id, acao, anterior, novo, obs in logs:
        rows.append([
            fmt_date(now),
            now.strftime("%H:%M:%S"),
            usuario,
            req_id,
            acao,
            anterior,
            novo,
            obs,
        ])
    append_rows(sh, "log_alteracoes", rows)


def authenticate(users_df: pd.DataFrame, usuario: str, senha: str) -> Optional[Dict]:
    match = users_df[
        (users_df["usuario"].astype(str).str.strip() == usuario.strip())
        & (users_df["senha"].astype(str).str.strip() == senha.strip())
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
        "Cadastros": "🗂️ Cadastros",
        "Admin": "⚙️ Admin",
    }
    return mapping.get(name, name)


def delivery_flag(r: pd.Series) -> str:
    if safe_str(r.get("status")) != "COMPRADO":
        return ""

    prev = parse_date_br(r.get("previsao_entrega"))
    if not prev:
        return ""

    today = parse_date_br(fmt_date(now_br()))
    if today is None:
        return ""

    if prev.date() < today.date():
        return "overdue"
    if prev.date() == today.date():
        return "today"
    return ""


def request_card(r: pd.Series, hint: str = "") -> None:
    cls = delivery_flag(r)
    forn = safe_str(r.get("fornecedor_final")) or safe_str(r.get("fornecedor_sugerido"))
    qty = safe_str(r.get("quantidade_aprovada")) or safe_str(r.get("quantidade_solicitada"))

    extra = ""
    if cls == "overdue":
        extra = "<span class='pill pill-critical'>Entrega atrasada</span>"
    elif cls == "today":
        extra = "<span class='pill pill-urgente'>Previsto para hoje</span>"

    nf = safe_str(r.get("nf_recebimento"))

    st.markdown(
        f"""
        <div class='yv-card {cls}'>
            <div style='display:flex;justify-content:space-between;gap:10px;align-items:flex-start;'>
                <div style='min-width:0;'>
                    <div class='yv-card-title'>{safe_str(r["produto"])}</div>
                    <div>{status_badge(safe_str(r["status"]))} {priority_badge(safe_str(r["prioridade"]))} {extra}</div>
                </div>
                <div class='yv-mini'>{safe_str(r["id_requisicao"])}</div>
            </div>
            <div class='yv-meta' style='margin-top:8px;'>
                Quantidade: <b>{qty} {safe_str(r["unidade"])}</b><br>
                Solicitante: {safe_str(r["nome_solicitante"])} | Setor: {safe_str(r["setor"])}<br>
                Fornecedor: {forn}<br>
                Compra: {safe_str(r["data_compra"]) or "-"}<br>
                Previsão: {safe_str(r["previsao_entrega"]) or "-"} | Recebimento: {safe_str(r["data_recebimento"]) or "-"}<br>
                NF: {nf or "-"}
            </div>
            {f"<div class='yv-mini' style='margin-top:8px;'>{hint}</div>" if hint else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home(req_df: pd.DataFrame, user: Dict) -> None:
    st.subheader("Resumo operacional")
    df = req_df.copy()
    if not can_any(user, ["admin", "aprovador", "compras", "recebimento"]):
        df = df[df["solicitante"].astype(str) == user["usuario"]]

    overdue = sum(1 for _, r in df.iterrows() if delivery_flag(r) == "overdue")
    today = sum(1 for _, r in df.iterrows() if delivery_flag(r) == "today")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_box("Pendentes", str((df["status"] == "PENDENTE_APROVACAO").sum()))
    with c2:
        kpi_box("Aprovados", str((df["status"] == "APROVADO").sum()))
    with c3:
        kpi_box("Hoje", str(today))
    with c4:
        kpi_box("Atrasados", str(overdue))

    st.markdown(
        "<div class='yv-toolbar'><b>Ações rápidas</b><div class='yv-meta'>Use o menu lateral para solicitar, aprovar, comprar, receber ou cadastrar.</div></div>",
        unsafe_allow_html=True,
    )

    prev = df.tail(8).iloc[::-1]
    if prev.empty:
        st.info("Ainda não há requisições.")
    else:
        for _, r in prev.iterrows():
            request_card(r)


def render_new_request(
    sh, itens_df: pd.DataFrame, req_df: pd.DataFrame, user: Dict
) -> None:
    st.subheader("Nova requisição")
    show_flash()

    search = st.text_input("Buscar item", placeholder="Nome, código ou categoria")
    tmp = itens_df.copy()
    if search:
        mask = (
            tmp["produto"].astype(str).str.contains(search, case=False, na=False)
            | tmp["cod_item"].astype(str).str.contains(search, case=False, na=False)
            | tmp["categoria"].astype(str).str.contains(search, case=False, na=False)
        )
        tmp = tmp[mask]

    if tmp.empty:
        st.info("Nenhum item encontrado.")
        return

    tmp = tmp.sort_values(["categoria", "produto"])
    labels = tmp.apply(
        lambda x: f'{safe_str(x["produto"])} | {safe_str(x["categoria"])} | cód. {safe_str(x["cod_item"])}',
        axis=1,
    ).tolist()
    selected = st.selectbox("Selecione o item", labels)
    row = tmp.iloc[labels.index(selected)]

    st.markdown(
        f"<div class='yv-card'><div class='yv-card-title'>{safe_str(row['produto'])}</div>"
        f"<div class='yv-meta'>Código: {safe_str(row['cod_item'])}<br>"
        f"Categoria: {safe_str(row['categoria'])}<br>"
        f"Fornecedor sugerido: {safe_str(row['fornecedor_principal'])}<br>"
        f"Custo de referência: {safe_str(row['preco_referencia']) or '-'}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='unit-box'>Unidade de medida: {safe_str(row['unidade']) or '-'}"
        f"<br><span class='yv-mini'>Informação exibida apenas para referência do solicitante.</span></div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    qtd = c1.number_input("Quantidade", min_value=0.01, value=1.0, step=1.0)
    prioridade = c2.selectbox("Prioridade", ["NORMAL", "URGENTE", "CRITICA"])
    data_necessaria = st.date_input("Necessário até")
    justificativa = st.text_area(
        "Justificativa", placeholder="Explique a necessidade, principalmente em urgências"
    )

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
                "",
                fmt_dt(now),
            ],
        )

        write_log(
            sh,
            user["usuario"],
            req_id,
            "nova_requisicao",
            "",
            "PENDENTE_APROVACAO",
            justificativa,
        )

        clear_caches()
        st.session_state["flash_message"] = f"Solicitação {req_id} enviada com sucesso."
        st.session_state["flash_type"] = "success"
        st.rerun()


def cancel_my_request(sh, req_df: pd.DataFrame, req_id: str, user: Dict) -> None:
    row_n = find_row_number_by_id(req_df, req_id)
    if row_n is None:
        st.error("Solicitação não encontrada.")
        return

    current = req_df[req_df["id_requisicao"] == req_id].iloc[0].to_dict()
    now = now_br()
    update_row_by_number(
        sh,
        "requisicoes",
        row_n,
        REQ_COLS,
        {
            "status": "CANCELADO",
            "ultima_atualizacao": fmt_dt(now),
        },
        current_row=current,
    )
    write_log(
        sh,
        user["usuario"],
        req_id,
        "cancelar_solicitacao",
        "PENDENTE_APROVACAO",
        "CANCELADO",
        "Cancelado pelo solicitante",
    )
    clear_caches()
    st.session_state["flash_message"] = f"Solicitação {req_id} cancelada com sucesso."
    st.session_state["flash_type"] = "warning"
    st.rerun()


def render_my_requests(sh, req_df: pd.DataFrame, user: Dict) -> None:
    st.subheader("Minhas requisições")
    show_flash()

    df = req_df[req_df["solicitante"].astype(str) == user["usuario"]].copy()

    c1, c2 = st.columns(2)
    busca = c1.text_input("Buscar item ou ID")
    status_filter = c2.multiselect("Status", STATUS_FLOW)

    if busca:
        df = df[
            df["produto"].astype(str).str.contains(busca, case=False, na=False)
            | df["id_requisicao"].astype(str).str.contains(busca, case=False, na=False)
        ]
    if status_filter:
        df = df[df["status"].isin(status_filter)]

    if df.empty:
        st.info("Nenhuma requisição encontrada.")
        return

    for _, r in df.iloc[::-1].iterrows():
        request_card(r)
        if safe_str(r["status"]) == "PENDENTE_APROVACAO":
            if st.button(
                f"Excluir solicitação {safe_str(r['id_requisicao'])}",
                key=f"cancel_{safe_str(r['id_requisicao'])}",
                use_container_width=True,
            ):
                cancel_my_request(sh=sh, req_df=req_df, req_id=safe_str(r["id_requisicao"]), user=user)


def render_approvals(sh, req_df: pd.DataFrame, user: Dict) -> None:
    if not can_any(user, ["aprovador", "admin"]):
        st.info("Seu perfil não possui acesso a aprovações.")
        return

    st.subheader("Aprovações")
    show_flash()

    df = req_df[req_df["status"].astype(str).str.strip() == "PENDENTE_APROVACAO"].copy()
    if df.empty:
        st.success("Não há itens pendentes de aprovação.")
        return

    c1, c2, c3 = st.columns(3)
    setor = c1.selectbox(
        "Setor",
        ["Todos"] + sorted([x for x in df["setor"].astype(str).unique().tolist() if x]),
    )
    categoria = c2.selectbox(
        "Categoria",
        ["Todas"] + sorted([x for x in df["categoria"].astype(str).unique().tolist() if x]),
    )
    prioridade = c3.selectbox("Prioridade", ["Todas", "NORMAL", "URGENTE", "CRITICA"])

    if setor != "Todos":
        df = df[df["setor"].astype(str) == setor]
    if categoria != "Todas":
        df = df[df["categoria"].astype(str) == categoria]
    if prioridade != "Todas":
        df = df[df["prioridade"].astype(str) == prioridade]

    for _, r in df.iloc[::-1].iterrows():
        request_card(r, "Aprove ou reprove abaixo")
        try:
            qty_default = float(str(r["quantidade_solicitada"]).replace(",", "."))
        except Exception:
            qty_default = 0.0

        form_key = f"approval_form_{r['id_requisicao']}"
        with st.form(form_key):
            c1, c2 = st.columns(2)
            qty_aprov = c1.number_input(
                "Qtd. aprovada",
                min_value=0.0,
                value=qty_default,
                key=f"ap_qtd_{r['id_requisicao']}",
            )
            obs = c2.text_input("Obs. aprovação", key=f"ap_obs_{r['id_requisicao']}")

            b1, b2 = st.columns(2)
            approve = b1.form_submit_button(
                "Aprovar",
                type="primary",
                use_container_width=True,
            )
            reject = b2.form_submit_button(
                "Reprovar",
                use_container_width=True,
            )

        if approve:
            row_n = int(r.get("_sheet_row_number", 0) or 0)
            if row_n <= 1:
                st.error("Requisição não encontrada.")
                return

            now = now_br()
            update_row_by_number(
                sh,
                "requisicoes",
                row_n,
                REQ_COLS,
                {
                    "status": "APROVADO",
                    "aprovador": user["usuario"],
                    "data_aprovacao": fmt_dt(now),
                    "observacao_aprovacao": obs,
                    "quantidade_aprovada": qty_aprov,
                    "ultima_atualizacao": fmt_dt(now),
                },
                current_row=r.to_dict(),
            )
            write_log(
                sh,
                user["usuario"],
                safe_str(r["id_requisicao"]),
                "aprovar",
                "PENDENTE_APROVACAO",
                "APROVADO",
                obs,
            )
            clear_caches()
            st.session_state["flash_message"] = "Requisição aprovada."
            st.session_state["flash_type"] = "success"
            st.rerun()

        if reject:
            if not obs.strip():
                st.error("Informe a observação para reprovar.")
                return

            row_n = int(r.get("_sheet_row_number", 0) or 0)
            if row_n <= 1:
                st.error("Requisição não encontrada.")
                return

            now = now_br()
            update_row_by_number(
                sh,
                "requisicoes",
                row_n,
                REQ_COLS,
                {
                    "status": "REPROVADO",
                    "aprovador": user["usuario"],
                    "data_aprovacao": fmt_dt(now),
                    "observacao_aprovacao": obs,
                    "ultima_atualizacao": fmt_dt(now),
                },
                current_row=r.to_dict(),
            )
            write_log(
                sh,
                user["usuario"],
                safe_str(r["id_requisicao"]),
                "reprovar",
                "PENDENTE_APROVACAO",
                "REPROVADO",
                obs,
            )
            clear_caches()
            st.session_state["flash_message"] = "Requisição reprovada."
            st.session_state["flash_type"] = "warning"
            st.rerun()

        st.divider()


def render_buying(sh, req_df: pd.DataFrame, user: Dict) -> None:
    if not can_any(user, ["compras", "admin"]):
        st.info("Seu perfil não possui acesso a compras.")
        return

    st.subheader("Compras")
    show_flash()

    df = req_df[req_df["status"].astype(str).str.strip() == "APROVADO"].copy()
    if df.empty:
        st.success("Não há requisições aprovadas aguardando compra.")
        return

    c1, c2, c3 = st.columns(3)
    fornecedor = c1.selectbox(
        "Fornecedor",
        ["Todos"] + sorted([x for x in df["fornecedor_sugerido"].astype(str).unique().tolist() if x]),
    )
    categoria = c2.selectbox(
        "Categoria",
        ["Todas"] + sorted([x for x in df["categoria"].astype(str).unique().tolist() if x]),
    )
    prioridade = c3.selectbox("Prioridade", ["Todas", "NORMAL", "URGENTE", "CRITICA"])

    if fornecedor != "Todos":
        df = df[df["fornecedor_sugerido"].astype(str) == fornecedor]
    if categoria != "Todas":
        df = df[df["categoria"].astype(str) == categoria]
    if prioridade != "Todas":
        df = df[df["prioridade"].astype(str) == prioridade]

    for _, r in df.iloc[::-1].iterrows():
        request_card(r, "Registre a compra e a previsão de entrega")

        form_key = f"buy_form_{r['id_requisicao']}"
        with st.form(form_key):
            forn_final = st.text_input(
                "Fornecedor final",
                value=safe_str(r["fornecedor_sugerido"]),
                key=f"buy_forn_{r['id_requisicao']}",
            )

            c1, c2 = st.columns(2)
            data_compra = c1.date_input("Data da compra", key=f"buy_dt_{r['id_requisicao']}")
            hora_compra = c2.time_input("Hora da compra", key=f"buy_tm_{r['id_requisicao']}")

            c3, c4 = st.columns(2)
            prev_data = c3.date_input("Previsão de entrega", key=f"buy_prev_dt_{r['id_requisicao']}")
            prev_hora = c4.time_input("Hora prevista de entrega", key=f"buy_prev_tm_{r['id_requisicao']}")

            obs = st.text_input("Obs. compras", key=f"buy_obs_{r['id_requisicao']}")

            bought = st.form_submit_button(
                "Marcar como comprado",
                type="primary",
                use_container_width=True,
            )

        if bought:
            row_n = int(r.get("_sheet_row_number", 0) or 0)
            if row_n <= 1:
                st.error("Requisição não encontrada.")
                return

            now = now_br()
            update_row_by_number(
                sh,
                "requisicoes",
                row_n,
                REQ_COLS,
                {
                    "status": "COMPRADO",
                    "comprador": user["usuario"],
                    "fornecedor_final": forn_final,
                    "data_compra": combine_date_time(data_compra, hora_compra),
                    "previsao_entrega": combine_date_time(prev_data, prev_hora),
                    "observacao_compras": obs,
                    "ultima_atualizacao": fmt_dt(now),
                },
                current_row=r.to_dict(),
            )
            write_log(
                sh,
                user["usuario"],
                safe_str(r["id_requisicao"]),
                "comprar",
                "APROVADO",
                "COMPRADO",
                obs,
            )
            clear_caches()
            st.session_state["flash_message"] = "Compra registrada com sucesso."
            st.session_state["flash_type"] = "success"
            st.rerun()

        st.divider()


def render_receiving(sh, req_df: pd.DataFrame, user: Dict) -> None:
    if not can_any(user, ["recebimento", "admin"]):
        st.info("Seu perfil não possui acesso a recebimento.")
        return

    st.subheader("Recebimento")
    show_flash()

    df = req_df[req_df["status"] == "COMPRADO"].copy()
    if df.empty:
        st.success("Não há itens aguardando recebimento.")
        return

    c1, c2 = st.columns(2)
    filtro = c1.selectbox("Filtro rápido", ["Todos", "Previstos hoje", "Atrasados"])
    busca = c2.text_input("Buscar item ou fornecedor")

    if filtro == "Previstos hoje":
        hoje = fmt_date(now_br())
        df = df[df["previsao_entrega"].astype(str).apply(only_date_str) == hoje]
    elif filtro == "Atrasados":
        rows = [r for _, r in df.iterrows() if delivery_flag(r) == "overdue"]
        df = pd.DataFrame(rows, columns=df.columns) if rows else pd.DataFrame(columns=df.columns)

    if busca:
        df = df[
            df["produto"].astype(str).str.contains(busca, case=False, na=False)
            | df["fornecedor_final"].astype(str).str.contains(busca, case=False, na=False)
            | df["fornecedor_sugerido"].astype(str).str.contains(busca, case=False, na=False)
            | df["id_requisicao"].astype(str).str.contains(busca, case=False, na=False)
        ]

    if df.empty:
        st.info("Nenhum pedido encontrado.")
        return

    st.markdown("### Recebimento em lote por NF")
    st.caption("Seleciona vários itens e confirma tudo em uma única operação com menos chamadas ao Google Sheets.")

    lote_df = df.copy()
    lote_df["label_lote"] = lote_df.apply(
        lambda r: f"{safe_str(r['id_requisicao'])} | {safe_str(r['produto'])} | {safe_str(r['quantidade_aprovada']) or safe_str(r['quantidade_solicitada'])} {safe_str(r['unidade'])} | {safe_str(r['fornecedor_final']) or safe_str(r['fornecedor_sugerido'])}",
        axis=1,
    )

    with st.form("recebimento_lote_form"):
        selected_labels = st.multiselect(
            "Itens para associar à mesma NF",
            options=lote_df["label_lote"].tolist(),
            default=[],
        )

        c1, c2 = st.columns(2)
        nf_lote = c1.text_input("NF de recebimento")
        obs_lote = c2.text_input("Observação do recebimento em lote")

        qtd_total_recebida = st.checkbox("Receber quantidades aprovadas integralmente", value=True)

        confirm_lote = st.form_submit_button(
            "Confirmar recebimento em lote",
            type="primary",
            use_container_width=True,
        )

    if confirm_lote:
        if not selected_labels:
            st.error("Selecione pelo menos um item.")
            return
        if not nf_lote.strip():
            st.error("Informe a NF de recebimento.")
            return

        selected_rows = lote_df[lote_df["label_lote"].isin(selected_labels)].copy()
        if selected_rows.empty:
            st.error("Nenhum item válido foi encontrado.")
            return

        now = now_br()
        updates = []
        logs = []

        for _, row in selected_rows.iterrows():
            req_id = safe_str(row["id_requisicao"])
            row_n = int(row.get("_sheet_row_number", 0) or 0)
            if row_n <= 1:
                continue

            qty_recebida = (
                safe_str(row["quantidade_aprovada"])
                or safe_str(row["quantidade_solicitada"])
                or "0"
            )

            payload = {
                "status": "RECEBIDO",
                "recebedor": user["usuario"],
                "data_recebimento": fmt_dt(now),
                "observacao_recebimento": obs_lote,
                "nf_recebimento": nf_lote.strip(),
                "ultima_atualizacao": fmt_dt(now),
            }
            if qtd_total_recebida:
                payload["quantidade_recebida"] = qty_recebida

            updates.append((row_n, payload, row.to_dict()))
            logs.append(
                (
                    user["usuario"],
                    req_id,
                    "receber_em_lote",
                    "COMPRADO",
                    "RECEBIDO",
                    f"NF {nf_lote.strip()} | {obs_lote}",
                )
            )

        if not updates:
            st.error("Não foi possível preparar a atualização em lote.")
            return

        batch_update_rows(sh, "requisicoes", REQ_COLS, updates)
        write_logs_batch(sh, logs)

        clear_caches()
        st.session_state["flash_message"] = f"Recebimento em lote confirmado com sucesso para {len(updates)} item(ns)."
        st.session_state["flash_type"] = "success"
        st.rerun()

    st.markdown("---")
    st.markdown("### Recebimento individual")

    for _, r in df.iloc[::-1].iterrows():
        request_card(r, "Confirme o recebimento abaixo")

        qtd_default = safe_float(
            safe_str(r["quantidade_aprovada"]) or safe_str(r["quantidade_solicitada"]) or "0",
            default=0.0,
        )

        form_key = f"receive_form_{r['id_requisicao']}"
        with st.form(form_key):
            c1, c2 = st.columns(2)
            qtd = c1.number_input(
                "Qtd. recebida",
                min_value=0.0,
                value=qtd_default,
                key=f"rec_qtd_{r['id_requisicao']}",
            )
            nf = c2.text_input("NF de recebimento", key=f"rec_nf_{r['id_requisicao']}")

            obs = st.text_input("Obs. recebimento", key=f"rec_obs_{r['id_requisicao']}")

            confirm = st.form_submit_button(
                "Confirmar recebimento",
                type="primary",
                use_container_width=True,
            )

        if confirm:
            if not nf.strip():
                st.error("Informe a NF de recebimento.")
                return

            row_n = int(r.get("_sheet_row_number", 0) or 0)
            if row_n <= 1:
                st.error("Requisição não encontrada.")
                return

            now = now_br()
            update_row_by_number(
                sh,
                "requisicoes",
                row_n,
                REQ_COLS,
                {
                    "status": "RECEBIDO",
                    "recebedor": user["usuario"],
                    "data_recebimento": fmt_dt(now),
                    "quantidade_recebida": qtd,
                    "observacao_recebimento": obs,
                    "nf_recebimento": nf.strip(),
                    "ultima_atualizacao": fmt_dt(now),
                },
                current_row=r.to_dict(),
            )
            write_log(
                sh,
                user["usuario"],
                safe_str(r["id_requisicao"]),
                "receber",
                "COMPRADO",
                "RECEBIDO",
                f"NF {nf.strip()} | {obs}",
            )
            clear_caches()
            st.session_state["flash_message"] = "Recebimento confirmado com sucesso."
            st.session_state["flash_type"] = "success"
            st.rerun()

        st.divider()


def render_panel(req_df: pd.DataFrame, user: Dict) -> None:
    st.subheader("Acompanhamento geral")
    show_flash()

    df = req_df.copy()

    overdue = sum(1 for _, r in df.iterrows() if delivery_flag(r) == "overdue")
    today = sum(1 for _, r in df.iterrows() if delivery_flag(r) == "today")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_box("Pendente", str((df["status"] == "PENDENTE_APROVACAO").sum()))
    with c2:
        kpi_box("Aprovado", str((df["status"] == "APROVADO").sum()))
    with c3:
        kpi_box("Hoje", str(today))
    with c4:
        kpi_box("Atrasado", str(overdue))

    c1, c2 = st.columns(2)
    busca = c1.text_input("Buscar item, fornecedor, ID ou NF")
    status = c2.multiselect("Status", STATUS_FLOW)

    if busca:
        df = df[
            df["produto"].astype(str).str.contains(busca, case=False, na=False)
            | df["fornecedor_sugerido"].astype(str).str.contains(busca, case=False, na=False)
            | df["fornecedor_final"].astype(str).str.contains(busca, case=False, na=False)
            | df["id_requisicao"].astype(str).str.contains(busca, case=False, na=False)
            | df["nf_recebimento"].astype(str).str.contains(busca, case=False, na=False)
        ]
    if status:
        df = df[df["status"].isin(status)]

    if not df.empty:
        st.markdown("#### Histórico por item")
        top_items = df["produto"].astype(str).value_counts().head(5)
        if not top_items.empty:
            st.dataframe(
                top_items.rename("qtd").reset_index().rename(columns={"index": "produto"}),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("#### Histórico por fornecedor")
        forn_series = (
            df["fornecedor_final"].replace("", pd.NA).fillna(df["fornecedor_sugerido"])
        ).astype(str).value_counts().head(5)
        if not forn_series.empty:
            st.dataframe(
                forn_series.rename("qtd").reset_index().rename(columns={"index": "fornecedor"}),
                use_container_width=True,
                hide_index=True,
            )

    if df.empty:
        st.info("Nenhum resultado encontrado.")
        return

    st.markdown("#### Lista de requisições")
    for _, r in df.iloc[::-1].iterrows():
        request_card(r)


def render_registry(sh, itens_df: pd.DataFrame, forn_df: pd.DataFrame, user: Dict) -> None:
    if not (can_manage_items(user) or can_manage_suppliers(user)):
        st.info("Seu perfil não possui acesso aos cadastros.")
        return

    st.subheader("Cadastros")
    show_flash()

    tabs = []
    tab_names = []
    if can_manage_items(user):
        tab_names.append("Novo item")
    if can_manage_suppliers(user):
        tab_names.append("Novo fornecedor")
    tab_names.append("Consulta")

    tabs = st.tabs(tab_names)
    idx = 0

    if can_manage_items(user):
        with tabs[idx]:
            st.markdown("### Cadastro de novo item")
            with st.form("novo_item_form"):
                c1, c2 = st.columns(2)
                cod_item = c1.text_input("Código do item", value=get_next_item_code(itens_df))
                produto = c2.text_input("Produto")

                c3, c4 = st.columns(2)
                categoria = c3.text_input("Categoria")
                unidade = c4.text_input("Unidade")

                fornecedores_opcoes = sorted([x for x in forn_df["fornecedor"].astype(str).tolist() if x])
                fornecedor_principal = st.selectbox(
                    "Fornecedor principal",
                    [""] + fornecedores_opcoes,
                )

                c5, c6 = st.columns(2)
                contato_fornecedor = c5.text_input("Contato do fornecedor")
                preco_referencia = c6.text_input("Preço de referência")

                c7, c8 = st.columns(2)
                estoque_minimo = c7.text_input("Estoque mínimo")
                ativo = c8.selectbox("Ativo", ["SIM", "NAO"])

                observacao = st.text_area("Observação")

                save_item = st.form_submit_button(
                    "Cadastrar item",
                    type="primary",
                    use_container_width=True,
                )

            if save_item:
                if not cod_item.strip() or not produto.strip():
                    st.error("Código e produto são obrigatórios.")
                elif (itens_df["cod_item"].astype(str).str.strip().str.upper() == cod_item.strip().upper()).any():
                    st.error("Já existe um item com esse código.")
                else:
                    append_row(
                        sh,
                        "itens",
                        [
                            cod_item.strip(),
                            produto.strip(),
                            categoria.strip(),
                            unidade.strip(),
                            fornecedor_principal.strip(),
                            contato_fornecedor.strip(),
                            preco_referencia.strip(),
                            estoque_minimo.strip(),
                            ativo,
                            observacao.strip(),
                        ],
                    )
                    clear_caches()
                    st.session_state["flash_message"] = "Item cadastrado com sucesso."
                    st.session_state["flash_type"] = "success"
                    st.rerun()
        idx += 1

    if can_manage_suppliers(user):
        with tabs[idx]:
            st.markdown("### Cadastro de novo fornecedor")
            with st.form("novo_fornecedor_form"):
                fornecedor = st.text_input("Fornecedor")
                c1, c2 = st.columns(2)
                categoria_principal = c1.text_input("Categoria principal")
                contato = c2.text_input("Contato")

                c3, c4 = st.columns(2)
                telefone = c3.text_input("Telefone")
                email = c4.text_input("Email")

                c5, c6 = st.columns(2)
                prazo_medio_dias = c5.text_input("Prazo médio em dias")
                ativo = c6.selectbox("Ativo ", ["SIM", "NAO"])

                observacao = st.text_area("Observação ")

                save_supplier = st.form_submit_button(
                    "Cadastrar fornecedor",
                    type="primary",
                    use_container_width=True,
                )

            if save_supplier:
                if not fornecedor.strip():
                    st.error("Fornecedor é obrigatório.")
                elif (forn_df["fornecedor"].astype(str).str.strip().str.upper() == fornecedor.strip().upper()).any():
                    st.error("Esse fornecedor já existe.")
                else:
                    append_row(
                        sh,
                        "fornecedores",
                        [
                            fornecedor.strip(),
                            categoria_principal.strip(),
                            contato.strip(),
                            telefone.strip(),
                            email.strip(),
                            prazo_medio_dias.strip(),
                            ativo.strip(),
                            observacao.strip(),
                        ],
                    )
                    clear_caches()
                    st.session_state["flash_message"] = "Fornecedor cadastrado com sucesso."
                    st.session_state["flash_type"] = "success"
                    st.rerun()
        idx += 1

    with tabs[idx]:
        c1, c2 = st.columns(2)
        if can_manage_items(user):
            with c1:
                st.markdown("### Itens cadastrados")
                st.dataframe(itens_df, use_container_width=True, hide_index=True)
        if can_manage_suppliers(user):
            with c2:
                st.markdown("### Fornecedores cadastrados")
                st.dataframe(forn_df, use_container_width=True, hide_index=True)


def render_admin(
    sh,
    itens_df: pd.DataFrame,
    users_df: pd.DataFrame,
    req_df: pd.DataFrame,
    forn_df: pd.DataFrame,
    user: Dict,
) -> None:
    if not has_profile(user, "admin"):
        st.info("Acesso exclusivo do administrador.")
        return

    st.subheader("Admin")
    tabs = st.tabs(["Novo usuário", "Usuários", "Itens", "Fornecedores", "Exportação"])

    with tabs[0]:
        with st.form("novo_usuario"):
            c1, c2 = st.columns(2)
            usuario = c1.text_input("Usuário")
            nome = c2.text_input("Nome")
            c3, c4 = st.columns(2)
            senha = c3.text_input("Senha")
            perfil = c4.text_input(
                "Perfis",
                value="solicitante",
                help="Ex.: solicitante;aprovador;compras;recebimento;cadastro_itens;cadastro_fornecedores;admin",
            )
            c5, c6 = st.columns(2)
            setor = c5.text_input("Setor")
            ativo = c6.selectbox("Ativo", ["SIM", "NAO"])
            ok = st.form_submit_button(
                "Adicionar usuário", use_container_width=True, type="primary"
            )

        if ok:
            if not usuario.strip() or not senha.strip():
                st.error("Usuário e senha são obrigatórios.")
            elif (users_df["usuario"].astype(str).str.strip() == usuario.strip()).any():
                st.error("Usuário já existe.")
            else:
                append_row(
                    sh,
                    "usuarios",
                    [usuario.strip(), nome.strip(), senha.strip(), perfil.strip(), setor.strip(), ativo],
                )
                clear_caches()
                st.success("Usuário criado.")
                st.rerun()

    with tabs[1]:
        st.dataframe(users_df, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.dataframe(itens_df, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.dataframe(forn_df, use_container_width=True, hide_index=True)

    with tabs[4]:
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Baixar requisições CSV",
            data=req_df.to_csv(index=False).encode("utf-8"),
            file_name="requisicoes_yvora.csv",
            mime="text/csv",
            use_container_width=True,
        )
        c2.download_button(
            "Baixar itens CSV",
            data=itens_df.to_csv(index=False).encode("utf-8"),
            file_name="itens_yvora.csv",
            mime="text/csv",
            use_container_width=True,
        )
        c3.download_button(
            "Baixar fornecedores CSV",
            data=forn_df.to_csv(index=False).encode("utf-8"),
            file_name="fornecedores_yvora.csv",
            mime="text/csv",
            use_container_width=True,
        )


def login_screen(users_df: pd.DataFrame, cookies) -> None:
    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)
    st.subheader("Acesso")
    with st.form("login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar", use_container_width=True, type="primary")

    if ok:
        user = authenticate(users_df, usuario, senha)
        if not user:
            st.error("Usuário ou senha inválidos.")
        else:
            st.session_state["yv_user"] = user
            save_login_cookie(cookies, user)
            st.session_state["flash_message"] = "Login realizado com sucesso."
            st.session_state["flash_type"] = "success"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def logout_button(cookies) -> None:
    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.pop("yv_user", None)
        clear_login_cookie(cookies)
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🧾", layout="centered")
    inject_css()

    cookies = EncryptedCookieManager(
        prefix="yvora_app_",
        password=COOKIE_PASSWORD,
    )
    if not cookies.ready():
        st.stop()

    show_header()

    try:
        sh = get_gsheet()
        itens_df, users_df, req_df, forn_df, _ = load_data_cached()
    except Exception as e:
        st.error(f"Falha ao conectar no Google Sheets: {e}")
        st.info(
            "Esta versão usa menos leituras e menos chamadas por ação. Se houver oscilação no Google Sheets, recarregue em alguns segundos."
        )
        return

    st.sidebar.markdown("### Acesso")

    user = st.session_state.get("yv_user")
    if not user:
        restored_user = try_restore_login_from_cookie(cookies, users_df)
        if restored_user:
            st.session_state["yv_user"] = restored_user
            user = restored_user

    if not user:
        login_screen(users_df, cookies)
        return

    st.sidebar.success(user.get("nome", user["usuario"]))
    st.sidebar.caption(" | ".join(user.get("profiles", [])) or "sem perfil")
    logout_button(cookies)

    menu = ["Início", "Nova requisição", "Minhas requisições", "Painel"]

    if can_any(user, ["aprovador", "admin"]):
        menu.append("Aprovações")
    if can_any(user, ["compras", "admin"]):
        menu.append("Compras")
    if can_any(user, ["recebimento", "admin"]):
        menu.append("Recebimento")
    if can_manage_items(user) or can_manage_suppliers(user):
        menu.append("Cadastros")
    if has_profile(user, "admin"):
        menu.append("Admin")

    menu_map = {mobile_menu_label(m): m for m in menu}
    selected = menu_map[st.sidebar.radio("Ir para", list(menu_map.keys()))]

    if selected == "Início":
        show_flash()
        render_home(req_df, user)
    elif selected == "Nova requisição":
        render_new_request(sh, itens_df, req_df, user)
    elif selected == "Minhas requisições":
        render_my_requests(sh, req_df, user)
    elif selected == "Painel":
        render_panel(req_df, user)
    elif selected == "Aprovações":
        render_approvals(sh, req_df, user)
    elif selected == "Compras":
        render_buying(sh, req_df, user)
    elif selected == "Recebimento":
        render_receiving(sh, req_df, user)
    elif selected == "Cadastros":
        render_registry(sh, itens_df, forn_df, user)
    elif selected == "Admin":
        render_admin(sh, itens_df, users_df, req_df, forn_df, user)


if __name__ == "__main__":
    main()