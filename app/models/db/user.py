from app.config import ConfigModels
class Users(ConfigModels.EmailPartnerDBConfig):
    __collection__ = "users"
    