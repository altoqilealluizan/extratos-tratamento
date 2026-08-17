from __future__ import annotations
import io
import re
from datetime import datetime
import pandas as pd
import streamlit as st
from ofxparse import OfxParser

try:
    import pdfplumber

    _PDF_OK = True
except ImportError:
    _PDF_OK = False

# ==============================================================================
# CONFIGURAÇÕES DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Consolidação de Extratos OFX",
    page_icon="💰",
    layout="wide"
)

# ==============================================================================
# DICIONÁRIOS E MAPEAMENTOS
# ==============================================================================
MAPA_RESULTADO = {
    "112075-1": "1.1.1.02.001 BANCO DO BRASIL S/A AG 3174-7 CC 112075",
    "1155": "1.1.1.02.002 CAIXA ECONOMICA FEDERAL AG 1011 CC 1155",
    "010500020567": "1.1.1.02.003 UNILOS AG 0105-8 CC 2056-7",
    "01375801802": "1.1.1.02.004 BANCO SAFRA S/A. AG 0137 CC 580180-2",
    "24357-4": "1.1.1.02.006 UNILOS AG 0105-8 CC 24357-4",
    "30646-0": "1.1.1.02.007 BANCO DO BRASIL S/A AG 3174-7 CC 30646-0",
    "30648-7": "1.1.1.02.008 BANCO DO BRASIL S/A AG 3174-7 CC 30648-7",
    "30552-9": "1.1.1.02.009 BANCO DO BRASIL S/A AG 3174-7 CC 30552-9",
    "30551-0": "1.1.1.02.011 BANCO DO BRASIL S.A  AG 3174-7 CC 30551-0",
    "010600437514": "1.1.1.02.012 CREDCREA AG 0106 CC 43751-4",
    "50744-0": "1.1.1.02.013 UNILOS AG 0105-8 C/C 50744-0",
    "579-1": "1.1.1.02.014 CAIXA ECONOMICA FEDERAL AG 4270 CC 579-1",
    "114080-9": "1.1.1.02.015 BANCO DO BRASIL S/A AG 3174-7 CC 114080-9",
    "26337-0": "1.1.1.02.016 BANCO DO BRASIL S/A AG 3174-7 CC 26337-0",
    "7084-2": "1.1.1.02.017 CAIXA ECONOMICA FEDERAL AG 0408 CC 7084-2",
    "010500030686": "1.1.1.02.018 UNILOS AG 0105-8 CC 3068-6",
    "640-2": "1.1.1.02.019 CAIXA ECONOMICA CAUCAO AG 4270 CC 640-2",
    "661-5": "1.1.1.02.020 CAIXA ECONOMICA FEDERAL AG 4270 CC 661-5",
    "3009017": "1.1.1.02.021 UNICRED AG 1706 CC 300901-7",
    "989877-0": "1.1.1.02.022 BANCO SOFISA AG 0019 CC 989877-0",
    "2050130069426": "1.1.1.02.023 BANCO SANTANDER AG 2050 CC 13006942-6",
    "010617594430": "1.1.1.02.024 CREDCREA AG 0106-6 CC 1759443-0",
    "2050290005049": "1.1.1.02.025 SANTANDER AG 2050 CC 290005049",
    "2260000000640801": "1.1.1.02.026 SICREDI AG 0226 CC 64080-1",
    "01372186694": "1.1.1.02.027 BANCO SAFRA AG 0137 CC VINCULADA 218669-4",
    "159667-5": "1.1.1.02.028 BANCO DO BRASIL S/A AG 16-7 C/C 159667-5",
    "989878-8": "1.1.1.02.029 BANCO SOFISA AG 0019 CC 989878-8",
    "316075": "1.1.1.02.030 UNICRED AG 1214 CC 316075",
    "0005772202819": "1.1.1.02.020 CAIXA ECONOMICA FEDERAL AG 4270 CC 661-5",
    "560586-5": "1.1.1.02.037 BANCO SICOOB AG 3069 CC 560.586-5",
    "0009898788": "1.1.1.02.029 BANCO SOFISA AG 0019 CC 989878-8",
    "010500243574": "",
    "002342546-8": "1.1.1.02.038 BANCO ABC AG 00019 CC 002342546-8",
    "002342555-7": "1.1.1.02.039 BANCO ABC AG 00019 CC 002342555-7",
    "002342557-3": "1.1.1.02.040 BANCO ABC AG 00019 CC 002342557-3",
    "0009898770": "1.1.1.02.022 BANCO SOFISA AG 0019 CC 989877-0",
}

