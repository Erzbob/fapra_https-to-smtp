import imaplib
import sys
import socket
import threading
import time
import smtp_mail_sending as smtp
import imap_mail_receiving as imap
from unique_id import MailID
from mail_subjects import MailSubject
from connection import GlobalAttributes


def start_communication_at_https_proxy_side(sock: socket.socket, final_connection_id: str, glob: GlobalAttributes,
                                            mail: imaplib.IMAP4, lock: threading.Lock):
    smtp_server = smtp.SMTPServer(glob.smtp_server_host, glob.smtp_server_port)
    # ein Mail-ID-Objekt für diese Verbindung
    local_mail_id_obj = MailID()
    while 1:
        try:
            # Ab hier dreht sich alles um das Empfangen von E-Mails und das Senden an den Socket.
            data_received = False
            start = time.time()
            while not data_received:
                # wenn nach einer längeren Zeit keine Antwort
                # mehr von der Browser-Seite kommt, dann wird die Verbindung beendet
                if (time.time() - start) > glob.max_timeout:
                    sys.exit(0)
                with lock:
                    data_is_coming = imap.receive_mails_by_subject(mail, (
                            MailSubject.DATA_IS_COMING.value + final_connection_id))
                    # wurden Byte-Daten von der Browser-Seite angekündigt, ...
                    if len(data_is_coming) > 0:
                        imap.mailbox_cleanup_with_one_criterion(mail,
                                                                '(SUBJECT "' + (
                                                                            MailSubject.DATA_IS_COMING.value + final_connection_id) + '")')
                        start = time.time()
                        while not data_received:
                            if time.time() - start > glob.max_timeout:
                                sys.exit(0)
                            # ... dann werden die IDs der Mails, die die Daten enthalten, abgeholt ...
                            mail_ids_data = imap.receive_mails_by_subject(mail, (
                                    MailSubject.BYTE_DATA.value + final_connection_id))
                            if len(mail_ids_data) > 0:
                                # ... und die Byte-Daten aus den Mails extrahiert und an den Socket übergeben.
                                data = imap.pop_byte_data(mail_ids_data, mail)
                                for byte in data:
                                    sock.send(byte)
                                data_received = True
                                break
                            time.sleep(0.1)
                if not data_received:
                    # eine kurze Zeit warten, falls noch keine Daten angekommen sind
                    time.sleep(0.1)
            # Ab hier dreht sich alles um das Empfangen vom Socket
            data_from_socket_received = False
            full_response = b''
            try:
                while 1:
                    reply_from_https_proxy = sock.recv(glob.network_buffer_size)
                    if len(reply_from_https_proxy) > 0:
                        full_response += reply_from_https_proxy
                        if not data_from_socket_received:
                            data_from_socket_received = True
                    # Ein leeres Byte signalisiert das Ende für diese Verbindung. Der Socket wird nie mehr
                    # etwas hergeben, was kein leeres Byte ist.
                    else:
                        if data_from_socket_received:
                            smtp.send_byte_data(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                                full_response, final_connection_id, local_mail_id_obj)
                            smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                                      final_connection_id, MailSubject.DATA_IS_COMING.value)
                        smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                                  final_connection_id, MailSubject.END_OF_COMMUNICATION.value)
                        sys.exit(0)
            # der TimeoutError hat zu bedeuten, dass der https-Proxy, also der Webserver im moment keine
            # Daten mehr abrufbereit hat. Er benötigt zuerst wieder Daten von der Browser-Seite.
            except TimeoutError:
                # Es sind an dieser Stelle Daten vom Socket vorhanden
                if data_from_socket_received:
                    smtp.send_byte_data(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                        full_response, final_connection_id, local_mail_id_obj)
                    smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                              final_connection_id, MailSubject.DATA_IS_COMING.value)
                # An dieser Stelle sind keine Daten vom Socket vorhanden. Die Browser-Seite
                # hat also nicht mit Socket-Daten zu rechnen, sondern muss noch mehr Daten
                # zu dieser Seite der Verbindung senden.
                else:
                    smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                              final_connection_id, MailSubject.MORE_DATA_IS_NEEDED.value)
        except socket.error:
            sys.exit(1)


