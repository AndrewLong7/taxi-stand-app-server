from enum import IntFlag


class TaxiStandType(IntFlag):
    URBAN = 1
    CROSS_HARBOUR = 1 << 1
    NT = 1 << 2
    LANTAU = 1 << 3
    ALL = URBAN | CROSS_HARBOUR | NT | LANTAU
