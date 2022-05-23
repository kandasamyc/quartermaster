import click
from pint import DimensionalityError
from sqlalchemy.orm import Session

from .init import Q_, engine, ureg
from .models import Item, Material


def validate_material_name(ctx, param, value):
    with Session(engine) as session:
        if Material.get(value, session) is not None:
            raise click.BadParameter(f"Material cannot already exist")
        else:
            return value


def validate_item_name(ctx, param, value):
    with Session(engine) as session:
        if Item.get(value, session) is not None:
            raise click.BadParameter(f"Item cannot already exist")
        else:
            return value


def validate_unit(ctx, param, value):
    if isinstance(value, tuple):
        return value

    try:
        quantity, _, unit = value.partition("x")
        if unit != "" and unit not in ureg:
            raise click.BadParameter(f"{unit} is not a valid unit")
        return int(quantity), unit
    except ValueError:
        raise click.BadParameter("format must be QxU")


def validate_material_arg(ctx, param, value):
    if isinstance(value, dict) and all(
        [isinstance(val, tuple) for val in value.values()]
    ):
        return value

    processed = {}
    with Session(engine) as session:
        try:
            for val in value:
                mat, _, quantity = val.partition("=")
                material_obj = Material.get(mat, session)
                if material_obj is None:
                    raise click.BadParameter(f"{mat} is not an existing material")
                magnitude, _, unit = quantity.partition("x")
                if unit != "" and unit not in ureg:
                    raise click.BadParameter(f"{unit} is not a valid unit")
                try:
                    Q_(1, material_obj.unit).to(unit)
                except DimensionalityError:
                    raise click.BadParameter(
                        f"{mat} must have a unit that is convertable to it's defined unit of {material_obj.unit}"
                    )
                processed[mat] = (magnitude, unit)
        except ValueError:
            raise click.BadParameter("Format must be N=QxU")
    return processed


def validate_item_arg(ctx, param, value):
    if isinstance(value, dict):
        return value

    processed = {}
    with Session(engine) as session:
        try:
            for val in value:
                item, _, amount = val.partition("=")
                item_obj = Item.get(item, session)
                if item_obj is None:
                    raise click.BadParameter(f"{item} is not an existing item")
                processed[item] = int(amount)
        except ValueError:
            raise click.BadParameter("Format must be I=A")
    return processed


def validate_material_exists(ctx, param, value):
    with Session(engine) as session:
        if Material.get(value, session) is None:
            raise click.BadParameter(f"Material does not exist")
        else:
            return value


def validate_item_exists(ctx, param, value):
    with Session(engine) as session:
        if Item.get(value, session) is None:
            raise click.BadParameter(f"Item does not exist")
        else:
            return value
