# Diseño: club de clientes de Carnicería Joaquin

## Objetivo

Que los clientes vuelvan más seguido, premiando las visitas. Lo usan en el mostrador dos personas mayores con poca experiencia en informática, y el cliente ve la pantalla, así que tiene que ser simple y vistoso.

## Decisiones

- **Sin mensajes a clientes:** no se usa WhatsApp, para no molestarlos.
- **Sin conexión con la caja:** el monto se carga a mano en cada visita, para tener el historial completo. El descuento se aplica a mano en la caja.
- **Local:** Python estándar y SQLite en la PC del negocio, atendiendo solo a esa PC.
- **Cumpleaños sin año:** se guardan día y mes, porque el año no hace falta.
- **Montos en pesos enteros:** el descuento se redondea al peso más cercano.

## Recorrido

DNI → ficha → sumar visita → monto. Si hay beneficio: descuento e importe final → confirmar. Si no hay: se registra y aparece el cartel con la promoción alcanzable más cercana.

Los movimientos se ven al final de Promociones, no en la navegación principal, porque son solo para el negocio.

## Promociones

Hay dos tipos, que no se mezclan:

- **Para todos:** ofertas del negocio, como Ganga Meat y Cuenta DNI. Tienen días y fechas, se muestran en el inicio cuando están vigentes y son solo informativas: no calculan nada, porque se cobran en la caja.
- **Beneficios del club:** individuales, según las visitas de cada cliente. Tienen un mecanismo, un beneficio (porcentaje, pesos o regalo), un piso, un techo y fechas opcionales. Mecanismos: racha semanal, racha acumulada, tarjeta de sellos, cumpleaños, día flojo, compra grande, bienvenida, volviste, fechas especiales y cliente histórico.

La racha semanal da 5% en la segunda visita de la semana y 10% en la tercera. Los demás valores iniciales son provisorios y los definen los dueños: racha acumulada (10% cada 4 semanas) y cumpleaños (15%).

## Estilo

Sigue la marca: logo, negro y rojo, títulos condensados en mayúsculas e íconos en círculos negros, como las historias destacadas de Instagram. Se suma el celeste como color de apoyo. Se carga con el teclado físico, sin teclado en pantalla.

## Fuera de esta versión

Página para clientes, sorteos, referidos, reportes, contraseña para la pestaña Promociones e instalador para Windows.
