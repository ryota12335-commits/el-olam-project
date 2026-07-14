from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash
import mysql.connector

app = Flask(__name__, template_folder='.')
app.secret_key = 'olam_security_secret_key_2026'

def obtener_conexion():
    return mysql.connector.connect(
        host="aribert.helioho.st",
        port=3306,
        user="aribert_olam",
        password="12345689",
        database="aribert_OLAM",
        auth_plugin="mysql_native_password",
        autocommit=True
    )


# ================================================================
# VISTAS DE NAVEGACIÓN (CON CONTROL DE ACCESO PRE_CONFIGURADO)
# ================================================================

@app.route('/')
def portada_inicio():
    return render_template('administracion/inicio.html')

@app.route('/login')
def login_page():
    return render_template('administracion/login.html')

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if 'username' not in session: 
        return redirect(url_for('login_page'))
    
    if session.get('rol') == 'Encargado de almacén':
        return redirect(url_for('productos'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT v.id_venta, v.dni_ruc, c.nombre AS nombre_cliente,
                       v.id_producto, a.nombre AS nombre_producto,
                       v.cantidad, v.total, v.puntos
                FROM ventas v
                LEFT JOIN clientes c ON v.dni_ruc = c.dni_ruc
                LEFT JOIN articulos a ON v.id_producto = a.id_producto
                ORDER BY v.id_venta DESC
                LIMIT 20
            """)
            lista_ventas = cursor.fetchall()
    finally:
        conn.close()
        
    return render_template('ventas/ventas.html', colaborador=session.get('colaborador', 'Usuario'), lista_ventas=lista_ventas)

@app.route('/usuarios')
def vista_usuarios():
    if 'username' not in session:
        return redirect(url_for('login_page'))
        
    if session.get('rol') not in ['Administrador', 'Supervisor']:
        if session.get('rol') == 'Cajero':
            return redirect(url_for('ventas'))
        else:
            return redirect(url_for('productos'))
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id, colaborador, username, rol FROM usuarios")
            lista_usuarios = cursor.fetchall()
    finally:
        conn.close()
        
    return render_template('administracion/usuarios.html', usuarios=lista_usuarios, colaborador=session.get('colaborador', 'Usuario'))

@app.route('/guardar_usuario', methods=['POST'])
def guardar_usuario():
    if 'username' not in session or session.get('rol') not in ['Administrador', 'Supervisor']:
        return redirect(url_for('login_page'))

    user_id = request.form.get('id_usuario')
    colaborador = request.form.get('colaborador_nombre') # Coincide con el name del HTML
    username = request.form.get('username')
    password = request.form.get('password')
    rol = request.form.get('rol')

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            if user_id: # LÓGICA DE EDICIÓN
                if password: # Si se escribe contraseña, se actualiza
                    cursor.execute("UPDATE usuarios SET colaborador=%s, username=%s, password=%s, rol=%s WHERE id=%s", 
                                   (colaborador, username, password, rol, user_id))
                else: # Si no, se actualiza sin cambiar la contraseña
                    cursor.execute("UPDATE usuarios SET colaborador=%s, username=%s, rol=%s WHERE id=%s", 
                                   (colaborador, username, rol, user_id))
                flash("Usuario actualizado correctamente.", "success")
            else: # LÓGICA DE CREACIÓN
                cursor.execute("INSERT INTO usuarios (colaborador, username, password, rol) VALUES (%s, %s, %s, %s)", 
                               (colaborador, username, password, rol))
                flash("Usuario registrado exitosamente.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('vista_usuarios'))

# Cambia esto en tu app.py
@app.route('/eliminar_usuario/<int:id>', methods=['POST']) # Cambiado a POST
def eliminar_usuario(id):
    if 'username' not in session or session.get('rol') != 'Administrador':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('vista_usuarios'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
            flash("Usuario eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar: {str(e)}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for('vista_usuarios'))

# ================================================================
# GESTIÓN DE CLIENTES Y FIDELIZACIÓN (CONEXIÓN REAL)
# ================================================================

@app.route('/clientes', methods=['GET'])
def clientes():
    if 'username' not in session: return redirect(url_for('login_page'))
    busqueda = request.args.get('buscar', '').strip()
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            if busqueda:
                cursor.execute("SELECT * FROM clientes WHERE dni_ruc LIKE %s OR nombre LIKE %s", (f"%{busqueda}%", f"%{busqueda}%"))
            else:
                cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC")
            lista_clientes = cursor.fetchall()
    finally: conn.close()
    return render_template('clientes/clientes.html', lista_clientes=lista_clientes, colaborador=session.get('colaborador'), busqueda=busqueda)

@app.route('/guardar_cliente', methods=['POST'])
def guardar_cliente():
    dni, nombre = request.form.get('dni_ruc'), request.form.get('nombre')
    conn = obtener_conexion()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO clientes (dni_ruc, nombre, telefono, correo, tipo_cliente, puntos) VALUES (%s, %s, %s, %s, %s, 0)", 
                           (dni, nombre, request.form.get('telefono'), request.form.get('correo'), request.form.get('tipo_cliente')))
            flash("Cliente registrado.", "success")
    finally: conn.close()
    return redirect(url_for('clientes'))

@app.route('/eliminar_cliente/<dni_ruc>')
def eliminar_cliente(dni_ruc):
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("DELETE FROM clientes WHERE dni_ruc = %s", (dni_ruc,))
            flash("Cliente eliminado.", "success")
    finally: conn.close()
    return redirect(url_for('clientes'))

@app.route('/editar_cliente/<dni_ruc>', methods=['GET'])
def editar_cliente(dni_ruc):
    # Esta ruta simplemente redirige a la página de clientes 
    # enviando los datos del cliente seleccionado para "llenar" el formulario
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM clientes WHERE dni_ruc = %s", (dni_ruc,))
            cliente_edit = cursor.fetchone()
            # Necesitarás cargar también la lista completa para la tabla
            cursor.execute("SELECT * FROM clientes")
            lista_clientes = cursor.fetchall()
    finally:
        conn.close()
    return render_template('clientes/clientes.html', lista_clientes=lista_clientes, cliente_edit=cliente_edit)

@app.route('/actualizar_cliente', methods=['POST'])
def actualizar_cliente():
    dni = request.form['dni_ruc']
    nombre = request.form['nombre']
    telefono = request.form['telefono']
    correo = request.form['correo']
    tipo = request.form['tipo_cliente']
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""UPDATE clientes SET nombre=%s, telefono=%s, correo=%s, tipo_cliente=%s 
                              WHERE dni_ruc=%s""", (nombre, telefono, correo, tipo, dni))
            flash("Cliente actualizado con éxito.", "success")
    finally:
        conn.close()
    return redirect(url_for('clientes'))

# --- RUTAS DE PREMIOS ---

@app.route('/api/productos')
def api_productos():
    conn = obtener_conexion()

    try:
        with conn.cursor(dictionary=True) as cursor:

            cursor.execute("""
                SELECT
                    id_producto,
                    nombre,
                    precio,
                    categoria,
                    stock
                FROM articulos
                ORDER BY nombre
            """)

            return jsonify(cursor.fetchall())

    finally:
        conn.close()
@app.route('/procesar_canje', methods=['POST'])
def procesar_canje():
    dni = request.form['dni']
    id_prod = request.form['id_producto']
    # Capturamos la cantidad enviada por el formulario
    cantidad = int(request.form.get('cantidad', 1)) 
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            # Obtenemos el precio unitario del producto
            cursor.execute("SELECT nombre, precio FROM articulos WHERE id_producto = %s", (id_prod,))
            prod = cursor.fetchone()
            
            # Cálculo del total de puntos a descontar: Precio Unitario * Cantidad
            puntos_totales = int(prod['precio']) * cantidad 
            
            # Realizamos el descuento en la tabla clientes
            cursor.execute("UPDATE clientes SET puntos = puntos - %s WHERE dni_ruc = %s AND puntos >= %s", 
                           (puntos_totales, dni, puntos_totales))
            
            if cursor.rowcount > 0:
                # Insertamos en el historial incluyendo la cantidad
                cursor.execute("INSERT INTO historial_premios (dni_ruc, nombre_producto, puntos_descontados, cantidad) VALUES (%s, %s, %s, %s)", 
                               (dni, prod['nombre'], puntos_totales, cantidad))
                flash(f"Canje exitoso: {cantidad} x {prod['nombre']} ({puntos_totales} pts)", "success")
            else:
                flash("Error: Puntos insuficientes para realizar el canje solicitado.", "danger")
    finally:
        conn.close()
    return redirect(url_for('clientes'))

# ================================================================
# GESTIÓN DE PRODUCTOS (TABLA ARTICULOS)
# ================================================================

@app.route('/productos', methods=['GET'])
def productos():
    if 'username' not in session: 
        return redirect(url_for('login_page'))
        
    colaborador = session.get('colaborador', 'Usuario')
    busqueda = request.args.get('buscar', '').strip()
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            if busqueda:
                query = """SELECT id_producto, nombre, marca, presentacion, categoria, precio, stock 
                           FROM articulos 
                           WHERE id_producto LIKE %s OR nombre LIKE %s 
                           ORDER BY id_producto ASC"""
                cursor.execute(query, (f"%{busqueda}%", f"%{busqueda}%"))
            else:
                query = "SELECT id_producto, nombre, marca, presentacion, categoria, precio, stock FROM articulos ORDER BY id_producto ASC"
                cursor.execute(query)
            lista_productos = cursor.fetchall()
    finally:
        conn.close()
        
    lista_tuplas = [
        (p['id_producto'], p['nombre'], p['marca'], p['presentacion'], p['categoria'], p['precio'], p['stock']) 
        for p in lista_productos
    ]
        
    return render_template('almacen/productos.html', 
                           lista_productos=lista_tuplas, 
                           colaborador=colaborador, 
                           busqueda=busqueda,
                           producto_edit=None)


@app.route('/guardar_producto', methods=['POST'])
def guardar_producto():
    if 'username' not in session:
        return redirect(url_for('login_page'))

    id_producto = request.form.get('id_producto', '').strip().upper()
    nombre = request.form.get('nombre', '').strip()
    marca = request.form.get('marca', '').strip()
    presentacion = request.form.get('presentacion', '').strip()
    categoria = request.form.get('categoria')
    precio = float(request.form.get('precio', 0.0))
    stock = int(request.form.get('stock', 0))
    es_edicion = request.form.get('es_edicion') == 'true'

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            if es_edicion:
                query = """UPDATE articulos 
                           SET nombre=%s, marca=%s, presentacion=%s, categoria=%s, precio=%s, stock=%s 
                           WHERE id_producto=%s"""
                cursor.execute(query, (nombre, marca, presentacion, categoria, precio, stock, id_producto))
                flash("Producto actualizado correctamente en el inventario.", "success")
            else:
                cursor.execute("SELECT id_producto FROM articulos WHERE id_producto = %s", (id_producto,))
                if cursor.fetchone():
                    flash(f"Error: El código de producto '{id_producto}' ya se encuentra registrado.", "danger")
                    return redirect(url_for('productos'))
                    
                cursor.execute("SELECT nombre FROM articulos WHERE nombre = %s", (nombre,))
                if cursor.fetchone():
                    flash(f"Error: Un producto con el nombre '{nombre}' ya existe.", "danger")
                    return redirect(url_for('productos'))

                query = """INSERT INTO articulos (id_producto, nombre, marca, presentacion, categoria, precio, stock) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (id_producto, nombre, marca, presentacion, categoria, precio, stock))
                flash("Nuevo producto guardado con éxito.", "success")
    except Exception as e:
        flash(f"Error operativo en la base de datos: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('productos'))


@app.route('/editar_producto/<id_producto>', methods=['GET'])
def editar_producto(id_producto):
    if 'username' not in session:
        return redirect(url_for('login_page'))
        
    colaborador = session.get('colaborador', 'Usuario')
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id_producto, nombre, marca, presentacion, categoria, precio, stock FROM articulos WHERE id_producto = %s", (id_producto,))
            p_edit = cursor.fetchone()
            
            cursor.execute("SELECT id_producto, nombre, marca, presentacion, categoria, precio, stock FROM articulos ORDER BY id_producto ASC")
            lista_productos = cursor.fetchall()
    finally:
        conn.close()
        
    lista_tuplas = [
        (p['id_producto'], p['nombre'], p['marca'], p['presentacion'], p['categoria'], p['precio'], p['stock']) 
        for p in lista_productos
    ]
    
    producto_edit_tupla = None
    if p_edit:
        producto_edit_tupla = (p_edit['id_producto'], p_edit['nombre'], p_edit['marca'], p_edit['presentacion'], p_edit['categoria'], p_edit['precio'], p_edit['stock'])
    
    return render_template('almacen/productos.html', 
                           lista_productos=lista_tuplas, 
                           colaborador=colaborador, 
                           producto_edit=producto_edit_tupla, 
                           busqueda="")


@app.route('/eliminar_producto/<id_producto>', methods=['GET'])
def eliminar_producto(id_producto):
    if 'username' not in session:
        return redirect(url_for('login_page'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("DELETE FROM articulos WHERE id_producto = %s", (id_producto,))
        flash("Producto eliminado correctamente del sistema.", "success")
    except Exception as e:
        flash(f"No se pudo eliminar el producto: {str(e)}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('productos'))


# ================================================================
# LOGOUT Y LOGIN PROCESS
# ================================================================

@app.route('/procesar-login', methods=['POST'])
def procesar_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            user = cursor.fetchone()
    finally:
        conn.close()
    
    if not user:
        flash("El nombre de usuario no existe.", "error")
        return redirect(url_for('login_page'))
    
    if user['password'] != password:
        flash("La contraseña ingresada es incorrecta. Inténtelo de nuevo.", "error")
        return redirect(url_for('login_page'))
        
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['rol'] = user['rol']
    session['colaborador'] = user['colaborador'] 
    
    if user['rol'] in ['Administrador', 'Supervisor']:
        return redirect(url_for('vista_usuarios'))
    elif user['rol'] == 'Cajero':
        return redirect(url_for('ventas'))
    elif user['rol'] == 'Encargado de almacén':
        return redirect(url_for('productos'))
    else:
        return redirect(url_for('login_page'))

@app.route('/procesar_venta', methods=['POST'])
def procesar_venta():
    if 'username' not in session:
        return redirect(url_for('login_page'))

    id_venta = request.form.get('id_venta', '').strip()
    tipo_cliente = request.form.get('tipo_cliente')
    dni = request.form.get('dni_ruc', '').strip()
    id_producto = request.form.get('id_producto')
    cantidad = float(request.form.get('cantidad') or 0)

    # ==========================
    # VALIDACIONES DEL DOCUMENTO
    # ==========================

    if tipo_cliente == "GENERAL" or not dni:
        dni = "00000000"
    elif tipo_cliente == "DNI":
        if len(dni) != 8:
            flash("El DNI debe tener exactamente 8 dígitos.", "danger")
            return redirect(url_for('ventas'))
    elif tipo_cliente == "RUC":
        if len(dni) != 11:
            flash("El RUC debe tener exactamente 11 dígitos.", "danger")
            return redirect(url_for('ventas'))

    conn = obtener_conexion()

    try:
        with conn.cursor(dictionary=True) as cursor:

            # ==========================
            # VALIDAR CLIENTE (Solo si NO es general)
            # ==========================
            if dni != "00000000":
                cursor.execute(
                    "SELECT puntos FROM clientes WHERE dni_ruc=%s",
                    (dni,)
                )
                cliente = cursor.fetchone()
                if not cliente:
                    flash("El cliente no está registrado.", "danger")
                    return redirect(url_for('ventas'))

            # ==========================
            # VALIDAR PRODUCTO
            # ==========================
            cursor.execute(
                "SELECT precio, stock, categoria FROM articulos WHERE id_producto=%s",
                (id_producto,)
            )
            producto = cursor.fetchone()

            if not producto:
                flash("Producto inexistente.", "danger")
                return redirect(url_for('ventas'))

            # ==========================
            # VALIDAR STOCK
            # ==========================
            if cantidad > float(producto["stock"]):
                flash(
                    f"Stock insuficiente. Disponible: {producto['stock']}",
                    "danger"
                )
                return redirect(url_for('ventas'))

            precio = float(producto["precio"])
            total = round(precio * cantidad, 2)

            # ==========================
            # CALCULAR PUNTOS
            # ==========================
            categoria = producto.get("categoria") or ""

            if dni == "00000000":
                puntos = 0
            elif categoria.lower() == "combustibles":
                puntos = round(cantidad, 3)
            else:
                puntos = 0

            # =====================================================
            # EDITAR VENTA
            # =====================================================
            if id_venta:
                cursor.execute("""
                    SELECT dni_ruc, id_producto, cantidad, puntos
                    FROM ventas
                    WHERE id_venta=%s
                """, (id_venta,))
                anterior = cursor.fetchone()

                if anterior:
                    # Devolver stock anterior
                    cursor.execute("""
                        UPDATE articulos
                        SET stock=stock+%s
                        WHERE id_producto=%s
                    """, (anterior["cantidad"], anterior["id_producto"]))

                    # Devolver puntos anteriores (Solo si el cliente anterior no era GENERAL)
                    if anterior["dni_ruc"] != "00000000" and anterior["dni_ruc"] is not None:
                        cursor.execute("""
                            UPDATE clientes
                            SET puntos=GREATEST(0, puntos-%s)
                            WHERE dni_ruc=%s
                        """, (anterior["puntos"], anterior["dni_ruc"]))

                # Guardamos la venta
                cursor.execute("""
                    UPDATE ventas
                    SET dni_ruc=%s,
                        id_producto=%s,
                        cantidad=%s,
                        total=%s,
                        puntos=%s
                    WHERE id_venta=%s
                """, (dni, id_producto, cantidad, total, puntos, id_venta))

                # Descontar nuevo stock
                cursor.execute("""
                    UPDATE articulos
                    SET stock=stock-%s
                    WHERE id_producto=%s
                """, (cantidad, id_producto))

                # Asignar nuevos puntos (Solo si el cliente actual no es GENERAL)
                if dni != "00000000":
                    cursor.execute("""
                        UPDATE clientes
                        SET puntos=puntos+%s
                        WHERE dni_ruc=%s
                    """, (puntos, dni))

                venta_id_final = id_venta
                flash("Venta actualizada correctamente.", "success")

            # =====================================================
            # NUEVA VENTA
            # =====================================================
            else:
                cursor.execute("""
                    INSERT INTO ventas
                    (dni_ruc, id_producto, cantidad, total, puntos)
                    VALUES(%s, %s, %s, %s, %s)
                """, (dni, id_producto, cantidad, total, puntos))

                venta_id_final = cursor.lastrowid

                # Descontar stock
                cursor.execute("""
                    UPDATE articulos
                    SET stock=stock-%s
                    WHERE id_producto=%s
                """, (cantidad, id_producto))

                # Sumar puntos (Solo si no es cliente GENERAL)
                if dni != "00000000":
                    cursor.execute("""
                        UPDATE clientes
                        SET puntos=puntos+%s
                        WHERE dni_ruc=%s
                    """, (puntos, dni))

                flash("Venta registrada correctamente.", "success")

    finally:
        conn.close()

    return redirect(url_for('comprobante', id_venta=venta_id_final))


@app.route('/editar_venta/<int:id_venta>', methods=['GET'])
def editar_venta(id_venta):
    if 'username' not in session:
        return redirect(url_for('login_page'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM ventas WHERE id_venta = %s", (id_venta,))
            venta_edit = cursor.fetchone()

            cursor.execute("""
                SELECT v.id_venta, v.dni_ruc, c.nombre AS nombre_cliente,
                       v.id_producto, a.nombre AS nombre_producto,
                       v.cantidad, v.total, v.puntos
                FROM ventas v
                LEFT JOIN clientes c ON v.dni_ruc = c.dni_ruc
                LEFT JOIN articulos a ON v.id_producto = a.id_producto
                ORDER BY v.id_venta DESC
                LIMIT 20
            """)
            lista_ventas = cursor.fetchall()
    finally:
        conn.close()

    if not venta_edit:
        flash("La venta que intenta editar no existe.", "danger")
        return redirect(url_for('ventas'))

    return render_template('ventas/ventas.html', colaborador=session.get('colaborador', 'Usuario'),
                           lista_ventas=lista_ventas, venta_edit=venta_edit)


@app.route('/eliminar_venta/<int:id_venta>', methods=['POST'])
def eliminar_venta(id_venta):
    if 'username' not in session:
        return redirect(url_for('login_page'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT dni_ruc, id_producto, cantidad, puntos FROM ventas WHERE id_venta = %s", (id_venta,))
            venta = cursor.fetchone()

            if venta:
                # Revertimos el impacto de la venta en el stock y en los puntos del cliente
                cursor.execute("UPDATE articulos SET stock = stock + %s WHERE id_producto = %s",
                               (venta['cantidad'], venta['id_producto']))
                cursor.execute("UPDATE clientes SET puntos = puntos - %s WHERE dni_ruc = %s",
                               (venta['puntos'], venta['dni_ruc']))
                cursor.execute("DELETE FROM ventas WHERE id_venta = %s", (id_venta,))
                flash("Venta eliminada. Stock y puntos revertidos correctamente.", "success")
            else:
                flash("La venta indicada no existe.", "danger")
    except Exception as e:
        flash(f"Error al eliminar la venta: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('ventas'))


@app.route('/comprobante/<int:id_venta>', methods=['GET'])
def comprobante(id_venta):
    if 'username' not in session:
        return redirect(url_for('login_page'))

    conn = obtener_conexion()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT v.id_venta, v.dni_ruc, v.cantidad, v.total, v.puntos, v.fecha_venta,
                       c.nombre AS nombre_cliente, c.puntos AS puntos_totales,
                       a.nombre AS nombre_producto, a.precio AS precio_unitario
                FROM ventas v
                LEFT JOIN clientes c ON v.dni_ruc = c.dni_ruc
                LEFT JOIN articulos a ON v.id_producto = a.id_producto
                WHERE v.id_venta = %s
            """, (id_venta,))
            venta = cursor.fetchone()
    finally:
        conn.close()

    if not venta:
        flash("El comprobante solicitado no existe.", "danger")
        return redirect(url_for('ventas'))

    return render_template('ventas/comprobante.html', venta=venta, colaborador=session.get('colaborador', 'Usuario'))

@app.route('/api/buscar_cliente/<dni>')
def buscar_cliente(dni):

    conn = obtener_conexion()

    try:

        with conn.cursor(dictionary=True) as cursor:

            cursor.execute("""
                SELECT
                    nombre,
                    tipo_cliente,
                    puntos
                FROM clientes
                WHERE dni_ruc=%s
            """,(dni,))

            cliente = cursor.fetchone()

            if cliente:

                return jsonify({
                    "encontrado": True,
                    "nombre": cliente["nombre"],
                    "tipo": cliente["tipo_cliente"],
                    "puntos": cliente["puntos"]
                })

            return jsonify({"encontrado": False})

    finally:
        conn.close()


@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente de forma segura.", "info")
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)