from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    status: str 
    environment: str
    database: str
    cost_centers: int