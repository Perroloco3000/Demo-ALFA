import socket
import re
import random
import string
import asyncio
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Alfa IA Enterprise")

# Configurar estáticos
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configurar Jinja2 - templates en la carpeta "templates/"
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ==========================================
# 1. BASE DE DATOS Y ESTADO GLOBAL EN MEMORIA
# ==========================================
MESSAGES: List[Dict] = [
    {
        "role": "assistant",
        "content": "¡Hola! Te doy la bienvenida a **Clínica Dental AlfaDent**. Soy **Alfa IA**, tu asistente virtual corporativo 🦷🤖✨\n\nPuedo responder a tus consultas sobre nuestros horarios ⏰, dirección y ubicación 📍, tratamientos dentales 🩺, precios 💰 o ayudarte a **agendar una cita** 📅 en línea.\n\n¿En qué te puedo colaborar hoy?",
        "time": datetime.now().strftime("%H:%M")
    }
]

BOOKINGS: List[Dict] = [
    {"id": "ALFA-823491", "date": "2026-08-12", "time": "10:00", "name": "Elena Torres",    "phone": "+56987654321", "created_at": "2026-08-10 10:15:30"},
    {"id": "ALFA-410982", "date": "2026-08-12", "time": "10:30", "name": "Marcos Riquelme", "phone": "+56911223344", "created_at": "2026-08-10 11:42:00"},
    {"id": "ALFA-591204", "date": "2026-08-15", "time": "16:00", "name": "Laura Benítez",   "phone": "+56955667788", "created_at": "2026-08-10 14:05:12"},
]

BOOKING_STATE = "idle"
TEMP_BOOKING: Dict = {}

VALID_SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00"
]

CLINIC_INFO = {
    "name": "Clínica Dental AlfaDent",
    "location": "Av. Principal Metrópolis, Nro. 450, Piso 2, Oficina 204",
    "hours": "Lunes a Viernes: 8:00 AM - 6:00 PM | Sábados: 9:00 AM - 1:00 PM",
    "services": [
        "🩺 Evaluación General y Diagnóstico Digital ($30 USD)",
        "😬 Ortodoncia Avanzada (Frenillos y Alineadores)",
        "✨ Blanqueamiento Dental Premium Láser",
        "🦷 Implantes, Coronas y Rehabilitación Oral"
    ],
    "faqs": {
        "horarios": "Atendemos de Lunes a Viernes de 8:00 AM a 6:00 PM, y los Sábados de 9:00 AM a 1:00 PM. Los domingos y feriados permanecemos cerrados.",
        "ubicacion": "Nuestra clínica se encuentra en la Av. Principal Metrópolis, Nro. 450, Piso 2, Oficina 204 (a pasos del Centro Financiero). Contamos con estacionamiento gratuito.",
        "servicios": "En AlfaDent ofrecemos: Evaluación General y Diagnóstico Digital, Ortodoncia Avanzada, Blanqueamiento Láser e Implantes Dentales. ¿Te gustaría agendar una cita?",
        "costos": "La consulta inicial tiene un costo de $30 USD (incluye radiografía preventiva básica). Para otros tratamientos, el presupuesto es personalizado y se entrega en la primera cita."
    }
}

# ==========================================
# 2. DETECTOR DE INTENCIONES CON REGEX SCORING
# ==========================================
INTENTS = {
    "greeting": [
        (r"\bhola\b", 3), (r"\bbuen(as|os)?\s*(dias|tardes|noches|dia)\b", 3),
        (r"\bquien eres\b", 2), (r"\bpresentate\b", 2), (r"\bhello\b", 1)
    ],
    "hours": [
        (r"\bhorario\b", 3), (r"\bhora\b", 1), (r"\bcuando\s+atienden\b", 3),
        (r"\babren\b", 2), (r"\bcierran\b", 2), (r"\bdias\s+de\s+atencion\b", 3)
    ],
    "location": [
        (r"\bubicacion\b", 3), (r"\bdireccion\b", 3), (r"\bdonde\s+(estan|quedan|queda)\b", 3),
        (r"\bcomo\s+llegar\b", 3), (r"\bmapa\b", 2)
    ],
    "services": [
        (r"\bservicio(s)?\b", 3), (r"\btratamiento(s)?\b", 3), (r"\bque\s+hacen\b", 2),
        (r"\bortodoncia\b", 2), (r"\blimpieza\b", 2), (r"\bblanqueamiento\b", 2), (r"\bimplante(s)?\b", 2)
    ],
    "prices": [
        (r"\bprecio(s)?\b", 3), (r"\bcosto(s)?\b", 3), (r"\bcuanto\s+(vale|cuesta)\b", 3),
        (r"\btarifa(s)?\b", 3), (r"\bvalor(es)?\b", 2), (r"\bpresupuesto\b", 2)
    ],
    "booking": [
        (r"\breservar\b", 3), (r"\breserva\b", 3), (r"\bcita\b", 3),
        (r"\bagendar\b", 3), (r"\bagenda\b", 2), (r"\bturno\b", 2)
    ],
    "view_bookings": [
        (r"^/reservas$", 5), (r"\bver\s+(mis\s+)?reservas\b", 3),
        (r"\bmis\s+citas\b", 3), (r"\blistado\s+de\s+reservas\b", 3)
    ],
    "bye": [
        (r"\badios\b", 3), (r"\bchao\b", 3), (r"\bhasta\s+luego\b", 3),
        (r"\bgracias\b", 2), (r"\bmuchas\s+gracias\b", 2)
    ]
}