MAPA_SUBSIDIARIA = {
    "112075-1": "S3ENG", "1155": "S3ENG", "010500020567": "S3ENG",
    "01375801802": "S3ENG", "24357-4": "EDUCATION", "30646-0": "INEXT",
    "30648-7": "QIHUB", "30552-9": "INEXT", "30551-0": "EDUCATION",
    "010600437514": "S3ENG", "50744-0": "S3ENG", "579-1": "S3ENG",
    "114080-9": "MN", "26337-0": "MN", "7084-2": "MN",
    "010500030686": "MN", "640-2": "S3ENG", "661-5": "MN",
    "3009017": "S3ENG", "989877-0": "S3ENG", "2050130069426": "S3ENG",
    "010617594430": "QIHUB", "2050290005049": "S3ENG", "2260000000640801": "S3ENG",
    "01372186694": "S3ENG", "159667-5": "QIHUB", "989878-8": "S3ENG",
    "316075": "MN", "0005772202819": "MN", "560586-5": "S3ENG",
    "0009898788": "S3ENG", "010500243574": "",
    "002342546-8": "S3ENG", "002342555-7": "S3ENG", "002342557-3": "S3ENG",
    "0009898770": "S3ENG",
}

MAPA_ID_SUBSIDIARIA = {"S3ENG": 3, "MN": 4, "EDUCATION": 5, "QIHUB": 6}

FILTRO_CNPJ = {"03984954000174", "04305879000130", "41551291000193", "37206151000100"}
FILTRO_TEXTO = ["TRANSFERENCIA ENTRE CONTAS", "LIBERACAO DE CONTA VINCULADA", "RETIRADA POUP.",
                "TRANSF.ENTRE CC - AUTOMATICO", "TRANSFERENCIA ENTRE C/C"]


# ==============================================================================
# FUNÇÕES DE NEGÓCIO E SUPORTE
# ==============================================================================
def definir_conta_transitoria(sub, desc):
    desc = str(desc).upper()
    is_cartao = any(p in desc for p in ["CARTOES", "CARTAO", "CARTAO CREDITO", "ANTECIPACAO RV",
                                        "CIELO", "VISA", "MASTERCARD", "ELO", "AMEX", "AMERICAN EXPRESS",
                                        "REPASSE VENDAS", "RC CIELO"])
    m = {
        "S3ENG": ("1.1.2.01.098 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (CARTÃO) - S3ENG",
                  "1.1.2.01.099 CLIENTE - TRANSITÓRIA DE RECEBIMENTO(YAPAY) - S3ENG"),
        "INEXT": ("1.1.2.01.102 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (CARTÃO) - INEXT",
                  "1.1.2.01.103 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (YAPAY) - INEXT"),
        "EDUCATION": ("1.1.2.01.106 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (CARTÃO) - EDUCATION",
                      "1.1.2.01.107 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (YAPAY) - EDUCATION"),
        "MN": ("1.1.2.01.110 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (CARTÃO) - MN",
               "1.1.2.01.111 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (YAPAY) - MN"),
        "QIHUB": ("1.1.2.01.114 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (CARTÃO) - QIHUB",
                  "1.1.2.01.115 CLIENTE - TRANSITÓRIA DE RECEBIMENTO (YAPAY) - QIHUB"),
    }
    c = m.get(sub)
    if not c:
        return None
    return c[0] if is_cartao else c[1]


def eh_transferencia(desc):
    d = re.sub(r"[.\-/]", "", str(desc).upper())
    for cnpj in FILTRO_CNPJ:
        if cnpj in d:
            return True
    for txt in FILTRO_TEXTO:
        txt_norm = re.sub(r"[.\-/]", "", txt.upper())
        if txt_norm in d:
            return True
    return False


