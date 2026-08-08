import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def get_smtp_config():
    """Obtiene la configuración SMTP desde variables de entorno."""
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.zoho.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "pass": os.environ.get("SMTP_PASS", ""),
        "from": os.environ.get("SMTP_FROM", "teamskiltwinhq@zohomail.com")
    }


def send_contact_email(nombre, email, telefono, empresa, interes, mensaje):
    """
    Envía un email de notificación de contacto al admin.
    Retorna (exito, mensaje_error)
    """
    config = get_smtp_config()

    if not config["user"] or not config["pass"]:
        return False, "SMTP no configurado. Configura SMTP_USER y SMTP_PASS en variables de entorno."

    subject = f"[SkillTwin] Nuevo contacto: {nombre}"

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
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{nombre}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Email:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;"><a href="mailto:{email}">{email}</a></td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Teléfono:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{telefono or 'No proporcionado'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Empresa:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{empresa or 'No proporcionada'}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #eee;">Interés:</td>
                    <td style="padding: 10px 15px; border-bottom: 1px solid #eee;">{interes or 'No especificado'}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding: 15px; background: #f9f9f9;">
                        <strong>Mensaje:</strong><br><br>
                        <div style="background: white; padding: 10px; border-radius: 4px; border-left: 3px solid #e94560;">
                            {mensaje}
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
    Nombre: {nombre}
    Email: {email}
    Teléfono: {telefono or 'No proporcionado'}
    Empresa: {empresa or 'No proporcionada'}
    Interés: {interes or 'No especificado'}
    
    Mensaje:
    {mensaje}
    
    ---
    Recibido el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}
    """

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"SkillTwin <{config['from']}>"
        msg['To'] = config['user']  # Admin receives all contact emails
        msg['Reply-To'] = email

        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(config['host'], config['port']) as server:
            server.starttls()
            server.login(config['user'], config['pass'])
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
                
                <p>Hola <strong>{nombre}</strong>,</p>
                
                <p>Hemos recibido tu mensaje y nos pondremos en contacto contigo en las próximas 24-48 horas hábiles.</p>
                
                <p>Mientras tanto, puedes explorar nuestra plataforma:</p>
                
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{os.environ.get('SKILLTWIN_PUBLIC_URL', 'http://localhost:8000')}" style="background: #e94560; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Visitar SkillTwin</a>
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
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"SkillTwin <{config['from']}>"
        msg['To'] = email

        msg.attach(MIMEText(f"Gracias {nombre}, hemos recibido tu mensaje.", 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        with smtplib.SMTP(config['host'], config['port']) as server:
            server.starttls()
            server.login(config['user'], config['pass'])
            server.send_message(msg)

        return True, None

    except Exception as e:
        return False, str(e)
