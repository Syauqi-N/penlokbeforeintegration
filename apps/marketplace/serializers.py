from rest_framework import serializers
from .models import Store, Product, Transaction
from apps.users.serializers import UserDetailSerializer

class StoreSerializer(serializers.ModelSerializer):
    owner = UserDetailSerializer(read_only=True)

    class Meta:
        model = Store
        fields = ['id', 'owner', 'name', 'description']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'store', 'name', 'price', 'stock', 'description']
        read_only_fields = ['store']

class TransactionSerializer(serializers.ModelSerializer):
    buyer = UserDetailSerializer(read_only=True)
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'