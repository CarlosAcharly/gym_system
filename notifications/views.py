from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import SMSNotification

@csrf_exempt
def sms_status_callback(request):
    sid = request.POST.get('MessageSid')
    status = request.POST.get('MessageStatus')

    if sid and status:
        SMSNotification.objects.filter(sid=sid).update(status=status)

    return HttpResponse('OK')
