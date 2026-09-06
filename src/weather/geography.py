from __future__ import annotations

from .models import Location


def _loc(id: str, name: str, district: str | None, kind: str, lat: float, lon: float, elev: float) -> Location:
    return Location(id=id, name=name, district=district, kind=kind, latitude=lat, longitude=lon, elevation_m=elev)


# Coordinates are intentionally explicit and reviewable. They are catalogue anchors, not claims of
# station observations. Add a station/observation source before treating a point as measured weather.
LOCATIONS: tuple[Location, ...] = (
    # District anchors
    _loc("srinagar", "Srinagar", "Srinagar", "district", 34.0837, 74.7973, 1585),
    _loc("anantnag", "Anantnag", "Anantnag", "district", 33.7311, 75.1487, 1600),
    _loc("bandipora", "Bandipora", "Bandipora", "district", 34.4170, 74.6430, 1558),
    _loc("baramulla", "Baramulla", "Baramulla", "district", 34.2090, 74.3420, 1593),
    _loc("budgam", "Budgam", "Budgam", "district", 34.0167, 74.7167, 1610),
    _loc("ganderbal", "Ganderbal", "Ganderbal", "district", 34.2167, 74.7833, 1950),
    _loc("kulgam", "Kulgam", "Kulgam", "district", 33.6440, 75.0190, 1739),
    _loc("kupwara", "Kupwara", "Kupwara", "district", 34.5260, 74.2570, 1589),
    _loc("pulwama", "Pulwama", "Pulwama", "district", 33.8740, 74.8990, 1630),
    _loc("shopian", "Shopian", "Shopian", "district", 33.7167, 74.8333, 2057),

    # Major towns / valley locations
    _loc("pampore", "Pampore", "Pulwama", "town", 34.0167, 74.9333, 1574),
    _loc("awantipora", "Awantipora", "Pulwama", "town", 33.9270, 75.0170, 1585),
    _loc("bijbehara", "Bijbehara", "Anantnag", "town", 33.7930, 75.1010, 1590),
    _loc("kokernag", "Kokernag", "Anantnag", "town", 33.5890, 75.3410, 2000),
    _loc("achabal", "Achabal", "Anantnag", "town", 33.6870, 75.2280, 1677),
    _loc("sopore", "Sopore", "Baramulla", "town", 34.3000, 74.4667, 1570),
    _loc("tangmarg", "Tangmarg", "Baramulla", "town", 34.0500, 74.3833, 1950),
    _loc("handwara", "Handwara", "Kupwara", "town", 34.3980, 74.2810, 1580),
    _loc("lolab", "Lolab", "Kupwara", "town", 34.4150, 74.3500, 1650),
    _loc("chadoora", "Chadoora", "Budgam", "town", 34.0270, 74.8000, 1590),

    # Hill stations / high-altitude destinations
    _loc("gulmarg", "Gulmarg", "Baramulla", "hill_station", 34.0484, 74.3805, 2650),
    _loc("pahalgam", "Pahalgam", "Anantnag", "hill_station", 34.0167, 75.3150, 2192),
    _loc("sonamarg", "Sonamarg", "Ganderbal", "hill_station", 34.3031, 75.2936, 2730),
    _loc("gurez", "Gurez", "Bandipora", "hill_station", 34.6280, 74.8300, 2400),
    _loc("aru", "Aru", "Anantnag", "hill_station", 34.0890, 75.3280, 2414),
    _loc("doodhpathri", "Doodhpathri", "Budgam", "hill_station", 33.8400, 75.2100, 2730),
    _loc("yusmarg", "Yusmarg", "Budgam", "hill_station", 33.8330, 74.6700, 2390),
    _loc("aharb al", "Aharbal", "Kulgam", "hill_station", 33.5860, 74.7680, 2266),
    _loc("sinthan_top", "Sinthan Top", "Kulgam", "mountain", 33.5550, 75.3900, 3748),
    _loc("zojila", "Zoji La", "Ganderbal", "pass", 34.2780, 75.4200, 3528),
)

BY_ID = {x.id: x for x in LOCATIONS}
DISTRICTS = tuple(x for x in LOCATIONS if x.kind == "district")
HILL_STATIONS = tuple(x for x in LOCATIONS if x.kind in {"hill_station", "mountain", "pass"})


def get_location(name_or_id: str) -> Location:
    key = name_or_id.strip().lower().replace(" ", "_")
    if key in BY_ID:
        return BY_ID[key]
    for location in LOCATIONS:
        if location.name.lower() == name_or_id.strip().lower():
            return location
    raise KeyError(f"Unknown location: {name_or_id}")
