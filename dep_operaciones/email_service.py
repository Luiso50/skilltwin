import os
import html as html_module
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

logger = logging.getLogger('skilltwin.email')


def get_smtp_config():
    """Obtiene la configuración SMTP desde variables de entorno."""
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.zoho.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "pass": os.environ.get("SMTP_PASS", ""),
        "from": os.environ.get("SMTP_FROM", "teamskiltwinhq@zohomail.com"),
    }


def send_contact_email(nombre, email, telefono, empresa, interes, mensaje):
    """
    Envía un email de notificación de contacto al admin.
    Retorna (exito, mensaje_error)
    """
    config = get_smtp_config()

    if not config["user"] or not config["pass"]:
        return (
            False,
            "SMTP no configurado. Configura SMTP_USER y SMTP_PASS en variables de entorno.",
        )

    # Escape HTML to prevent injection
    safe_nombre = html_module.escape(str(nombre))
    safe_email = html_module.escape(str(email))
    safe_telefono = html_module.escape(str(telefono or "No proporcionado"))
    safe_empresa = html_module.escape(str(empresa or "No proporcionada"))
    safe_interes = html_module.escape(str(interes or "No especificado"))
    safe_mensaje = html_module.escape(str(mensaje))

    subject = f"[SkillTwin] Nuevo contacto: {safe_nombre}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">SkillTwin</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">Nuevo mensaje de contacto</p>
        </div>

        <div style="padding: 20px; background: #f5f5f5;">
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden;">
                <tr style="background: #e94560; color: white;">
                    <td colspan="2" style="padding: 15px; font-weight: bold;">Datos del Contacto</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee; width: 120px;">Nombre:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{safe_nombre}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Email:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;"><a href="mailto:{safe_email}">{safe_email}</a></td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Teléfono:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{safe_telefono}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Empresa:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{safe_empresa}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Interés:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{safe_interes}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding: 15px; background: #f9f9f9;">
                        <strong>Mensaje:</strong><br><br>
                        <div style="background: white; padding: 10px; border-radius: 4px; border-left: 3px solid #e94560;">
                            {safe_mensaje}
                        </div>
                    </td>
                </tr>
            </table>

            <p style="text-align: center; color: #666; font-size: 12px; margin-top: 20px;">
                Recibido el {datetime.now().strftime("%d/%m/%Y a las %H:%M")} | SkillTwin Platform
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Nuevo contacto en SkillTwin
    ========================
    Nombre: {safe_nombre}
    Email: {safe_email}
    Teléfono: {safe_telefono}
    Empresa: {safe_empresa}
    Interés: {safe_interes}

    Mensaje:
    {safe_mensaje}

    ---
    Recibido el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SkillTwin <{config['from']}>"
        msg["To"] = config["user"]  # Admin receives all contact emails
        msg["Reply-To"] = email

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)

        return True, None

    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación SMTP. Verifica SMTP_USER y SMTP_PASS."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"


def send_confirmation_email(nombre, email):
    """
    Envía un email de confirmación al usuario que se contactó.
    Retorna (exito, mensaje_error)
    """
    config = get_smtp_config()

    if not config["user"] or not config["pass"]:
        return False, "SMTP no configurado"

    safe_nombre = html_module.escape(str(nombre))

    subject = "SkillTwin - Hemos recibido tu mensaje"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">SkillTwin</h1>
        </div>

        <div style="padding: 30px; background: #f5f5f5;">
            <div style="background: white; padding: 25px; border-radius: 8px;">
                <h2 style="color: #1a1a2e; margin-top: 0;">¡Gracias por contactarnos!</h2>

                <p>Hola <strong>{safe_nombre}</strong>,</p>

                <p>Hemos recibido tu mensaje y nos pondremos en contacto contigo en las próximas 24-48 horas hábiles.</p>

                <p>Mientras tanto, puedes explorar nuestra plataforma:</p>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{os.environ.get("SKILLTWIN_PUBLIC_URL", "http://localhost:8000")}" style="background: #e94560; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Visitar SkillTwin</a>
                </div>

                <p style="color: #666; font-size: 12px;">
                    Si tienes preguntas adicionales, responde a este email.
                </p>
            </div>

            <p style="text-align: center; color: #666; font-size: 11px; margin-top: 20px;">
                © 2026 SkillTwin - Gemelos Digitales de Expertos
            </p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SkillTwin <{config['from']}>"
        msg["To"] = email

        msg.attach(
            MIMEText(f"Gracias {safe_nombre}, hemos recibido tu mensaje.", "plain", "utf-8")
        )
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)

        return True, None

    except Exception as e:
        return False, str(e)


