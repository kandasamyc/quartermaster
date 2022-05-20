from enum import unique

from sqlalchemy.orm import relationship
from sqlalchemy.sql import exists, select
from sqlalchemy.sql.schema import Column, ForeignKey, Table
from sqlalchemy.sql.sqltypes import Integer, String

from init import Q_, Base


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
        self.stock = (Q_(self.stock, self.unit) + Q_(n, u)).to(self.unit).magnitude

    def decrement(self, n, u):
        result = (Q_(self.stock, self.unit) - Q_(n, u)).to(self.unit).magnitude
        if result >= 0:
            self.stock = result

    def __repr__(self) -> str:
        return f"Material(id={self.id!r}, name={self.name!r}, stock={self.stock!r}, unit={self.unit!r})"


class Item(Base):
    __tablename__ = "item"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    materials = relationship("Association")

    def add_material(self, mat, quant, unit, session=None):
        a = Association(quantity=quant, unit=unit)
        a.material = mat
        self.materials.append(a)
        if session:
            session.add(a)
        return a

    @staticmethod
    def create_item(item_name, materials, session):
        item = Item(name=item_name)
        session.add(item)
        for name, info in materials.items():
            mat = session.execute(select(Material).where(Material.name == name)).first()
            if mat is None:
                mat = Material(name=name)
                session.add(mat)
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
