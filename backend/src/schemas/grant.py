from pydantic import BaseModel, Field
class GrantInput(BaseModel):
    user_id: int
    team: str = Field(min_length=1, max_length=40)
