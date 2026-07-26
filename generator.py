"""
generator.py
Generates two STL files (back plate + text) via OpenSCAD CLI,
then packages them into a Bambu-compatible .3mf with AMS extruder assignments.
"""

import struct, subprocess, zipfile, resource
from pathlib import Path

# Максимум памяти для одного процесса OpenSCAD (МБ).
# Если он превысит лимит — упадёт сам, а не утянет весь контейнер.
OPENSCAD_MEM_LIMIT_MB = 300


def _limit_memory():
    """Вызывается в дочернем процессе перед запуском OpenSCAD."""
    try:
        limit = OPENSCAD_MEM_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except Exception:
        pass


# Имя шрифта в боте -> имя семейства, которое понимает OpenSCAD/fontconfig
FONT_FAMILY = {
    "Pacifico":       "Pacifico",
    "Lobster":        "Lobster",
    "Russo One":      "Russo One",
    "Yeseva One":     "Yeseva One",
    "Neucha":         "Neucha",
    "Play":           "Play:style=Bold",
    "Comfortaa":      "Comfortaa:style=Bold",
    "Ruslan Display": "Ruslan Display",
    "Cookie":         "Cookie",
    "Courgette":      "Courgette",
    "Bangers":        "Bangers",
    "Satisfy":        "Satisfy",
    "Righteous":      "Righteous",
    "Dancing Script": "Dancing Script:style=Bold",
}

# ── OpenSCAD template ─────────────────────────────────────────────────────────

SCAD_TEMPLATE = """\
$fn = 24;

name_text  = "{name}";
font_name  = "{font}";
font_size  = {font_size};
text_h     = {text_height};
back_h     = {back_height};
border     = 2;
ring_r     = {ring_radius};
ring_off   = 0;
part       = "{part}";

if (part == "back") back_with_hole();
if (part == "text") keychain_text();

module back_with_hole() {{
    difference() {{
        back_plate();
        translate([(-ring_r*1.5 + ring_off), (font_size / 2), -1])
            cylinder(h = back_h + 2, r = ring_r);
    }}
}}

module back_plate() {{
    linear_extrude(back_h) offset(r = border) label();
    hull() {{
        translate([(-ring_r*1.5 + ring_off), (font_size / 2), 0]) cylinder(h = back_h, r = ring_r + 2);
        translate([2,                          (font_size / 2), 0]) cylinder(h = back_h, r = ring_r + 2);
    }}
}}

module keychain_text() {{
    translate([0, 0, back_h])
        linear_extrude(text_h) label();
}}

module label() {{
    text(name_text, size = font_size, font = font_name);
}}
"""

# ── STL parser ────────────────────────────────────────────────────────────────

def _parse_stl_binary(b: bytes):
    """Двоичный STL."""
    offset = 80
    n_tris = struct.unpack_from("<I", b, offset)[0]
    offset += 4

    expected = 84 + n_tris * 50
    if len(b) < expected:
        raise ValueError(
            f"Повреждённый binary STL: заявлено {n_tris} треугольников "
            f"({expected} байт), фактически {len(b)} байт"
        )

    vertices, triangles, vmap = [], [], {}
    for _ in range(n_tris):
        offset += 12  # нормаль пропускаем
        tri = []
        for _ in range(3):
            v = struct.unpack_from("<3f", b, offset); offset += 12
            if v not in vmap:
                vmap[v] = len(vertices); vertices.append(v)
            tri.append(vmap[v])
        triangles.append(tri)
        offset += 2  # атрибут
    return vertices, triangles


def _parse_stl_ascii(b: bytes):
    """Текстовый STL — именно его OpenSCAD выдаёт по умолчанию."""
    text = b.decode("utf-8", errors="replace")
    vertices, triangles, vmap = [], [], {}
    current = []

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("vertex"):
            if line.startswith("endloop") and len(current) == 3:
                triangles.append(current)
                current = []
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            v = (float(parts[1]), float(parts[2]), float(parts[3]))
        except ValueError:
            continue
        if v not in vmap:
            vmap[v] = len(vertices); vertices.append(v)
        current.append(vmap[v])
        if len(current) == 3:
            triangles.append(current)
            current = []

    if not triangles:
        raise ValueError("ASCII STL не содержит треугольников (пустая модель)")
    return vertices, triangles


