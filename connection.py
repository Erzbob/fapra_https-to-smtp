import socket
import sys


# Diese Klasse stellt ein Objekt bereit, dessen Attribute stellvertretend
# für individuelle Benutzereinstellungen stehen.
class GlobalAttributes:
    def __init__(self,
		         linux_user: str, linux_password: str,
		         sender_mail_address: str, receiver_mail_address: str,
		         socket_port: int, socket_host: str,
		         smtp_server_host: str, smtp_server_port: int,
		         imap_server_host: str, imap_server_port: int,
		         network_buffer_size: int,
		         timeout: float, max_timeout: float):
		    self.linux_user = linux_user
		    self.linux_password = linux_password
		    self.sender_mail_address = sender_mail_address
		    self.receiver_mail_address = receiver_mail_address
		    self.socket_port = socket_port
		    self.socket_host = socket_host
		    self.network_buffer_size = network_buffer_size
		    self.smtp_server_host = smtp_server_host
		    self.smtp_server_port = smtp_server_port
		    self.imap_server_host = imap_server_host
		    self.imap_server_port = imap_server_port
		    self.timeout = timeout
		    self.max_timeout = max_timeout


# Hierüber wird ein Socket-Objekt bereitgestellt, über den ein Browser mit dem Programm kommuniziert.
# Alle Daten, welche ein Browser an einen Webserver senden möchte, sendet der Browser an diesen Socket.
def provide_a_socket_to_a_browser(browser_host, browser_port, max_connection):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((browser_host, browser_port))
        sock.listen(max_connection)
        print('[*] Server started erfolgreich [ an Port ' + str(browser_port) + ' ]')
        return sock
    except Exception:
        print('[*] Unable to Initialize Socket')
        sys.exit(1)


# Wenn ein Browser eine neue Verbindung zu einem Webserver herstellen möchte, dann
# wird hier vom Browser-Socket ein neuer Ableger erstellt, der ausschließlich für
# die neue Verbindung bereitgestellt wird.
def browser_establishes_new_connection(sock: socket.socket, buffer_size, timeout: float):
    conn, addr = sock.accept()
    first_request = conn.recv(buffer_size)  # blockiert so lange, bis der Browser eine neue Verbindung öffnet
    conn.settimeout(timeout)
    return conn, addr, first_request


# Diese Methode erlaubt es dem Programm, ein neues Socket-Objekt zu erstellen,
# über welches es Daten an einen HTTPS-Proxy senden kann.
def provide_a_socket_and_connect_to_a_https_proxy(proxy_host, proxy_port, timeout: float):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((proxy_host, proxy_port))
        print('[*] Verbindung erfolgreich hergestellt [ an Port ' + str(proxy_port) + ' ]')
        return sock
    except Exception:
        print('[*] Unable to Initialize Socket')
        sys.exit(1)
