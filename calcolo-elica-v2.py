import io
import math
import os
import tkinter as tk
from tkinter import messagebox, ttk

# Configurazione matplotlib per ambiente headless (evita problemi con GUI thread-based di Tkinter)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Importazioni ReportLab (100% Python, nessuna dipendenza C/GTK)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def genera_grafico_elica(input_data, res):
    """Genera un grafico tecnico dell'elica con matplotlib e restituisce un buffer BytesIO."""
    fig, ax = plt.subplots(figsize=(6, 3.2), subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#f4f6f9")

    num_pale = input_data["pale"]
    angoli = [i * (2 * math.pi / num_pale) for i in range(num_pale)]
    
    # Disegno stilizzato delle pale dell'elica in coordinate polari
    r_max = res["diametro_utilizzato"] / 2.0
    theta = [a + d for a in angoli for d in [-0.4, -0.2, 0, 0.2, 0.4]]
    r_vals = [r_max * 0.2, r_max * 0.6, r_max, r_max * 0.6, r_max * 0.2] * num_pale

    for i in range(num_pale):
        idx = i * 5
        t_slice = theta[idx:idx+5]
        r_slice = r_vals[idx:idx+5]
        ax.fill(t_slice, r_slice, color="#007acc", alpha=0.6, edgecolor="#1e222b", linewidth=1.5)

    # Mozzo centrale dell'elica
    ax.fill([0, 2*math.pi], [r_max * 0.22, r_max * 0.22], color="#1e222b")
    
    ax.set_yticklabels([])
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_title(
        f"Schema CAD Elica — {num_pale} Pale | Diametro: {res['diametro_utilizzato']}\" | Passo: {res['passo_rec']}\"",
        fontsize=9,
        fontweight="bold",
        pad=10,
        color="#1e222b"
    )

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=200)
    buffer.seek(0)
    plt.close(fig)
    return buffer


def calcola_elica(
    peso_kg,
    lunghezza_m,
    cv,
    rpm_max,
    riduzione,
    num_pale,
    tipo_carena,
    diametro_input=None,
):
    lunghezza_ft = lunghezza_m * 3.28084
    peso_ton = peso_kg / 1000.0
    rpm_elica = rpm_max / riduzione

    v_carena = 2.43 * math.sqrt(lunghezza_m)

    if tipo_carena == "Dislocante":
        v_target = min(v_carena, 1.34 * math.sqrt(lunghezza_ft))
        slip_base = 0.28
    elif tipo_carena == "Semi-dislocante":
        v_target = 2.1 * math.sqrt(lunghezza_ft)
        slip_base = 0.20
    else:  # Planante
        crouch_stat = 180
        v_target = crouch_stat / math.sqrt(
            (peso_kg * 2.20462) / (cv if cv > 0 else 1)
        )
        slip_base = 0.13

    slip = slip_base - (num_pale - 3) * 0.015
    slip = max(0.08, min(slip, 0.35))

    k_diam = 19.8 - (num_pale - 3) * 0.75
    diametro_calcolato = (k_diam * math.sqrt(cv)) / (rpm_elica**0.2)
    diametro_finale = (
        diametro_input
        if (diametro_input and diametro_input > 0)
        else diametro_calcolato
    )

    v_teorica = v_target / (1.0 - slip)
    passo_calcolato = (v_teorica * 1215.2 * riduzione) / rpm_max

    if diametro_input and diametro_input > 0:
        delta_d = diametro_calcolato - diametro_input
        passo_calcolato += delta_d * 0.8

    spinta_kgf = (
        ((cv * 75 * 0.55) / (v_target * 0.51444)) if v_target > 0 else 0
    )
    coppia_nm = (cv * 716.2 / (rpm_elica if rpm_elica > 0 else 1)) * 9.80665

    return {
        "v_carena": round(v_carena, 2),
        "v_target": round(v_target, 2),
        "slip_pct": round(slip * 100, 1),
        "diametro_rec": round(diametro_calcolato, 2),
        "diametro_utilizzato": round(diametro_finale, 2),
        "passo_rec": round(passo_calcolato, 2),
        "rpm_elica": round(rpm_elica, 0),
        "spinta_kgf": round(spinta_kgf, 1),
        "coppia_nm": round(coppia_nm, 1),
    }


