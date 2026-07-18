"""SQLAlchemy models. Importing this package registers all tables on Base.metadata."""
from app.models.decision import Recommendation, Substitution
from app.models.ml import (
    Forecast,
    ModelRun,
    PredictionExplanation,
    ShortagePrediction,
)
from app.models.ops import Alert, AuditLog, Notification
from app.models.reference import (
    AtcClass,
    Governorate,
    Medication,
    Pharmacy,
    Supplier,
    User,
)
from app.models.transactional import (
    DistributionRecord,
    ExternalSignal,
    ImportOrder,
    NationalStock,
    Order,
    OrderItem,
    Reservation,
    Return,
    SalesDaily,
    Shipment,
    ShortageHistory,
    StockBatch,
    StockLevel,
)

__all__ = [
    "AtcClass",
    "Medication",
    "Governorate",
    "Pharmacy",
    "Supplier",
    "User",
    "StockLevel",
    "StockBatch",
    "NationalStock",
    "SalesDaily",
    "Order",
    "OrderItem",
    "Reservation",
    "Return",
    "ImportOrder",
    "Shipment",
    "DistributionRecord",
    "ShortageHistory",
    "ExternalSignal",
    "ModelRun",
    "Forecast",
    "ShortagePrediction",
    "PredictionExplanation",
    "Recommendation",
    "Substitution",
    "Alert",
    "Notification",
    "AuditLog",
]