def start_communication_at_browserside(sock: socket.socket, final_connection_id: str, mail_id_object: MailID,
                                       glob: GlobalAttributes, mail: imaplib.IMAP4, lock: threading.Lock):
    smtp_server = smtp.SMTPServer(glob.smtp_server_host, glob.smtp_server_port)
    while 1:
        # Ab hier dreht sich alles um das Empfangen von E-Mails.
        new_data_per_mail_received = False
        more_data_is_needed_at_https_proxy_side = False
        close_conn = False
        start = time.time()
        while not new_data_per_mail_received:
            # wenn nach einer längeren Zeit keine Antwort mehr von der
            # Webserver-Seite kommt, dann wird die Verbindung beendet
            if (time.time() - start) > glob.max_timeout:
                sys.exit(0)
            with lock:
                more_data_is_needed_mails = imap.receive_mails_by_subject(mail, (
                        MailSubject.MORE_DATA_IS_NEEDED.value + final_connection_id))
                # Falls die Webserver-Seite noch mehr Daten von diesem Socket benötigt, dann
                # wird direkt zu der Stelle im Programm gesprungen, an der Daten vom Socket empfangen werden.
                if len(more_data_is_needed_mails) > 0:
                    imap.mailbox_cleanup_with_one_criterion(mail,
                                                            '(SUBJECT "' + (
                                                                    MailSubject.MORE_DATA_IS_NEEDED.value + final_connection_id) + '")')
                    more_data_is_needed_at_https_proxy_side = True
                    break
            with lock:
                data_is_coming = imap.receive_mails_by_subject(mail,
                                                               (MailSubject.DATA_IS_COMING.value + final_connection_id))
                # wurden Byte-Daten von der Webserver-Seite angekündigt,
                # dann soll die Schleife nicht noch einmal ausgeführt werden.
                if len(data_is_coming) > 0:
                    imap.mailbox_cleanup_with_one_criterion(mail,
                                                            '(SUBJECT "' + (
                                                                    MailSubject.DATA_IS_COMING.value + final_connection_id) + '")')
                    new_data_per_mail_received = True
            # Wenn im vorherigen Schleifendurchgang ein Aufruf zum Beenden der Verbindung empfangen wurde, ...
            if close_conn:
                # ... dann springe zum Programmabschnitt wo vom Socket empfangen wird,
                # falls eine Ankündigung für Byte-Daten empfangen wurde, ...
                if new_data_per_mail_received:
                    break
                # ... oder beende hier sofort die Verbindung, falls keine weiteren Daten
                # zur Abholung bereitstehen.
                else:
                    sys.exit(0)
            with lock:
                eoc_mail_id = imap.receive_mails_by_subject(mail, (
                        MailSubject.END_OF_COMMUNICATION.value + final_connection_id))
                # wurde eine Mail mit dem Aufruf zum Beenden der Verbindung empfangen,
                # dann wird dies für den nächsten Schleifendurchlauf vermerkt.
                if len(eoc_mail_id) > 0:
                    imap.mailbox_cleanup_with_one_criterion(mail, '(SUBJECT "' + (
                            MailSubject.END_OF_COMMUNICATION.value + final_connection_id) + '")')
                    close_conn = True
            # Falls noch keine Daten empfangen wurden, dann wird eine kurze Zeit abgewartet.
            if not new_data_per_mail_received:
                time.sleep(0.1)
        # Ab hier dreht sich alles um das Empfangen von E-Mails mit angekündigten Byte-Daten.
        # Auch hier, direkt im Anschluss werden die abgeholten Byte-Daten an den Socket übergeben.
        start = time.time()
        with lock:
            while 1:
                if time.time() - start > glob.max_timeout:
                    sys.exit(0)
                # hier wird noch einmal geprüft, ob der Webserver noch weitere Daten von diesem Socket benötigt.
                if more_data_is_needed_at_https_proxy_side:
                    # direkt an die Stelle im Programm springen, wo vom Socket empfangen wird.
                    break
                mail_ids_data = imap.receive_mails_by_subject(mail, (MailSubject.BYTE_DATA.value + final_connection_id))
                anzahl_empfangener_mails_mit_bytedaten = len(mail_ids_data)
                print(
                    'Die Länge der Mail-IDs-Liste die bei Verbindung ' + final_connection_id + ' für Byte-Daten empfangen wurde, betraegt: ' + str(
                        anzahl_empfangener_mails_mit_bytedaten))
                if anzahl_empfangener_mails_mit_bytedaten > 512:  # bei einer Puffergröße von 8 KB sind das 4 MB. Ich gehe daher davon aus, dass es sich dann um Video-Daten handelt
                    imap.mailbox_cleanup_with_one_criterion(mail, '(SUBJECT "' + final_connection_id + '")')
                    sys.exit(0)
                # Falls E-Mails mit Byte-Daten zur Abholung bereitstehen, ...
                if len(mail_ids_data) > 0:
                    # ... hole die Daten aus den E-Mails ...
                    data = imap.pop_byte_data(mail_ids_data, mail)
                    print(
                        'Daten aus Mails bei der Browserseite geholt. Verbindung ' + final_connection_id + ' | Anzahl der Daten = ' + str(
                            len(data)))
                    anzahl_zu_uebermittelnder_bytes = len(data)
                    # ... und sende die Daten an den Socket.
                    for byte in data:
                        try:
                            sock.send(byte)
                        except ConnectionResetError:
                            break
                        except BrokenPipeError:
                            break
                    # Wenn die Anzahl der Mails mit Byte-Daten mit der Anzahl der bytes, die dem Socket übergeben
                    # wurden, übereinstimmt, dann kann diese Schleife beendet werden
                    if anzahl_zu_uebermittelnder_bytes == anzahl_empfangener_mails_mit_bytedaten:
                        break
                # Falls im Moment keine Mails mit Daten angekommen sind, wird eine kurze Zeit gewartet.
                time.sleep(0.1)
        # Ab hier dreht sich alles um das Empfangen vom Socket und
        # das anschließende Senden der Byte-Daten-Mails an die Webserver-Seite.
        try:
            reply_from_browser = sock.recv(glob.network_buffer_size)  # empfange Daten vom Browser
            if len(reply_from_browser) > 0:
                smtp.send_byte_data(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                    reply_from_browser, final_connection_id, mail_id_object)
                smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                          final_connection_id, MailSubject.DATA_IS_COMING.value)
                print('Daten vom Browser_sock empfangen [ ' + final_connection_id + ' ] : ' + str(reply_from_browser))
            # Falls nur ein leeres Byte vom Socket zurückkommt, dann wird die Verbindung hier beendet
            else:
                sys.exit(0)
        # Der Socket gibt gar keine Daten mehr her, in dieser Runde.
        except socket.error:
            # Falls eine Aufforderung zum Beenden der Verbindung empfangen wurde,
            # dann wird jetzt die Verbindung beendet.
            if close_conn:
                sys.exit(0)
            # Der Socket hat später noch Daten. Der Browser hält diese aber noch zurück, da er vorher noch
            # Daten von einer anderen Verbindung erwartet. Beispiel: Bei der Website https://fernuni-hagen.de
            # "pausiert" der Browser den "Haupt-Thread" (mit der CONNECT-Methode) solange, bis er Daten
            # über den "Neben-Thread" (mit der POST-Methode) vom https-Proxy erhält.
            else:
                # der Socket wird auf einen hohen Timeout-Wert gesetzt. Dies soll
                # einen blockierenden Socket 'simulieren'.
                sock.settimeout(glob.max_timeout)
                try:
                    reply_from_browser = sock.recv(glob.network_buffer_size)  # empfange Daten vom Browser
                # Passiert erneut ein Timeout, dann wird die Verbindung beendet.
                except socket.error:
                    sys.exit(0)
                # Werden nichtleere Byte-Daten während dieser Zeit empfangen, dann geht die Kommunikation normal weiter.
                if len(reply_from_browser) > 0:
                    smtp.send_byte_data(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                        reply_from_browser, final_connection_id, mail_id_object)
                    smtp.send_flag_by_subject(smtp_server, glob.sender_mail_address, glob.receiver_mail_address,
                                              final_connection_id, MailSubject.DATA_IS_COMING.value)
                # Wird nur ein leeres Byte empfangen, dann wird die Verbindung beendet.
                else:
                    sys.exit(0)
                # Wurden Daten vom Socket empfange, dann wird er wieder auf den ursprünglichen
                # Timeout-Wert gesetzt.
                sock.settimeout(glob.timeout)
