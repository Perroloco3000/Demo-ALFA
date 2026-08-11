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
BOOKINGS: List[Dict] = []
CHATS: Dict[str, Dict] = {}

def get_welcome_content():
    return "¡Hola! Qué gusto saludarte. Te doy una cálida bienvenida a la **Clínica Dental AlfaDent**. 😊\n\nMi nombre es **Alfa** y estaré encantado de ayudarte el día de hoy. Puedo darte información sobre nuestros horarios de atención ⏰, dirección y ubicación 📍, tratamientos disponibles 🩺, precios de consulta 💰, o si lo prefieres, ayudarte a **agendar una cita** 📅 en solo un momento.\n\nCuéntame, ¿cómo te encuentras hoy y en qué te puedo colaborar?"

def init_chat_session(session_id: str, name: str = None) -> Dict:
    if session_id not in CHATS:
        if not name:
            num = len(CHATS) + 1
            name = f"Estudiante {num}"
        CHATS[session_id] = {
            "id": session_id,
            "name": name,
            "messages": [
                {
                    "role": "assistant",
                    "content": get_welcome_content(),
                    "time": datetime.now().strftime("%H:%M")
                }
            ],
            "booking_state": "idle",
            "temp_booking": {},
            "avatar": "/static/logo.png",
            "last_message": "¡Hola! Qué gusto saludarte...",
            "time": datetime.now().strftime("%H:%M")
        }
    return CHATS[session_id]

