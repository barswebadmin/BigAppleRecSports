from pydantic import ConfigDict


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


BaseModelConfig = ConfigDict(
    alias_generator=snake_to_camel,
    populate_by_name=True,
)


