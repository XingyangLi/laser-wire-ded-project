import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread
V="/workspace/validation/annotated/"; S="/workspace/laser_wire_ded_viz/val3mm_fe_ni_defocus/"
out=S+"comparison/val3mm_defocus_vs_experiment.png"
plt.rcParams.update({"text.color":"#ddd","axes.edgecolor":"#555"})
fig=plt.figure(figsize=(16,13),facecolor="#16161a")
fig.suptitle("Laser wire DED validation: experiment vs sim 'val3mm_fe_ni_defocus' (600 W, 2.67 mm/s, WFS 18.2 mm/s, focus -1.5 mm, A_wire 0.25 / A_sub 0.35, 3 mm track)",
             color="#f5c542",fontsize=13,x=0.01,ha="left",y=0.985)
gs=fig.add_gridspec(3,2,height_ratios=[1,1,0.9],hspace=0.12,wspace=0.04,left=0.01,right=0.99,top=0.95,bottom=0.01)
panels=[(V+"annot2_f_0021.png","Exp X-ray: H = 1.32 ± 0.20 mm, pool L = 3.33 mm, pen ~0.08 mm (guide 0.25-0.45); tip in pool, no ball"),
        (S+"latest_section_long.png","Sim t = 1.12 s: tip in pool, no ball; plateau H ~0.85 mm, pool L 3.7-3.9 mm, pen 0.08-0.17 mm"),
        (V+"eds_measured.png","Exp EDS long section: H 0.94 mm, unmelted Fe 5-12 %, d ~0.19 mm, along the whole track, inside the bead"),
        (S+"build_long_section.png","Sim build (first ~1 mm): unmelted Fe 11.5 %, 6 pieces d 0.11-0.42 mm, sitting below the plate line")]
for i,(f,t) in enumerate(panels):
    ax=fig.add_subplot(gs[i//2,i%2]); ax.imshow(imread(f)); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(t,fontsize=9.5,color="#ddd",loc="left")
    ax.set_facecolor("#16161a")
ax=fig.add_subplot(gs[2,:]); ax.axis("off")
rows=[("metric","Experiment","Sim (defocus, 3 mm)","verdict"),
("wire tip / balling","tip in pool, no ball","tip in pool (tip z 0.8 mm), no ball","match"),
("bead height [mm]","1.32 ± 0.20 (X-ray); EDS 0.94","~0.85 plateau behind pool (probe 0.70)","too low (~35 %)"),
("bead area [mm²]","~2.3-2.4 (bead-vol. match)","0.9-1.0 at probe; ~1.5 wire metal per mm of track","feed under-delivered"),
("delivered wire area [mm²]","0.353 nominal (5 x 0.3 mm)","~0.20 effective (from metal-volume balance)","~56 % of nominal"),
("penetration [mm]","0.08 ± 0.03 (auto); guide 0.25-0.45","0.085 avg last 20 %; 0.17 latest","OK (low end)"),
("pool length [mm]","3.33 ± 0.18","3.69 avg last 20 %; 3.90 latest","~11-17 % long"),
("unmelted Fe (x > 1.5 mm)","5-12 % area; d ~0.19 mm","11.5 % of deposited Fe; 6 pieces, median ~0.21 mm","amount and size match"),
("unmelted Fe location","along whole track, mid/upper bead","keeps forming after t ~0.45 s, but below the plate line","depth wrong"),
("unmelted Ni","none visible (Ni map: only Fe islands)","~12 % of deposited Ni, 4 pieces","too much")]
tab=ax.table(cellText=rows,loc="upper left",cellLoc="left",colWidths=[0.16,0.26,0.35,0.2])
tab.auto_set_font_size(False); tab.set_fontsize(10); tab.scale(1,1.55)
for (r,c),cell in tab.get_celld().items():
    cell.set_edgecolor("#333"); cell.set_facecolor("#1e1e24" if r else "#2a2a33")
    cell.get_text().set_color("#f5c542" if r==0 else ("#9fe39f" if c==3 and rows[r][3] in("match","OK (low end)","amount and size match") else ("#ff9f80" if c==3 else "#ddd")))
fig.savefig(out,dpi=110,facecolor=fig.get_facecolor()); print(out)
