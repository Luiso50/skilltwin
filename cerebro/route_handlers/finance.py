import logging
import urllib.parse
from datetime import datetime
from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos
from dep_desarrollo import motor_clonacion

logger = logging.getLogger('cerebro')


def handle_finanzas_data(handler):
    if not handler.require_admin():
        return
    try:
        datos = gestor_financiero.cargar_finanzas()
        handler.send_json_response(datos)
    except Exception as e:
        logger.error(f"Error en finanzas-data: {e}", exc_info=True)
        handler.send_error_response("Error interno del servidor", status=500)


def handle_export_report(handler):
    if not handler.require_admin():
        return
    try:
        query_params = urllib.parse.urlparse(handler.path).query
        params = urllib.parse.parse_qs(query_params)
        report_type = params.get('type', ['clones'])[0]

        if report_type == 'clones':
            datos = motor_clonacion.cargar_datos()
            report_data = {
                "tipo": "reporte_clones",
                "fecha": datetime.now().isoformat(),
                "total_clones": len(datos["clones"]),
                "clones": datos["clones"]
            }
        elif report_type == 'finanzas':
            datos = gestor_financiero.cargar_finanzas()
            report_data = {
                "tipo": "reporte_financiero",
                "fecha": datetime.now().isoformat(),
                "datos": datos
            }
        elif report_type == 'ordenes':
            datos = gestor_ordenes.cargar_ordenes()
            report_data = {
                "tipo": "reporte_ordenes",
                "fecha": datetime.now().isoformat(),
                "total_ordenes": len(datos["ordenes"]),
                "ordenes": datos["ordenes"]
            }
        else:
            handler.send_error_response("Tipo de reporte no válido. Opciones: clones, finanzas, ordenes")
            return

        handler.send_json_response(report_data)
    except Exception as e:
        logger.error(f"Error en /api/export-report: {e}")
        handler.send_error_response(str(e), 500)


def handle_admin_dashboard(handler):
    if not handler.require_admin():
        return
    try:
        stats_pagos = gestor_pagos.obtener_estadisticas_pagos()
        ordenes_data = gestor_ordenes.cargar_ordenes()
        stats_ordenes = {
            "total_ordenes": len(ordenes_data["ordenes"]),
            "ordenes_completadas": len([o for o in ordenes_data["ordenes"].values() if o["estado"] == "completada"])
        }

        handler.send_json_response({
            "pagos": stats_pagos,
            "ordenes": stats_ordenes
        })
    except Exception as e:
        logger.error(f"Error en /api/admin-dashboard: {e}")
        handler.send_error_response(str(e), 500)