def parse_stl(stl_bytes: bytes):
    """Автоматически определяет формат STL и разбирает его."""
    if not stl_bytes or len(stl_bytes) < 15:
        raise ValueError(f"STL слишком мал: {len(stl_bytes)} байт")

    head = stl_bytes[:80].lstrip()

    # ASCII STL начинается со слова "solid" и содержит "facet"
    looks_ascii = head[:5].lower() == b"solid" and b"facet" in stl_bytes[:2000].lower()

    if looks_ascii:
        return _parse_stl_ascii(stl_bytes)

    try:
        return _parse_stl_binary(stl_bytes)
    except Exception:
        # На всякий случай пробуем как текст
        return _parse_stl_ascii(stl_bytes)


# ── 3MF builder ───────────────────────────────────────────────────────────────

_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels"   ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model"  ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Default Extension="config" ContentType="application/xml"/>
</Types>"""

_RELS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0"
    Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""

def _obj_xml(obj_id, vertices, triangles):
    verts = "\n".join(f'          <vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>' for v in vertices)
    tris  = "\n".join(f'          <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>' for t in triangles)
    return (f'    <object id="{obj_id}" type="model">\n'
            f"      <mesh>\n"
            f"        <vertices>\n{verts}\n        </vertices>\n"
            f"        <triangles>\n{tris}\n        </triangles>\n"
            f"      </mesh>\n    </object>")

def build_3mf(back_stl, text_stl, back_color, text_color, output_path):
    bv, bt = parse_stl(back_stl)
    tv, tt = parse_stl(text_stl)
    model_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
        "  <resources>\n"
        + _obj_xml(1, bv, bt) + "\n"
        + _obj_xml(2, tv, tt) + "\n"
        "  </resources>\n"
        "  <build>\n"
        '    <item objectid="1"/>\n    <item objectid="2"/>\n'
        "  </build>\n</model>"
    )
    model_settings = (
        '<?xml version="1.0" encoding="utf-8"?>\n<config>\n'
        '  <object id="1" instances_count="1">\n'
        '    <metadata key="name" value="back_plate"/>\n'
        '    <metadata key="extruder" value="1"/>\n  </object>\n'
        '  <object id="2" instances_count="1">\n'
        '    <metadata key="name" value="text_layer"/>\n'
        '    <metadata key="extruder" value="2"/>\n  </object>\n</config>'
    )
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("3D/3dmodel.model", model_xml)
        zf.writestr("Metadata/model_settings.config", model_settings)
    return output_path

# ── Public API ────────────────────────────────────────────────────────────────

def _render_stl(scad_text, out_stl, timeout=60):
    scad_file = Path(str(out_stl).replace(".stl", ".scad"))
    scad_file.write_text(scad_text, encoding="utf-8")
    # Пробуем binary STL; если версия OpenSCAD не знает флаг — обычный вызов
    cmd = ["xvfb-run", "--auto-servernum", "openscad", "--render",
           "--export-format", "binstl", "-o", str(out_stl), str(scad_file)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout,
                            preexec_fn=_limit_memory)

    if result.returncode != 0 and b"export-format" in result.stderr.lower():
        cmd = ["xvfb-run", "--auto-servernum", "openscad", "--render",
               "-o", str(out_stl), str(scad_file)]
        result = subprocess.run(cmd, capture_output=True, timeout=timeout,
                            preexec_fn=_limit_memory)

    stderr = result.stderr.decode(errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"OpenSCAD код {result.returncode}: {stderr[-500:]}")

    out_path = Path(out_stl)
    if not out_path.exists():
        raise RuntimeError(f"STL не создан. OpenSCAD: {stderr[-500:]}")

    size = out_path.stat().st_size
    if size < 200:
        raise RuntimeError(
            "Пустая модель — шрифт не содержит нужных символов "
            f"(STL {size} байт). OpenSCAD: {stderr[-300:]}"
        )

def generate_keychain_3mf(
    name: str,
    font: str,
    back_color: str,
    text_color: str,
    work_dir,
    font_size: float = 16,
    text_height: float = 2.0,
    back_height: float = 3.0,
    ring_radius: float = 2.0,
) -> str:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:15] or "keychain"
    back_stl = work_dir / f"{safe}_back.stl"
    text_stl = work_dir / f"{safe}_text.stl"
    out_3mf  = work_dir / f"{safe}_keychain.3mf"

    family = FONT_FAMILY.get(font, font)
    params = dict(name=name, font=family, font_size=font_size,
                  text_height=text_height, back_height=back_height,
                  ring_radius=ring_radius)

    _render_stl(SCAD_TEMPLATE.format(**params, part="back"), back_stl)
    _render_stl(SCAD_TEMPLATE.format(**params, part="text"), text_stl)

    build_3mf(back_stl.read_bytes(), text_stl.read_bytes(),
              back_color, text_color, str(out_3mf))
    return str(out_3mf)

# ── Шаблон для SVG-логотипов (эмблемы авто и логотипы клиентов) ─────────────

SVG_TEMPLATE = """\
$fn = 24;