def send_password_reset_email(nombre, email, reset_code):
    """
    Envía un email con el código de recuperación de contraseña.
    Retorna (exito, mensaje_error)
    """
    config = get_smtp_config()

    if not config["user"] or not config["pass"]:
        return False, "SMTP no configurado"

    safe_nombre = html_module.escape(str(nombre))

    subject = "SkillTwin - Recuperación de Contraseña"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">SkillTwin</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">Recuperación de Contraseña</p>
        </div>

        <div style="padding: 30px; background: #f5f5f5;">
            <div style="background: white; padding: 25px; border-radius: 8px;">
                <h2 style="color: #1a1a2e; margin-top: 0;">Tu código de recuperación</h2>

                <p>Hola <strong>{safe_nombre}</strong>,</p>

                <p>Recibimos una solicitud para restablecer tu contraseña. Usa el siguiente código:</p>

                <div style="text-align: center; margin: 25px 0;">
                    <div style="background: #f0f0f0; padding: 15px; border-radius: 8px; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1a1a2e;">
                        {reset_code}
                    </div>
                </div>

                <p style="color: #666; font-size: 14px;">Este código expira en <strong>15 minutos</strong>.</p>

                <p style="color: #666; font-size: 14px;">Si no solicitaste este cambio, ignora este email.</p>
            </div>

            <p style="text-align: center; color: #666; font-size: 11px; margin-top: 20px;">
                © 2026 SkillTwin - Gemelos Digitales de Expertos
            </p>
        </div>
    </body>
    </html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"SkillTwin <{config['from']}>"
        msg["To"] = email

        msg.attach(MIMEText(f"Tu código de recuperación es: {reset_code}", "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)

        return True, None

    except Exception as e:
        return False, str(e)


def send_contract_email(cliente_email, cliente_nombre, ruta_contrato, orden_id=None):
    """
    Envía un contrato generado (.docx) como adjunto al cliente.
    Retorna (exito, mensaje_error)
    """
    config = get_smtp_config()

    if not config["user"] or not config["pass"]:
        return False, "SMTP no configurado"

    if not os.path.exists(ruta_contrato):
        return False, f"Archivo de contrato no encontrado: {ruta_contrato}"

    nombre_archivo = os.path.basename(ruta_contrato)
    safe_cliente_nombre = html_module.escape(str(cliente_nombre))
    asunto = f"SkillTwin - Tu Contrato de Licencia {f'#{orden_id}' if orden_id else ''}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">SkillTwin</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">Tu Contrato de Licencia</p>
        </div>

        <div style="padding: 30px; background: #f5f5f5;">
            <div style="background: white; padding: 25px; border-radius: 8px;">
                <h2 style="color: #1a1a2e; margin-top: 0;">¡Contrato Listo!</h2>

                <p>Hola <strong>{safe_cliente_nombre}</strong>,</p>

                <p>Adjunto encontrarás tu contrato de licencia de clon digital.
                   Por favor, revísalo cuidadosamente y conserve una copia para tus registros.</p>

                {'<p><strong>Número de Orden:</strong> ' + orden_id + '</p>' if orden_id else ''}

                <div style="background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4f7bba;">
                    <strong>Archivo adjunto:</strong> {nombre_archivo}
                </div>

                <p style="color: #666; font-size: 14px;">
                    Si tienes alguna pregunta sobre el contrato, responde a este email o contacta nuestro soporte.
                </p>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{os.environ.get('SKILLTWIN_PUBLIC_URL', 'https://skilltwin.es')}"
                       style="background: #e94560; color: white; padding: 12px 25px;
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Visitar SkillTwin
                    </a>
                </div>
            </div>

            <p style="text-align: center; color: #666; font-size: 11px; margin-top: 20px;">
                © 2026 SkillTwin - Gemelos Digitales de Expertos
            </p>
        </div>
    </body>
    </html>
    """

    text_body = f"""
SkillTwin - Tu Contrato de Licencia
====================================

Hola {safe_cliente_nombre},

Adjunto encontrarás tu contrato de licencia de clon digital.
Por favor, revísalo cuidadosamente y conserve una copia para tus registros.

{'Número de Orden: ' + orden_id if orden_id else ''}

Archivo adjunto: {nombre_archivo}

Si tienes alguna pregunta, responde a este email.

---
© 2026 SkillTwin - Gemelos Digitales de Expertos
"""

    try:
        msg = MIMEMultipart()
        msg["Subject"] = asunto
        msg["From"] = f"SkillTwin <{config['from']}>"
        msg["To"] = cliente_email

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Adjuntar el archivo Word
        with open(ruta_contrato, "rb") as f:
            parte = MIMEBase("application", "vnd.openxmlformats-officedocument.wordprocessingml.document")
            parte.set_payload(f.read())
            encoders.encode_base64(parte)
            parte.add_header(
                "Content-Disposition",
                f'attachment; filename="{nombre_archivo}"'
            )
            msg.attach(parte)

        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)

        logger.info(f"Contrato enviado a {cliente_email}")
        return True, None

    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación SMTP. Verifica SMTP_USER y SMTP_PASS."
    except smtplib.SMTPException as e:
        return False, f"Error SMTP: {str(e)}"
    except Exception as e:
        return False, f"Error inesperado: {str(e)}"
