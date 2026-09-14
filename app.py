import streamlit as st
import pandas as pd
import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Set Page Config
st.set_page_config(
    page_title="Sistem Serah Terima Kasir - RS Adhyaksa Jatim",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1e4d2b; text-align: center; margin-bottom: 5px; }
    .sub-header { font-size: 15px; color: #444; text-align: center; margin-bottom: 20px; }
    .stButton>button { width: 100%; background-color: #1e4d2b; color: white; font-weight: bold; }
    .stAlert { padding: 8px 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🏥 SISTEM INTEGRASI SERAH TERIMA CLOSING KASIR</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Rumah Sakit Adhyaksa Jawa Timur</div>', unsafe_allow_html=True)

# Variables Default
penerimaan_tunai = 0.0
total_non_tunai_bruto = 0.0
total_biaya_admin = 0.0

# Sidebar: File Upload & Configuration
st.sidebar.header("📂 1. Upload Tarikan File SIMRS")
uploaded_file = st.sidebar.file_uploader("Unggah File Excel SIMRS (.xlsx)", type=["xlsx"])

df = None
file_parsed = False

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        file_parsed = True
        st.sidebar.success("✅ File SIMRS berhasil diuraikan secara otomatis!")
    except Exception as e:
        st.sidebar.error(f"❌ Gagal membaca file: {e}")
else:
    st.sidebar.info("📌 Unggah file Excel tarikan SIMRS untuk merekap transaksi & biaya admin EDC secara otomatis.")

# Form Input Parameters
with st.container():
    col1, col2, col3 = st.columns([1.1, 1, 1.1])
    
    with col1:
        st.subheader("📋 Informasi Shift & Tanggal")
        tgl_shift = st.date_input("Tanggal Shift", value=datetime.date.today())
        shift_opt = st.selectbox("Shift Operasional", [
            "PAGI (07.00 - 14.00 WIB)",
            "SIANG (14.00 - 21.00 WIB)",
            "MALAM (21.00 - 07.00 WIB)"
        ])
        petugas_lama = st.text_input("Petugas Shift Lama (Menyerahkan)", "CHORI CHOIRUNNISA'")
        petugas_baru = st.text_input("Petugas Shift Baru (Menerima)", "ABDUL JALIL SANTRI AJI")

    # Processing SIMRS Data if Uploaded
    if file_parsed and df is not None:
        cols_map = {str(c).strip().lower(): c for c in df.columns}
        
        col_tgl = cols_map.get('tanggal transaksi') or cols_map.get('tanggal') or cols_map.get('tgl_transaksi')
        col_total = cols_map.get('total transaksi') or cols_map.get('nominal') or cols_map.get('total') or cols_map.get('jumlah')
        col_jenis = cols_map.get('jenis pembayaran') or cols_map.get('metode pembayaran') or cols_map.get('pembayaran') or cols_map.get('jenis_pembayaran')
        
        col_admin = None
        for key in cols_map.keys():
            if any(term in key for term in ['admin', 'mdr', 'potongan', 'edc', 'fee', 'biaya admin', 'admin_edc']):
                col_admin = cols_map[key]
                break
        
        col_notx = cols_map.get('no. transaksi') or cols_map.get('no_transaksi') or cols_map.get('id')
        
        if col_tgl and col_total and col_jenis:
            df[col_tgl] = pd.to_datetime(df[col_tgl], dayfirst=True, errors='coerce')
            df_filtered = df[df[col_tgl].dt.date == tgl_shift]
            
            if not df_filtered.empty:
                if col_notx:
                    tx_grouped = df_filtered.groupby([col_notx, col_jenis]).first().reset_index()
                else:
                    tx_grouped = df_filtered

                # Filter Cash
                cash_mask = tx_grouped[col_jenis].astype(str).str.upper().str.contains('CASH|TUNAI')
                penerimaan_tunai = float(tx_grouped[cash_mask][col_total].sum())
                
                # Filter Non-Tunai (Gabungan QRIS, EDC, Debit, Kredit, Transfer)
                nontunai_mask = ~cash_mask
                total_non_tunai_bruto = float(tx_grouped[nontunai_mask][col_total].sum())
                
                if col_admin and col_admin in tx_grouped.columns:
                    total_biaya_admin = float(pd.to_numeric(tx_grouped[nontunai_mask][col_admin], errors='coerce').fillna(0).sum())

                st.sidebar.success(f"📊 Berhasil merekap {len(tx_grouped)} transaksi pada {tgl_shift}")
                if col_admin:
                    st.sidebar.info(f"💡 Kolom Admin EDC terdeteksi: `{col_admin}`")

    with col2:
        st.subheader("💰 Transaksi Tunai (Rp)")
        modal_awal = st.number_input("Saldo Awal Kas Shift (Modal Kembalian)", value=1141700.0, step=50000.0)
        penerimaan_tunai = st.number_input("Penerimaan Tunai Pelayanan", value=penerimaan_tunai, step=10000.0)
        piutang_tunai = st.number_input("Pelunasan Piutang Tunai", value=0.0, step=10000.0)
        deposit_tunai = st.number_input("Penerimaan Deposit Tunai", value=0.0, step=10000.0)
        refund_tunai = st.number_input("Dikurangi: Batal / Refund Tunai", value=0.0, step=10000.0)

    with col3:
        st.subheader("💳 Transaksi Non-Tunai (Gabungan)")
        st.caption("ℹ️ Semua transaksi non-tunai (QRIS, Debit, Kredit, Transfer) digabung jadi satu.")
        
        total_non_tunai_bruto = st.number_input("Total Penerimaan Non-Tunai (Bruto)", value=total_non_tunai_bruto, step=50000.0)
        total_biaya_admin = st.number_input("Total Biaya Admin EDC / MDR (Rp)", value=total_biaya_admin, step=1000.0)
        
        total_non_tunai_netto = total_non_tunai_bruto - total_biaya_admin
        st.info(f" Total Netto Non-Tunai: **Rp {total_non_tunai_netto:,.2f}**")

# Cash Breakdown & Calculations
st.markdown("---")
st.subheader("💵 Input Pecahan Uang Fisik Kasir (Cash Count)")
st.caption("Kasir cukup memasukkan jumlah lembar/keping uang fisik di brankas.")

col_pec1, col_pec2, col_pec3, col_pec4 = st.columns(4)

with col_pec1:
    l100 = st.number_input("100.000 (Lembar)", min_value=0, value=8)
    l50 = st.number_input("50.000 (Lembar)", min_value=0, value=6)

with col_pec2:
    l20 = st.number_input("20.000 (Lembar)", min_value=0, value=2)
    l10 = st.number_input("10.000 (Lembar)", min_value=0, value=13)

with col_pec3:
    l5 = st.number_input("5.000 (Lembar)", min_value=0, value=16)
    l2 = st.number_input("2.000 (Lembar)", min_value=0, value=18)

with col_pec4:
    l1 = st.number_input("1.000 (Lembar/Keping)", min_value=0, value=1)
    logam = st.number_input("Total Uang Logam (Rp)", min_value=0.0, value=51700.0, step=100.0)

# Calculations
total_kas_seharusnya = modal_awal + penerimaan_tunai + piutang_tunai + deposit_tunai - refund_tunai
total_uang_fisik = (l100 * 100000) + (l50 * 50000) + (l20 * 20000) + (l10 * 10000) + (l5 * 5000) + (l2 * 2000) + (l1 * 1000) + logam
selisih_kas = total_uang_fisik - total_kas_seharusnya
total_pendapatan_netto = (penerimaan_tunai + piutang_tunai + deposit_tunai - refund_tunai) + total_non_tunai_netto

st.markdown("---")
st.subheader("📊 Hasil Rekonsiliasi Otomatis Shift")
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.metric(label="Total Kas Fisik (Modal+Tunai)", value=f"Rp {total_kas_seharusnya:,.2f}")
with m_col2:
    st.metric(label="Uang Tunai Aktual (Brankas)", value=f"Rp {total_uang_fisik:,.2f}")
with m_col3:
    status_selisih = "PAS / SESUAI" if selisih_kas == 0 else ("LEBIH" if selisih_kas > 0 else "KURANG")
    st.metric(label=f"Selisih Kas ({status_selisih})", value=f"Rp {selisih_kas:,.2f}")
with m_col4:
    st.metric(label="Total Admin EDC / MDR", value=f"Rp {total_biaya_admin:,.2f}")

st.markdown("---")
st.subheader("📝 Catatan & Transaksi Dalam Proses")
catatan_tambahan = st.text_area("Catatan Tambahan / Detail Admin EDC", "Uang lebih Rp 22 karena pasien tidak mau menerima kembalian")

# Generate PDF function
def create_pdf():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, alignment=1, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, alignment=1, spaceAfter=10)
    normal_bold = ParagraphStyle('NormalBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=8)
    
    elements = []
    elements.append(Paragraph("RUMAH SAKIT ADHYAKSA JAWA TIMUR", title_style))
    elements.append(Paragraph("FORMULIR SERAH TERIMA & CLOSING KASIR SHIFT", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e4d2b"), spaceAfter=10))
    
    meta_data = [
        [Paragraph("<b>Tanggal Shift:</b>", normal_style), Paragraph(str(tgl_shift), normal_style), Paragraph("<b>Petugas Menyerahkan:</b>", normal_style), Paragraph(petugas_lama, normal_style)],
        [Paragraph("<b>Shift Operasional:</b>", normal_style), Paragraph(shift_opt, normal_style), Paragraph("<b>Petugas Menerima:</b>", normal_style), Paragraph(petugas_baru, normal_style)]
    ]
    t_meta = Table(meta_data, colWidths=[100, 170, 110, 170])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F2F4F3")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>1. REKAPITULASI PENERIMAAN KAS & NON-TUNAI</b>", normal_bold))
    rekap_data = [
        ["Uraian Penerimaan", "Nominal Bruto (Rp)", "Potongan Admin EDC/MDR (Rp)", "Netto Masuk (Rp)"],
        ["Saldo Awal Kas / Modal Kembalian", f"{modal_awal:,.2f}", "-", f"{modal_awal:,.2f}"],
        ["Penerimaan Tunai Pelayanan", f"{penerimaan_tunai:,.2f}", "-", f"{penerimaan_tunai:,.2f}"],
        ["Total Penerimaan Non-Tunai (QRIS/EDC/Transfer)", f"{total_non_tunai_bruto:,.2f}", f"{total_biaya_admin:,.2f}", f"{total_non_tunai_netto:,.2f}"],
        ["GRAND TOTAL PENDAPATAN SHIFT", f"{(penerimaan_tunai + total_non_tunai_bruto):,.2f}", f"{total_biaya_admin:,.2f}", f"{total_pendapatan_netto:,.2f}"]
    ]
    t_rekap = Table(rekap_data, colWidths=[210, 110, 115, 115])
    t_rekap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e4d2b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#E8F5E9")),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_rekap)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>2. RINCIAN UANG FISIK BRANKAS (CASH COUNT)</b>", normal_bold))
    cash_data = [
        ["Pecahan", "Jumlah", "Total Nominal", "Pecahan", "Jumlah", "Total Nominal"],
        ["Rp 100.000", str(l100), f"Rp {l100*100000:,.2f}", "Rp 5.000", str(l5), f"Rp {l5*5000:,.2f}"],
        ["Rp 50.000", str(l50), f"Rp {l50*50000:,.2f}", "Rp 2.000", str(l2), f"Rp {l2*2000:,.2f}"],
        ["Rp 20.000", str(l20), f"Rp {l20*20000:,.2f}", "Rp 1000", str(l1), f"Rp {l1*1000:,.2f}"],
        ["Rp 10.000", str(l10), f"Rp {l10*10000:,.2f}", "Uang Logam", "-", f"Rp {logam:,.2f}"],
        ["TOTAL UANG FISIK AKTUAL", "", "", "", "", f"Rp {total_uang_fisik:,.2f}"],
        ["KAS SEHARUSNYA (MODAL + TUNAI)", "", "", "", "", f"Rp {total_kas_seharusnya:,.2f}"],
        [f"SELISIH KAS ({status_selisih})", "", "", "", "", f"Rp {selisih_kas:,.2f}"]
    ]
    t_cash = Table(cash_data, colWidths=[90, 50, 135, 90, 50, 135])
    t_cash.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#444444")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (2,-1), 'RIGHT'),
        ('ALIGN', (4,0), (5,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('SPAN', (0,5), (4,5)),
        ('SPAN', (0,6), (4,6)),
        ('SPAN', (0,7), (4,7)),
        ('FONTNAME', (0,5), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,7), (-1,7), colors.HexColor("#FFF3E0")),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_cash)
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph(f"<b>Catatan Kasir:</b> {catatan_tambahan}", normal_style))
    elements.append(Spacer(1, 15))
    
    sig_data = [
        ["Petugas Shift Lama (Menyerahkan)", "Petugas Shift Baru (Menerima)", "Mengetahui (Supervisor/Kasie)"],
        ["\n\n\n________________________", "\n\n\n________________________", "\n\n\n________________________"],
        [petugas_lama, petugas_baru, " ( .................................... ) "]
    ]
    t_sig = Table(sig_data, colWidths=[180, 180, 190])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    elements.append(t_sig)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

st.markdown("---")
st.subheader("🖨️ Cetak & Unduh Dokumen Closing")
pdf_bytes = create_pdf()

st.download_button(
    label="📄 Unduh Form Closing Kasir (PDF)",
    data=pdf_bytes,
    file_name=f"Serah_Terima_Kasir_{tgl_shift}.pdf",
    mime="application/pdf"
)