svg_file  = "{svg_path}";
logo_size = {logo_size};
text_h    = {text_height};
back_h    = {back_height};
border    = {border};
ring_r    = {ring_radius};
part      = "{part}";

if (part == "back") back_with_hole();
if (part == "text") logo_top();

module shape() {{
    resize([0, logo_size, 0], auto = true)
        import(svg_file, center = true);
}}

// Кольцо крепится сверху — работает для логотипов любой ширины
ring_y = logo_size / 2 + border + ring_r + 1;

module back_plate() {{
    linear_extrude(back_h) offset(r = border) shape();
    hull() {{
        translate([0, ring_y, 0])           cylinder(h = back_h, r = ring_r + 2);
        translate([0, ring_y - ring_r - 4, 0]) cylinder(h = back_h, r = ring_r + 2);
    }}
}}

module back_with_hole() {{
    difference() {{
        back_plate();
        translate([0, ring_y, -1]) cylinder(h = back_h + 2, r = ring_r);
    }}
}}

module logo_top() {{
    translate([0, 0, back_h]) linear_extrude(text_h) shape();
}}
"""


def generate_logo_3mf(
    svg_path: str,
    back_color: str,
    text_color: str,
    work_dir,
    name: str = "logo",
    logo_size: float = 30.0,
    text_height: float = 2.0,
    back_height: float = 3.0,
    ring_radius: float = 2.0,
    border: float = 2.0,
) -> str:
    """Собирает .3mf из SVG-контура — обводка такая же, как у именных брелоков."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if not Path(svg_path).exists():
        raise RuntimeError(f"SVG не найден: {svg_path}")

    safe = "".join(c for c in name if c.isalnum() or c in "-_")[:20] or "logo"
    back_stl = work_dir / f"{safe}_back.stl"
    text_stl = work_dir / f"{safe}_top.stl"
    out_3mf  = work_dir / f"{safe}_keychain.3mf"

    params = dict(
        svg_path=str(svg_path), logo_size=logo_size,
        text_height=text_height, back_height=back_height,
        border=border, ring_radius=ring_radius,
    )

    _render_stl(SVG_TEMPLATE.format(**params, part="back"), back_stl)
    _render_stl(SVG_TEMPLATE.format(**params, part="text"), text_stl)

    build_3mf(back_stl.read_bytes(), text_stl.read_bytes(),
              back_color, text_color, str(out_3mf))
    return str(out_3mf)
