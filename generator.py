"""
generator.py
Generates two STL files (back plate + text) via OpenSCAD CLI,
then packages them into a Bambu-compatible .3mf with AMS extruder assignments.
"""

import os
import struct
import subprocess
import zipfile
from pathlib import Path

# ── OpenSCAD template ────────────────────────────────────────────────────────

SCAD_TEMPLATE = """\
$fn = 100;

name_text  = "{name}";
font_name  = "{font}";
font_size  = 16;
text_h     = 2;
back_h     = 3;
border     = 2;
ring_off   = 0;
part       = "{part}";   // "back" | "text"

if (part == "back") back_with_hole();
if (part == "text") keychain_text();

module back_with_hole() {{
    difference() {{
        back_plate();
        translate([(-3 + ring_off), (font_size / 2), -1])
            cylinder(h = back_h + 2, r = 2);
    }}
}}

module back_plate() {{
    linear_extrude(back_h) offset(r = border) label();
    hull() {{
        translate([(-3 + ring_off), (font_size / 2), 0]) cylinder(h = back_h, r = 4);
        translate([2,               (font_size / 2), 0]) cylinder(h = back_h, r = 4);
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

# ── STL parser ───────────────────────────────────────────────────────────────

def parse_stl(stl_bytes: bytes):
    """Parse binary STL → (vertices list, triangles list)."""
    offset = 80
    n_tris = struct.unpack_from("<I", stl_bytes, offset)[0]
    offset += 4

    vertices = []
    triangles = []
    vmap: dict = {}

    for _ in range(n_tris):
        offset += 12  # skip normal
        tri = []
        for _ in range(3):
            v = struct.unpack_from("<3f", stl_bytes, offset)
            offset += 12
            if v not in vmap:
                vmap[v] = len(vertices)
                vertices.append(v)
            tri.append(vmap[v])
        triangles.append(tri)
        offset += 2  # skip attribute

    return vertices, triangles


# ── 3MF builder ──────────────────────────────────────────────────────────────

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


def _obj_xml(obj_id: int, vertices, triangles) -> str:
    verts = "\n".join(
        f'          <vertex x="{v[0]:.6f}" y="{v[1]:.6f}" z="{v[2]:.6f}"/>'
        for v in vertices
    )
    tris = "\n".join(
        f'          <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>'
        for t in triangles
    )
    return (
        f'    <object id="{obj_id}" type="model">\n'
        f"      <mesh>\n"
        f"        <vertices>\n{verts}\n        </vertices>\n"
        f"        <triangles>\n{tris}\n        </triangles>\n"
        f"      </mesh>\n"
        f"    </object>"
    )


def _model_settings(back_color: str, text_color: str) -> str:
    return f"""\
<?xml version="1.0" encoding="utf-8"?>
<config>
  <object id="1" instances_count="1">
    <metadata key="name"     value="back_plate"/>
    <metadata key="extruder" value="1"/>
  </object>
  <object id="2" instances_count="1">
    <metadata key="name"     value="text_layer"/>
    <metadata key="extruder" value="2"/>
  </object>
</config>"""


def build_3mf(back_stl: bytes, text_stl: bytes,
              back_color: str, text_color: str,
              output_path: str) -> str:
    bv, bt = parse_stl(back_stl)
    tv, tt = parse_stl(text_stl)

    model_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
        "  <resources>\n"
        + _obj_xml(1, bv, bt) + "\n"
        + _obj_xml(2, tv, tt) + "\n"
        "  </resources>\n"
        "  <build>\n"
        '    <item objectid="1"/>\n'
        '    <item objectid="2"/>\n'
        "  </build>\n"
        "</model>"
    )

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("3D/3dmodel.model", model_xml)
        zf.writestr("Metadata/model_settings.config",
                    _model_settings(back_color, text_color))

    return output_path


# ── Public entry point ────────────────────────────────────────────────────────

def _render_stl(scad_text: str, out_stl: Path, timeout: int = 90):
    scad_file = out_stl.with_suffix(".scad")
    scad_file.write_text(scad_text, encoding="utf-8")
    cmd = ["openscad", "-o", str(out_stl), str(scad_file)]
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"OpenSCAD failed:\n{result.stderr.decode(errors='replace')}"
        )


def generate_keychain_3mf(
    name: str,
    font: str,
    back_color: str,
    text_color: str,
    work_dir,
) -> str:
    """
    Returns path to the generated .3mf file.
    Raises RuntimeError if OpenSCAD is unavailable or fails.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c for c in name if c.isalnum() or c in "-_")[:15] or "keychain"

    back_stl = work_dir / f"{safe_name}_back.stl"
    text_stl = work_dir / f"{safe_name}_text.stl"
    out_3mf  = work_dir / f"{safe_name}_keychain.3mf"

    _render_stl(SCAD_TEMPLATE.format(name=name, font=font, part="back"), back_stl)
    _render_stl(SCAD_TEMPLATE.format(name=name, font=font, part="text"), text_stl)

    build_3mf(
        back_stl.read_bytes(),
        text_stl.read_bytes(),
        back_color,
        text_color,
        str(out_3mf),
    )

    return str(out_3mf)
