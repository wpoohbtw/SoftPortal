from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool
    is_active: bool = True


class ProjectPublic(BaseModel):
    id: int | None = None
    key: str
    name: str
    path: str
    description: str
    is_active: bool = True
    can_access: bool | None = None


class SessionResponse(BaseModel):
    user: UserPublic
    projects: list[ProjectPublic]


class OkResponse(BaseModel):
    ok: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=256)