def detect_intent(text: str) -> Tuple[str, int]:
    text_lower = text.lower().strip()
    if text_lower == "/reservas":
        return "view_bookings", 100
    scores = {intent: 0 for intent in INTENTS}
    for intent, patterns in INTENTS.items():
        for pattern, weight in patterns:
            if re.findall(pattern, text_lower):
                scores[intent] += weight
    best = max(scores, key=scores.get)
    return (best, scores[best]) if scores[best] > 0 else ("fallback", 0)

# ==========================================
# 3. GESTIÓN DE CITAS Y VALIDACIONES
# ==========================================
def get_available_slots(date_str: str) -> List[str]:
    booked = {b["time"] for b in BOOKINGS if b["date"] == date_str}
    return [s for s in VALID_SLOTS if s not in booked]

def generate_booking_code() -> str:
    while True:
        code = f"ALFA-{''.join(random.choices(string.digits, k=6))}"
        if not any(b["id"] == code for b in BOOKINGS):
            return code

def validate_phone(phone: str) -> bool:
    return len(re.sub(r'\D', '', phone)) >= 8

def parse_date_input(text: str) -> Tuple[Optional[str], Optional[str]]:
    from datetime import timedelta
    text = text.strip().lower()
    today = datetime.today()
    if "hoy" in text:
        return today.strftime("%Y-%m-%d"), None
    if "mañana" in text or "manana" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d"), None
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', text) or \
        re.match(r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$', text)
    if not m:
        return None, "Formato incorrecto. Usa YYYY-MM-DD o escribe *hoy* o *mañana*."
    try:
        if len(m.group(1)) == 4:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime(y, mo, d)
        if dt.date() < today.date():
            return None, "La fecha no puede ser anterior a hoy."
        return dt.strftime("%Y-%m-%d"), None
    except ValueError:
        return None, "Día inválido en el calendario."