# Inicializar el chat base
init_chat_session("default", "AlfaDent Asistente")

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
        # Mapea session_id -> List[WebSocket]
        self.mobile_sockets: Dict[str, List[WebSocket]] = {}
        self.desktop_sockets: List[WebSocket] = []

    async def connect_mobile(self, ws: WebSocket, session_id: str):
        await ws.accept()
        if session_id not in self.mobile_sockets:
            self.mobile_sockets[session_id] = []
        self.mobile_sockets[session_id].append(ws)

    def disconnect_mobile(self, ws: WebSocket, session_id: str):
        if session_id in self.mobile_sockets:
            self.mobile_sockets[session_id] = [s for s in self.mobile_sockets[session_id] if s != ws]
            if not self.mobile_sockets[session_id]:
                del self.mobile_sockets[session_id]

    async def connect_desktop(self, ws: WebSocket):
        await ws.accept()
        self.desktop_sockets.append(ws)

    def disconnect_desktop(self, ws: WebSocket):
        self.desktop_sockets = [s for s in self.desktop_sockets if s != ws]

    async def send_to_mobile(self, session_id: str, payload: dict):
        if session_id in self.mobile_sockets:
            for ws in self.mobile_sockets[session_id]:
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass

    async def send_to_desktop(self, payload: dict):
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
async def handle_user_input(session_id: str, text: str):
    chat = init_chat_session(session_id)
    messages = chat["messages"]
    booking_state = chat["booking_state"]
    temp_booking = chat["temp_booking"]
    ts = datetime.now().strftime("%H:%M")

    # Guardar mensaje del usuario
    msg_user = {"role": "user", "content": text, "time": ts}
    messages.append(msg_user)
    
    # Broadcast a mobile
    await manager.send_to_mobile(session_id, {"type": "chat", "role": "user", "content": text, "time": ts})
    # Broadcast a desktop
    await manager.send_to_desktop({
        "type": "chat",
        "session_id": session_id,
        "role": "user",
        "content": text,
        "time": ts
    })
    
    # Enviar lista de chats actualizada para actualizar last_message en sidebar
    chat["last_message"] = text[:40] + ("..." if len(text) > 40 else "")
    chat["time"] = ts
    await manager.send_to_desktop({
        "type": "chats_update",
        "chats": list(CHATS.values())
    })

    # Mostrar "escribiendo..."
    await manager.send_to_mobile(session_id, {"type": "typing", "status": True})
    await manager.send_to_desktop({"type": "typing", "session_id": session_id, "status": True})
    await asyncio.sleep(1.0)

    reply = ""

    if booking_state != "idle":
        if booking_state == "waiting_date":
            date_val, err = parse_date_input(text)
            if err:
                reply = f"❌ {err}\n\nEscribe la fecha en formato YYYY-MM-DD, 'hoy' o 'mañana'."
            else:
                temp_booking["date"] = date_val
                chat["booking_state"] = "waiting_time"
                free = get_available_slots(date_val)
                reply = f"📅 Fecha: **{date_val}**\n\n🕒 Horarios disponibles:\n{', '.join(free)}\n\n¿A qué hora deseas tu cita? (HH:MM)"

        elif booking_state == "waiting_time":
            t_val, err = parse_time_input(text, temp_booking["date"])
            if err == "occupied":
                free = get_available_slots(temp_booking["date"])
                reply = f"❌ Ese horario ya está ocupado.\n\n👉 Disponibles: {', '.join(free)}\n\nElige otro horario:"
            elif err:
                reply = f"⚠️ {err}"
            else:
                temp_booking["time"] = t_val
                chat["booking_state"] = "waiting_name"
                reply = f"⏰ Hora: **{t_val}**\n\n¿A nombre de quién queda la cita?"

        elif booking_state == "waiting_name":
            if len(text.strip()) < 3:
                reply = "⚠️ El nombre es muy corto. Escribe nombre y apellido."
            else:
                temp_booking["name"] = text.strip()
                chat["booking_state"] = "waiting_phone"
                reply = f"👤 Paciente: **{text.strip()}**\n\nEscribe tu número de teléfono de contacto:"

        elif booking_state == "waiting_phone":
            if not validate_phone(text.strip()):
                reply = "⚠️ Número inválido (mínimo 8 dígitos). Escríbelo nuevamente:"
            else:
                temp_booking["phone"] = text.strip()
                code = generate_booking_code()
                new_b = {
                    "id": code,
                    "date": temp_booking["date"],
                    "time": temp_booking["time"],
                    "name": temp_booking["name"],
                    "phone": temp_booking["phone"],
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                BOOKINGS.append(new_b)
                reply = (
                    f"🎉 **¡CITA CONFIRMADA!**\n\n"
                    f"🆔 Código: `{code}`\n"
                    f"👤 Paciente: {temp_booking['name']}\n"
                    f"📅 Fecha: {temp_booking['date']}\n"
                    f"⏰ Hora: {temp_booking['time']} hrs\n"
                    f"📞 Tel: {temp_booking['phone']}\n\n"
                    f"¡Te esperamos 10 minutos antes! 😊🦷\n\n"
                    f"¿Deseas hacer otra consulta?"
                )
                chat["booking_state"] = "idle"
                temp_booking.clear()
                # Notificar dashboard de escritorio
                await manager.send_to_desktop({
                    "type": "bookings_update",
                    "bookings": BOOKINGS,
                    "count": len(BOOKINGS)
                })
    else:
        intent, _ = detect_intent(text)
        if intent == "greeting":
            reply = "¡Hola! Muy buenos días. Qué gusto saludarte, espero que estés teniendo un excelente día. Bienvenido a AlfaDent. 😊 ¿Cómo te encuentras hoy? ¿En qué te puedo colaborar?"
        elif intent == "hours":
            reply = f"Con gusto. ⏰ Respecto a nuestros **horarios de atención**:\n\n{CLINIC_INFO['faqs']['horarios']}\n\n¿Te gustaría que te ayude a agendar una cita en alguno de estos horarios?"
        elif intent == "location":
            reply = f"¡Por supuesto! 📍 Nos encontramos ubicados en:\n\n{CLINIC_INFO['faqs']['ubicacion']}\n\nContamos con facilidades de acceso. ¿Tienes alguna duda de cómo llegar?"
        elif intent == "services":
            svc = "\n".join(CLINIC_INFO["services"])
            reply = f"🩺 Con gusto te detallo los **tratamientos y servicios** que ofrecemos en AlfaDent:\n\n{svc}\n\n¿Te interesaría agendar una evaluación para alguno de estos tratamientos?"
        elif intent == "prices":
            reply = f"💰 Respecto a los **costos y precios** de nuestros servicios:\n\n{CLINIC_INFO['faqs']['costos']}\n\n¿Te gustaría reservar una primera cita de evaluación?"
        elif intent == "booking":
            chat["booking_state"] = "waiting_date"
            temp_booking.clear()
            reply = "📅 ¡Excelente! Con muchísimo gusto te ayudo a agendar tu cita. \n\nPara empezar, por favor indícame la fecha en la que te gustaría visitarnos (puedes escribir 'hoy', 'mañana' o una fecha específica como YYYY-MM-DD)."
        elif intent == "view_bookings":
            if not BOOKINGS:
                reply = "ℹ️ Por el momento no contamos con citas registradas en el sistema. ¿Te gustaría agendar una?"
            else:
                lines = "\n".join([f"• **{b['id']}** | {b['name']} | {b['date']} {b['time']}" for b in BOOKINGS])
                reply = f"📋 ¡Claro que sí! Aquí tienes la lista de las **citas registradas** actualmente:\n\n{lines}\n\n¿Deseas realizar algún cambio o tienes otra consulta?"
        elif intent == "bye":
            reply = "¡Muchísimas gracias por comunicarte con nosotros! Que tengas un excelente día y recuerda que en AlfaDent estamos para cuidar de tu sonrisa. ¡Hasta luego! 😊🦷"
        else:
            reply = "Disculpa, no logré comprender del todo tu consulta. 😅 ¿Podrías indicarme si deseas información sobre nuestros horarios, ubicación, servicios, precios, o si te gustaría agendar una cita? Estaer encantado de ayudarte."

    # Guardar respuesta del asistente
    msg_asst = {"role": "assistant", "content": reply, "time": ts}
    messages.append(msg_asst)
    
    # Actualizar metadatos de sesión
    chat["last_message"] = reply[:40] + ("..." if len(reply) > 40 else "")
    chat["time"] = ts

    # Desactivar "escribiendo..."
    await manager.send_to_mobile(session_id, {"type": "typing", "status": False})
    await manager.send_to_desktop({"type": "typing", "session_id": session_id, "status": False})
    
    # Broadcast mensaje del bot
    await manager.send_to_mobile(session_id, {"type": "chat", "role": "assistant", "content": reply, "time": ts})
    await manager.send_to_desktop({
        "type": "chat",
        "session_id": session_id,
        "role": "assistant",
        "content": reply,
        "time": ts
    })
    
    # Enviar lista de chats actualizada a desktop
    await manager.send_to_desktop({
        "type": "chats_update",
        "chats": list(CHATS.values())
    })

import urllib.parse
import os

IS_VERCEL = os.environ.get("VERCEL", "") == "1"

# ==========================================
# 6. RUTAS FASTAPI
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def get_desktop(request: Request):
    # Detectar si estamos en Vercel o en local
    if IS_VERCEL:
        # En Vercel, usar el dominio del request (ej: demo-alfa.vercel.app)
        host = request.headers.get("host", request.url.hostname)
        scheme = "https"
        mobile_url = f"{scheme}://{host}/mobile"
    else:
        # Localmente, usar IP local
        local_ip = get_local_ip()
        mobile_url = f"http://{local_ip}:8000/mobile"
    
    mobile_url_encoded = urllib.parse.quote(mobile_url, safe='')
    return templates.TemplateResponse(
        request=request,
        name="desktop.html",
        context={
            "mobile_url": mobile_url,
            "mobile_url_encoded": mobile_url_encoded,
            "is_vercel": IS_VERCEL,
            "chats": list(CHATS.values()),
            "bookings": BOOKINGS,
        }
    )

from fastapi.responses import RedirectResponse

@app.get("/mobile", response_class=HTMLResponse)
async def get_mobile(request: Request, session_id: Optional[str] = None):
    if not session_id:
        # Generar un ID de sesión aleatorio
        import random, string
        new_sess = "session_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return RedirectResponse(url=f"/mobile?session_id={new_sess}")
        
    chat = init_chat_session(session_id)
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "messages": chat["messages"],
            "session_id": session_id,
            "chat_name": chat["name"]
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
    await manager.send_to_desktop({
        "type": "bookings_update",
        "bookings": BOOKINGS,
        "count": len(BOOKINGS)
    })
    return {"status": "ok", "booking": new_b, "count": len(BOOKINGS)}

@app.post("/api/clear_bookings")
async def clear_bookings():
    BOOKINGS.clear()
    await manager.send_to_desktop({
        "type": "bookings_update",
        "bookings": BOOKINGS,
        "count": 0
    })
    return {"status": "ok", "count": 0}

@app.post("/api/clear_chat")
async def clear_chat(request: Request):
    data = await request.json()
    session_id = data.get("session_id", "default")
    
    chat = init_chat_session(session_id)
    chat["booking_state"] = "idle"
    chat["temp_booking"].clear()
    
    chat["messages"] = [
        {
            "role": "assistant",
            "content": get_welcome_content(),
            "time": datetime.now().strftime("%H:%M")
        }
    ]
    chat["last_message"] = "¡Hola! Qué gusto saludarte..."
    chat["time"] = datetime.now().strftime("%H:%M")

    # Notificar a la app móvil y al escritorio
    await manager.send_to_mobile(session_id, {
        "type": "clear_chat",
        "messages": chat["messages"]
    })
    await manager.send_to_desktop({
        "type": "clear_chat",
        "session_id": session_id,
        "messages": chat["messages"]
    })
    await manager.send_to_desktop({
        "type": "chats_update",
        "chats": list(CHATS.values())
    })
    return {"status": "ok", "messages": chat["messages"]}

@app.get("/api/state")
async def get_state(session_id: str = "default"):
    chat = init_chat_session(session_id)
    return {
        "messages": chat["messages"],
        "bookings": BOOKINGS,
        "count": len(BOOKINGS),
        "chats": list(CHATS.values())
    }

@app.post("/api/send_message")
async def api_send_message(request: Request):
    data = await request.json()
    content = data.get("content", "").strip()
    session_id = data.get("session_id", "default")
    if content:
        await handle_user_input(session_id, content)
    
    chat = init_chat_session(session_id)
    return {
        "status": "ok",
        "messages": chat["messages"],
        "bookings": BOOKINGS,
        "count": len(BOOKINGS),
        "chats": list(CHATS.values())
    }

@app.websocket("/ws/desktop")
async def ws_desktop(websocket: WebSocket):
    await manager.connect_desktop(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("content"):
                session_id = data.get("session_id", "default")
                await handle_user_input(session_id, data["content"])
    except (WebSocketDisconnect, Exception):
        manager.disconnect_desktop(websocket)

@app.websocket("/ws/mobile")
async def ws_mobile(websocket: WebSocket):
    session_id = websocket.query_params.get("session_id", "default")
    await manager.connect_mobile(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("content"):
                await handle_user_input(session_id, data["content"])
    except (WebSocketDisconnect, Exception):
        manager.disconnect_mobile(websocket, session_id)

if __name__ == "__main__":
    import uvicorn
    ip = get_local_ip()
    print("=" * 55)
    print("  ALFA IA - Clínica Dental AlfaDent")
    print(f"  Desktop: http://localhost:8000")
    print(f"  Móvil:   http://{ip}:8000/mobile")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8000)
