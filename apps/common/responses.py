# =========================
# common/responses.py
# =========================
from rest_framework.response import Response

def ok(data=None, message="OK", status=200):
    return Response({"ok": True, "message": message, "data": data}, status=status)

def fail(message="Error", errors=None, status=400):
    return Response({"ok": False, "message": message, "errors": errors}, status=status)
