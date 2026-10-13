from pydantic import BaseModel, ConfigDict


class OrmOut(BaseModel):
    """Βάση για κάθε *Out: διαβάζει τις τιμές κατευθείαν από αντικείμενο SQLAlchemy."""
    model_config = ConfigDict(from_attributes=True)
