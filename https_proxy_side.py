import argparse
import sys
import time
import threading
import imap_mail_receiving as imap
import smtp_mail_sending as smtp
import connection as conn
import communication as comm
from unique_id import ConnectionID
from mail_subjects import MailSubject


# **** Kommandozeilenargumente parsen ****
parser = argparse.ArgumentParser()
# Die folgenden Daten müssen von jedem Benutzer individuell angepasst werden.
# Änderungen der Werte beim Parameter 'default' möglich.
# Nach dem Programmstart werden dies Daten nicht mehr verändert
parser.add_argument('-sock_port', help="Proxy-Port. 8888 by default. (type = int)", default=8888, type=int)  # Tinyproxy hört standardmäßig bei Port 8888 zu.
parser.add_argument('-lin_usr', help='linux user-name. This user has access to the mailbox to which the other end sends mails. (type = str)', default='', type=str)
parser.add_argument('-lin_usr_pw', help='the password of the linux user. When fetching the mails, authentication with this password is necessary. (type = str)', default='', type=str)
parser.add_argument('-send_addr', help='the e-mail address of the sender (away from this end). (type = str)', default='', type=str)
parser.add_argument('-recv_addr', help='the e-mail address of the receiver (on the other end). (type = str)', default='', type=str)
args = parser.parse_args()

if len(args.lin_usr) == 0 or len(args.lin_usr_pw) == 0 or len(args.send_addr) == 0 or len(args.recv_addr) == 0:
    print('Fehler: keiner der Parameter "linux-user", "linux-user-passwort", "sender-address", "receiver-address", '
          'darf leer sein. Bitte übergeben sie jedem Parameter einen gültigen Wert.')
    sys.exit(1)

try:
    # jeder Thread, der in der Main-Methode erzeugt wird, erhält eine Referenz auf dieses Objekt
    glob = conn.GlobalAttributes(args.lin_usr, args.lin_usr_pw, args.send_addr, args.recv_addr,
                                 args.sock_port, socket_host='localhost', smtp_server_host='localhost',
                                 smtp_server_port=25, imap_server_host='localhost', imap_server_port=143,
                                 network_buffer_size=8192, timeout=1.0, max_timeout=30.0)
except KeyboardInterrupt:
    print("\n[*] User has requested an interrupt")
    print("[*] Application Exiting.....")
    sys.exit(6)


if __name__ == "__main__":
    # ein einziger IMAP-Server um Mails beim Mail-Server abzuholen
    # jeder Thread bekommt eine Referenz auf dieses Objekt.
    imap_server = imap.provide_imap_server(glob.linux_user, glob.linux_password, glob.imap_server_host, glob.imap_server_port)
    # initiales Löschen aller Mails in einer Mailbox
    imap.mailbox_cleanup_with_one_criterion(imap_server, 'ALL')
    # ein Schlüssel zu einem Schloss, mit dem kritische Programmabschnitte entsperrt werden müssen.
    # der Schlüssel existiert nur ein einziges Mal.
    lock = threading.Lock()
    # ein Objekt das Verbindungs-IDs generiert.
    # Diese Seite und die Browserseite verwenden für eine Kommunikation die gleiche ID
    connection_id_object = ConnectionID()
    # Von Zeit zu Zeit, wenn keine Verbindung vorliegt, werden alle Mails aus der Mailbox gelöscht
    at_least_one_connection_is_established = False
    try:
        while True:
            with lock:
                # Mail mit Verbindungswunsch abrufen
                mail_ids = imap.receive_mails_by_subject(imap_server, MailSubject.WISH_TO_CONNECT.value)
                if len(mail_ids) > 0:
                    # eine ID, welche die Browserseite mitgesendet hat, wird aus einer Mail geholt.
                    initial_id = imap.pop_initial_id_from_connection_wish_message(mail_ids, imap_server)
                    connection_ID = connection_id_object.get_next_connection_id()
                    final_connection_ID = ('+' + str(connection_ID) + '.').strip()
                    smtp_server = smtp.SMTPServer(glob.smtp_server_host, glob.smtp_server_port)
                    # Die Initiale ID wird mit der finalen Verbindungs ID, welche von dieser Seite vergeben wird,
                    # zusammen zur Browserseite zurückgeschickt.
                    smtp.send_connection_id(smtp_server, glob.sender_mail_address, glob.receiver_mail_address, initial_id, connection_ID)
                    # Eine neue Verbindung zum HTTPS-Proxy wird über einen neuen Socket hergestellt.
                    proxy_conn_sock = conn.provide_a_socket_and_connect_to_a_https_proxy(glob.socket_host, glob.socket_port, timeout=glob.timeout)
                    print('neuer Wunsch zum Verbinden | sock-name = ' + str(proxy_conn_sock.getsockname()) + ' | sock-peername = ' + str(proxy_conn_sock.getpeername()))
                    # Hier wird ein neuer Thread für die neue Verbindung erzeugt und im Anschluss gestartet.
                    new_conn = threading.Thread(target=comm.start_communication_at_https_proxy_side, args=(proxy_conn_sock, final_connection_ID, glob, imap_server, lock))
                    new_conn.start()
                    at_least_one_connection_is_established = True
            # jede halbe Sekunde prüfen, ob ein neuer Verbindungswunsch vorliegt.
            time.sleep(0.5)
            '''if at_least_one_connection_is_established == True and threading.active_count() == 1: # hin und wieder, wenn keine Verbindung besteht, soll das Postfach komplett geleert werden.
                # logging.debug('+++++++++++++++++++++++++++++++++++ Der Master-Thread löscht alle Mails in der Mailbox +++++++++++++++++++++++++++++++++++')
                print('+++++++++++++++++++++++++++++++++++ Der Master-Thread löscht alle Mails in der Mailbox +++++++++++++++++++++++++++++++++++')
                mail.select('inbox')
                imap.mailbox_cleanup_with_one_criterion(mail, 'ALL')
                at_least_one_connection_is_established = False'''
    except KeyboardInterrupt:
        print("\n[*] Graceful Shutdown")
        print('+++++++++++++++++++++++++++++++++++ Die Anzahl aller Threads (inkl. Master) vor dem Ende ist %d +++++++++++++++++++++++++++++++++++' % threading.active_count())
        sys.exit(0)
