import os
from datetime import datetime
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from dep_legal.header_documento import crear_documento_con_encabezado

CONTRATOS_DIR = os.path.join(os.path.dirname(__file__), "contratos")


def generar_contrato(id_experto, nombre, especialidad, comision=15.0):
    """Genera un acuerdo de servicio legal en formato Word (.docx) para un nuevo experto."""
    # Asegurar que la carpeta de contratos existe
    if not os.path.exists(CONTRATOS_DIR):
        os.makedirs(CONTRATOS_DIR)

    nombre_archivo = f"contrato_{id_experto}.docx"
    ruta_guardado = os.path.join(CONTRATOS_DIR, nombre_archivo)

    try:
        # Crear documento con encabezado estándar SkillTwin
        doc = crear_documento_con_encabezado()

        # ── TÍTULO DEL CONTRATO ──
        titulo = doc.add_heading(
            "ACUERDO DE LICENCIA DE CLON DIGITAL Y SERVICIOS", level=0
        )
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitulo = doc.add_paragraph()
        subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_sub = subtitulo.add_run("SKILLTWIN")
        run_sub.font.size = Pt(14)
        run_sub.font.color.rgb = RGBColor(79, 123, 186)
        run_sub.bold = True

        doc.add_paragraph()  # Espaciado

        # ── FECHA ──
        p_fecha = doc.add_paragraph()
        run_fecha = p_fecha.add_run(
            f"Con fecha de hoy, {datetime.now().strftime('%d/%m/%Y')}, las partes acuerdan:"
        )
        run_fecha.italic = True

        doc.add_paragraph()

        # ── SECCIÓN 1: PARTES ──
        doc.add_heading("1. PARTES CONTRATANTES", level=2)

        p_parte1 = doc.add_paragraph()
        p_parte1.add_run("De una parte: ").bold = True
        p_parte1.add_run(
            "La plataforma SKILLTWIN (en adelante, la \"Plataforma\")."
        )

        p_parte2 = doc.add_paragraph()
        p_parte2.add_run("De otra parte: ").bold = True
        p_parte2.add_run(
            f"D/Dña. {nombre}, especialista en {especialidad} "
            f"(en adelante, el \"Licenciante\")."
        )

        doc.add_paragraph()

        # ── SECCIÓN 2: OBJETO ──
        doc.add_heading("2. OBJETO DEL ACUERDO", level=2)

        doc.add_paragraph(
            "El Licenciante concede una licencia no exclusiva y revocable a la Plataforma "
            "para procesar su base de conocimiento provista y generar un \"Gemelo Digital\" "
            "(Clon de IA) capaz de responder preguntas en su nombre a usuarios de la red."
        )

        doc.add_paragraph()

        # ── SECCIÓN 3: COMISIONES ──
        doc.add_heading("3. COMISIONES Y FACTURACIÓN", level=2)

        comision_texto = [
            "- La Plataforma cobrará una tarifa a los clientes finales por cada consulta realizada al Clon de IA.",
            f"- De los ingresos generados, la Plataforma retendrá un {comision}% en concepto "
            f"de comisión por servicio, mantenimiento de servidores y procesamiento de APIs.",
            f"- El {100 - comision}% restante será transferido al Licenciante de forma mensual.",
        ]

        for linea in comision_texto:
            doc.add_paragraph(linea)

        doc.add_paragraph()

        # ── SECCIÓN 4: PROTECCIÓN DE DATOS ──
        doc.add_heading("4. PROTECCIÓN DE DATOS Y PRIVACIDAD", level=2)

        privacidad = [
            "- La Plataforma se compromete a no compartir, transferir ni utilizar la base "
            "de conocimiento del Licenciante para entrenar otros modelos de IA externos.",
            "- El Licenciante puede solicitar la baja total del servicio y la eliminación "
            "completa de sus datos y de su Clon de IA en cualquier momento con un "
            "preaviso de 48 horas.",
        ]

        for linea in privacidad:
            doc.add_paragraph(linea)

        doc.add_paragraph()

        # ── SECCIÓN 5: RESPONSABILIDAD ──
        doc.add_heading("5. RESPONSABILIDAD", level=2)
        doc.add_paragraph(
            "La Plataforma no será responsable de las opiniones o respuestas generadas "
            "por el Clon de IA, las cuales tienen carácter estrictamente consultivo e informal."
        )

        doc.add_paragraph()
        doc.add_paragraph("Firmado digitalmente en conformidad:")
        doc.add_paragraph()
        doc.add_paragraph(f"Licenciante: {nombre}")
        doc.add_paragraph("Plataforma: SKILLTWIN")

        doc.save(ruta_guardado)
        return ruta_guardado
    except Exception as e:
        print(f"Error generando contrato: {e}")
        return None
