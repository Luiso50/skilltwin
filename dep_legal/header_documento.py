
    doc.add_heading("Documento de Prueba", level=1)
    doc.add_paragraph("Este es un documento de prueba con encabezado SkillTwin.")

    test_path = os.path.join(os.path.dirname(__file__), "test_documento.docx")
    doc.save(test_path)
    print(f"Documento de prueba guardado en: {test_path}")
