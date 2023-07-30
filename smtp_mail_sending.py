import smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from unique_id import MailID
from mail_subjects import MailSubject


# diese Klasse stellt einen SMTP-Server bereit, über den E-Mails an den Mail-Server gesendet werden können.
class SMTPServer:
    def __init__(self, smtp_server_host: str, smtp_port: int):
        self.smtp_server = smtplib.SMTP(smtp_server_host, smtp_port)
        self.smtp_server.ehlo()


# eine E-Mail, welche für einen neuen Verbindungswunsch steht, an den Mail-Server senden
def wish_to_connect_mail(server: SMTPServer, sender: str, receiver: str, initial_id: str):  # Empfänger erwartet ein int
    text_msg = MIMEText(initial_id)
    text_msg['From'] = sender
    text_msg['To'] = receiver
    text_msg['Subject'] = MailSubject.WISH_TO_CONNECT.value
    server.smtp_server.sendmail(sender, receiver, text_msg.as_string())


# eine E-Mail, welche eine finale Verbindungs-ID enthält, an den Mail-Server senden
def send_connection_id(server: SMTPServer, sender: str, receiver: str, initial_id: str,
                       final_id: int):  # Empfänger erwartet ein str
    connection_id_as_string = str(final_id)
    text_msg = MIMEText(connection_id_as_string)
    text_msg['From'] = sender
    text_msg['To'] = receiver
    text_msg['Subject'] = MailSubject.CONNECTION_ID.value + initial_id
    server.smtp_server.sendmail(sender, receiver, text_msg.as_string())


# eine E-Mail, welche Byte-Daten enthält, die für einen Socket bestimmt sind, an den Mail-Server senden
def send_byte_data(server: SMTPServer, sender: str, receiver: str, data: bytes, unique_connection_id: str,
                   mail_id_object: MailID):  # Empfänger erwartet ein bytes
    byte_msg = MIMEBase('application', 'octet-stream')
    byte_msg['From'] = sender
    byte_msg['To'] = receiver
    byte_msg['Subject'] = MailSubject.BYTE_DATA.value + unique_connection_id + mail_id_object.get_next_mail_id()
    byte_msg.set_payload(data)
    encoders.encode_base64(byte_msg)
    byte_msg.add_header('Content-Disposition', f'attachment; filename={"some"}')
    msg = byte_msg.as_string()
    server.smtp_server.sendmail(sender, receiver, msg)


# eine E-Mail, welche ein bestimmtes Signal im Betreff enthält, an einen Mail-Server senden
def send_flag_by_subject(server: SMTPServer, sender: str, receiver: str, connection_id: str,
                         subject):  # Empfänger erwartet einen gewissen Betreff
    text_msg = MIMEText('')
    text_msg['From'] = sender
    text_msg['To'] = receiver
    text_msg['Subject'] = subject + connection_id
    server.smtp_server.sendmail(sender, receiver, text_msg.as_string())