def parse_time_input(text: str, date_str: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.match(r'^(\d{1,2}):(\d{2})$', text.strip())
    if not m:
        return None, "Usa formato 24h HH:MM (ej: 14:30)."
    time_str = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    if time_str not in VALID_SLOTS:
        return None, "Bloque inválido. Citas cada 30 min de 09:00 a 18:00."
    if time_str not in get_available_slots(date_str):
        return None, "occupied"
    return time_str, None

# ==========================================
# 4. GESTOR DE CONEXIONES WEBSOCKET
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.mobile_sockets: List[WebSocket] = []
        self.desktop_sockets: List[WebSocket] = []

    async def connect_mobile(self, ws: WebSocket):
        await ws.accept(); self.mobile_sockets.append(ws)

    def disconnect_mobile(self, ws: WebSocket):
        self.mobile_sockets = [s for s in self.mobile_sockets if s != ws]

    async def connect_desktop(self, ws: WebSocket):
        await ws.accept(); self.desktop_sockets.append(ws)

    def disconnect_desktop(self, ws: WebSocket):
        self.desktop_sockets = [s for s in self.desktop_sockets if s != ws]

    async def broadcast(self, payload: dict):
        for ws in self.mobile_sockets + self.desktop_sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    async def broadcast_desktop(self, payload: dict):
        for ws in self.desktop_sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

manager = ConnectionManager()

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

# ==========================================
# 5. LÓGICA DEL BOT
# ==========================================
async def handle_user_input(text: str):
    global BOOKING_STATE, TEMP_BOOKING
    ts = datetime.now().strftime("%H:%M")

    await manager.broadcast({"type": "chat", "role": "user", "content": text, "time": ts})
    MESSAGES.append({"role": "user", "content": text, "time": ts})

    await manager.broadcast({"type": "typing", "status": True})
    await asyncio.sleep(1.0)

    reply = ""

    if BOOKING_STATE != "idle":
        if BOOKING_STATE == "waiting_date":
            date_val, err = parse_date_input(text)
            if err:
                reply = f"❌ {err}\n\nEscribe la fecha en formato YYYY-MM-DD, 'hoy' o 'mañana'."
            else:
                TEMP_BOOKING["date"] = date_val
                BOOKING_STATE = "waiting_time"
                free = get_available_slots(date_val)
                reply = f"📅 Fecha: **{date_val}**\n\n🕒 Horarios disponibles:\n{', '.join(free)}\n\n¿A qué hora deseas tu cita? (HH:MM)"

        elif BOOKING_STATE == "waiting_time":
            t_val, err = parse_time_input(text, TEMP_BOOKING["date"])
            if err == "occupied":
                free = get_available_slots(TEMP_BOOKING["date"])
                reply = f"❌ Ese horario ya está ocupado.\n\n👉 Disponibles: {', '.join(free)}\n\nElige otro horario:"
            elif err:
                reply = f"⚠️ {err}"
            else:
                TEMP_BOOKING["time"] = t_val
                BOOKING_STATE = "waiting_name"
                reply = f"⏰ Hora: **{t_val}**\n\n¿A nombre de quién queda la cita?"

        elif BOOKING_STATE == "waiting_name":
            if len(text.strip()) < 3:
                reply = "⚠️ El nombre es muy corto. Escribe nombre y apellido."
            else:
                TEMP_BOOKING["name"] = text.strip()
                BOOKING_STATE = "waiting_phone"
                reply = f"👤 Paciente: **{text.strip()}**\n\nEscribe tu número de teléfono de contacto:"

        elif BOOKING_STATE == "waiting_phone":
            if not validate_phone(text.strip()):
                reply = "⚠️ Número inválido (mínimo 8 dígitos). Escríbelo nuevamente:"
            else:
                TEMP_BOOKING["phone"] = text.strip()
                code = generate_booking_code()
                new_b = {
                    "id": code,
                    "date": TEMP_BOOKING["date"],
                    "time": TEMP_BOOKING["time"],
                    "name": TEMP_BOOKING["name"],
                    "phone": TEMP_BOOKING["phone"],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                BOOKINGS.append(new_b)
                reply = (
                    f"🎉 **¡CITA CONFIRMADA!**\n\n"
                    f"🆔 Código: `{code}`\n"
                    f"👤 Paciente: {TEMP_BOOKING['name']}\n"
                    f"📅 Fecha: {TEMP_BOOKING['date']}\n"
                    f"⏰ Hora: {TEMP_BOOKING['time']} hrs\n"
                    f"📞 Tel: {TEMP_BOOKING['phone']}\n\n"
                    f"¡Te esperamos 10 minutos antes! 😊🦷\n\n"
                    f"¿Deseas hacer otra consulta?"
                )
                BOOKING_STATE = "idle"
                TEMP_BOOKING.clear()
                # Notificar dashboard de escritorio
                await manager.broadcast_desktop({
                    "type": "bookings_update",
                    "bookings": BOOKINGS,
                    "count": len(BOOKINGS)
                })
    else:
        intent, _ = detect_intent(text)
        if intent == "greeting":
            reply = "¡Hola! Bienvenido a **Clínica Dental AlfaDent**. Soy **Alfa IA** 🦷🤖\n\nPuedo ayudarte con:\n• Horarios ⏰\n• Ubicación 📍\n• Servicios 🩺\n• Precios 💰\n• Agendar cita 📅\n\n¿En qué te ayudo?"
        elif intent == "hours":
            reply = f"⏰ **Horarios:**\n{CLINIC_INFO['faqs']['horarios']}"
        elif intent == "location":
            reply = f"📍 **Dirección:**\n{CLINIC_INFO['faqs']['ubicacion']}"
        elif intent == "services":
            svc = "\n".join(CLINIC_INFO["services"])
            reply = f"🩺 **Servicios AlfaDent:**\n\n{svc}\n\n¿Te agendamos una cita?"
        elif intent == "prices":
            reply = f"💰 **Precios:**\n{CLINIC_INFO['faqs']['costos']}"
        elif intent == "booking":
            BOOKING_STATE = "waiting_date"
            TEMP_BOOKING.clear()
            reply = "📅 ¡Iniciemos tu cita!\n\n¿Para qué fecha? (YYYY-MM-DD, 'hoy' o 'mañana')"
        elif intent == "view_bookings":
            if not BOOKINGS:
                reply = "ℹ️ No hay citas registradas aún."
            else:
                lines = "\n".join([f"• **{b['id']}** | {b['name']} | {b['date']} {b['time']}" for b in BOOKINGS])
                reply = f"📋 **Citas registradas:**\n\n{lines}"
        elif intent == "bye":
            reply = "¡Hasta luego! En AlfaDent nos importa tu salud bucal. 😊🦷"
        else:
            reply = "No entendí tu mensaje. 🤖\n\nPuedes preguntarme sobre **horarios**, **ubicación**, **servicios** o escribir **'cita'** para agendar."

    await manager.broadcast({"type": "typing", "status": False})
    await manager.broadcast({"type": "chat", "role": "assistant", "content": reply, "time": ts})
    MESSAGES.append({"role": "assistant", "content": reply, "time": ts})

import urllib.parse

# ==========================================
# 6. RUTAS FASTAPI
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def get_desktop(request: Request):
    local_ip = get_local_ip()
    mobile_url = f"http://{local_ip}:8000/mobile"
    mobile_url_encoded = urllib.parse.quote(mobile_url, safe='')
    return templates.TemplateResponse(
        request=request,
        name="desktop.html",
        context={
            "mobile_url": mobile_url,
            "mobile_url_encoded": mobile_url_encoded,
            "local_ip": local_ip,
            "messages": MESSAGES,
            "bookings": BOOKINGS,
        }
    )

@app.get("/mobile", response_class=HTMLResponse)
async def get_mobile(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "messages": MESSAGES,
        }
    )

@app.post("/api/add_test_booking")
async def add_test_booking():
    names = ["Carlos Mendoza", "Ana María Silva", "Roberto Gómez", "Patricia Morales", "Diego Castro"]
    times = ["09:00", "11:30", "14:00", "15:30", "17:00"]
    dates = ["2026-08-14", "2026-08-15", "2026-08-16", "2026-08-17"]
    
    code = generate_booking_code()
    new_b = {
        "id": code,
        "date": random.choice(dates),
        "time": random.choice(times),
        "name": random.choice(names),
        "phone": f"+569{random.randint(10000000, 99999999)}",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    BOOKINGS.append(new_b)
    await manager.broadcast_desktop({
        "type": "bookings_update",
        "bookings": BOOKINGS,
        "count": len(BOOKINGS)
    })
    return {"status": "ok", "booking": new_b, "count": len(BOOKINGS)}

@app.get("/api/state")
async def get_state():
    return {
        "messages": MESSAGES,
        "bookings": BOOKINGS,
        "count": len(BOOKINGS)
    }

@app.post("/api/send_message")
async def api_send_message(request: Request):
    data = await request.json()
    content = data.get("content", "").strip()
    if content:
        await handle_user_input(content)
    return {
        "status": "ok",
        "messages": MESSAGES,
        "bookings": BOOKINGS,
        "count": len(BOOKINGS)
    }

@app.websocket("/ws/desktop")
async def ws_desktop(websocket: WebSocket):
    await manager.connect_desktop(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("content"):
                await handle_user_input(data["content"])
    except (WebSocketDisconnect, Exception):
        manager.disconnect_desktop(websocket)

@app.websocket("/ws/mobile")
async def ws_mobile(websocket: WebSocket):
    await manager.connect_mobile(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("content"):
                await handle_user_input(data["content"])
    except (WebSocketDisconnect, Exception):
        manager.disconnect_mobile(websocket)

if __name__ == "__main__":
    import uvicorn
    ip = get_local_ip()
    print("=" * 55)
    print("  ALFA IA - Clínica Dental AlfaDent")
    print(f"  Desktop: http://localhost:8000")
    print(f"  Móvil:   http://{ip}:8000/mobile")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8000)
