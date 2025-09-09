# 
import socket

HOST = "0.0.0.0"   # Escuchar en todas las interfaces
PORT = 9000        # Puerto que queremos abrir

# Crear el socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)  # hasta 5 conexiones en cola

print(f"Servidor escuchando en {HOST}:{PORT}...")

while True:
    conn, addr = server_socket.accept()
    print(f"Conexión establecida desde {addr}")
    conn.sendall(b"Hola, estas conectado al servidor en puerto 9000!\n")
    conn.close()
