from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction as db_transaction

from .models import Store, Product, Transaction
from .serializers import StoreSerializer, ProductSerializer, TransactionSerializer
from .permissions import IsStoreOwner
from .services import PaymentGatewayService
from apps.lockers.models import Locker
from apps.lockers.services import BlynkAPIService
from apps.lockers.tasks import send_notification_task

class MyStoreView(generics.RetrieveUpdateAPIView):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]
    
    def get_object(self):
        store, created = Store.objects.get_or_create(owner=self.request.user, defaults={'name': f"{self.request.user.username}'s Store"})
        self.check_object_permissions(self.request, store)
        return store

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsStoreOwner]

    def get_queryset(self):
        try:
            return Product.objects.filter(store__owner=self.request.user)
        except Store.DoesNotExist:
            return Product.objects.none()

    def perform_create(self, serializer):
        store = get_object_or_404(Store, owner=self.request.user)
        serializer.save(store=store)

class CreateTransactionView(generics.CreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        product = get_object_or_404(Product, id=request.data.get('product_id'))
        quantity = int(request.data.get('quantity', 1))
        
        if product.stock < quantity:
            return Response({"error": "Not enough stock."}, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            product.stock -= quantity
            product.save()
            transaction = Transaction.objects.create(
                buyer=request.user, seller=product.store.owner, product=product,
                quantity=quantity, total_price=product.price * quantity
            )
        
        pg_service = PaymentGatewayService()
        success, payment_url = pg_service.create_payment(
            transaction_id=transaction.id, amount=transaction.total_price,
            customer_details={'email': request.user.email, 'name': request.user.username}
        )
        if not success:
            return Response({"error": "Failed to create payment session."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = self.get_serializer(transaction)
        response_data = serializer.data
        response_data['payment_url'] = payment_url
        return Response(response_data, status=status.HTTP_201_CREATED)

class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transaction, id=request.data.get('transaction_id'))
        if request.data.get('payment_status') == 'success' and transaction.status == Transaction.TransactionStatus.PENDING:
            transaction.status = Transaction.TransactionStatus.ESCROW
            transaction.save()
            send_notification_task.delay(user_id=transaction.seller.id, message=f"Pembayaran untuk '{transaction.product.name}' berhasil.")
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_400_BAD_REQUEST)

class SellerDepositItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transaction, id=request.data.get('transaction_id'))
        if request.user != transaction.seller or transaction.status != Transaction.TransactionStatus.ESCROW:
            return Response({"error": "Action not allowed."}, status=status.HTTP_403_FORBIDDEN)
        
        locker = Locker.objects.filter(type=Locker.LockerType.MARKETPLACE, status=Locker.LockerStatus.AVAILABLE).first()
        if not locker:
            return Response({"error": "No available marketplace locker."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        blynk_service = BlynkAPIService(token=locker.blynk_device_token)
        success, _ = blynk_service.set_virtual_pin(pin=locker.blynk_vpin_control, value=1)
        if success:
            locker.status = Locker.LockerStatus.OCCUPIED
            locker.save()
            return Response({"message": "Locker is open. Please deposit the item."}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to open locker."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConfirmMarketplaceDepositWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        transaction = Transaction.objects.filter(status=Transaction.TransactionStatus.ESCROW).first()
        if transaction:
            transaction.status = Transaction.TransactionStatus.AWAITING_PICKUP
            transaction.save()
            otp = "654321"
            send_notification_task.delay(user_id=transaction.buyer.id, message=f"Barang '{transaction.product.name}' siap diambil. Kode OTP: {otp}")
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)

class BuyerRetrieveItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        transaction = get_object_or_404(Transaction, id=request.data.get('transaction_id'))
        if request.user != transaction.buyer or transaction.status != Transaction.TransactionStatus.AWAITING_PICKUP or request.data.get('otp') != "654321":
            return Response({"error": "Action not allowed or invalid OTP."}, status=status.HTTP_403_FORBIDDEN)

        locker = Locker.objects.filter(type=Locker.LockerType.MARKETPLACE, status=Locker.LockerStatus.OCCUPIED).first()
        blynk_service = BlynkAPIService(token=locker.blynk_device_token)
        success, _ = blynk_service.set_virtual_pin(pin=locker.blynk_vpin_control, value=1)
        if success:
            return Response({"message": "Locker is open. Please retrieve your item."}, status=status.HTTP_200_OK)
        return Response({"error": "Failed to open locker."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ConfirmMarketplaceRetrievalWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        transaction = Transaction.objects.filter(status=Transaction.TransactionStatus.AWAITING_PICKUP).first()
        if transaction:
            pg_service = PaymentGatewayService()
            success, _ = pg_service.release_escrow(transaction.id)
            if success:
                transaction.status = Transaction.TransactionStatus.RELEASED
                transaction.save()
                locker = Locker.objects.filter(type=Locker.LockerType.MARKETPLACE, status=Locker.LockerStatus.OCCUPIED).first()
                if locker:
                    locker.status = Locker.LockerStatus.AVAILABLE
                    locker.save()
                send_notification_task.delay(user_id=transaction.seller.id, message=f"Dana untuk '{transaction.product.name}' telah dilepaskan.")
                return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_204_NO_CONTENT)