def processar_ofx_files(uploaded_files):
    consolidado = []
    contas_falt, subs_falt = set(), set()
    linhas_ignoradas = 0

    for file in uploaded_files:
        if not file.name.lower().endswith('.ofx'):
            continue
        try:
            # Garante a leitura a partir do início do buffer
            file.seek(0)
            ofx = OfxParser.parse(file)
            rows = []

            for acc in ofx.accounts:
                st.info(f"📁 Arquivo **{file.name}** | Conta ID detectada: `{acc.account_id}`")

                if not hasattr(acc, "statement"):
                    st.warning(f"A conta `{acc.account_id}` no arquivo {file.name} não possui extrato.")
                    continue

                for tx in acc.statement.transactions:
                    rows.append({
                        "Data": tx.date,
                        "Valor": tx.amount,
                        "Descricao": tx.memo,
                        "Conta ID": str(acc.account_id),
                        "ID Transacao": tx.id,
                    })

            if not rows:
                st.warning(f"Nenhuma transação encontrada no arquivo `{file.name}`.")
                continue

            df = pd.DataFrame(rows)
            df["Data"] = pd.to_datetime(df["Data"]).dt.strftime("%Y-%m-%d")
            df["Data_fmt"] = pd.to_datetime(df["Data"]).dt.strftime("%d/%m/%Y")

            # Filtro de transferências
            mask = df["Descricao"].apply(eh_transferencia)
            linhas_ignoradas += mask.sum()
            df = df[~mask].copy()

            if df.empty:
                st.warning(
                    f"Todas as transações de `{file.name}` foram removidas pelo filtro de transferências entre contas.")
                continue

            # Filtro de entradas (somente valores positivos)
            df["Entrada"] = df["Valor"].apply(lambda x: x if x > 0 else None)
            df_in = df[df["Entrada"].notnull()].copy()

            if df_in.empty:
                st.warning(f"O arquivo `{file.name}` não contém débitos positivos/entradas de saldo.")
                continue

            df_in["Resultado"] = df_in["Conta ID"].map(MAPA_RESULTADO)
            df_in["Sub"] = df_in["Conta ID"].map(MAPA_SUBSIDIARIA)

            if df_in["Resultado"].isnull().any():
                faltantes = df_in[df_in["Resultado"].isnull()]["Conta ID"].unique()
                contas_falt.update(faltantes)
                st.error(f"Conta ID não cadastrada em MAPA_RESULTADO: {faltantes}")

            if df_in["Sub"].isnull().any():
                subs_falt.update(df_in[df_in["Sub"].isnull()]["Conta ID"].unique())

            df_d = pd.DataFrame({
                "ID EXTERNO": "Lancamento_" + df_in["Data"] + "_" + df_in["Sub"].astype(str),
                "DATA": df_in["Data_fmt"],
                "MOEDA": "Real",
                "TAXA DE CAMBIO": 1,
                "CONTA": df_in["Resultado"],
                "DEBITO": df_in["Entrada"],
                "CREDITO": "",
                "Descricao da linha": df_in["Descricao"],
                "Memorando": "Recebimentos_" + df_in["Data"],
                "Subsidiaria": df_in["Sub"],
            })

            df_c = df_d.copy()
            df_c["CONTA"] = df_c.apply(lambda r: definir_conta_transitoria(r["Subsidiaria"], r["Descricao da linha"]),
                                       axis=1)
            df_c["CREDITO"] = df_c["DEBITO"]
            df_c["DEBITO"] = ""

            for _df in (df_d, df_c):
                _df["Subsidiaria"] = _df["Subsidiaria"].map(lambda v: MAPA_ID_SUBSIDIARIA.get(v, v))

            consolidado.append(pd.concat([df_d, df_c], ignore_index=True))

        except Exception as e:
            st.error(f"Erro ao processar o arquivo {file.name}: {e}")

    return consolidado, contas_falt, subs_falt, linhas_ignoradas


def processar_pdf_sofisa(uploaded_files):
    if not _PDF_OK:
        return pd.DataFrame()

    TX_PAT = re.compile(r"(\d{2}/\d{2}/\d{2})\s+\d+\s+(RC\s+\S+(?:\s+\S+)*?)\s+\d{6,}\s+([\d.,]+)\s*$", re.MULTILINE)
    blocos = []

    for file in uploaded_files:
        if not (file.name.lower().endswith('.pdf') and "SOFISA" in file.name.upper()):
            continue
        try:
            file.seek(0)
            with pdfplumber.open(file) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)

            m_conta = re.search(r"Conta:\s*([\d]+)", text)
            if not m_conta:
                continue

            conta_id = m_conta.group(1)
            conta_banco = MAPA_RESULTADO.get(conta_id, "")
            sub_nome = MAPA_SUBSIDIARIA.get(conta_id, "")

            if not conta_banco or not sub_nome:
                st.error(f"Conta PDF Sofisa `{conta_id}` não mapeada.")
                continue

            sub_id = MAPA_ID_SUBSIDIARIA.get(sub_nome, sub_nome)
            rows = []

            for m in TX_PAT.finditer(text):
                d_raw, desc, valor_str = m.groups()
                valor = float(valor_str.replace(".", "").replace(",", "."))
                if valor <= 0:
                    continue
                dt = datetime.strptime(d_raw, "%d/%m/%y")
                d_fmt = dt.strftime("%d/%m/%Y")
                d_iso = dt.strftime("%Y-%m-%d")
                desc = desc.strip()
                id_ext = "Lancamento_" + d_iso + "_" + sub_nome + "_SOFISA"
                memo = "Recebimentos_" + d_iso
                trans = definir_conta_transitoria(sub_nome, desc)

                rows.append({"ID EXTERNO": id_ext, "DATA": d_fmt, "MOEDA": "Real", "TAXA DE CAMBIO": 1,
                             "CONTA": conta_banco, "DEBITO": valor, "CREDITO": "", "Descricao da linha": desc,
                             "Memorando": memo, "Subsidiaria": sub_id})
                rows.append({"ID EXTERNO": id_ext, "DATA": d_fmt, "MOEDA": "Real", "TAXA DE CAMBIO": 1,
                             "CONTA": trans, "DEBITO": "", "CREDITO": valor, "Descricao da linha": desc,
                             "Memorando": memo, "Subsidiaria": sub_id})

            if rows:
                blocos.append(pd.DataFrame(rows))
        except Exception as e:
            st.error(f"Erro ao ler PDF Sofisa {file.name}: {e}")

    return pd.concat(blocos, ignore_index=True) if blocos else pd.DataFrame()


