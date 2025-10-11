from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')

urlpatterns = [
    path('store/me/', views.MyStoreView.as_view(), name='my-store'),
    path('', include(router.urls)),
    path('transactions/create/', views.CreateTransactionView.as_view(), name='create-transaction'),
    path('transactions/deposit-item/', views.SellerDepositItemView.as_view(), name='seller-deposit-item'),
    path('transactions/retrieve-item/', views.BuyerRetrieveItemView.as_view(), name='buyer-retrieve-item'),
    path('webhooks/payment/', views.PaymentWebhookView.as_view(), name='payment-webhook'),
    path('webhooks/confirm-deposit/', views.ConfirmMarketplaceDepositWebhookView.as_view(), name='confirm-marketplace-deposit'),
    path('webhooks/confirm-retrieval/', views.ConfirmMarketplaceRetrievalWebhookView.as_view(), name='confirm-marketplace-retrieval'),
]