from typing import Optional
from pydantic import BaseModel, Field, validator


class EmailInput(BaseModel):
    """Schema for input email data."""
    id: str
    subject: str
    body: str
    sender_email: Optional[str] = None
    to_emails: Optional[str] = None
    cc_emails: Optional[str] = None


class ShipmentExtraction(BaseModel):
    """Schema for extracted shipment details."""
    id: str
    product_line: Optional[str] = Field(
        None,
        description="Either 'pl_sea_import_lcl' or 'pl_sea_export_lcl'"
    )
    origin_port_code: Optional[str] = Field(
        None,
        description="5-letter UN/LOCODE for origin port"
    )
    origin_port_name: Optional[str] = Field(
        None,
        description="Canonical port name from reference"
    )
    destination_port_code: Optional[str] = Field(
        None,
        description="5-letter UN/LOCODE for destination port"
    )
    destination_port_name: Optional[str] = Field(
        None,
        description="Canonical port name from reference"
    )
    incoterm: Optional[str] = Field(
        None,
        description="Shipping incoterm (FOB, CIF, etc.)"
    )
    cargo_weight_kg: Optional[float] = Field(
        None,
        description="Cargo weight in kilograms"
    )
    cargo_cbm: Optional[float] = Field(
        None,
        description="Cargo volume in cubic meters"
    )
    is_dangerous: bool = Field(
        False,
        description="Whether cargo contains dangerous goods"
    )

    @validator('cargo_weight_kg', 'cargo_cbm')
    def round_to_two_decimals(cls, v):
        """Round numeric fields to 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v

    @validator('cargo_weight_kg', 'cargo_cbm')
    def validate_positive_or_null(cls, v):
        """Ensure weight and CBM are positive or null."""
        if v is not None and v < 0:
            raise ValueError("Weight and CBM must be positive")
        return v

    @validator('incoterm')
    def normalize_incoterm(cls, v):
        """Normalize incoterm to uppercase."""
        if v is not None:
            return v.upper()
        return v


class PortReference(BaseModel):
    """Schema for port code reference data."""
    code: str
    name: str