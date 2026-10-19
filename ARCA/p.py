import xml.etree.ElementTree as ET

def extract_credentials(xml_response):
    try:
        # Parsear el XML
        root = ET.fromstring(xml_response)

        # Encontrar los valores de token y sign
        token = root.find('.//credentials/token').text
        sign = root.find('.//credentials/sign').text

        # Retornar como tuplas o strings según necesites
        return token, sign
    except ET.ParseError as e:
        print(f"Error al parsear el XML: {e}")
        return None, None

# Ejemplo de uso:
xml_response = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<loginTicketResponse version="1.0">
    <header>
        <source>CN=wsaahomo, O=AFIP, C=AR, SERIALNUMBER=CUIT 33693450239</source>
        <destination>SERIALNUMBER=CUIT 20361814305, CN=test1</destination>
        <uniqueId>2069524910</uniqueId>
        <generationTime>2024-11-26T20:15:11.881-03:00</generationTime>
        <expirationTime>2024-11-27T08:15:11.881-03:00</expirationTime>
    </header>
    <credentials>
        <token>PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pgo8c3NvIHZlcnNpb249IjIuMCI+CiAgICA8aWQgc3JjPSJDTj13c2FhaG9tbywgTz1BRklQLCBDPUFSLCBTRVJJQUxOVU1CRVI9Q1VJVCAzMzY5MzQ1MDIzOSIgdW5pcXVlX2lkPSI1NjMzMjcxMDgiIGdlbl90aW1lPSIxNzMyNjYyODUxIiBleHBfdGltZT0iMTczMjcwNjExMSIvPgogICAgPG9wZXJhdGlvbiB0eXBlPSJsb2dpbiIgdmFsdWU9ImdyYW50ZWQiPgogICAgICAgIDxsb2dpbiBlbnRpdHk9IjMzNjkzNDUwMjM5IiBzZXJ2aWNlPSJ3Y29uc2N1aXQiIHVpZD0iU0VSSUFMTlVNQkVSPUNVSVQgMjAzNjE4MTQzMDUsIENOPXRlc3QxIiBhdXRobWV0aG9kPSJjbXMiIHJlZ21ldGhvZD0iMjIiPgogICAgICAgICAgICA8cmVsYXRpb25zPgogICAgICAgICAgICAgICAgPHJlbGF0aW9uIGtleT0iMjAzNjE4MTQzMDUiIHJlbHR5cGU9IjQiLz4KICAgICAgICAgICAgPC9yZWxhdGlvbnM+CiAgICAgICAgPC9sb2dpbj4KICAgIDwvb3BlcmF0aW9uPgo8L3Nzbz4K</token>
        <sign>LkDqoi+ji5Y0hShSaPUBxhm3hpAfhOBXPZldsc0XQChjA/s9yCQH5AbPcgpTbtH90sqeXRI3DhRKm97nSG/VWOXHUW3bC+PaY2MI515RrQCNZ91gs3scMwV8Kztnq2pVesizhv0BQ4uveFL7qsFPZthxPkrKIkK8U2sYypT0U/8=</sign>
    </credentials>
</loginTicketResponse>
"""

# Extraer los datos
token, sign = extract_credentials(xml_response)

# Imprimir los resultados
print(f"Token: {token}")
print(f"Sign: {sign}")
