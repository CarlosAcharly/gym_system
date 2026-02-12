from twilio.rest import Client
from django.conf import settings

def send_sms(to_phone, message):
    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    sms = client.messages.create(
    body=message,
    from_=settings.TWILIO_PHONE_NUMBER,
    to=to_phone,
    status_callback='https://TU_DOMINIO/notifications/sms/status/'
)


    return sms.sid
