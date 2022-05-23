from pint import UnitRegistry
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from rich.console import Console
import os

db_path = f"{os.getenv('HOME')}/.quartermaster"
if not os.path.exists(db_path):
    os.makedirs(db_path)
if not os.path.exists(f"{db_path}/data.db"):
    with open(f"{db_path}/data.db", "w"):
        pass

Base = declarative_base()
engine = create_engine(f"sqlite:///{db_path}/data.db", future=True)

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

console = Console()
