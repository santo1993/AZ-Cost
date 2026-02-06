"""
Resource Models.
"""
from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime

class Resource(BaseModel):
    id: str
    name: str
    type: str
    subscription_id: str
    resource_group: str
    location: str
    tags: Dict[str, str] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
    sku: Optional[Dict[str, Any]] = None
    kind: Optional[str] = None
    managed_by: Optional[str] = None
    
    # Enhanced properties
    power_state: Optional[str] = None  # For VMs
    created_time: Optional[datetime] = None
    last_used: Optional[datetime] = None

class ResourceListResponse(BaseModel):
    items: List[Resource]
    total_count: int
    page: int
    page_size: int

class OptimizationIssue(BaseModel):
    id: str
    resource_id: str
    resource_name: str
    resource_type: str
    subscription_id: str
    resource_group: str
    issue_type: str  # Zombie, Orphaned, Oversized, Advisor
    severity: str    # High, Medium, Low
    description: str
    potential_savings: float
    recommendation: str
