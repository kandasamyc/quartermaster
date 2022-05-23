import functools
import click
from pint import DimensionalityError
from pint.unit import Unit
from rich.console import Console
from rich.table import Table
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from exceptions import StockRequiredException

from init import Q_, Base, engine, ureg
from models import Association, Base, Item, Material

Base.metadata.create_all(engine)
console = Console()

# with Session(engine) as session:
#    Material.create("flour", 17, "cup", session)
#    Material.create("egg", 33, "items", session)
#    Material.create("cinnamon", 16, "dashes", session)
#    Item.create(
#        "pancake",
#        {"flour": (0.5, "cup"), "egg": (1, "item"), "cinnamon": (1, "pinch")},
#        session,
#    )
#    session.commit()
#
# with Session(engine) as session:
#    p = session.scalar(select(Item).where(Item.name == "pancake"))
#    print([i.material for i in p.materials])
#
#    print(p.produceable())
#    print(p.materials_needed(1))


@click.group()
def cli():
    """A simple CLI to manage your inventory of items and materials"""
    pass


@click.command("list")
def list_entries():
    """List the materials and items currently tracked"""
    materials = Table(title="Materials")

    materials.add_column("ID")
    materials.add_column("Name")
    materials.add_column("Stock")
    materials.add_column("Category")
    materials.add_column("Location")

    with Session(engine) as session:
        for mat in session.scalars(select(Material)):
            materials.add_row(
                str(mat.id),
                mat.name,
                "{:}".format(Q_(mat.stock, mat.unit)).replace("dimensionless", "item"),
                mat.category,
                mat.location,
            )

    # console.print(materials)

    items = Table(title="Items")

    items.add_column("ID")
    items.add_column("Name")
    items.add_column("Category")
    items.add_column("Produceable")

    with Session(engine) as session:
        for item in session.scalars(select(Item)):
            items.add_row(
                str(item.id), item.name, item.category, str(item.produceable())
            )

    # console.print(items)

    group = Table.grid(expand=True)

    group.add_column()
    group.add_column()
    group.add_row(materials, items)

    console.print(group)


@click.group()
def create():
    pass


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


@click.command("mat")
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_name)
@click.argument("stock", type=click.UNPROCESSED, callback=validate_unit)
@click.option("-c", "--category")
@click.option("-l", "--location")
def create_material(name, stock, category, location):
    with Session(engine) as session:
        Material.create(
            name=name, s=stock[0], u=stock[1], c=category, l=location, session=session
        )


@click.command("item")
@click.argument("name", type=click.UNPROCESSED, callback=validate_item_name)
@click.argument(
    "mats", nargs=-1, type=click.UNPROCESSED, callback=validate_material_arg
)
@click.option("-c", "--category")
def create_item(name, mats, category):
    with Session(engine) as session:
        Item.create(item_name=name, materials=mats, session=session, category=category)


@click.command()
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("quantity", type=click.UNPROCESSED, callback=validate_unit)
def replenish(name, quantity):
    with Session(engine) as session:
        Material.get(name, session).increment(quantity[0], quantity[1])
        session.commit()


@click.command()
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("quantity", type=click.UNPROCESSED, callback=validate_unit)
def consume(name, quantity):
    with Session(engine) as session:
        try:
            Material.get(name, session).decrement(quantity[0], quantity[1])
            session.commit()
        except StockRequiredException:
            raise click.BadParameter(
                f"Quantity to decrease cannot be more than current stock"
            )


@click.command()
@click.argument("name", type=click.UNPROCESSED, callback=validate_item_exists)
@click.argument("amount")
def produce(name, amount):
    with Session(engine) as session:
        try:
            Item.get(name, session).produce(amount)
            session.commit()
        except StockRequiredException:
            raise click.BadParameter(f"Stock is required to produce this item")


@click.command()
@click.argument("items", nargs=-1, type=click.UNPROCESSED, callback=validate_item_arg)
def provision(items):
    with Session(engine) as session:
        all_mats = merge_dicts(
            [
                Item.get(name, session).materials_needed(amount)
                for name, amount in items.items()
            ]
        )
        mats = Table(title="Materials Needed")
        mats.add_column("Material")
        mats.add_column("Amount")
        for mat, amount in all_mats.items():
            mats.add_row(
                mat,
                "{:}".format(amount).replace(
                    "dimensionless", "items" if amount.m > 1 else "item"
                ),
            )
        console.print(mats)


@click.group()
def modify():
    pass


@click.command("mat")
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("prop", type=click.Choice(["location", "category"]))
@click.argument("new_value")
def modify_material(name, prop, new_value):
    with Session(engine) as session:
        mat = Material.get(name, session)
        if prop == "location":
            mat.location = new_value
        else:
            mat.category = new_value
        session.commit()


@click.command("item")
@click.argument("name", type=click.UNPROCESSED, callback=validate_item_exists)
@click.argument("new_value")
def modify_item(name, new_value):
    with Session(engine) as session:
        item = Item.get(name, session)
        item.category = new_value
        session.commit()


def merge_dicts(dict_list):
    return functools.reduce(
        lambda d1, d2: {k: d1.get(k, 0) + d2.get(k, 0) for k in set(d1) | set(d2)},
        dict_list,
    )


cli.add_command(list_entries)
create.add_command(create_material)
create.add_command(create_item)
modify.add_command(modify_material)
modify.add_command(modify_item)
cli.add_command(create)
cli.add_command(replenish)
cli.add_command(consume)
cli.add_command(produce)
cli.add_command(provision)
cli.add_command(modify)
