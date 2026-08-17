# Ejecuta el servidor SkillTwin desde la raíz del repositorio.
Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Path -Parent)
Set-Location -Path .\cerebro
python server.py
