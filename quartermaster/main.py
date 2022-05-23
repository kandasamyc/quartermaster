import functools
import click
from pint import DimensionalityError
from pint.unit import Unit
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from .exceptions import StockRequiredException

from .init import Q_, Base, engine, ureg
from .models import Association, Base, Item, Material
from .commands import (
    cli,
    create,
    modify,
    list_entries,
    create_material,
    create_item,
    modify_material,
    modify_item,
    replenish,
    consume,
    produce,
    provision,
)

Base.metadata.create_all(engine)

create.add_command(create_material)
create.add_command(create_item)
modify.add_command(modify_material)
modify.add_command(modify_item)

cli.add_command(create)
cli.add_command(modify)
cli.add_command(list_entries)
cli.add_command(replenish)
cli.add_command(consume)
cli.add_command(produce)
cli.add_command(provision)
