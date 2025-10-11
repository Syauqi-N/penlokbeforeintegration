from django.db import models
from django.conf import settings

class Locker(models.Model):
    class LockerType(models.TextChoices):
        INBOUND = 'INBOUND', 'Inbound'
        STORAGE = 'STORAGE', 'Storage'
        MARKETPLACE = 'MARKETPLACE', 'Marketplace'

    class LockerStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    number = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20, choices=LockerType.choices)
    status = models.CharField(max_length=20, choices=LockerStatus.choices, default=LockerStatus.AVAILABLE)
    last_opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    blynk_device_token = models.CharField(max_length=255)
    blynk_vpin_control = models.IntegerField()
    blynk_vpin_sensor = models.IntegerField()

class LockerLog(models.Model):
    class Action(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        CLOSE = 'CLOSE', 'Close'
        DEPOSIT = 'DEPOSIT', 'Deposit'
        RETRIEVE = 'RETRIEVE', 'Retrieve'

    locker = models.ForeignKey(Locker, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    details = models.TextField(blank=True, null=True)

class Delivery(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified'
        DEPOSITED = 'DEPOSITED', 'Deposited in Locker 1'
        COMPLETED = 'COMPLETED', 'Moved to Locker 2'
        FAILED = 'FAILED', 'Failed'

    receipt_number = models.CharField(max_length=255, unique=True, help_text="Nomor Resi")
    courier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, limit_choices_to={'role': 'COURIER'})
    locker = models.ForeignKey(Locker, on_delete=models.PROTECT, limit_choices_to={'type': 'INBOUND'})
    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)