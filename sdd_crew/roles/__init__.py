"""Los seis validadores, en el orden en que se ejecutan."""
from sdd_crew.roles import architect, backend, chapter, frontend, security, testing
from sdd_crew.roles.base import Rol

ROLES: tuple[Rol, ...] = tuple(m.ROL for m in (architect, backend, frontend, testing, security, chapter))
POR_CLAVE: dict[str, Rol] = {r.clave: r for r in ROLES}
