from pydantic import BaseModel, ConfigDict

_DBConfig = ConfigDict(
    str_strip_whitespace=True,
    populate_by_name=True,
    extra="ignore",
)
_BaseConfig = ConfigDict(
    str_strip_whitespace=True,
    populate_by_name=True,
    extra="ignore",
)


class ConfigModels:
    class EmailPartnerBaseConfig(BaseModel):
        model_config = _BaseConfig

    class EmailPartnerDBConfig(BaseModel):
        model_config = _DBConfig
