import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "replace-with-a-secret-key")
    # Make sure you have installed PyMySQL (or mysqlclient) and update your credentials
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:Abhayhegde%402005@localhost/rebookdb"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