# ==============================================================================
# INTERFACE STREAMLIT
# ==============================================================================
st.title("⚡ Consolidação Diária de Extratos (OFX/PDF)")
st.caption("Importe seus extratos bancários para gerar os lançamentos contábeis prontos para importação no ERP.")

uploaded_files = st.file_uploader(
    "Selecione ou arraste um ou mais arquivos OFX (ou PDFs do Sofisa)",
    type=["ofx", "pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    with st.spinner("Processando arquivos..."):
        bloco_ofx, contas_falt, subs_falt, transf_ignoradas = processar_ofx_files(uploaded_files)
        df_sofisa = processar_pdf_sofisa(uploaded_files)

        partes = []
        if bloco_ofx:
            partes.append(pd.concat(bloco_ofx, ignore_index=True))
        if not df_sofisa.empty:
            partes.append(df_sofisa)

        if partes:
            df_final = pd.concat(partes, ignore_index=True)

            deb = pd.to_numeric(df_final["DEBITO"], errors="coerce").sum()
            cred = pd.to_numeric(df_final["CREDITO"], errors="coerce").sum()
            balanceado = round(deb, 2) == round(cred, 2)

            st.write("---")
            st.subheader("📊 Resumo do Processamento")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Linhas Geradas", len(df_final))
            m2.metric("Soma Débitos", f"R$ {deb:,.2f}")
            m3.metric("Soma Créditos", f"R$ {cred:,.2f}")
            m4.metric("Status Balanceamento", "OK ✅" if balanceado else "Erro ❌")

            if not balanceado:
                st.error("🚨 Atenção: A soma dos Débitos difere da soma dos Créditos!")

            if contas_falt or subs_falt:
                st.warning(
                    f"⚠️ **Contas/Subsidiárias pendentes de cadastro:**\n- **Contas:** {list(contas_falt)}\n- **Subsidiárias:** {list(subs_falt)}")

            if transf_ignoradas > 0:
                st.info(
                    f"ℹ️ Foram filtradas **{transf_ignoradas}** movimentações referentes a transferências internas.")

            st.subheader("👁️ Pré-visualização dos Lançamentos")
            st.dataframe(df_final, use_container_width=True)

            st.subheader("📥 Exportar Dados Tratados")
            col_csv, col_excel = st.columns(2)

            # Exportação em CSV
            csv_bytes = df_final.to_csv(index=False, sep=",", encoding="utf-8-sig").encode("utf-8-sig")
            data_hoje = datetime.now().strftime("%Y-%m-%d")
            col_csv.download_button(
                label="📄 Baixar Arquivo CSV",
                data=csv_bytes,
                file_name=f"{data_hoje}_CONSOLIDADO.csv",
                mime="text/csv",
                use_container_width=True
            )

            # Exportação em Excel
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                df_final.to_excel(writer, index=False)

            col_excel.download_button(
                label="📊 Baixar Arquivo Excel (.xlsx)",
                data=buffer_excel.getvalue(),
                file_name=f"{data_hoje}_CONSOLIDADO.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        else:
            st.error(
                "Nenhum lançamento válido foi gerado a partir dos arquivos selecionados. Verifique as mensagens acima para detalhes.")