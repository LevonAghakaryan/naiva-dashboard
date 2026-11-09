from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import get_finance_service
from app.schemas.finance import CategoryIn, CategoryOut, FinancePageOut, MonthStr, TransactionIn, TransactionOut
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/page", response_model=FinancePageOut)
def page(
    month: MonthStr | None = Query(None, description="YYYY-MM; default = current month"),
    service: FinanceService = Depends(get_finance_service),
):
    """Everything the finance page shows for one month: cards, list, pending, calendar, charts."""
    return service.page(month)


# ---------- transactions ----------

@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(data: TransactionIn, service: FinanceService = Depends(get_finance_service)):
    return service.create_transaction(data)


@router.put("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, data: TransactionIn, service: FinanceService = Depends(get_finance_service)):
    """Edit a transaction (all fields are sent, like on create)."""
    return service.update_transaction(tx_id, data)


@router.post("/transactions/{tx_id}/confirm", response_model=TransactionOut)
def confirm_transaction(tx_id: int, service: FinanceService = Depends(get_finance_service)):
    """Pending → done («Ստացա» / «Վճարեցի»)."""
    return service.confirm_transaction(tx_id)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, service: FinanceService = Depends(get_finance_service)):
    service.delete_transaction(tx_id)
    return Response(status_code=204)


# ---------- categories ----------

@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, service: FinanceService = Depends(get_finance_service)):
    return service.create_category(data)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, service: FinanceService = Depends(get_finance_service)):
    """Its transactions move to «Այլ եկամուտ» / «Այլ ծախս». System categories can't be deleted."""
    service.delete_category(category_id)
    return Response(status_code=204)
