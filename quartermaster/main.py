from .commands import (
    cli,
    consume,
    create,
    create_item,
    create_material,
    list_entries,
    modify,
    modify_item,
    modify_material,
    produce,
    provision,
    replenish,
)
from .init import engine
from .models import Base

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
