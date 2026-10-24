import json
import os
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

API_KEY = os.environ["TRACKING_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ENVIOS = [
    {
        "nombre": "Chachapoyas",
        "numero": os.environ["GUIA_CHACHAPOYAS"],
        "codigo": os.environ["CODIGO_CHACHAPOYAS"],
    },
    {
        "nombre": "Pucallpa",
        "numero": os.environ["GUIA_PUCALLPA"],
        "codigo": os.environ["CODIGO_PUCALLPA"],
    },
    {
        "nombre": "Lima",
        "numero": os.environ["GUIA_LIMA"],
        "codigo": os.environ["CODIGO_LIMA"],
    },
]

BASE_API = "https://api.tracking-peru.com/v1/tracking"
ARCHIVO_ESTADOS = Path("estados_avisados.json")


def consultar(url, headers=None, datos=None):
    cuerpo = None
    if datos is not None:
        cuerpo = urllib.parse.urlencode(datos).encode("utf-8")

    req = urllib.request.Request(
        url, data=cuerpo, headers=headers or {}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HTTP {error.code}: {detalle[:300]}"
        ) from None


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resultado = consultar(url, datos={
        "chat_id": CHAT_ID,
        "text": mensaje,
    })
    if not resultado.get("ok"):
        raise RuntimeError("Telegram no confirmó el envío.")


def main():
    if ARCHIVO_ESTADOS.exists():
        try:
            estados = json.loads(
                ARCHIVO_ESTADOS.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            estados = {}
    else:
        estados = {}

    for envio in ENVIOS:
        nombre = envio["nombre"]
        try:
            query = urllib.parse.urlencode({
                "carrier": "shalom",
                "number": envio["numero"],
                "code": envio["codigo"],
            })
            datos = consultar(
                f"{BASE_API}?{query}",
                headers={"X-API-Key": API_KEY},
            )

            estado = str(datos.get("status", "unknown")).lower()
            detalle = datos.get("status_raw", estado)
            print(f"{nombre}: {estado} ({detalle})")

            if estado in ("at_destination", "available_for_pickup"):
                clave = nombre
                if estados.get(clave) != estado:
                    if estado == "available_for_pickup":
                        texto = "Está disponible para recoger."
                    else:
                        texto = (
                            "Llegó a la agencia de destino. "
                            "Confirma el estado antes de ir."
                        )

                    enviar_telegram(
                        f"📦 {nombre} — Shalom\n"
                        f"Estado: {detalle}\n{texto}"
                    )
                    estados[clave] = estado
                    print(f"{nombre}: aviso enviado.")

        except Exception as error:
            print(f"Error en {nombre}: {error}")

    ARCHIVO_ESTADOS.write_text(
        json.dumps(estados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
