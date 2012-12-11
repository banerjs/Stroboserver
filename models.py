import json
import operator

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from myproject.gcm import beats
from myproject.gcm.api import send_gcm_message, parse_gcm_result

# Helper functions for Class Methods
def unregister(device):
   try:
       device.delete()
   except:
       pass

def reregister(device, nreg):
    device.reg_id = nreg
    try:
        device.save(force_update=True)
    except:
        pass

# Models present in the database
class Device(models.Model):
    cluster_id = models.CharField(max_length=50, verbose_name=_("Cluster ID"))
    reg_id = models.TextField(verbose_name=_("RegID"), unique=True)
    creation_date = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)
    modified_date = models.DateTimeField(verbose_name=_("Modified date"), auto_now=True)
    is_active = models.BooleanField(verbose_name=_("Is active?"), default=False)

    def __unicode__(self):
        return 'Cluster '+self.cluster_id+', Device '+str(self.id)

    class Meta:
        verbose_name = _("Device")
        verbose_name_plural = _("Devices")
        ordering = ['cluster_id', '-modified_date']

    @property
    def is_registered(self):
        """
        Check if we can send message to this device
        """
        pass

    def send_message(self, msg):
        """
        Send message to current device
        """
        return send_gcm_message(api_key=settings.GCM_APIKEY, reg_id=[self.reg_id], data=msg, collapse_key="D_Update")

    def save(self, debug=False, *args, **kwargs):
       if self.cluster_id != 'NONE':
          cluster = Cluster.objects.get(cluster_id=self.cluster_id)
          freq = int(cluster.frequency)
          msg = {'frequency':freq, 'cluster':self.cluster_id}
          try:
             ret = self.send_message(msg)
          except Exception as e:
             ret = e
          if debug:
             print ret
       super(Device, self).save(*args, **kwargs)


class Song(models.Model):
    song_name = models.CharField(max_length=200, verbose_name=_('Song Name'), unique=True)
    beat_frequencies = models.TextField(verbose_name=_('Beat Frequencies'))

    def __unicode__(self):
        return self.song_name

    def save_beats(self):
        music = beats.read_wave(settings.SONGS_DIR+self.song_name)
        energies = beats.get_subband_energies(music)
        music = beats.get_subband_beats(music,energies)
        data = beats.get_subchannel_beat(music, beats.get_beat_frequencies(music))
        return data

    def save(self, recreate=True, *args, **kwargs):
        if recreate:
            self.beat_frequencies = json.dumps(self.save_beats())
        super(Song, self).save(*args, **kwargs)

    def get_beats(self):
        return json.loads(self.beat_frequencies)


class Event(models.Model):
    event_name = models.CharField(max_length=500)
    current_song = models.ForeignKey(Song)

    def __unicode__(self):
        return self.event_name


class Cluster(models.Model):
    cluster_id = models.CharField(max_length=50)
    frequency = models.FloatField()
    event = models.ForeignKey(Event, null=False, blank=False)

    class Meta:
        unique_together = (('cluster_id', 'event'),)

    def __unicode__(self):
        return 'Cluster '+self.cluster_id+' at '+self.event.event_name

    def save(self, message=None, debug=False, *args, **kwargs):
        if message:
            self.send_message(message, debug)
        super(Cluster, self).save(*args, **kwargs)

    def send_message(self, msg, debug=False):
        devices = Device.objects.filter(cluster_id=self.cluster_id)
        get_regs = operator.attrgetter('reg_id')
        
        if not devices:
            if debug:
                print 'No devices with cluster ID =', cluster
                return
        if debug:
            print 'Devices found =', devices

        try:
            reply = send_gcm_message(settings.GCM_APIKEY, map(get_regs, devices), msg, 'C_Update')
            results = parse_gcm_result(reply)
        except Exception as e:
            results = []
            reply = e

        if results:
            for i,result in enumerate(results):
                if result != 'OK':
                    if result[0] == 'reg_id':
                        reregister(devices[i], result[1])
                    else: #error received
                        if result[1] == 'NotRegistered' or result[1] == 'InvalidRegistration':
                            unregister(devices[i])
                        else: #Another error that we don't need to deal with yet
                            pass

        if debug:
            print 'Reply from server =', reply
            print 'Results =', results
