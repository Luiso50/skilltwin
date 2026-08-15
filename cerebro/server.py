                clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
                pregunta = security.sanitize_string(data.get("pregunta", ""), 500)

                if not clon_id or not pregunta:
                    self.send_error_response("clon_id y pregunta son requeridos")
                    return

                # Rate limiting for demo: 3 questions per IP per day
                client_ip = security.get_client_ip(self)
                demo_key = f"demo_{client_ip}"

                today = datetime.now().strftime("%Y-%m-%d")
                if demo_key not in _demo_counters or _demo_counters[demo_key]["date"] != today:
                    _demo_counters[demo_key] = {"date": today, "count": 0}

                if _demo_counters[demo_key]["count"] >= 3:
                    self.send_error_response("Has alcanzado el límite de 3 preguntas diarias. Regístrate para acceso ilimitado.", 429)
                    return

                # Verify clone exists
                datos = motor_clonacion.cargar_datos()
                if clon_id not in datos["clones"]:
                    self.send_error_response("Clon no encontrado")
                    return

                # Generate response