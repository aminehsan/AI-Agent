from pydantic import BaseModel, Field


class EnvironmentVariable(BaseModel):
    name: str = Field(description="Environment-variable name for this process.")
    value: str = Field(description="Complete environment-variable value.")
