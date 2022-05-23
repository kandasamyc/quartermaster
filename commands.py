import click
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.orm import Session
from models import Material, Item
from init import engine, Q_, console
from validators import (
    validate_item_arg,
    validate_item_exists,
    validate_item_name,
    validate_material_arg,
    validate_material_exists,
    validate_material_name,
    validate_unit,
)


@click.group()
def cli():
    """A simple CLI to manage your inventory of items and materials"""
    pass


@click.group()
def modify():
    """Modify a property of a material or item"""
    pass


@click.group()
def create():
    """Create a material or item"""
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

    group = Table.grid(expand=True)

    group.add_column()
    group.add_column()
    group.add_row(materials, items)

    console.print(group)


@click.command("mat")
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_name)
@click.argument("stock", type=click.UNPROCESSED, callback=validate_unit)
@click.option("-c", "--category")
@click.option("-l", "--location")
def create_material(name, stock, category, location):
    """Create a material"""
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
    """Create an item"""
    with Session(engine) as session:
        Item.create(item_name=name, materials=mats, session=session, category=category)


@click.command()
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("quantity", type=click.UNPROCESSED, callback=validate_unit)
def replenish(name, quantity):
    """Increase the stock of a material"""
    with Session(engine) as session:
        Material.get(name, session).increment(quantity[0], quantity[1])
        session.commit()


@click.command()
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("quantity", type=click.UNPROCESSED, callback=validate_unit)
def consume(name, quantity):
    """Decrease the stock of a material"""
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
    """Decrease the stock of the material by the amount required to produce the given amount of an item"""
    with Session(engine) as session:
        try:
            Item.get(name, session).produce(amount)
            session.commit()
        except StockRequiredException:
            raise click.BadParameter(f"Stock is required to produce this item")


@click.command()
@click.argument("items", nargs=-1, type=click.UNPROCESSED, callback=validate_item_arg)
def provision(items):
    """Display the quantity of materials needed to produce the given amount of each item"""

    def merge_dicts(dict_list):
        return functools.reduce(
            lambda d1, d2: {k: d1.get(k, 0) + d2.get(k, 0) for k in set(d1) | set(d2)},
            dict_list,
        )

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


@click.command("mat")
@click.argument("name", type=click.UNPROCESSED, callback=validate_material_exists)
@click.argument("prop", type=click.Choice(["location", "category"]))
@click.argument("new_value")
def modify_material(name, prop, new_value):
    """Modify a materials location or category"""
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
    "Modify an item's category"
    with Session(engine) as session:
        item = Item.get(name, session)
        item.category = new_value
        session.commit()
