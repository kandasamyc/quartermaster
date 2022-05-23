from pint import UnitRegistry
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine("sqlite:///test.db", future=True)

ureg = UnitRegistry(
    preprocessors=[
        lambda x: x.replace("items", "dimensionless"),
        lambda x: x.replace("item", "dimensionless"),
    ],
    fmt_locale="en",
)
ureg.define("pinch = tbsp / 16 = pch = pinches")
ureg.define("dash = tbsp / 8 = dsh = dashes")
Q_ = ureg.Quantity
