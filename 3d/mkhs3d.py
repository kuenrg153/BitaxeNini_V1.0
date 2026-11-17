"""Write simple box-built STEP (AP214) models for the BitaxeNini heatsinks, in KiCad model coordinates for the HS1
footprint (origin = HS1 centre on the F.Cu surface; +X right, +Y = up on screen (= -board y), +Z = away from F side;
the B side surface is at z = -BOARD).  usage: mkhs3d.py OUTDIR"""
import os, sys
OUT = sys.argv[1]
BOARD = 1.6            # board thickness
ASIC_H = 1.0           # KF1950 seated height above B surface (assumed; no 3D model in the library)
HOLES = [(-10.0, 0.0), (10.0, 0.0)]; HOLE = 3.4   # M3 clearance, modelled as square cut-outs

def cut(box, holes=HOLES, s=HOLE):
    """split an axis-aligned box (x0,y0,z0,x1,y1,z1) around square holes (through Z)"""
    out = [box]
    for hx, hy in holes:
        hx0, hx1, hy0, hy1 = hx - s / 2, hx + s / 2, hy - s / 2, hy + s / 2
        nxt = []
        for x0, y0, z0, x1, y1, z1 in out:
            if x1 <= hx0 or x0 >= hx1 or y1 <= hy0 or y0 >= hy1: nxt.append((x0, y0, z0, x1, y1, z1)); continue
            if x0 < hx0: nxt.append((x0, y0, z0, hx0, y1, z1))
            if x1 > hx1: nxt.append((hx1, y0, z0, x1, y1, z1))
            mx0, mx1 = max(x0, hx0), min(x1, hx1)
            if y0 < hy0: nxt.append((mx0, y0, z0, mx1, hy0, z1))
            if y1 > hy1: nxt.append((mx0, hy1, z0, mx1, y1, z1))
        out = nxt
    return out

class Step:
    def __init__(s): s.e = []
    def add(s, txt): s.e.append(txt); return f'#{len(s.e)}'
    def pt(s, p): return s.add("CARTESIAN_POINT('',(%s));" % ','.join(f'{v:.6f}' for v in p))
    def dr(s, d): return s.add("DIRECTION('',(%s));" % ','.join(f'{v:.6f}' for v in d))
    def box(s, b):
        x0, y0, z0, x1, y1, z1 = b
        V = {(i, j, k): s.add(f"VERTEX_POINT('',{s.pt((x1 if i else x0, y1 if j else y0, z1 if k else z0))});") for i in (0, 1) for j in (0, 1) for k in (0, 1)}
        P = {key: ((x1 if key[0] else x0), (y1 if key[1] else y0), (z1 if key[2] else z0)) for key in V}
        E = {}
        def edge(a, c):
            k = (min(a, c), max(a, c))
            if k not in E:
                pa, pc = P[k[0]], P[k[1]]; d = [pc[i] - pa[i] for i in range(3)]; L = sum(v * v for v in d) ** 0.5
                line = s.add(f"LINE('',{s.pt(pa)},{s.add(f'VECTOR({chr(39)}{chr(39)},{s.dr([v / L for v in d])},{L:.6f});')});")
                E[k] = s.add(f"EDGE_CURVE('',{V[k[0]]},{V[k[1]]},{line},.T.);")
            return s.add(f"ORIENTED_EDGE('',*,*,{E[k]},{'.T.' if a == k[0] else '.F.'});")
        faces = []
        for axis in range(3):
            for side in (0, 1):
                n = [0, 0, 0]; n[axis] = 1 if side else -1
                o = [a for a in range(3) if a != axis]
                def key(u, v):
                    k = [0, 0, 0]; k[axis] = side; k[o[0]] = u; k[o[1]] = v; return tuple(k)
                loop = [key(0, 0), key(1, 0), key(1, 1), key(0, 1)]
                # orient CCW about the outward normal
                p = [P[k] for k in loop]
                a = [p[1][i] - p[0][i] for i in range(3)]; c = [p[2][i] - p[1][i] for i in range(3)]
                cr = [a[1] * c[2] - a[2] * c[1], a[2] * c[0] - a[0] * c[2], a[0] * c[1] - a[1] * c[0]]
                if sum(cr[i] * n[i] for i in range(3)) < 0: loop.reverse()
                oes = [edge(loop[i], loop[(i + 1) % 4]) for i in range(4)]
                el = s.add(f"EDGE_LOOP('',({','.join(oes)}));")
                fb = s.add(f"FACE_OUTER_BOUND('',{el},.T.);")
                ref = [0, 0, 0]; ref[o[0]] = 1
                ax = s.add(f"AXIS2_PLACEMENT_3D('',{s.pt(P[loop[0]])},{s.dr(n)},{s.dr(ref)});")
                pl = s.add(f"PLANE('',{ax});")
                faces.append(s.add(f"ADVANCED_FACE('',({fb}),{pl},.T.);"))
        sh = s.add(f"CLOSED_SHELL('',({','.join(faces)}));")
        return s.add(f"MANIFOLD_SOLID_BREP('',{sh});")

