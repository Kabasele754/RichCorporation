# =========================================
# apps/library/services/loan.py
# =========================================
from django.utils import timezone
from apps.abc_apps.library.models import Item, Loan

def borrow_item(item_code: str, borrowed_by, issued_by=None, purpose="reading", purpose_detail="", due_at=None):
    item = Item.objects.get(code=item_code)
    if item.status != "available":
        raise ValueError("Item not available")

    loan = Loan.objects.create(
        item=item,
        borrowed_by=borrowed_by,
        issued_by=issued_by,
        purpose=purpose,
        purpose_detail=purpose_detail,
        due_at=due_at,
        borrowed_at=timezone.now(),
    )
    item.status = "borrowed"
    item.save(update_fields=["status"])
    return loan

def return_item(item_code: str, return_checked_by=None):
    item = Item.objects.get(code=item_code)

    loan = Loan.objects.filter(item=item, returned_at__isnull=True).order_by("-borrowed_at").first()
    if not loan:
        raise ValueError("No active loan found for this item")

    loan.returned_at = timezone.now()
    loan.return_checked_by = return_checked_by
    loan.save(update_fields=["returned_at", "return_checked_by"])

    item.status = "available"
    item.save(update_fields=["status"])
    return loan
