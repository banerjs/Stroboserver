from urllib2 import HTTPError

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from myproject.gcm import beats
from myproject.gcm.models import Device, Song, Cluster, Event
from myproject.gcm.api import send_gcm_message, parse_gcm_result

def parse_song(file_name, recreate=True):
   s = Song(song_name=file_name)
   s.save(recreate=recreate)

@csrf_exempt
def device(request):
    """
    Register device

    Args:
        database_id - previous reg_id
        reg_id - reg id from android app
        cluster_id - cluster_id of device
    """
    database_id = request.POST.get('database_id', None)
    if not database_id:
        return HttpResponseBadRequest()

    device, created = Device.objects.get_or_create(reg_id=database_id)
    if not created:
        device.reg_id = request.POST.get('reg_id')
    device.is_active = True
    device.cluster_id = request.POST.get('cluster_id')
    device.save()

    return HttpResponse()

@csrf_exempt
def delete(request):
    """
    Unregister device

    Args:
        database_id - id of device to be deleted
    """
    database_id = request.POST.get('database_id', None)
    if not database_id:
        return HttpResponseNotFound()

    try:
        device = Device.objects.get(reg_id=database_id)
        device.delete()
    except:
        return HttpResponseBadRequest()

    return HttpResponse()

@csrf_exempt
def cluster(request, debug=False):
   """
   Assign a new cluster to the device that sent this request.
   Assumption: There is only 1 event in the database. Later on match
   the cluster to an event.
   """
   event = Event.objects.get(event_name='CPSC434 Presentation')
   song = event.current_song
   song_data = song.get_beats()

   try:
      device = Device.objects.get(reg_id=request.POST.get('database_id', 0))
   except:
      return HttpResponseNotFound()
   newid = str(Cluster.objects.count()) # Make a more intelligent scheme later
   ncluster = Cluster(cluster_id=newid, event=event)
   device.cluster_id = newid
   device.save(force_update=True)

   data = sorted(song_data.iteritems(), key=lambda x: x[1][1], reverse=True) # Again a more intelligent scheme later
   freq = int(data[int(newid)%len(data)][1][0])

   if debug:
      print 'Data:', data
      print 'Freq:', freq
   msg = {'frequency': freq, 'cluster': newid}

   if debug:
      print 'Sending message:', msg

   ncluster.frequency = freq
   ncluster.save(msg, debug)

   return HttpResponse()
