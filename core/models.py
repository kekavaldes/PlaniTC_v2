from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExploracionAdq:
    id: str
    orden: int
    tipo: str = "adquisicion"
    nombre: str = "SIN CONTRASTE"
    tipo_exp: str | None = None
    doble_muestreo: str | None = None
    voz_adq: str | None = None
    mod_corriente: str | None = None
    kvp: str | int | None = None
    mas_val: str | int | None = None
    ind_cal: str | None = None
    ind_ruido: str | None = None
    rango_ma: str | None = None
    conf_det: str | None = None
    sfov: str | None = None
    grosor_prosp: str | None = None
    pitch: str | None = None
    rot_tubo: str | None = None
    retardo: str | None = None
    inicio_ref: str | None = None
    ini_mm: int = 0
    fin_ref: str | None = None
    fin_mm: int = 400
    topo1_inicio_ref: str | None = None
    topo1_ini_mm: int = 0
    topo1_fin_ref: str | None = None
    topo1_fin_mm: int = 400
    topo2_inicio_ref: str | None = None
    topo2_ini_mm: int = 0
    topo2_fin_ref: str | None = None
    topo2_fin_mm: int = 400
    periodo_bolus: str = "1 sg"
    n_imagenes_bolus: int = 15
    posicion_corte: str = "BOTON AORTICO"
    umbral_disparo: str = ""
    kvp_bolus: int = 100
    mas_bolus: int = 20
    store: dict[str, Any] = field(default_factory=dict)
