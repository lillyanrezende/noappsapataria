from pydantic import BaseModel
from typing import List, Optional, Any

class MetaDataItem(BaseModel):
    id: Optional[int] = None
    key: str
    value: Any

class LineItem(BaseModel):
    id: int
    name: str
    product_id: int
    variation_id: Optional[int] = None
    quantity: int
    sku: Optional[str] = None
    meta_data: List[MetaDataItem] = []

class WooCommerceOrderWebhook(BaseModel):
    id: int
    status: str
    date_created: str
    line_items: List[LineItem]
    # Pode adicionar mais campos se precisar (ex: billing, shipping, total, etc.)