def genera_pdf_report(
    input_data, res, output_filename="Report_Calcolo_Propulsivo.pdf"
):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.HexColor("#007acc"),
        spaceAfter=3,
    )
    sub_style = ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=colors.HexColor("#5c6370"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#1e222b"),
        spaceBefore=10,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5
    )
    bold_cell = ParagraphStyle(
        "BoldCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
    )
    white_bold = ParagraphStyle(
        "WhiteBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.white,
    )

    story.append(
        Paragraph(
            "SECONDO DAVIDE — REPORT TECNICO PROPULSIVO", title_style
        )
    )
    story.append(
        Paragraph(
            "Dimensionamento Idrodinamico dell'Elica & Analisi Prestazionale",
            sub_style,
        )
    )
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#007acc"),
            spaceAfter=12,
        )
    )

    story.append(Paragraph("1. SPECIFICA DATI DI INGRESSO", section_style))
    data_in = [
        [
            Paragraph("Parametro", white_bold),
            Paragraph("Valore", white_bold),
            Paragraph("Unità", white_bold),
            Paragraph("Note Tecniche", white_bold),
        ],
        [
            Paragraph("Dislocamento Operativo", cell_style),
            Paragraph(f"{input_data['peso']:,}", bold_cell),
            Paragraph("kg", cell_style),
            Paragraph("Massa totale in ordine di marcia", cell_style),
        ],
        [
            Paragraph("Lunghezza Galleggiamento", cell_style),
            Paragraph(str(input_data["lunghezza"]), bold_cell),
            Paragraph("m", cell_style),
            Paragraph("Sviluppo della carena bagnata", cell_style),
        ],
        [
            Paragraph("Configurazione Carena", cell_style),
            Paragraph(str(input_data["carena"]), bold_cell),
            Paragraph("--", cell_style),
            Paragraph("Modello Froude / Crouch", cell_style),
        ],
        [
            Paragraph("Potenza Motore", cell_style),
            Paragraph(str(input_data["cv"]), bold_cell),
            Paragraph("CV", cell_style),
            Paragraph("Potenza erogata all'asse", cell_style),
        ],
        [
            Paragraph("Regime Max Motore", cell_style),
            Paragraph(str(input_data["rpm"]), bold_cell),
            Paragraph("RPM", cell_style),
            Paragraph("Giri massimo regime", cell_style),
        ],
        [
            Paragraph("Rapporto Invertitore", cell_style),
            Paragraph(f"{input_data['riduzione']}:1", bold_cell),
            Paragraph("--", cell_style),
            Paragraph(
                f"Regime elica: {res['rpm_elica']:.0f} RPM", cell_style
            ),
        ],
        [
            Paragraph("Numero Pale Elica", cell_style),
            Paragraph(str(input_data["pale"]), bold_cell),
            Paragraph("pale", cell_style),
            Paragraph("Geometria superficie portante", cell_style),
        ],
    ]
    t1 = Table(data_in, colWidths=[130, 70, 50, 250])
    t1.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1e222b"),
                ),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ]
        )
    )
    story.append(t1)
    story.append(Spacer(1, 10))

    story.append(
        Paragraph("2. RISULTATI DEL CALCOLO PROPULSIVO", section_style)
    )
    data_res = [
        [
            Paragraph("Grandezza Calcolata", white_bold),
            Paragraph("Valore", white_bold),
            Paragraph("Unità", white_bold),
            Paragraph("Descrizione Tecnica", white_bold),
        ],
        [
            Paragraph("Passo Elica Consigliato", bold_cell),
            Paragraph(f"<b>{res['passo_rec']}\"</b>", bold_cell),
            Paragraph("in", cell_style),
            Paragraph("Pollici per rivoluzione (Pitch)", cell_style),
        ],
        [
            Paragraph("Diametro Consigliato", bold_cell),
            Paragraph(f"<b>{res['diametro_utilizzato']}\"</b>", bold_cell),
            Paragraph("in", cell_style),
            Paragraph(f"Teorico: {res['diametro_rec']}\"", cell_style),
        ],
        [
            Paragraph("Velocità Stimata Scafo", cell_style),
            Paragraph(str(res["v_target"]), bold_cell),
            Paragraph("nodi", cell_style),
            Paragraph("Velocità operativa prevista", cell_style),
        ],
        [
            Paragraph("Velocità Limite Carena", cell_style),
            Paragraph(str(res["v_carena"]), bold_cell),
            Paragraph("nodi", cell_style),
            Paragraph("Soglia limite regime dislocante", cell_style),
        ],
        [
            Paragraph("Scorrimento (Slip)", cell_style),
            Paragraph(str(res["slip_pct"]), bold_cell),
            Paragraph("%", cell_style),
            Paragraph("Perdita idrodinamica stimata", cell_style),
        ],
        [
            Paragraph("Spinta Statica / Dinamica", cell_style),
            Paragraph(str(res["spinta_kgf"]), bold_cell),
            Paragraph("kgf", cell_style),
            Paragraph("Spinta utile all'asse", cell_style),
        ],
        [
            Paragraph("Coppia all'Asse Elica", cell_style),
            Paragraph(str(res["coppia_nm"]), bold_cell),
            Paragraph("Nm", cell_style),
            Paragraph("Coppia trasmissibile", cell_style),
        ],
    ]
    t2 = Table(data_res, colWidths=[130, 70, 50, 250])
    t2.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#007acc"),
                ),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ]
        )
    )
    story.append(t2)
    story.append(Spacer(1, 10))

    # Inserimento della rappresentazione grafica dell'elica generata con Matplotlib
    story.append(Paragraph("3. SCHEMA GEOMETRICO DELL'ELICA", section_style))
    img_buffer = genera_grafico_elica(input_data, res)
    img_flowable = RLImage(img_buffer, width=450, height=240)
    story.append(img_flowable)

    doc.build(story)


