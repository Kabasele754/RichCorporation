from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models_verification import VerificationDocument
from .serializers_verification import (
    VerificationUploadSerializer,
    VerificationDocSerializer,
)


class VerifyUploadIdView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = VerificationUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc = serializer.save(user=request.user, status="PENDING")

        return Response(
            VerificationDocSerializer(doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class VerifyMyDocsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VerificationDocument.objects.filter(user=request.user).order_by("-created_at")
        data = VerificationDocSerializer(qs[:10], many=True, context={"request": request}).data
        return Response({"results": data})


class VerifyConfirmView(APIView):
    """
    POST /api/auth/verify/confirm/
    body: { "password": "...", "document_id": 123 }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = (request.data.get("password") or "").strip()
        document_id = request.data.get("document_id")

        if not password or not document_id:
            return Response(
                {"detail": "password and document_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ✅ check password
        user = authenticate(username=request.user.username, password=password)
        if not user:
            return Response({"detail": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            doc = VerificationDocument.objects.get(id=document_id, user=request.user)
        except VerificationDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ Mark doc as pending (already) and set user "verified" request flag in profile map
        # --> Ici tu peux: mettre un champ is_verified dans un Profile model
        # Pour l’instant: tu peux stocker dans un JSON (si ton API renvoie profile dict)
        # Sinon, laisse seulement doc.status PENDING.

        return Response(
            {
                "detail": "Verification submitted. Awaiting approval.",
                "document": VerificationDocSerializer(doc, context={"request": request}).data,
            }
        )
