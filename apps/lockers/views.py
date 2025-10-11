from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Delivery, Locker, LockerLog
from .permissions import IsCourierUser, IsOwnerUser
from .services import BlynkAPIService
from .tasks import send_notification_task

class VerifyDeliveryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCourierUser]

    def post(self, request, *args, **kwargs):
        receipt_number = request.data.get('receipt_number')
        if not receipt_number:
            return Response({'error': 'Receipt number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            delivery = Delivery.objects.get(receipt_number=receipt_number, status=Delivery.DeliveryStatus.PENDING)
            inbound_locker = delivery.locker
            
            if inbound_locker.status != Locker.LockerStatus.AVAILABLE:
                return Response({'error': 'Inbound locker is currently occupied.'}, status=status.HTTP_409_CONFLICT)

            blynk_service = BlynkAPIService(token=inbound_locker.blynk_device_token)
            success, message = blynk_service.set_virtual_pin(pin=inbound_locker.blynk_vpin_control, value=1)

            if not success:
                return Response({'error': 'Failed to communicate with the locker.', 'details': message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            delivery.status = Delivery.DeliveryStatus.VERIFIED
            delivery.save()

            inbound_locker.status = Locker.LockerStatus.OCCUPIED
            inbound_locker.last_opened_by = request.user
            inbound_locker.save()
            
            LockerLog.objects.create(
                locker=inbound_locker,
                user=request.user,
                action=LockerLog.Action.OPEN,
                details=f"Courier verified receipt: {receipt_number}"
            )
            
            return Response({'message': 'Receipt verified. Locker is open.'}, status=status.HTTP_200_OK)

        except Delivery.DoesNotExist:
            return Response({'error': 'Invalid or already processed receipt number.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConfirmDepositWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            delivery = Delivery.objects.get(status=Delivery.DeliveryStatus.VERIFIED)
            inbound_locker = delivery.locker
            storage_locker = Locker.objects.filter(type=Locker.LockerType.STORAGE, status=Locker.LockerStatus.AVAILABLE).first()
            if not storage_locker:
                return Response({'error': 'No available storage locker.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            delivery.status = Delivery.DeliveryStatus.COMPLETED
            delivery.save()
            
            inbound_locker.status = Locker.LockerStatus.AVAILABLE
            inbound_locker.save()
            
            storage_locker.status = Locker.LockerStatus.OCCUPIED
            storage_locker.save()

            LockerLog.objects.create(locker=inbound_locker, action=LockerLog.Action.DEPOSIT, details="Item moved to storage locker.")
            LockerLog.objects.create(locker=storage_locker, action=LockerLog.Action.DEPOSIT, details=f"Item from receipt {delivery.receipt_number} stored.")

            owner_user_id = 1 
            send_notification_task.delay(
                user_id=owner_user_id, 
                message=f"Barang Anda dengan resi {delivery.receipt_number} telah berhasil disimpan."
            )
            return Response({'message': 'Deposit confirmed.'}, status=status.HTTP_200_OK)
        except Delivery.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class OpenStorageLockerView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerUser]

    def post(self, request, *args, **kwargs):
        locker_number = request.data.get('locker_number')
        otp = request.data.get('otp')

        if not otp or otp != "123456":
            return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            storage_locker = Locker.objects.get(number=locker_number, type=Locker.LockerType.STORAGE, status=Locker.LockerStatus.OCCUPIED)

            blynk_service = BlynkAPIService(token=storage_locker.blynk_device_token)
            success, message = blynk_service.set_virtual_pin(pin=storage_locker.blynk_vpin_control, value=1)

            if not success:
                return Response({'error': 'Failed to communicate with the locker.', 'details': message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            storage_locker.status = Locker.LockerStatus.AVAILABLE
            storage_locker.last_opened_by = request.user
            storage_locker.save()
            
            LockerLog.objects.create(
                locker=storage_locker,
                user=request.user,
                action=LockerLog.Action.RETRIEVE,
                details=f"Owner retrieved item from storage locker."
            )

            return Response({'message': 'Locker is open. Please retrieve your item.'}, status=status.HTTP_200_OK)
        except Locker.DoesNotExist:
            return Response({'error': 'Locker not found or is not occupied.'}, status=status.HTTP_404_NOT_FOUND)