def write(path, name, boxes, rgb):
    s = Step()
    ctx_app = s.add("APPLICATION_CONTEXT('core data for automotive mechanical design processes');")
    s.add(f"APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,{ctx_app});")
    pctx = s.add(f"PRODUCT_CONTEXT('',{ctx_app},'mechanical');")
    prod = s.add(f"PRODUCT('{name}','{name}','',({pctx}));")
    pdf = s.add(f"PRODUCT_DEFINITION_FORMATION('','',{prod});")
    pdc = s.add(f"PRODUCT_DEFINITION_CONTEXT('part definition',{ctx_app},'design');")
    pd = s.add(f"PRODUCT_DEFINITION('design','',{pdf},{pdc});")
    pds = s.add(f"PRODUCT_DEFINITION_SHAPE('','',{pd});")
    lu = s.add("(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));")
    au = s.add("(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));")
    su = s.add("(NAMED_UNIT(*)SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());")
    unc = s.add(f"UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),{lu},'distance_accuracy_value','confusion accuracy');")
    ctx = s.add(f"(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT(({unc}))GLOBAL_UNIT_ASSIGNED_CONTEXT(({lu},{au},{su}))REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY'));")
    origin = s.add(f"AXIS2_PLACEMENT_3D('',{s.pt((0, 0, 0))},{s.dr((0, 0, 1))},{s.dr((1, 0, 0))});")
    # each entry is either a box (x0,y0,z0,x1,y1,z1) in the default colour, or (box, (r,g,b))
    items = [(b, rgb) if len(b) == 6 and not isinstance(b[0], tuple) else (b[0], b[1]) for b in boxes]
    breps = [s.box(b) for b, _ in items]
    rep = s.add(f"ADVANCED_BREP_SHAPE_REPRESENTATION('{name}',({','.join(breps + [origin])}),{ctx});")
    s.add(f"SHAPE_DEFINITION_REPRESENTATION({pds},{rep});")
    psas = {}
    def style(c):
        if c not in psas:
            col = s.add(f"COLOUR_RGB('',{c[0]:.3f},{c[1]:.3f},{c[2]:.3f});")
            fasc = s.add(f"FILL_AREA_STYLE_COLOUR('',{col});"); fas = s.add(f"FILL_AREA_STYLE('',({fasc}));")
            ssfa = s.add(f"SURFACE_STYLE_FILL_AREA({fas});"); sss = s.add(f"SURFACE_SIDE_STYLE('',({ssfa}));")
            ssu = s.add(f"SURFACE_STYLE_USAGE(.BOTH.,{sss});"); psas[c] = s.add(f"PRESENTATION_STYLE_ASSIGNMENT(({ssu}));")
        return psas[c]
    styled = [s.add(f"STYLED_ITEM('color',({style(c)}),{b});") for b, (_, c) in zip(breps, items)]
    s.add(f"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',({','.join(styled)}),{ctx});")
    hdr = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('BitaxeNini heatsink model'),'2;1');\n"
           f"FILE_NAME('{name}.step','2026-11-17T00:00:00',(''),(''),'mkhs3d.py','mkhs3d.py','');\n"
           "FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));\nENDSEC;\nDATA;\n")
    body = ''.join(f'#{i + 1}={t}\n' for i, t in enumerate(s.e))
    open(path, 'w', encoding='ascii', newline='\n').write(hdr + body + 'ENDSEC;\nEND-ISO-10303-21;\n')
    print(f'{os.path.basename(path)}: {len(boxes)} boxes, {len(s.e)} entities')

