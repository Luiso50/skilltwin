import os
from datetime import datetime

CONTRATOS_DIR = os.path.join(os.path.dirname(__file__), "contratos")

def generar_contrato(id_experto, nombre, especialidad, comision=15.0):
    """Genera un acuerdo de servicio legal formateado para un nuevo experto."""
    # Asegurar que la carpeta de contratos existe
    if not os.path.exists(CONTRATOS_DIR):
        os.makedirs(CONTRATOS_DIR)
        
    fecha_actual = datetime.now().strftime("%d de %B de %Y")
    nombre_archivo = f"contrato_{id_experto}.txt"
    ruta_guardado = os.path.join(CONTRATOS_DIR, nombre_archivo)
    
    plantilla = f"""======================================================================
ACUERDO DE LICENCIA DE CLON DIGITAL Y SERVICIOS - SKILLTWIN
======================================================================

Con fecha de hoy, {datetime.now().strftime('%Y-%m-%d')}, las partes acuerdan:

1. PARTES CONTRATANTES:
   - De una parte, la plataforma SKILLTWIN (en adelante, la "Plataforma").
   - De otra parte, D/Dña. {nombre}, especialista en {especialidad} (en adelante, el "Licenciante").

2. OBJETO DEL ACUERDO:
   El Licenciante concede una licencia no exclusiva y revocable a la Plataforma 
   para procesar su base de conocimiento provista y generar un "Gemelo Digital" 
   (Clon de IA) capaz de responder preguntas en su nombre a usuarios de la red.

3. COMISIONES Y FACTURACION:
   - La Plataforma cobrara una tarifa a los clientes finales por cada consulta 
     realizada al Clon de IA.
   - De los ingresos generados por el Clon de IA, la Plataforma retendra un 
     {comision}% en concepto de comision por servicio, mantenimiento de servidores
     y procesamiento de APIs.
   - El {100 - comision}% restante sera transferido al Licenciante de forma mensual.

4. PROTECCION DE DATOS Y PRIVACIDAD:
   - La Plataforma se compromete a no compartir, transferir ni utilizar la base 
     de conocimiento del Licenciante para entrenar otros modelos de IA externos.
   - El Licenciante puede solicitar la baja total del servicio y la eliminacion 
     completa de sus datos y de su Clon de IA en cualquier momento con un 
     preaviso de 48 horas.

5. RESPONSABILIDAD:
   La Plataforma no sera responsable de las opiniones o respuestas generadas 
   por el Clon de IA, las cuales tienen caracter estrictamente consultivo e informal.

Firmado digitalmente en conformidad:

[ Firma: SKILLTWIN CORP ]                [ Firma: {nombre.upper()} ]
Representante de la Plataforma            Licenciante del Clon
======================================================================
"""
    
    try:
        with open(ruta_guardado, "w", encoding="utf-8") as f:
            f.write(plantilla)
        print(f"\n[CONTRATO] Contrato de licencia generado con exito!")
        print(f"[ARCHIVO] Guardado en: {ruta_guardado}")
        return ruta_guardado
    except Exception as e:
        print(f"[ERROR] No se pudo generar el contrato: {e}")
        return None

def main():
    print("="*50)
    print("    GENERADOR DE CONTRATOS LEGALES - SKILLTWIN")
    print("="*50)
    
    nombre = input("Nombre completo del profesional: ").strip()
    id_experto = input("ID de usuario único (ej. rsanchez): ").strip().lower()
    especialidad = input("Especialidad o Habilidad a licenciar: ").strip()
    
    comision_str = input("Porcentaje de comision para la plataforma (Defecto: 15%): ").strip()
    comision = 15.0
    if comision_str:
        try:
            comision = float(comision_str)
        except ValueError:
            print("[ALERTA] Entrada invalida, usando 15.0% por defecto.")
            
    if nombre and id_experto and especialidad:
        generar_contrato(id_experto, nombre, especialidad, comision)
    else:
        print("[ALERTA] Todos los campos de texto son obligatorios.")

if __name__ == "__main__":
    main()
