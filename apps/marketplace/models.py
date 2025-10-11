from django.db import models
from django.conf import settings

class Store(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    description = models.TextField()

class Transaction(models.Model):
    class TransactionStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        PAID = 'PAID', 'Paid'
        ESCROW = 'ESCROW', 'Escrow'
        AWAITING_PICKUP = 'AWAITING_PICKUP', 'Awaiting Pickup'
        RELEASED = 'RELEASED', 'Escrow Released'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    payment_gateway_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)