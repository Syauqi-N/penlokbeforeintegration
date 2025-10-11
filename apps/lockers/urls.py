from django.urls import path
from .views import VerifyDeliveryView, ConfirmDepositWebhookView, OpenStorageLockerView

urlpatterns = [
    path('inbound/verify-delivery/', VerifyDeliveryView.as_view(), name='verify-delivery'),
    path('inbound/confirm-deposit/', ConfirmDepositWebhookView.as_view(), name='confirm-deposit-webhook'),
    path('storage/open/', OpenStorageLockerView.as_view(), name='open-storage-locker'),
]