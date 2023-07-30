import argparse
import sys
import threading
import time
import smtp_mail_sending as smtp
import imap_mail_receiving as imap
import connection as conn
import communication as comm
from unique_id import MailID
from mail_subjects import MailSubject


# **** Kommandozeilenargumente parsen ****
parser = argparse.ArgumentParser()
# Die folgenden Daten müssen von jedem Benutzer individuell angepasst werden.
# Änderungen der Werte beim Parameter 'default' möglich.
# Nach dem Programmstart werden dies Daten nicht mehr verändert
parser.add_argument('-sock_port', help="Browser-Socket-Port. 8000 by default (type = int)", default=8000, type=int)
parser.add_argument('-lin_usr', help='Linux user-name. This user has access to the mailbox to which the other end sends mails. (type = str)', default='', type=str)
parser.add_argument('-lin_usr_pw', help='the password of the linux user. When fetching the mails, authentication with this password is necessary. (type = str)', default='', type=str)
parser.add_argument('-send_addr', help='the e-mail address of the sender (away from this end). (type = str)', default='', type=str)
parser.add_argument('-recv_addr', help='the e-mail address of the receiver (on the other end). (type = str)', default='', type=str)
args = parser.parse_args()

if len(args.lin_usr) == 0 or len(args.lin_usr_pw) == 0 or len(args.send_addr) == 0 or len(args.recv_addr) == 0:
    print('Fehler: keiner der Parameter "linux-user", "linux-user-passwort", "sender-address", "receiver-address", '
          'darf leer sein. Bitte übergeben sie jedem Parameter einen gültigen Wert.')
    sys.exit(1)

try:
    # Die Anzahl der Verbindungen die ein Socket von Außen akzeptiert.
    max_connection = 1
    # jeder Thread, der in der Main-Methode erzeugt wird, erhält eine Referenz auf dieses Objekt
    glob = conn.GlobalAttributes(args.lin_usr, args.lin_usr_pw, args.send_addr, args.recv_addr,
                                 args.sock_port, socket_host='localhost', smtp_server_host='localhost',
                                 smtp_server_port=25, imap_server_host='localhost', imap_server_port=143,
                                 network_buffer_size=8192, timeout=1.0, max_timeout=30.0)
except KeyboardInterrupt:
    print("\n[*] User has requested an interrupt")
    print("[*] Application Exiting.....")
    sys.exit(0)

if __name__ == '__main__':
    # Dieser Socket steht dem Browser zum Senden und Empfangen von Daten zur verfügung
    sock = conn.provide_a_socket_to_a_browser(glob.socket_host, glob.socket_port, max_connection)
    # ein einziger IMAP-Server um Mails beim Mail-Server abzuholen
    # jeder Thread bekommt eine Referenz auf dieses Objekt.
    mail = imap.provide_imap_server(glob.linux_user, glob.linux_password, glob.imap_server_host, glob.imap_server_port)
    # initiales Löschen aller Mails in einer Mailbox
    imap.mailbox_cleanup_with_one_criterion(mail, 'ALL')
    # ein Schlüssel zu einem Schloss, mit dem kritische Programmabschnitte entsperrt werden müssen.
    # der Schlüssel existiert nur ein einziges Mal.
    lock = threading.Lock()
    initial_id = 0
    # Nur für die innere While-Schleife gedacht. Falls für eine Verbindung,
    # niemals eine Bestätigung empfangen wird, wird sie ignoriert.
    timeout = 5.0
    try:
        while True:
            browser_conn_sock, addr, first_request_from_browser = conn.browser_establishes_new_connection(sock, glob.network_buffer_size, timeout=glob.timeout)
            print('neuer Wunsch zum Verbinden | sock-name = ' + str(browser_conn_sock.getsockname()) + ' | sock-peername = ' + str(browser_conn_sock.getpeername()))
            initial_id_as_string = '-' + str(initial_id) + '.'
            local_mail_id_obj = MailID()
            verbindung_bestaetigt = False
            smtp_server = smtp.SMTPServer(glob.smtp_server_host, glob.smtp_server_port)
            smtp.wish_to_connect_mail(smtp_server, glob.sender_mail_address, glob.receiver_mail_address, initial_id_as_string)  # = -1. , -2. , -3. , ...
            start = time.time()
            while not verbindung_bestaetigt:
                with lock:
                    connection_ID_mails = imap.receive_mails_by_subject(mail, (MailSubject.CONNECTION_ID.value + initial_id_as_string))
                    # Falls ein Verbindungswunsch von der Webserver-Seite bestätigt wurde,
                    # geht es im Anschluss mit einem neuen Thread für diese Verbindung weiter.
                    if len(connection_ID_mails) > 0:
                        connection_ID = imap.pop_connection_id(connection_ID_mails, mail)
                        final_connection_ID = ('+' + str(connection_ID) + '.').strip()
                        verbindung_bestaetigt = True
                if not verbindung_bestaetigt:
                    time.sleep(0.1)
                if time.time() - start > timeout:
                    break
            if verbindung_bestaetigt:
                smtp.send_byte_data(smtp_server, glob.sender_mail_address, glob.receiver_mail_address, first_request_from_browser, final_connection_ID, local_mail_id_obj)
                smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address, final_connection_ID, MailSubject.DATA_IS_COMING.value)
                print('Daten vom Browser_sock empfangen [ ' + final_connection_ID + ' ] : ' + str(first_request_from_browser))
                new_conn = threading.Thread(target=comm.start_communication_at_browserside, args=(browser_conn_sock, final_connection_ID, local_mail_id_obj, glob, mail, lock))
                new_conn.start()
            initial_id -= 1
    except KeyboardInterrupt:
        sock.close()
        print("\n[*] Keyboard - Graceful Shutdown")
        print('* Die Anzahl aller Threads (inkl. Master) vor dem Ende ist %d *' % threading.active_count())
        sys.exit(0)
