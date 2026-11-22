import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-taskflow")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", 
                                        "sqlite:///taskflow.db",
                                        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = True