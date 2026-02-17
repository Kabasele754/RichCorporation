# =========================
# common/responses.py
# =========================
from rest_framework.response import Response
from rest_framework import status

def ok(data=None, message="OK", status=200):
    return Response({"ok": True, "message": message, "data": data}, status=status)

def fail(message="Error", errors=None, status=400):
    return Response({"ok": False, "message": message, "errors": errors}, status=status)

def bad(message="Bad request", status_code=status.HTTP_400_BAD_REQUEST, data=None):
    payload = {"message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code)
