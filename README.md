# Club de clientes de Carnicería Joaquin

Programa local para anotar clientes, sumar visitas y aplicar promociones. Funciona en la PC del negocio, sin internet y sin instalar nada más que Python 3.

## Instalar en la PC del negocio

Necesita Windows 10 u 11 de 64 bits. No hace falta instalar Python ni Git.

1. Descargá [la última versión](https://github.com/fgallo11/carniceria-joaquin/releases/latest/download/ClubCarniceriaJoaquin.zip).
2. Extraela en una carpeta propia, por ejemplo `C:\Club Carniceria Joaquin`. No uses "Archivos de programa".
3. Hacé clic derecho en `Abrir Club de Clientes` > Enviar a > Escritorio (crear acceso directo).

La primera vez, Windows o el antivirus pueden mostrar un aviso porque el programa no está firmado. Se sigue con "Más información" y "Ejecutar de todos modos".

Para actualizar, extraé la versión nueva en la misma carpeta y aceptá reemplazar los archivos. **No borres la carpeta `datos`**: ahí están los clientes, y el `.zip` no la incluye.

## Abrirlo

- **PC del negocio (Windows):** doble clic en el acceso directo. El programa trae su propio Python.
- **Linux:** ejecutar `./iniciar.sh`.

Se abre en el navegador, en `http://localhost:8765/`. Solo se puede usar desde esa misma PC. En Windows no muestra ninguna ventana y sigue abierto hasta que se apaga la PC; otro doble clic vuelve a abrir el navegador.

## Uso diario

1. Ingresá el DNI y tocá **Buscar**. Si no está anotado, el programa ofrece anotarlo.
2. Tocá **Sumar la visita de hoy**.
3. Poné el total que marcó la caja. Se pide en todas las visitas.
4. Si tiene un beneficio, el programa muestra el descuento y lo que hay que cobrar. Aplicá ese descuento en la caja, porque este programa no está conectado con ella.
5. Si no tiene beneficio, aparece un cartel con su próximo premio.

En **Promociones** hay dos listas:

- **Para todos:** las ofertas del negocio, como Ganga Meat o Cuenta DNI. Se eligen los días y las fechas, y aparecen en el inicio cuando corresponde. Son informativas: se cobran en la caja como siempre.
- **Beneficios del club:** lo que gana cada cliente según sus visitas. Se prende o apaga cada uno y se cambian el porcentaje, el descuento máximo (techo), la compra mínima (piso) y las fechas.

Al final de **Promociones** están **Clientes** y **Movimientos**, solo para el negocio.

En **Clientes** se busca por nombre, DNI o estado, y cada perfil muestra los datos del cliente, su estado (activo, por perder la racha o dejó de venir), su racha, cuánto compró y ahorró, los beneficios que usó y sus últimos movimientos. Los datos del cliente se cambian desde su perfil.

En **Movimientos** se ven todas las visitas, con búsqueda por nombre o DNI y por fechas. Ahí se puede cambiar o anular una visita, recuperar una anulada y cargar una que quedó sin registrar. Al cargar a mano no se calculan premios: se guarda lo que realmente se cobró, y las rachas se actualizan solas.

## Reglas

- La semana va de lunes a domingo.
- Un cliente puede sumar más de una visita por día, y cada una cuenta para las promociones.
- Racha semanal: premia la segunda y la tercera visita de una misma semana.
- Racha acumulada: se perdona una semana sin venir. Dos semanas seguidas la cortan.
- Los descuentos no se acumulan: se aplica el mayor. Los regalos se entregan además del descuento.

## Copias de seguridad

Cada día se guarda una copia en `datos/copias/` y se conservan las últimas 30. Están en el mismo disco que el programa: si la PC se rompe, se pierden con ella. Conviene copiar la carpeta `datos` a un pendrive o a la nube cada tanto.

## Para desarrollo

```bash
python3 -m unittest discover -s tests
```

GitHub Actions corre las pruebas, arma el paquete y lo abre en Windows con cada cambio en `main`. Para publicar una versión, se crea y se sube una etiqueta `vX.Y.Z`.

- `reglas.py`: rachas, promociones y cálculos.
- `app.py`: servidor local y base de datos SQLite.
- `static/`: pantallas.
