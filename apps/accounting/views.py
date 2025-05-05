from rest_framework import viewsets
from .models import KhaznaTransaction
from .serializers import KhaznaTransactionSerializer
from rest_framework.permissions import IsAuthenticated


class KhaznaTransactionViewSet(viewsets.ModelViewSet):
    queryset = KhaznaTransaction.objects.all()
    serializer_class = KhaznaTransactionSerializer
    permission_classes = [IsAuthenticated]

