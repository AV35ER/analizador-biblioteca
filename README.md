# Analizador Léxico de Reservas de Biblioteca

Python y Flask realizan el análisis léxico, construyen los AFND por Thompson, convierten a AFD y generan SVG mediante Graphviz en memoria. Conserva cinco tokens, quíntuplas, tablas, equivalencias, TXT multilínea y zoom. El navegador no implementa el analizador.

## Arquitectura gratuita

- **GitHub Free:** código y pruebas.
- **Render Free:** contenedor con Python 3.13, Flask, Gunicorn y el ejecutable Graphviz.
- **Netlify Free:** página estática, formulario y controles. El navegador consulta directamente la API de Render por HTTPS.

No se utiliza Render Starter, servicios de pago, pruebas temporales, tarjeta de crédito ni servicios para mantener artificialmente activo el servidor. Selecciona explícitamente los planes Free y no añadas métodos de pago. Si una plataforma exige verificación mediante tarjeta para tu cuenta, no continúes por ese camino: utiliza la alternativa local descrita al final. No se ha publicado ni conectado ninguna cuenta desde este proyecto.

### Por qué ya no usamos el proxy

Render Free se suspende después de 15 minutos sin tráfico y puede tardar alrededor de un minuto en reactivarse. Netlify corta las solicitudes de proxy a los 26 segundos. Esa combinación podía impedir incluso abrir la página. Fuentes: [Render Free](https://render.com/docs/free) y [Netlify proxy](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/).

Ahora Netlify sirve la introducción, definición del lenguaje y formulario sin contactar con Render. Únicamente al pulsar **Compilar**, el navegador:

1. Conserva una copia del texto y del archivo que se van a enviar.
2. Consulta `/healthz` directamente, con intentos de hasta 15 segundos, durante un máximo aproximado de tres minutos.
3. Muestra la espera y permite cancelarla. No hace peticiones periódicas mientras la página está inactiva.
4. Cuando el servidor responde, envía el formulario multipart a `/api/analizar`, con una espera máxima de 90 segundos.
5. Inserta los resultados generados por las mismas plantillas Flask y activa el selector y los controles de zoom.

Los fallos de red, páginas HTML de reactivación y respuestas transitorias durante la espera se reintentan. Si el análisis falla o tarda demasiado, la entrada permanece en el formulario para volver a pulsar Compilar. Un POST no se repite automáticamente. Cancelar detiene la espera del navegador; un análisis ya recibido puede terminar en el servidor.

Esto elimina el timeout del proxy, **no garantiza disponibilidad absoluta**. Si hay una caída, bloqueo de red o cuotas agotadas, el backend puede seguir inaccesible. La primera página depende únicamente de Netlify; el primer análisis puede necesitar varios minutos. Los límites gratuitos pueden pausar servicios. No actives ampliaciones de pago para superarlos. [Netlify Free](https://www.netlify.com/blog/introducing-netlify-free-plan/) y [cuotas de Render](https://render.com/docs/free).

## 1. Publicar el código en GitHub

Crea manualmente un repositorio vacío en GitHub Free, sin README inicial. Desde PowerShell, en la raíz del proyecto, reemplaza los valores del remoto:

```powershell
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "Preparar despliegue gratuito"
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

Revisa lo preparado antes del commit. Los archivos `.env`, claves, entornos virtuales, cachés y memoria local se excluyen mediante `.gitignore`. No incluyas credenciales. Si ya existe repositorio, omite `git init`; si ya existe `origin`, revisa `git remote -v` antes de cambiarlo. No uses un push forzado. El archivo vacío original `requierements.txt` se conserva; se utiliza `requirements.txt`.

## 2. Desplegar Render Free

Para evitar seleccionar accidentalmente un plan de pago:

1. En Render, New → Web Service → conecta el repositorio y selecciona `main`.
2. Elige **Docker** como lenguaje/runtime, Dockerfile `./Dockerfile`, contexto raíz y plan **Free**. No selecciones una prueba temporal de otro plan.
3. Deja Docker Command vacío. El Dockerfile instala Graphviz mediante apt, instala dependencias y ejecuta las pruebas.
4. Configura Health Check Path como `/healthz`. El puerto es `10000`, escuchando en `0.0.0.0`; Gunicorn lee `PORT`.
5. Crea el servicio sin añadir tarjeta. Copia la URL HTTPS real que te asigne Render.
6. En Environment añade `CORS_ORIGINS` con el origen exacto de tu futura página Netlify, por ejemplo el formato `https://NOMBRE-ELEGIDO.netlify.app`, sin barra final ni rutas. Si aún no conoces el nombre, completa este paso después de crear el proyecto Netlify y vuelve a desplegar Render.

También se incluye `render.yaml` con `plan: free`; al usar Blueprint, revisa que siga indicando Free y completa `CORS_ORIGINS`. Si el flujo de Blueprint pide tarjeta, prueba la creación manual del Web Service Free; si la cuenta también lo exige, no añadas una tarjeta.

Render usa `gunicorn --config gunicorn.conf.py app:app`. Durante el arranque, genera los diez SVG y los conserva en memoria antes de atender consultas. No se necesita disco persistente, base de datos ni SECRET_KEY para las funciones actuales. No actives FLASK_DEBUG. Python se fija mediante la imagen Docker, no mediante PYTHON_VERSION en Render.

La variable `CORS_ORIGINS` admite varios orígenes separados por comas. Usa únicamente los dominios que necesitas. Los previews de Netlify tienen orígenes distintos y no quedan autorizados automáticamente. No se usa `*` ni cookies entre dominios.

Fuente: [Docker en Render](https://render.com/docs/docker).

## 3. Publicar Netlify Free

1. En Netlify Free, Import an existing project → GitHub → mismo repositorio, rama `main`.
2. Usa la raíz como base. El TOML configura build `python generar_frontend.py`, publicación `netlify-public` y Python `3.13`.
3. En las variables de entorno de build añade **`RENDER_API_URL`** con el origen HTTPS real copiado de Render, sin rutas. No pongas una URL de Netlify en esta variable.
4. Ejecuta el deploy gratuito y elige un nombre disponible para la página. Si el panel requiere publicar explícitamente para hacerla pública, hazlo únicamente cuando estés listo para entregar.
5. Copia el origen Netlify exacto a **`CORS_ORIGINS`** en Render y aplica el cambio/redeploy.
6. Abre Netlify y pulsa Compilar. Puedes comprobarlo después de dejar Render más de 15 minutos sin tráfico: la página debe abrirse, mostrar la espera y analizar cuando Render responda.

No actives Netlify Forms ni añadas Functions o reglas de proxy. Netlify solo genera y sirve archivos estáticos. Instala los paquetes Python durante el build; no necesita el ejecutable Graphviz porque el build no genera autómatas. Las dos plataformas se comunican mediante el navegador.

`generar_frontend.py` reutiliza `templates/index.html`, por lo que no hay una segunda interfaz que mantener. `templates/resultados.html` comparte tablas, quíntuplas y gráficos entre el modo local y la API. El `index.html` generado se excluye de Git y se reconstruye en cada build. El build de Netlify falla si no se configura `RENDER_API_URL`; el marcador `.invalid` de `config.js` solo sirve como aviso local y nunca debe utilizarse como destino real.

**Solo debes completar dos valores:** `RENDER_API_URL` en Netlify y `CORS_ORIGINS` en Render. Un cambio en la primera variable necesita un nuevo build de Netlify. Un cambio de dominio Netlify requiere actualizar CORS en Render. Ninguno de esos valores es una contraseña.

## Comprobación antes de entregar

- `RESERVAR L025 U104 7;`: cinco tokens, cero errores y diez SVG al recorrer los cinco tokens.
- `RESERVAR X025 U104 7;`: cuatro tokens y error para `X025`.
- Carga un TXT UTF-8 con varias líneas y verifica tablas, quíntuplas y conjuntos de estados.
- Prueba Acercar, Alejar, Restablecer y el desplazamiento.
- Prueba cancelar durante la reactivación y volver a compilar sin perder la entrada.

El límite del TXT es 1 MiB (1.048.576 bytes). El backend comprueba el tamaño aunque el navegador lo haya validado. Los SVG viajan dentro de la respuesta de la API; no se leen imágenes locales. Las respuestas de API y salud llevan `Cache-Control: no-store`.

Desde tu entorno Python puedes comprobar directamente Render con:

```powershell
.\.venv\Scripts\python.exe verificar_http.py https://TU_ORIGEN_REAL_DE_RENDER
```

Ese script verifica el backend; no debe apuntarse a Netlify porque allí ya no existen las rutas Flask. La comunicación entre dominios debe probarse en el navegador publicado.

## Pruebas locales

Con Python y Graphviz instalados (`dot -V` debe funcionar), desde PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -v
node --test test_cliente.cjs
.\.venv\Scripts\python.exe app.py
```

Abre `http://127.0.0.1:5000`. Si `py` no funciona, usa la ruta del Python instalado para crear el entorno. El modo local conserva el formulario Flask completo y no necesita CORS ni Netlify.

Para probar también la página estática localmente, en otras terminales:

```powershell
.\.venv\Scripts\python.exe generar_frontend.py
.\.venv\Scripts\python.exe -m http.server 8080 --directory netlify-public
```

Solo para esa comprobación, cambia `netlify-public/config.js` a `window.BIBLIOTECA_API = "http://127.0.0.1:5000";` y arranca Flask con `$env:CORS_ORIGINS="http://127.0.0.1:8080"`. Abre exactamente ese origen. Restaura el marcador antes de subir cambios; en Netlify el build escribirá la URL real desde su variable de entorno.

Las pruebas Python comprueban algoritmos, equivalencia, epsilon, SVG/tablas/quíntuplas, límites, TXT, API, CORS y generación estática sin Graphviz. Las pruebas JavaScript simulan reactivación, HTML de espera, errores de red, timeout, cancelación, multipart y validaciones. Gunicorn requiere Unix: su prueba se omite en Windows. El workflow GitHub construye Docker y prueba Gunicorn en Linux; no despliega nada ni mantiene el servidor despierto.

## Respaldo gratuito más robusto

No es posible garantizar un primer análisis remoto inmediato con Render Free. Para una evaluación que deba funcionar incluso sin Internet, entrega también el código o un ZIP y utiliza **Flask + Graphviz localmente** con las instrucciones anteriores. Ventajas: mismos algoritmos, sin suspensión, cuotas, tarjeta ni servicios externos. Desventajas: hay que instalar Python/Graphviz y no proporciona por sí solo una dirección pública Netlify funcional sin backend remoto.

Si la universidad ofrece un servidor gratuito que permanezca encendido y permita contenedores, puedes alojar allí el mismo backend y cambiar únicamente `RENDER_API_URL` y CORS. Evita la suspensión de Render sin reescribir Python. Depende de que esa infraestructura exista y esté autorizada; no se presupone su disponibilidad.

No se han verificado Render, Netlify ni CORS en sus dominios de producción: esas pruebas requieren el despliegue real. El frontend estático con espera es la solución gratuita implementada para usar la dirección Netlify sin depender del timeout del proxy.
