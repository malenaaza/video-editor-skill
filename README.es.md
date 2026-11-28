# Editor de vídeo para creadores: un plugin de Claude Code para vídeos con una persona hablando a cámara

[English](README.md) · **Español**


https://github.com/user-attachments/assets/aa4c613b-1997-4f54-aed8-40265f171824




<img width="1080" height="960" alt="cover-before-after" src="https://github.com/user-attachments/assets/63d6c838-5fdb-4293-abb4-8a602d206b84" />


Un plugin para [Claude Code](https://claude.com/claude-code) que edita en tu propio ordenador vídeos cortos y de YouTube en los que hablas a cámara, con FFmpeg y Whisper. Tú sigues siendo el director: te pregunta antes de decidir cualquier cosa que sea cuestión de criterio.

> Esta página es una traducción al castellano de España de la parte del [README](README.md) que más se lee. La lista completa de archivos está solo en la versión en inglés. Claude te habla en el idioma en el que le escribas; no hace falta que cambies nada para usar la skill en español.

## Qué hace

- Quita repeticiones de toma, pausas, muletillas ("eh", "mm", tarareos) y tramos de silencio, con transcripción palabra por palabra, una segunda pasada para cazar muletillas y una comprobación del movimiento de la boca
- Acelera un poco la forma de hablar (opcional) manteniendo tu tono
- Subtítulos (normales, o con cada palabra iluminada a medida que la dices), títulos, usuario, tarjeta final y logos con los colores y las fuentes de tu marca, guardados una vez y reutilizados
- Exportaciones verticales (Reels, TikTok, Shorts) y horizontales (YouTube), y división de grabaciones largas en varios vídeos
- Eliminación de ruido de fondo y zumbido, mejora y nivelado de la voz, efectos de sonido, emojis animados, títulos y etiquetas de producto (con Remotion) y arreglos para material oscuro
- Letras grandes detrás de ti (el efecto de "texto detrás del sujeto"): una palabra gancho o un título en el fondo, con tu figura delante, que aparece cuando lo dices
- Suavizado de piel que sigue la cara (cara y cuello, más fuerte en primeros planos), un embellecido ligero opcional (brillo suave, ojeras y blanco de los ojos más luminosos; nunca maquillaje ni cambiar rasgos) y blanqueado de dientes, desenfoque de fondo que mantiene nítidos los productos que sostienes (y que no se añade cuando tu cámara ya desenfocó el fondo), una parte en blanco y negro, un acercamiento lento a tu cara en una frase clave
- Crea sus propias carpetas: en la primera configuración te pregunta dónde guardar los archivos de trabajo (sugiere `~/video-work`), comprueba que la carpeta no esté en OneDrive, iCloud, Dropbox ni Google Drive (donde los vídeos grandes se quedan sin tiempo) y la crea junto con una carpeta para cada vídeo. Nunca tienes que crear carpetas a mano
- Pixela las caras de otras personas que salen en el plano (transeúntes, clientes, niños) y mantiene nítida la tuya: sigue todas las caras, te enseña una hoja para revisarlas, cubre los momentos en que el detector las pierde y comprueba el resultado por si queda alguna cara visible. Las personas pequeñas o lejanas (personal y clientes al fondo de una tienda) necesitan la búsqueda a fondo; solo oculta caras, no voces ni identificadores con nombre
- Una segunda cámara para algunas partes: tu cámara principal graba todo el vídeo y tu iPhone graba algunas partes desde otro ángulo. Si se grabó a la vez, las sincroniza por el sonido y cambia a la imagen del iPhone en esas partes mientras tu voz sigue siendo la de la cámara principal; si se grabaron como tomas separadas, las une. En ambos casos primero hace que los clips del iPhone coincidan (mismos fotogramas por segundo, a ritmo constante, mismo tamaño, HDR convertido en vídeo normal) y marca en la lista de planos qué partes van en cada cámara
- Material en Log (Apple Log, S-Log y otros) convertido con la LUT oficial del fabricante de la cámara
- Un paquete listo para publicar para cada vídeo: texto, hashtags y fotograma de portada, o una portada con fotos de tus productos (eliges el fotograma de portada mientras editas; las imágenes de producto ya recortadas se usan tal cual)
- Revisa cómo se grabó cada vídeo (Blackmagic Camera, la app Cámara del iPhone, móviles Android, Sony, GoPro, DJI) y te dice una vez qué cambiar para mejorar el material: fotogramas por segundo según las luces de tu país, obturador, 4K, sonido Bluetooth, HDR, cámara frontal
- Para YouTube: Shorts sacados de tu vídeo horizontal que te siguen como un operador de cámara, grabaciones de pantalla con zooms suaves sobre la acción (y una composición con la pantalla encima de ti para Shorts), capítulos para la descripción y miniaturas con tu cara y unas pocas palabras grandes
- Vídeos con marionetas, sin nadie a cámara: uno o dos personajes adultos ilustrados o un robot (dibujados con código, todos originales, con los colores de tu marca y los tonos de piel y pelo que elijas) dicen tu guion con una voz gratuita creada en tu ordenador, con castellano de España e inglés británico incluidos, con bocas que coinciden con cada sonido, parpadeo, expresiones, subtítulos con las palabras exactas del guion y una traducción opcional debajo de cada frase para estudiantes de idiomas
- Para vídeos educativos: una página web real en una ventana de navegador que se desplaza hasta lo que mencionas y lo resalta, de dos a cuatro cifras que cuentan hacia arriba mientras las dices, y un antes y después con un barrido (un prompt débil y uno bueno), y una lista que marca «tres cosas» una a una mientras las dices (con lo que nombras, o solo 1, 2, 3), una fila de pasos que se iluminan uno a uno para un proceso contado en orden, una barra con nombre y cargo cuando presentas a alguien, una tarjeta de cita que hace aparecer las palabras que lees, una cuenta atrás para «en tres, dos, uno», un anillo que se llena hasta el porcentaje que dices, barras que crecen al comparar cifras, un resaltado tipo rotulador para la frase que recalcas, un botón de suscribirse que se pulsa, títulos de sección en pantalla, notificaciones de mensajes que se apilan mientras las enumeras, y una imagen o un vídeo corto en una ventana en la esquina mientras hablas
- Tarjetas de herramienta para vídeos sobre IA: cuando nombras una herramienta, entran su logo y su nombre; las herramientas nombradas seguidas se apilan, y una herramienta no se vuelve a mostrar durante un rato
- Una ventana de chat de IA para vídeos sobre IA: tu prompt se escribe con clics de teclas, se envía, el asistente piensa y responde palabra a palabra, con los colores de tu marca, horizontal o vertical
- Explicaciones animadas para vídeos educativos: cajas, flechas y un punto que se mueve que muestran cómo funciona algo (cómo un MCP conecta Claude con tu Gmail, cómo viaja una petición), cada una apareciendo al nombrarla, con los colores de tu marca, horizontal o vertical, con pops y whooshes cronometrados con la imagen
- Una lista de correcciones de palabras que se guarda una vez y se aplica a todos los vídeos: los nombres de marcas, productos y palabras extranjeras que un transcriptor siempre escribe mal se corrigen en tus subtítulos (y, con Whisper, se le pasan al transcriptor como pista)
- Elección del motor de transcripción: Whisper, o NVIDIA Parakeet (varias veces más rápido en un ordenador sin tarjeta gráfica), con una herramienta que compara los dos sobre tu propia voz antes de cambiar
- Comprueba cada corte por su sonido antes de renderizar (una palabra recortada por la mitad, un resto de una palabra quitada, un corte que pasa como un destello) y lo arregla, conservando o descartando la palabra entera
- Comprueba la apertura de cada vídeo: un primer fotograma negro, una primera palabra recortada, silencio antes de que hables, un efecto de sonido en tu primera palabra, nada que leer con el sonido apagado, y qué dicen los primeros 3 segundos
- Comprueba cada exportación antes de entregarla: fotogramas negros, un fotograma suelto que dejó un corte, imagen y sonido que terminan separados, sonido que se corta, etiquetas de color que faltan y palabras recortadas en un corte
- Guion primero: pídele un guion y escribe uno (si aún no tienes tema, te sugiere cinco ideas, cada una con un gancho, y escribe la que elijas) con capítulos, grabaciones de pantalla y Shorts marcados, y de uno a tres clips de IA para ambientar (una metáfora visual, una escena de intro) con prompts listos para pegar en Google Flow u otro generador, todos con el mismo aspecto y nunca para texto, diagramas ni personas reales; después de grabar, hace coincidir cada clip con tu cámara y lo coloca bajo tu voz, y además prepara un texto limpio para tu teleprompter si usas uno (lo pregunta una vez); cuando lo grabas, se queda con la última toma buena de cada frase, te dice lo que te faltó y saca de ahí los capítulos y los Shorts
- Varios vídeos en una petición: respondes a las preguntas una sola vez para todos, cada vídeo tiene su propia carpeta y sigue la edición normal (de dos en dos, para no sobrecargar el ordenador), y ves juntos todos los planes de corte y borradores y apruebas cada uno antes de la exportación final. Un vídeo cada vez funciona exactamente igual que antes

No tienes que acordarte de esta lista: pregunta a la skill "¿qué puedes hacer?" y te enseña un menú, y antes de cada edición te sugiere los extras que encajan con ese vídeo.

## Se adapta a tu ordenador

En el primer uso ejecuta `scripts/detect_setup.py`, que comprueba tu CPU y tu GPU y **prueba a codificar vídeo con cada codificador por hardware que tenga tu FFmpeg**: NVIDIA (NVENC), Intel (Quick Sync), AMD (AMF) y Apple (VideoToolbox). Recomienda el más rápido que de verdad funciona, comprueba si Whisper puede usar una GPU NVIDIA y lee la memoria de tu GPU para decir si el ordenador podría generar vídeo con IA en local. Después te pregunta lo poco que no puede detectar: tus cámaras, si grabas en Log, tus idiomas, tus marcas y adónde van los vídeos terminados. Todo se guarda en `~/.video-editor/my-setup.md`, así que nunca pregunta dos veces.

Los renders de trabajo usan el codificador por hardware por velocidad. La exportación final usa siempre `libx264` a alta calidad, así que el resultado se ve igual en cualquier ordenador.

## Instalación

La skill es un plugin de Claude Code. En Claude Code, escribe estos dos comandos (o pégalos en una terminal con `claude` delante, sin la barra):

```
/plugin marketplace add malenaaza/video-editor-skill
```

```
/plugin install video-editor@malenaaza
```

El plugin tiene dos skills, y estos comandos instalan las dos: **video-editor** (editar los vídeos que grabas) y **puppet-video** (marionetas animadas que dicen un guion, sin nadie a cámara).

Reinicia Claude Code y pide una edición ("edita este vídeo para Reels: ...") o un vídeo con marionetas ("haz un vídeo con marionetas en el que Lola pide un café en inglés"). La primera vez comprueba tu ordenador y te hace unas pocas preguntas de configuración; el primer vídeo con marionetas también instala sus herramientas de voz y de sincronización labial.

**¿Ya la instalaste de la forma antigua** (una carpeta `video-editor` copiada en `~/.claude/skills/`)? Di "actualiza mi skill de video-editor" (o *update my video-editor skill*). Claude actualiza esa copia y luego te pasa al plugin: instala el plugin, hace una copia de seguridad de la carpeta antigua y la quita, para que Claude no encuentre la skill dos veces. Tus ajustes en `~/.video-editor/` se quedan como están.

Funciona en tu ordenador, así que está pensado para Claude Code (la terminal, las extensiones de IDE o la pestaña Code de la aplicación de escritorio de Claude). En un chat normal de Claude.ai no puede acceder a tus archivos ni a tus herramientas instaladas.

### Actualización

Las actualizaciones del plugin llegan por el sistema de plugins de Claude Code. Escribe `/plugin`, abre **Marketplaces**, elige **malenaaza** y actualiza, o activa **auto-update** ahí una vez para que las versiones nuevas lleguen solas. Después empieza una sesión nueva de Claude Code. Si lo permites (te lo pregunta una vez), Claude también comprueba una vez por semana y te avisa en una línea cuando hay una versión nueva; solo contacta con GitHub y no envía nada sobre ti.

- **Tus ajustes están a salvo.** Viven en `~/.video-editor/my-setup.md`, fuera de la skill, y una actualización nunca los toca. Los ajustes de cada vídeo (`retouch.json`) están en la carpeta de ese vídeo.
- **Por favor, no edites los archivos de la propia skill.** Las preferencias van en tus ajustes, y Claude las guarda ahí cuando le pides un cambio ("menos desenfoque", "pon siempre mi logo aquí").
- **¿Quieres tu propia versión de la skill?** Haz una copia del repositorio en GitHub (un "fork") y añade tu copia como marketplace.
- **Sin el sistema de plugins:** aún puedes copiar la carpeta `plugins/video-editor/skills/video-editor` en `~/.claude/skills/` y decir "actualiza mi skill de video-editor" para actualizarla. Para los vídeos con marionetas, copia también ahí `plugins/video-editor/skills/puppet-video`, al lado (usa los scripts del editor de vídeo). Un clon de desarrollador enlazado ahí se actualiza con `git pull`.

### Qué instala en el primer uso

En el primer uso te guía para instalar lo que falte:

- FFmpeg 7+ y yt-dlp
- Python 3.10–3.12 con `openai-whisper` y `faster-whisper`
- Para el retoque, el desenfoque y la comprobación de la boca: `mediapipe` y `opencv-python`, más los modelos de cara y de manos de MediaPipe de Google
- Opcional: Node 20+ para los gráficos de Remotion, rembg para recortar productos en las portadas, y un modelo RNNoise (o `deep-filter` de DeepFilterNet) para quitar ruido
- Si grabas en Log: la LUT oficial del fabricante de tu cámara, que descargas tú
- Para los vídeos con marionetas: Piper (`piper-tts`, las voces) y sus archivos de voz, y Rhubarb Lip Sync (las formas de la boca)

## Qué está probado

Se desarrolló y usó en Windows 11 con un portátil Intel (gráficos Intel Arc, Quick Sync), con vídeos en español y en inglés. Los ajustes de codificadores NVIDIA, AMD y Apple, la transcripción con CUDA y los comandos de macOS y Linux están incluidos pero todavía no se han probado en hardware real. Cada codificador se prueba antes de usarse, así que nunca se elige un ajuste que no funcione en tu ordenador. Los informes y los arreglos son bienvenidos.

Los umbrales de color de la máscara de piel se ajustaron con pieles de claras a medias. La skill le dice a Claude que compruebe la máscara y los ajuste en el primer retoque de cada persona (mira `skin_cr_min` en `scripts/retouch/settings.py`). Los valores de un vídeo van en un `retouch.json` en la carpeta de ese vídeo, para no editar nunca los propios scripts.

## ¿Has encontrado un error, o tienes una idea?

Díselo a Claude con tus propias palabras: "la piel se ve mal en 3:32", "ojalá pudiera añadir música". Guarda una nota en tu ordenador y se ofrece a enviársela al autor. Si dices que sí, escribe un informe corto (sin nombres, carpetas personales, fotogramas ni vídeos), te lo enseña y te da un enlace que lo abre en GitHub ya rellenado: solo pulsas Enviar (hace falta una cuenta gratuita de GitHub). Si hay una dirección de correo configurada, puedes enviarlo por correo.

Los arreglos y las ideas nuevas te llegan al actualizar: "Actualiza mi skill de video-editor" (o *Update my video-editor skill*).

## Pruebas y cambios

`tests/test_skill.py` ejecuta el plan de cortes, los subtítulos y los archivos de filtros sobre un clip pequeño generado (necesita Python, FFmpeg y numpy; la prueba de la clave de color también necesita OpenCV). GitHub la ejecuta en cada envío. `CHANGELOG.md` enumera lo que trae cada actualización.
