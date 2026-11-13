from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "message": "Registration successful",
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
