from models import Association, Material, Item, Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from init import engine, Base


Base.metadata.create_all(engine)

with Session(engine) as session:
    Material.create("flour", 0.5, "cups", session)
    Material.create("egg", 4, "", session)
    Item.create("pancake", {"flour": (0.5, "cup"), "egg": (1, "")}, session)
    session.commit()

with Session(engine) as session:
    p = session.scalar(select(Item).where(Item.name == "pancake"))
    print([i.material for i in p.materials])

    print(p.produceable())
    print(p.materials_needed(1))
