from enum import unique

from sqlalchemy.orm import relationship
from sqlalchemy.sql import exists, select
from sqlalchemy.sql.schema import Column, ForeignKey, Table
from sqlalchemy.sql.sqltypes import Integer, String
from pint import Unit

from init import Q_, Base, ureg
from exceptions import (
    UndefinedUnitException,
    UndefinedMaterialException,
    StockRequiredException,
    ZeroQuantityException,
)


class Association(Base):
    __tablename__ = "association"
    item_id = Column(ForeignKey("item.id"), primary_key=True)
    material_id = Column(ForeignKey("material.id"), primary_key=True)
    quantity = Column(Integer)
    unit = Column(String)
    material = relationship("Material")

    def __repr__(self) -> str:
        return f"Association(item_id={self.item_id!r}, material_id={self.material_id!r}, quantity={self.quantity!r})"


class Material(Base):
    __tablename__ = "material"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    stock = Column(Integer)
    unit = Column(String)

    def increment(self, n, u):
        if u not in ureg:
            raise UndefinedUnitException(f"{u} is not a defined unit")
        self.stock = (Q_(self.stock, self.unit) + Q_(n, u)).to(self.unit).magnitude

    def decrement(self, n, u):
        if u != "" and u not in ureg:
            raise UndefinedUnitException(f"{u} is not a defined unit")
        result = (Q_(self.stock, self.unit) - Q_(n, u)).to(self.unit).magnitude
        if result >= 0:
            self.stock = result
        else:
            raise StockRequiredException()

    @staticmethod
    def get(name, session):
        return session.execute(select(Material).where(Material.name == name)).first()[0]

    @staticmethod
    def create(name, s, u, session):
        if u != "" and u not in ureg:
            raise UndefinedUnitException(f"{u} is not a defined unit")
        mat = Material(name=name, stock=s, unit=str(ureg.Unit(u)))
        session.add(mat)
        session.commit()

    def __repr__(self) -> str:
        return f"Material(id={self.id!r}, name={self.name!r}, stock={self.stock!r}, unit={self.unit!r})"


class Item(Base):
    __tablename__ = "item"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    materials = relationship("Association")

    def add_material(self, mat, quant, unit, session=None):
        if unit != "" and unit not in ureg:
            raise UndefinedUnitException(f"Unit {unit} is not a defined unit")
        if quant == 0:
            raise ZeroQuantityException(
                f"A quantity of 0 is not allowed for {mat} and {self}"
            )
        a = Association(quantity=quant, unit=str(ureg.Unit(unit)))
        a.material = mat
        self.materials.append(a)
        if session:
            session.add(a)
        return a

    @staticmethod
    def create(item_name, materials, session):
        item = Item(name=item_name)
        session.add(item)
        for name, info in materials.items():
            mat = Material.get(name, session)
            if mat is None:
                raise UndefinedMaterialException(f"{name} is not a defined material")
            item.add_material(mat, info[0], info[1], session)
        session.commit()

    def produceable(self):
        return min(
            [
                (Q_(mat.material.stock, mat.material.unit) / Q_(mat.quantity, mat.unit))
                .to_base_units()
                .magnitude
                for mat in self.materials
            ]
        )

    def consume(self, num):
        for assoc in self.materials:
            assoc.material.decrement(assoc.quantity, assoc.unit)

    def materials_needed(self, n=1):
        needed = {}
        for assoc in self.materials:
            a_needed = (
                Q_(assoc.quantity * n, assoc.unit)
                - Q_(assoc.material.stock, assoc.material.unit)
            ).to(assoc.unit)
            if a_needed.magnitude > 0:
                needed[assoc.material.name] = a_needed
        return needed

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, name={self.name!r})"
