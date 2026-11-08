from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import get_finance_service
from app.schemas.finance import (
    CategoryIn,
    CategoryOut,
    DealIn,
    DealOut,
    DealPatch,
    DealsBoardOut,
    FinanceSummaryOut,
    MonthlyOut,
    MonthStr,
    SourcesOut,
    TransactionIn,
    TransactionOut,
    TransactionPatch,
    TransactionsOut,
    TxType,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/api/finance", tags=["finance"])

MonthQuery = Query(None, description="YYYY-MM; default = current month")


# ---------- read ----------

@router.get("/summary", response_model=FinanceSummaryOut)
def summary(month: MonthStr | None = MonthQuery, service: FinanceService = Depends(get_finance_service)):
    return service.summary(month)


@router.get("/monthly", response_model=MonthlyOut)
def monthly(
    month: MonthStr | None = MonthQuery,
    months: int = Query(6, ge=1, le=24),
    service: FinanceService = Depends(get_finance_service),
):
    return service.monthly(month, months)


@router.get("/sources", response_model=SourcesOut)
def sources(
    month: MonthStr | None = MonthQuery,
    type: TxType = Query("income"),
    service: FinanceService = Depends(get_finance_service),
):
    return service.sources(month, type)


# ---------- categories ----------

@router.get("/categories", response_model=list[CategoryOut])
def categories(service: FinanceService = Depends(get_finance_service)):
    return service.categories()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryIn, service: FinanceService = Depends(get_finance_service)):
    return service.create_category(data)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, service: FinanceService = Depends(get_finance_service)):
    service.delete_category(category_id)
    return Response(status_code=204)


# ---------- deals (kanban) ----------

@router.get("/deals", response_model=DealsBoardOut)
def deals(service: FinanceService = Depends(get_finance_service)):
    return service.board()


@router.post("/deals", response_model=DealOut, status_code=201)
def create_deal(data: DealIn, service: FinanceService = Depends(get_finance_service)):
    return service.create_deal(data)


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(deal_id: int, data: DealPatch, service: FinanceService = Depends(get_finance_service)):
    return service.update_deal(deal_id, data)


@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(deal_id: int, service: FinanceService = Depends(get_finance_service)):
    service.delete_deal(deal_id)
    return Response(status_code=204)


# ---------- transactions ----------

@router.get("/transactions", response_model=TransactionsOut)
def transactions(
    month: MonthStr | None = Query(None, description="YYYY-MM; only transactions up to the end of this month"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: TxType | None = Query(None, description="income | expense; empty = both"),
    category_id: int | None = Query(None),
    service: FinanceService = Depends(get_finance_service),
):
    return service.transactions(month, limit, offset, type, category_id)


@router.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(data: TransactionIn, service: FinanceService = Depends(get_finance_service)):
    return service.create_transaction(data)


@router.patch("/transactions/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, data: TransactionPatch, service: FinanceService = Depends(get_finance_service)):
    return service.update_transaction(tx_id, data)


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, service: FinanceService = Depends(get_finance_service)):
    service.delete_transaction(tx_id)
    return Response(status_code=204)
