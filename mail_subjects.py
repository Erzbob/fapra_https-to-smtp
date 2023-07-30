from enum import Enum


class MailSubject(Enum):
    BYTE_DATA = 'byte_data'
    CONNECTION_ID = 'connection_ID'
    DATA_IS_COMING = 'data_is_coming'
    END_OF_COMMUNICATION = 'EOC'
    MORE_DATA_IS_NEEDED = 'more_data_is_needed'
    WISH_TO_CONNECT = 'wish_to_connect'
