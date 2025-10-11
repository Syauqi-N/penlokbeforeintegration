from rest_framework.permissions import BasePermission
from .models import Store

class IsStoreOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Store):
            return obj.owner == request.user
        return obj.store.owner == request.user

class IsTransactionParticipant(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.buyer or request.user == obj.seller