class AppElicaIngegneristica(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("SECONDO DAVIDE — Calcolo Propulsivo & Eliche Navali")
        self.geometry("800x680")
        self.resizable(False, False)

        self.COLOR_BG = "#1e222b"
        self.COLOR_PANEL = "#282c34"
        self.COLOR_ACCENT = "#007acc"
        self.COLOR_TEXT = "#abb2bf"
        self.COLOR_WHITE = "#ffffff"
        self.COLOR_GREEN = "#98c379"
        self.COLOR_BORDER = "#3e4451"

        self.configure(bg=self.COLOR_BG)
        self.latest_res = None
        self.latest_inputs = None

        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.COLOR_PANEL)
        style.configure(
            "TLabel",
            background=self.COLOR_PANEL,
            foreground=self.COLOR_TEXT,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Header.TLabel",
            background=self.COLOR_BG,
            foreground=self.COLOR_WHITE,
            font=("Segoe UI", 14, "bold"),
        )
        style.configure(
            "SubHeader.TLabel",
            background=self.COLOR_PANEL,
            foreground=self.COLOR_ACCENT,
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "OutputVal.TLabel",
            background=self.COLOR_PANEL,
            foreground=self.COLOR_GREEN,
            font=("Consolas", 11, "bold"),
        )
        style.configure(
            "TEntry",
            fieldbackground="#1b1d23",
            foreground=self.COLOR_WHITE,
            insertcolor=self.COLOR_WHITE,
            bordercolor=self.COLOR_BORDER,
        )
        style.configure(
            "TCombobox",
            fieldbackground="#1b1d23",
            background=self.COLOR_PANEL,
            foreground=self.COLOR_WHITE,
            arrowcolor=self.COLOR_WHITE,
        )
        style.configure(
            "Calc.TButton",
            font=("Segoe UI", 10, "bold"),
            background=self.COLOR_ACCENT,
            foreground=self.COLOR_WHITE,
            borderwidth=0,
        )
        style.map("Calc.TButton", background=[("active", "#005999")])
        style.configure(
            "Pdf.TButton",
            font=("Segoe UI", 9, "bold"),
            background="#98c379",
            foreground="#1e222b",
            borderwidth=0,
        )
        style.map("Pdf.TButton", background=[("active", "#7eb05d")])

    def _create_widgets(self):
        header_frame = tk.Frame(self, bg=self.COLOR_BG)
        header_frame.pack(fill="x", padx=20, pady=15)

        ttk.Label(
            header_frame,
            text="SECONDO DAVIDE — DIMENSIONAMENTO ELICHE",
            style="Header.TLabel",
        ).pack(anchor="w")
        tk.Label(
            header_frame,
            text=(
                "Modulo di Calcolo Idrodinamico & Esportazione Scheda Tecnica"
            ),
            bg=self.COLOR_BG,
            fg="#5c6370",
            font=("Segoe UI", 9, "italic"),
        ).pack(anchor="w")

        main_frame = tk.Frame(self, bg=self.COLOR_BG)
        main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        input_panel = ttk.Frame(
            main_frame, style="TFrame", relief="solid", borderwidth=1
        )
        input_panel.pack(
            side="left", fill="both", expand=True, padx=(0, 10), pady=10
        )

        ttk.Label(
            input_panel, text="PARAMETRI DI PROGETTO", style="SubHeader.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 10))

        self.inputs = {}
        fields = [
            ("Dislocamento (kg):", "peso", "4200"),
            ("Lunghezza Galleggiamento (m):", "lunghezza", "9.5"),
            (
                "Tipo di Carena:",
                "carena",
                ["Planante", "Semi-dislocante", "Dislocante"],
            ),
            ("Potenza Motore (CV):", "cv", "260"),
            ("Regime Max Motore (RPM):", "rpm", "3800"),
            ("Rapporto Invertitore (x:1):", "riduzione", "2.0"),
            ("Numero Pale Elica:", "pale", ["3", "4", "5"]),
            ("Diametro Imposto (in) [Opz.]:", "diametro", ""),
        ]

        for i, field in enumerate(fields, start=1):
            ttk.Label(input_panel, text=field[0]).grid(
                row=i, column=0, sticky="w", padx=15, pady=4
            )
            if isinstance(field[2], list):
                combo = ttk.Combobox(
                    input_panel, values=field[2], state="readonly", width=16
                )
                combo.current(0)
                combo.grid(row=i, column=1, sticky="e", padx=15, pady=4)
                self.inputs[field[1]] = combo
            else:
                entry = ttk.Entry(input_panel, width=18)
                entry.insert(0, field[2])
                entry.grid(row=i, column=1, sticky="e", padx=15, pady=4)
                self.inputs[field[1]] = entry

        ttk.Button(
            input_panel,
            text="ESEGUI CALCOLO",
            style="Calc.TButton",
            command=self._on_calcola,
        ).grid(
            row=len(fields) + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=15,
            pady=(15, 10),
        )

        output_panel = ttk.Frame(
            main_frame, style="TFrame", relief="solid", borderwidth=1
        )
        output_panel.pack(
            side="right", fill="both", expand=True, padx=(10, 0), pady=10
        )

        ttk.Label(
            output_panel,
            text="RISULTATI IDRODINAMICI",
            style="SubHeader.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(10, 10))

        self.outputs = {}
        out_fields = [
            ("Passo Elica Consigliato:", "passo_rec", "in"),
            ("Diametro Elica Consigliato:", "diametro_rec", "in"),
            ("Velocità Stimata Scafo:", "v_target", "nodi"),
            ("Velocità Limite Carena:", "v_carena", "nodi"),
            ("Regresso Ipotizzato (Slip):", "slip_pct", "%"),
            ("Regime Rotazione Elica:", "rpm_elica", "RPM"),
            ("Spinta Teorica all'Asse:", "spinta_kgf", "kgf"),
            ("Coppia all'Asse Elica:", "coppia_nm", "Nm"),
        ]

        for i, field in enumerate(out_fields, start=1):
            ttk.Label(output_panel, text=field[0]).grid(
                row=i, column=0, sticky="w", padx=15, pady=5
            )
            val_frame = ttk.Frame(output_panel)
            val_frame.grid(row=i, column=1, sticky="e", padx=15, pady=5)
            val_lbl = ttk.Label(val_frame, text="--", style="OutputVal.TLabel")
            val_lbl.pack(side="left")
            ttk.Label(
                val_frame,
                text=f" {field[2]}",
                font=("Segoe UI", 8),
                foreground="#5c6370",
            ).pack(side="left")
            self.outputs[field[1]] = val_lbl

        self.btn_pdf = ttk.Button(
            output_panel,
            text="ESPORTA REPORT PDF",
            style="Pdf.TButton",
            command=self._on_esporta_pdf,
        )
        self.btn_pdf.grid(
            row=len(out_fields) + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=15,
            pady=(15, 10),
        )

    def _on_calcola(self):
        try:
            peso = float(self.inputs["peso"].get().replace(",", "."))
            lunghezza = float(self.inputs["lunghezza"].get().replace(",", "."))
            cv = float(self.inputs["cv"].get().replace(",", "."))
            rpm = float(self.inputs["rpm"].get().replace(",", "."))
            riduzione = float(self.inputs["riduzione"].get().replace(",", "."))
            carena = self.inputs["carena"].get()
            pale = int(self.inputs["pale"].get())

            diam_str = self.inputs["diametro"].get().strip()
            diametro = float(diam_str.replace(",", ".")) if diam_str else None

            res = calcola_elica(
                peso, lunghezza, cv, rpm, riduzione, pale, carena, diametro
            )
            self.latest_res = res
            self.latest_inputs = {
                "peso": peso,
                "lunghezza": lunghezza,
                "cv": cv,
                "rpm": rpm,
                "riduzione": riduzione,
                "carena": carena,
                "pale": pale,
                "diametro": diametro,
            }

            for key, widget in self.outputs.items():
                widget.config(text=str(res[key]))

        except Exception as e:
            messagebox.showerror(
                "Errore Input", f"Verifica i dati inseriti: {e}"
            )

    def _on_esporta_pdf(self):
        if not self.latest_res:
            self._on_calcola()
            if not self.latest_res:
                return

        try:
            filename = "Report_Calcolo_Propulsivo_Secondo_Davide.pdf"
            genera_pdf_report(self.latest_inputs, self.latest_res, filename)
            messagebox.showinfo(
                "Report Generato",
                f"Il report PDF con schema grafico è stato generato con successo:\n{os.path.abspath(filename)}",
            )
        except Exception as e:
            messagebox.showerror(
                "Errore Esportazione PDF", f"Impossibile creare il PDF: {e}"
            )


if __name__ == "__main__":
    app = AppElicaIngegneristica()
    app.mainloop()