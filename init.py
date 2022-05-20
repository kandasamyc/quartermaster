from pint import UnitRegistry
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
engine = create_engine("sqlite:///test.db", future=True, echo=True)

ureg = UnitRegistry()
Q_ = ureg.Quantity
