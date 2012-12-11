from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from myproject.gcm.models import Device, Song, Cluster, Event

class DeviceAdmin(admin.ModelAdmin):
    list_display = ['cluster_id', 'modified_date', 'is_active']
    search_fields = ('cluster_id',)
    list_filter = ['is_active']
    date_hierarchy = 'modified_date'
    readonly_fields = ('reg_id',)
    actions = ['send_test_message']

    def send_test_message(self, request, queryset):
        for device in queryset:
            device.send_message('GCM: Test message')
        self.message_user(request, _("All messages were sent."))
    send_test_message.short_description = _("Send test message")


admin.site.register(Device, DeviceAdmin)
admin.site.register([Song, Cluster, Event])
