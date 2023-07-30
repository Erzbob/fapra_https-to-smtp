import email
import imaplib
import base64
import time
import sys
from mail_subjects import MailSubject


# einen IMAP-Server bereitstellen, der Zugriff auf die 'inbox' beim Mailverzeichnis hat,
# in dem Postfix ankommende Mails ablegt
def provide_imap_server(user: str, password: str, imap_server_host: str, imap_server_port: int):
    try:
        # timeout =~ 278 Stunden =~ 11.57 Tage
        imap_server = imaplib.IMAP4(imap_server_host, imap_server_port, 1000000.0)
        imap_server.login(user, password)
        imap_server.select('inbox')
        return imap_server
    except imaplib.IMAP4.abort:
        print('Fehler beim Bereitstellen des IMAP4-Objekts')
        sys.exit(1)


# eine Liste von Mail-IDs anhand eines Betreffs abrufen
def receive_mails_by_subject(imap_server: imaplib.IMAP4, abrufbetreff):
    while 1:
        try:
            imap_server.select('inbox')
            abrufbetreff = '(SUBJECT "' + (str(abrufbetreff).strip()) + '")'
            status, mail_data = imap_server.search(None, abrufbetreff)
            mail_ids = []
            num_is_not_none = True
            for num in mail_data:
                if num is not None:
                    mail_ids += num.split()
                else:
                    num_is_not_none = False
                    break
            if num_is_not_none:
                return mail_ids
        except imaplib.IMAP4.abort:
            time.sleep(0.1)


# eine finale Verbindungs-ID aus einer Mail holen und die Mail anschließend löschen
def pop_connection_id(mail_ids, imap_server: imaplib.IMAP4):
    return subroutine_pop_integer(mail_ids, imap_server, MailSubject.CONNECTION_ID.value)


# eine initiale Verbindungs-ID aus einer Mail holen und die Mail anschließend löschen
def pop_initial_id_from_connection_wish_message(mail_ids, imap_server: imaplib.IMAP4):
    for i in mail_ids:
        status, mail_data = imap_server.fetch(i, '(RFC822)')  # RFC6854
        for response_part in mail_data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_subject = message['subject']
                initial_id = str(message.get_payload()).strip()
                mailbox_cleanup_with_one_criterion(imap_server, '(SUBJECT "' + mail_subject + '")')
                return initial_id


# Byte-Daten, welche für einen Browser oder https-Proxy gedacht sind,
# aus einer Mail holen und die Mail anschließend löschen
def pop_byte_data(mail_ids, imap_server: imaplib.IMAP4):
    list_of_bytes = []
    criteria_for_cleanup = []
    for i in mail_ids:
        status, mail_data = imap_server.fetch(i, '(RFC822)')
        for response_part in mail_data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_subject = message['subject']
                decoded_content = base64.b64decode(message.get_payload())
                list_of_bytes.append(decoded_content)
                criteria_for_cleanup.append('(SUBJECT "' + mail_subject + '")')
    if len(criteria_for_cleanup) > 0:
        mailbox_cleanup_with_more_criteria(imap_server, criteria_for_cleanup)
    return list_of_bytes


# einen ganzzahligen Wert aus einer Mail holen und die Mail anschließend löschen.
def subroutine_pop_integer(mail_ids, imap_server: imaplib.IMAP4,
                           subject):  # hier sollte ein Enum MailSubject verwendet werden
    for i in mail_ids:
        status, data = imap_server.fetch(i, '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                message = email.message_from_bytes(response_part[1])
                mail_subject = message['Subject']
                mail_content = message.get_payload()
                wanted_integer = int(mail_content)
                criterion_for_cleanup = '(SUBJECT "' + mail_subject + '")'
                mailbox_cleanup_with_one_criterion(imap_server, criterion_for_cleanup)
                return wanted_integer
    return -1


# eine Mail, anhand eines Kriteriums, aus einer Mailbox löschen.
# Das Kriterium ist in diesem Kontext ein E-Mail-Betreff.
def mailbox_cleanup_with_one_criterion(imap_server: imaplib.IMAP4, criterion_for_cleanup):
    typ, mail_data = imap_server.search(None, criterion_for_cleanup)
    for num in mail_data[0].split():
        imap_server.store(num, '+FLAGS', '\\Deleted')
    imap_server.expunge()


# mehrere Mails, anhand eines Kriteriums, aus einer Mailbox löschen.
# Das Kriterium ist in diesem Kontext ein E-Mail-Betreff.
def mailbox_cleanup_with_more_criteria(imap_server: imaplib.IMAP4, criteria_for_cleanup: list[str]):
    # hier werden gleich mehrerer Mails auf einmal gelöscht
    for criterion in criteria_for_cleanup:
        typ, mail_data = imap_server.search(None, criterion)
        for num in mail_data[0].split():
            imap_server.store(num, '+FLAGS', '\\Deleted')
    imap_server.expunge()
