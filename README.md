# Alfa IA Enterprise - Réplica Dual Síncrona WhatsApp (Modo Oscuro)

Este repositorio contiene el prototipo funcional **Enterprise** de **Alfa IA**, un asistente virtual automatizado para la **Clínica Dental AlfaDent**. 

El demo integra un diseño de **Pantalla Dividida (Side-by-Side)** que simula la interacción síncrona en tiempo real entre el teléfono celular del paciente y la consola de escritorio de la clínica, todo renderizado bajo el diseño **WhatsApp Dark Mode**.

---

## 🛠️ Tecnologías y Estructura

- **Python 3.8+**: Lenguaje de desarrollo principal.
- **Streamlit**: Framework utilizado para levantar la interfaz y sincronizar el estado síncrono.
- **Pandas**: Motor para simular e interactuar con la base de datos SQL clínica.
- **HTML5 & CSS3 (Inyectado)**: Estilización a medida para lograr:
  - Un **Smartphone con notch superior** y pantalla scrollable en el lado izquierdo.
  - La réplica de **WhatsApp Web Desktop (Modo Oscuro)** en el lado derecho.
  - Burbujas de diálogo verde oscuro (`#005c4b`) y gris oscuro (`#202c33`), doble check azul (`✓✓`), reloj de mensaje e indicador de escritura animado (`typing indicator`).
- **Regex & Scoring Engine**: Clasificador de intenciones conversacionales según ponderación de patrones regulares.
- **Validación de Disponibilidad Temporal**: Motor inteligente de citas médicas con intervalos de 30 minutos (09:00 a 18:00) y prevención activa de colisión de horarios.

---

## 📦 Instalación y Ejecución

1. Abre tu terminal de comandos en el directorio del proyecto:
   ```bash
   cd c:\Users\Promiley\Desktop\Protecto-Gerencia
   ```
2. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación de Streamlit:
   ```bash
   streamlit run app.py
   ```
4. Abre [http://localhost:8501](http://localhost:8501) en tu navegador.

---

## 🎓 Guion de Presentación para Defensa de Tesis (Paso a Paso)

Sigue esta secuencia para demostrar el valor técnico y visual del demo ante la comisión evaluadora:

### Paso 1: Introducción y Arquitectura Dual
- **Acción**: Muestra la pantalla principal en tu navegador.
- **Explicación**: *"Estimados evaluadores, les presento la interfaz del prototipo de **Alfa IA**. A diferencia de los demos tradicionales, este entorno cuenta con una **Arquitectura Dual Simultánea**. A la izquierda simulamos el **dispositivo móvil del paciente** (dentro de una maqueta de smartphone con notch y pantalla adaptada) y a la derecha vemos la **consola de control de escritorio de la clínica**. Ambas pantallas se sincronizan de manera síncrona, emulando la comunicación en tiempo real."*

### Paso 2: Mensajería Síncrona y FAQs
- **Acción**: Escribe un mensaje en el celular (izquierda), por ejemplo: *"hola, me gustaría saber dónde están ubicados"*, y presiona enviar (o presiona el botón rápido **"📍 Pedir Ubicación"**).
- **Explicación**: *"Al enviar el mensaje desde el celular, observamos dos cosas: en primer lugar, el mensaje aparece inmediatamente reflejado en el monitor clínico de la derecha. En segundo lugar, se activa un **typing indicator** (indicador de escritura con animación) antes de que la IA responda, dándole un toque realista y orgánico a la conversación."*

### Paso 3: Agendamiento de Citas y Validación de Colisiones SQL
- **Acción**: Presiona el botón rápido del celular **"📅 Agendar Cita"** o escribe *"cita"*.
- **Explicación**: *"Iniciamos el proceso de reserva gestionado por una máquina de estados conversacional."*
- **Acción**: Escribe la fecha: *"2026-08-12"*.
- **Explicación**: *"El bot valida la fecha en formato YYYY-MM-DD y consulta de inmediato la base de datos simulada en memoria. Nos indica que hay citas reservadas por otros pacientes y nos sugiere únicamente los bloques que están libres."*
- **Acción**: Introduce una hora ya ocupada (ej. *"10:30"*).
- **Explicación**: *"El sistema detecta una colisión horaria: el bloque de las 10:30 ya se encuentra reservado por 'Marcos Riquelme' en nuestra base de datos. Para asegurar la consistencia del sistema y evitar dobles agendamientos, el bot rechaza la entrada y nos pide nuevamente ingresar un bloque válido."*
- **Acción**: Ingresa una hora libre (ej. *"11:00"*), tu nombre y número telefónico.
- **Explicación**: *"Al completar los datos de contacto, la IA genera un ticket con un código único aleatorio en formato ALFA-XXXXXX, que actúa como identificador primario del registro."*

### Paso 4: Comando `/reservas` e Intranet Clínica
- **Acción**: Escribe `/reservas` en el celular (columna izquierda).
- **Explicación**: *"Mediante comandos del sistema, el paciente puede consultar sus registros. El bot traduce la consulta y renderiza una tabla HTML compacta de citas activas directamente en la burbuja del chat."*
- **Acción**: Cambia a la pestaña de la derecha **"📊 Intranet / Base de Datos"**.
- **Explicación**: *"Por último, en el panel administrativo interno de la clínica, los recepcionistas y doctores pueden supervisar la ocupación horaria en tiempo real, visualizar la tabla completa de registros médicos y descargar la base de datos como un reporte CSV para su análisis."*
- **Cierre**: *"Esto demuestra un ecosistema empresarial completo: experiencia de usuario impecable e instantánea para el cliente, y control administrativo íntegro para la PyME."*