ALU = (0.78, 0.79, 0.81)
# --- flat-base heatsink, top (F) side: 60 x 44 footprint, 44 mm tall overall on 0.2 mm thermal tape:
#     5 mm base + 39 mm fins (1.0 thick, 2.5 mm pitch, running along Y like the ridged sink); 2x M3 clearance through all
FT, FB, FH = 0.2, 5.0, 39.0
flat = cut((-30, -22, FT, 30, 22, FT + FB))
x = -30 + 0.75
while x + 1.0 <= 30 + 1e-9:
    flat += cut((x, -22, FT + FB, x + 1.0, 22, FT + FB + FH)); x += 2.5
write(os.path.join(OUT, 'Heatsink_Flat_60x44x44.step'), 'Heatsink_Flat_60x44x44', flat, ALU)
# --- ridged M30 cut-off, bottom (B) side: 3 ridges (8 wide, 2 tall, full 68 length) resting on the ASIC tops,
#     68 x 68 x 3 base, fins 1.0 thick on 2.5 mm pitch, 15 tall, running along Y; M3 clearance through base and fins
zt = -BOARD - ASIC_H                        # ridge contact face (ASIC top)
boxes = []
for rx in (-20, 0, 20): boxes += cut((rx - 4, -34, zt - 2, rx + 4, 34, zt))
zb = zt - 2
boxes += cut((-34, -34, zb - 3, 34, 34, zb))
x = -34 + 0.75
while x + 1.0 <= 34:
    boxes += cut((x, -34, zb - 3 - 15, x + 1.0, 34, zb - 3)); x += 2.5
write(os.path.join(OUT, 'Heatsink_Ridged_M30_68x68.step'), 'Heatsink_Ridged_M30_68x68', boxes, ALU)
# --- 12 x 12 x 5 heatsink under U2 (B side), centred at board (126.5, 78.25) = HS1 offset (-4.5, -40.25 board) -> model y +40.25
cx, cy = 126.5 - 131.0, -(78.25 - 118.5)
u2 = [(cx - 6, cy - 6, -BOARD - 1.0, cx + 6, cy + 6, -BOARD - 0.2)]          # 0.8 mm base on 0.2 mm thermal pad
fx = cx - 6 + 0.5
while fx + 1.0 <= cx + 6 + 1e-9:
    u2.append((fx, cy - 6, -BOARD - 5.2, fx + 1.0, cy + 6, -BOARD - 1.0)); fx += 2.2       # pin/plate fins, 5 mm total
write(os.path.join(OUT, 'Heatsink_U2_12x12x5.step'), 'Heatsink_U2_12x12x5', u2, (0.15, 0.15, 0.17))

# --- KF1950 ASIC (library frame, F side): 8.5 x 8.5 mm body, 1.0 mm seated height (matches ASIC_H), pin-1 dot
#     pad 1 is at local (-3.898, -3.537)  ->  model (-x, +y)
BLK, MARK = (0.10, 0.10, 0.11), (0.85, 0.85, 0.85)
kf = [((-4.25, -4.25, 0.05, 4.25, 4.25, ASIC_H), BLK), ((-3.55, 3.0, ASIC_H, -2.95, 3.6, ASIC_H + 0.02), MARK)]
write(os.path.join(OUT, 'KF1950.step'), 'KF1950', kf, BLK)

# --- 0.91" 128x32 I2C OLED module (SSD1306) on the 1x4 header (library frame, F side; header pin 1 at local (0.2,0),
#     pins along local +y = model -y).  Module PCB 38 x 12 x 1.2 sits at the top of the header pins and runs toward
#     local -x; glass 30 x 11.5 (panel size per MichMich/KiCad-SSD1306_OLED-0.91-128x32), active area 22.38 x 5.58.
PCB_C, GLASS_C, ACT_C = (0.08, 0.25, 0.60), (0.12, 0.12, 0.14), (0.01, 0.01, 0.02)
yc = -3.81                                   # module centre line (model y) = middle of the 4 pins
z0 = 2.54 + 6.0 - 1.2                        # module seated at the END of the header pins (pins 6 mm above the plastic), pin tips flush with the module top
oled = [((-36.0, yc - 6.0, z0, 2.0, yc + 6.0, z0 + 1.2), PCB_C),
        ((-35.5, yc - 5.75, z0 + 1.2, -5.5, yc + 5.75, z0 + 1.2 + 1.4), GLASS_C),
        ((-32.2, yc - 2.79, z0 + 2.6, -9.82, yc + 2.79, z0 + 2.62), ACT_C)]
write(os.path.join(OUT, 'OLED_0.91in_128x32_I2C_Module.step'), 'OLED_0.91in_128x32_I2C_Module', oled, PCB_C)
