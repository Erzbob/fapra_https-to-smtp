
# stellt ein Objekt zur Verfügung, über das Verbindungs-IDs vergeben werden können
class ConnectionID:
    def __init__(self):
        self.connection_id = -1

    def get_next_connection_id(self):
        self.connection_id += 1
        return self.connection_id


# stellt ein Objekt zur Verfügung, über das für eine bestimmte Verbindungs-ID,
# zusätzlich noch Mail-IDs vergeben werden können. Bei jedem Senden von Byte-Daten
# mittels einer Mail, wird als Betreff für die Mail, eine Kombination aus (unter anderem)
# Verbindungs-ID und Mail-ID gewählt. Dies hat den Grund, dass Mails aus einem Postfach,
# anhand des Betreffs gelöscht werden können, ohne Gefahr zu laufen, dass andere Mails mit
# derselben Verbindungs-ID gelöscht werden.
class MailID:
    def __init__(self):
        self.mail_id = -1

    def get_next_mail_id(self):
        self.mail_id += 1
        return str(self.mail_id) + '.'
